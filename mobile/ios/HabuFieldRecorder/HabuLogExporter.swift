import Foundation

/// Deterministic, owner-initiated TXT projection of a single immutable JSONL session.
/// This is a readable log, not confirmation of personal captures or evidence of active GPS search.
/// Locations are exported ONLY when they reference a verified, previously saved
/// GPS fix measured within 90 seconds BEFORE an event. Never interpolate positions.
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

        // Indexed source fixes provide independent proof that an attached
        // position actually exists in this same append-only track.
        var fixesByTime: [Double: [TrackRecord]] = [:]
        for fix in records where fix.kind == "fix" {
            fixesByTime[fix.time, default: []].append(fix)
        }
        func positionLines(_ record: TrackRecord) throws -> [String] {
            let present = record.fixTime != nil || record.latitude != nil ||
                record.longitude != nil || record.accuracy != nil || record.altitude != nil
            guard present else { return ["位置: 未取得"] }
            guard let fixTime = record.fixTime, fixTime.isFinite, fixTime > 0,
                  let lat = record.latitude, let lon = record.longitude,
                  let accuracy = record.accuracy,
                  lat.isFinite, lon.isFinite, accuracy.isFinite,
                  abs(lat) <= 90, abs(lon) <= 180, accuracy >= 0,
                  accuracy <= 100000, fixTime <= record.time,
                  record.time - fixTime <= 90,
                  record.altitude == nil || record.altitude!.isFinite,
                  fixesByTime[fixTime, default: []].contains(where: {
                      $0.latitude == lat && $0.longitude == lon &&
                      $0.accuracy == accuracy && $0.altitude == record.altitude
                  }) else {
                throw TrackStoreError.invalidSession
            }
            return [
                "GPS測位時刻: " + (try timestamp(fixTime)),
                "GPS精度: " + String(accuracy) + "m",
                String(lat), String(lon),
                "端末の実測GPS座標（生き物の正確な位置を保証しません）"
            ]
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
            case "condition":
                // A condition is a source-timed observation, not a capture,
                // inferred climate reading or guaranteed search exposure.
                let surfaces = ["dry": "ドライ", "damp": "湿り",
                                "wet": "濡れ", "puddle": "水たまり"]
                let weather = ["clear": "晴れ", "cloudy": "曇り",
                               "rain": "雨", "fog": "霧"]
                let description: String
                switch record.conditionCategory {
                case "road_surface":
                    guard record.conditionSource == "owner_visual",
                          let value = record.conditionValue,
                          let label = surfaces[value],
                          record.airTemperatureC == nil else {
                        throw TrackStoreError.invalidSession
                    }
                    description = "路面: " + label + "（本人目視）"
                case "weather":
                    guard record.conditionSource == "owner_visual",
                          let value = record.conditionValue,
                          let label = weather[value],
                          record.airTemperatureC == nil else {
                        throw TrackStoreError.invalidSession
                    }
                    description = "天気: " + label + "（本人目視）"
                case "air_temperature":
                    guard record.conditionSource == "thermometer",
                          record.conditionValue == nil,
                          let celsius = record.airTemperatureC,
                          celsius.isFinite, (-30...60).contains(celsius) else {
                        throw TrackStoreError.invalidSession
                    }
                    description = "気温（温度計で実測）: " + String(celsius) + "℃"
                default:
                    throw TrackStoreError.invalidSession
                }
                lines.append(contentsOf: [when, "環境観測", description] +
                    (try positionLines(record)) + [""])
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
                lines.append(contentsOf: try positionLines(record))
                lines.append("")
            default:
                throw TrackStoreError.invalidSession
            }
        }
        // Source JSONL retains subsecond timestamps, true GPS fixes and accuracy.
        // TXT shows only source-verified attached fixes, never guessed coordinates.
        return lines.joined(separator: "\n") + "\n"
    }
}
