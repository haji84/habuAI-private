package org.habuai.field

import android.content.Context
import android.location.Location
import org.json.JSONObject
import java.io.File
import java.util.UUID

/** Byte-preserving append-only observed events; active state is not an inferred GPS point. */
class TrackingStore(private val context: Context) {
    private val prefs = context.getSharedPreferences("owner_track_state", Context.MODE_PRIVATE)
    private val directory = File(context.filesDir, "private-tracks").apply { mkdirs() }
    fun activeId(): String? = prefs.getString("active_id", null)
    fun latestId(): String? = prefs.getString("latest_id", null)
    fun create(): String {
        activeId()?.let { return it }
        val id = UUID.randomUUID().toString()
        prefs.edit().putString("active_id", id).putString("latest_id", id).commit()
        append(id, JSONObject().put("kind", "start").put("id", id)
            .put("time", System.currentTimeMillis()))
        return id
    }
    fun stop() {
        activeId()?.let { id ->
            append(id, JSONObject().put("kind", "stop").put("time", System.currentTimeMillis()))
            prefs.edit().remove("active_id").commit()
        }
    }
    fun fix(id: String, location: Location) {
        if (activeId() != id) return
        if (!location.hasAccuracy() || !location.latitude.isFinite() || !location.longitude.isFinite() ||
            !location.accuracy.isFinite() || location.accuracy < 0 ||
            location.latitude !in -90.0..90.0 || location.longitude !in -180.0..180.0) return
        val point = JSONObject().put("kind", "fix").put("time", location.time)
            .put("latitude", location.latitude).put("longitude", location.longitude)
            .put("accuracy", location.accuracy.toDouble())
        if (location.hasAltitude() && location.altitude.isFinite()) point.put("altitude", location.altitude)
        append(id, point)
    }
    fun gap(id: String, reason: String) {
        if (activeId() == id) append(id, JSONObject().put("kind", "gap")
            .put("time", System.currentTimeMillis()).put("reason", reason.take(100)))
    }
    fun observation(type: String, species: String, count: Int) {
        val id = activeId() ?: error("探索中ではありません")
        require(type in setOf("capture", "sighting", "roadkill", "other"))
        require(species.isNotBlank() && species.length <= 80 && count in 1..100)
        append(id, JSONObject().put("kind", "event").put("id", UUID.randomUUID().toString())
            .put("type", type).put("species", species).put("count", count)
            .put("owner", "self").put("time", System.currentTimeMillis()))
    }
    fun read(id: String): List<JSONObject> {
        require(id.matches(Regex("[0-9a-f-]{36}"))) { "Invalid session id" }
        val file = File(directory, "$id.ndjson")
        if (!file.exists()) return emptyList()
        return file.readLines(Charsets.UTF_8).filter { it.isNotBlank() }.map { JSONObject(it) }
    }
    private fun append(id: String, value: JSONObject) {
        val f = File(directory, "$id.ndjson")
        // Flush to local storage for each GNSS observation, including with screen locked.
        f.outputStreamAppend().use { stream ->
            stream.write((value.toString() + "\n").toByteArray(Charsets.UTF_8))
            stream.flush()
            stream.fd.sync()
        }
    }
    private fun File.outputStreamAppend() = java.io.FileOutputStream(this, true)
}
