import Foundation

/// Coordinates never appear in the owner's acceptance summary or in CI logs.
/// A summary is evidence of saved records, NOT proof of the device being locked.
struct RecordEvidence {
    let fixCount: Int
    let observationCount: Int
    let fiveMinuteGaps: Int
    let gpxSegments: Int
    let firstFixTime: Date?
    let lastFixTime: Date?
    let stopped: Bool

    static func summarize(_ records: [TrackRecord]) -> RecordEvidence {
        var fixes = 0
        var events = 0
        var longGaps = 0
        var segments = 0
        var previous: Double?
        var pendingGap = false
        var startTime: Double?
        var endTime: Double?
        for record in records {
            if record.kind == "event" { events += 1; continue }
            if record.kind == "gap" { pendingGap = true; continue }
            guard record.kind == "fix",
                  let latitude = record.latitude,
                  let longitude = record.longitude,
                  let accuracy = record.accuracy,
                  latitude.isFinite, longitude.isFinite, accuracy.isFinite,
                  abs(latitude) <= 90, abs(longitude) <= 180,
                  accuracy >= 0, record.time > 0 else { continue }
            fixes += 1
            startTime = min(startTime ?? record.time, record.time)
            endTime = max(endTime ?? record.time, record.time)
            if let last = previous {
                let delta = record.time - last
                if delta >= 300 { longGaps += 1 }
                if pendingGap || delta >= 300 || delta <= 0 { segments += 1 }
            } else {
                segments += 1
            }
            previous = record.time
            pendingGap = false
        }
        return RecordEvidence(
            fixCount: fixes, observationCount: events, fiveMinuteGaps: longGaps,
            gpxSegments: segments,
            firstFixTime: startTime.map(Date.init(timeIntervalSince1970:)),
            lastFixTime: endTime.map(Date.init(timeIntervalSince1970:)),
            stopped: records.last?.kind == "stop"
        )
    }

    var displayText: String {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .medium
        let first = firstFixTime.map(formatter.string(from:)) ?? "なし"
        let last = lastFixTime.map(formatter.string(from:)) ?? "なし"
        return "保存GPS: \(fixCount)点、観察: \(observationCount)件、5分以上の測位空白: \(fiveMinuteGaps)回、GPX区間: \(gpxSegments)、終了記録: \(stopped ? "あり" : "なし")。最初の測位: \(first)、最後の測位: \(last)。座標は表示しません。"
    }
}
