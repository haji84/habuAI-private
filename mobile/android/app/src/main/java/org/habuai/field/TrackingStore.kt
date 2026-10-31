package org.habuai.field

import android.content.Context
import android.location.Location
import org.json.JSONObject
import java.io.File
import java.util.UUID

/** Byte-preserving append-only observed events; active state is not an inferred GPS point. */
class TrackingStore(private val context: Context) {
    companion object {
        // Activity and foreground service use separate TrackingStore instances.
        // Serialize their writes so NDJSON lines cannot interleave.
        private val fileWriteLock = Any()
    }
    private val prefs = context.getSharedPreferences("owner_track_state", Context.MODE_PRIVATE)
    private val directory = File(context.filesDir, "private-tracks").apply { mkdirs() }
    fun activeId(): String? = prefs.getString("active_id", null)
    fun latestId(): String? = prefs.getString("latest_id", null)

    /** Retain all sessions, including completed and unreadable logs.
     * Enumerate by local file timestamp without sending GPS or parsing content.
     */
    fun allSessionIds(): List<String> =
        directory.listFiles().orEmpty()
            .filter { it.isFile && it.name.endsWith(".ndjson") &&
                it.name.removeSuffix(".ndjson").matches(Regex("[0-9a-f-]{36}")) }
            .sortedByDescending { it.lastModified() }
            .map { it.name.removeSuffix(".ndjson") }

    init {
        // Crash window: the stop record can reach disk before active_id is
        // cleared. Reconcile the marker without altering the source log.
        reconcileCompletedActiveSession()
    }

    private fun reconcileCompletedActiveSession() {
        val current = activeId() ?: return
        val records = try { read(current) } catch (_: Exception) { return }
        if (SessionRecovery.hasCompleted(records.map { it.optString("kind") })) {
            check(prefs.edit().remove("active_id").commit()) {
                "Could not reconcile completed session"
            }
        }
    }

    fun create(): String {
        reconcileCompletedActiveSession()
        activeId()?.let {
            // Resume only an unclosed, parseable session. If the existing file
            // is damaged, preserve it for raw recovery instead of appending.
            val records = read(it)
            check(SessionRecovery.canResume(records.map { event -> event.optString("kind") })) {
                "Unrecognized existing session: export its raw log before restarting"
            }
            // A previous service may have been reclaimed. This explicit
            // user restart leaves an honest gap instead of invented GPS.
            gap(it, "explicit-user-restart")
            return it
        }
        val id = UUID.randomUUID().toString()
        SessionStartCoordinator.begin(
            writeStart = {
                append(id, JSONObject().put("kind", "start").put("id", id)
                    .put("time", System.currentTimeMillis()))
            },
            persistActive = {
                prefs.edit().putString("active_id", id).putString("latest_id", id).commit()
            }
        )
        return id
    }
    // Read-only recovery discovery after a failed commit or process restart.
    // Never resume GPS automatically: an orphan is evidence, not an active session.
    fun orphanedStarts(): List<String> {
        val rows = directory.listFiles().orEmpty()
            .filter { it.isFile && it.name.endsWith(".ndjson") && it.name.removeSuffix(".ndjson").matches(Regex("[0-9a-f-]{36}")) }
            .mapNotNull { file ->
                val id = file.name.removeSuffix(".ndjson")
                // Retain corrupt or truncated originals as recovery candidates:
                // discarding unreadable files here would hide important evidence.
                val kinds = try { read(id).map { it.optString("kind") } }
                    catch (_: Exception) { listOf("start", "unreadable-original") }
                id to kinds
            }
        return SessionRecovery.pending(activeId(), rows)
    }
    fun recoveryCandidates(): List<String> = orphanedStarts()

    fun rawBytes(id: String): ByteArray {
        require(id.matches(Regex("[0-9a-f-]{36}"))) { "Invalid session id" }
        return synchronized(fileWriteLock) {
            File(directory, "$id.ndjson").readBytes()
        }
    }
    fun stop() {
        // Atomic against GPS callbacks and manual observations. Never append
        // a fix after the durable stop record due to a stale activeId check.
        synchronized(fileWriteLock) {
            activeId()?.let { id ->
                append(id, JSONObject().put("kind", "stop").put("time", System.currentTimeMillis()))
                check(prefs.edit().remove("active_id").commit()) {
                    "Could not persist stopped session state"
                }
            }
        }
    }
    fun fix(id: String, location: Location) {
        if (!location.hasAccuracy() || !location.latitude.isFinite() || !location.longitude.isFinite() ||
            !location.accuracy.isFinite() || location.accuracy < 0 ||
            location.latitude !in -90.0..90.0 || location.longitude !in -180.0..180.0) return
        val point = JSONObject().put("kind", "fix").put("time", location.time)
            .put("latitude", location.latitude).put("longitude", location.longitude)
            .put("accuracy", location.accuracy.toDouble())
        if (location.hasAltitude() && location.altitude.isFinite()) point.put("altitude", location.altitude)
        synchronized(fileWriteLock) {
            if (activeId() != id) return
            append(id, point)
        }
    }
    fun gap(id: String, reason: String) {
        synchronized(fileWriteLock) {
            if (activeId() == id) append(id, JSONObject().put("kind", "gap")
                .put("time", System.currentTimeMillis()).put("reason", reason.take(100)))
        }
    }
    fun observation(type: String, species: String, count: Int) {
        require(type in setOf("capture", "sighting", "roadkill", "other"))
        require(species.isNotBlank() && species.length <= 80 && count in 1..100)
        synchronized(fileWriteLock) {
            val id = activeId() ?: error("探索中ではありません")
            append(id, JSONObject().put("kind", "event").put("id", UUID.randomUUID().toString())
                .put("type", type).put("species", species).put("count", count)
                .put("owner", "self").put("time", System.currentTimeMillis()))
        }
    }
    fun read(id: String): List<JSONObject> {
        require(id.matches(Regex("[0-9a-f-]{36}"))) { "Invalid session id" }
        val file = File(directory, "$id.ndjson")
        if (!file.exists()) return emptyList()
        return synchronized(fileWriteLock) {
            file.readLines(Charsets.UTF_8).filter { it.isNotBlank() }.map { JSONObject(it) }
        }
    }
    private fun append(id: String, value: JSONObject) {
        val f = File(directory, "$id.ndjson")
        // Each observation is flushed durably. Lock across independent
        // activity/service instances to prevent torn or interleaved records.
        synchronized(fileWriteLock) {
            f.outputStreamAppend().use { stream ->
                stream.write((value.toString() + "\n").toByteArray(Charsets.UTF_8))
                stream.flush()
                stream.fd.sync()
            }
        }
    }
    private fun File.outputStreamAppend() = java.io.FileOutputStream(this, true)
}
