package org.habuai.field

import org.json.JSONObject
import java.time.Instant

/** GPX: source-only points. Missing observations never become artificial segments. */
object TrackExport {
    fun toGpx(records: List<JSONObject>): String {
        val out = StringBuilder("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            .append("<gpx version=\"1.1\" creator=\"HABU FIELD Android\" ")
            .append("xmlns=\"http://www.topografix.com/GPX/1/1\">")
            .append("<trk><name>Recorded GPS</name>")
        var opened = false
        var last = -1L
        var split = false
        records.forEach { item ->
            when (item.optString("kind")) {
                "gap" -> split = true
                "fix" -> {
                    val time = item.optLong("time", -1)
                    val lat = item.optDouble("latitude", Double.NaN)
                    val lon = item.optDouble("longitude", Double.NaN)
                    val acc = item.optDouble("accuracy", Double.NaN)
                    if (time <= 0 || !lat.isFinite() || !lon.isFinite() ||
                        lat !in -90.0..90.0 || lon !in -180.0..180.0 || !acc.isFinite() || acc < 0) return@forEach
                    if (last >= 0 && (time <= last || time - last >= 300_000)) split = true
                    if (opened && split) { out.append("</trkseg>"); opened = false }
                    if (!opened) { out.append("<trkseg>"); opened = true }
                    out.append("<trkpt lat=\"").append(lat).append("\" lon=\"").append(lon).append("\">")
                    if (item.has("altitude") && item.optDouble("altitude").isFinite())
                        out.append("<ele>").append(item.optDouble("altitude")).append("</ele>")
                    out.append("<time>").append(Instant.ofEpochMilli(time)).append("</time></trkpt>")
                    last = time
                    split = false
                }
            }
        }
        if (opened) out.append("</trkseg>")
        return out.append("</trk></gpx>\n").toString()
    }
    fun toLog(records: List<JSONObject>): String {
        return buildString {
            append("HABU FIELD Android observed log\n")
            records.forEach { r ->
                append(r.toString()).append('\n')
            }
            append("GPS points and owner events are observations, not automatically dashboard-confirmed captures.\n")
        }
    }
}
