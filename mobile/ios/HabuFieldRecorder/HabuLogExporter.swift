import Foundation

/// Deterministic, owner-initiated TXT projection of a single immutable JSONL session.
/// This is a readable log, not confirmation of personal captures or evidence of active GPS search.
/// It never guesses an observation's coordinates from a nearby GPS fix.
enum HabuLogExporter {
    private static let timeZone = TimeZone(identifier: "Asia/Tokyo")!

    private static func safeLine(_ value: String) -> String {
        // A note or species must not inject a second dated event into the log.
        value.replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func txt(_ records: [TrackRecord]) throws -> String {
        guard let first = records.first, first.kind == "start",
              first.time.isFinite, first.time > 0 else {
            throw TrackStoreError.invalidSession
        }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.timeZone = timeZone
        formatter.dateFormat = "yyyy/MM/dd HH:mm:ss"

        func timestamp(_ value: Double) throws -> String {
            guard value.isFinite, value > 0 else { throw TrackStoreError.invalidSession }
            return formatter.string(from: Date(timeIntervalSince1970: value))
        }

        var lines = ["ハブログ", ""]
        var closed = false
        for (index, record) in records.enumerated() {
            if index > 0 && record.kind == "start" { throw TrackStoreError.invalidSession }
            if record.kind == "fix" { continue }

            let when = try timestamp(record.time)
            if record.time < first.time { throw TrackStoreError.invalidSession }
            if closed { throw TrackStoreError.invalidSession }

            switch record.kind {
            case "start":
                lines.append(contentsOf: [when, "エリア探索開始", ""])
            case "stop":
                closed = true
                lines.append(contentsOf: [when, "エリア探索終了", ""])
            case "gap":
                lines.append(contentsOf: [when, "GPS中断", "これは測位の中断であり、探索実施を証明しません。"])
                if let note = record.note, !safeLine(note).isEmpty {
                    lines.append("中断理由: " + safeLine(note))
                }
                lines.append("")
            case "event":
                let labels = [
                    "capture": "捕獲", "sighting": "目撃",
                    "roadkill": "轢死", "other": "その他"
                ]
                guard let type = record.type, let label = labels[type],
                      let species = record.species, !safeLine(species).isEmpty,
                      let count = record.count, (1...100).contains(count),
                      record.owner == nil || record.owner == "self" || record.owner == "other" else {
                    throw TrackStoreError.invalidSession
                }
                // Older original records contain no owner field. Never infer "self".
                let owner = record.owner == "self" ? "本人" :
                    (record.owner == "other" ? "他者" : "未確認")
                lines.append(contentsOf: [
                    when, label, String(count) + "匹", safeLine(species),
                    (type == "capture" ? "捕獲者: " : "記録者: ") + owner
                ])
                if let id = record.id, !safeLine(id).isEmpty {
                    lines.append("記録ID: " + safeLine(id))
                }
                if let note = record.note, !safeLine(note).isEmpty {
                    lines.append("備考: " + safeLine(note))
                }
                lines.append("")
            default:
                throw TrackStoreError.invalidSession
            }
        }
        // Source JSONL retains subsecond timestamps and actual GPS fixes.
        // Human-readable TXT intentionally contains no inferred locations.
        return lines.joined(separator: "\n") + "\n"
    }
}
