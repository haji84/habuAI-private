import Foundation

/// A device-local, unconfirmed summary. Never replaces the independently
/// reconciled owner dashboard or becomes a model training/Negative label.
/// No coordinates, free-text observations, or source bytes leave the phone.
struct HabuLocalSummary {
    struct Night: Identifiable {
        let id: String       // 07:00 JST operational-night date
        var captures = 0
        var habuSightings = 0
        var wildlifeSightings = 0
    }

    var completedSessions = 0
    var unfinishedSessions = 0
    var heldSessions = 0
    var gpsFixes = 0
    var ownerHabuCaptures = 0
    var habuSightings = 0
    var wildlifeSightings = 0
    var heldEvents = 0
    var nights: [Night] = []

    static func from(store: TrackStore) -> HabuLocalSummary {
        var result = HabuLocalSummary()
        var byNight: [String: Night] = [:]
        var seenEvents: Set<String> = []

        for sessionID in store.allSessionIds() {
            let rows: [TrackRecord]
            do {
                rows = try store.read(id: sessionID)
            } catch {
                result.heldSessions += 1
                continue
            }
            guard let first = rows.first, first.kind == "start",
                  first.time.isFinite else {
                result.heldSessions += 1
                continue
            }
            guard let last = rows.last, last.kind == "stop",
                  last.time.isFinite, last.time >= first.time else {
                result.unfinishedSessions += 1
                continue
            }
            result.completedSessions += 1
            for row in rows {
                if row.kind == "fix" {
                    if row.time.isFinite, row.latitude?.isFinite == true,
                       row.longitude?.isFinite == true, row.accuracy?.isFinite == true {
                        result.gpsFixes += 1
                    }
                    continue
                }
                guard row.kind == "event" else { continue }
                guard row.time.isFinite, row.time >= first.time, row.time <= last.time,
                      let eventID = row.id, UUID(uuidString: eventID) != nil,
                      seenEvents.insert(eventID.lowercased()).inserted,
                      let count = row.count, (1...100).contains(count),
                      let species = row.species?.trimmingCharacters(in: .whitespacesAndNewlines),
                      !species.isEmpty else {
                    result.heldEvents += 1
                    continue
                }
                let night = operationalNight(row.time)
                var item = byNight[night] ?? Night(id: night)
                if row.type == "capture" && species == "ハブ" && row.owner == "self" {
                    result.ownerHabuCaptures += count
                    item.captures += count
                } else if row.type == "sighting" && species == "ハブ" {
                    result.habuSightings += count
                    item.habuSightings += count
                } else if row.type == "sighting" && species != "ハブ" {
                    result.wildlifeSightings += count
                    item.wildlifeSightings += count
                } else {
                    // Roadkill, other people's captures, unclear capture ownership,
                    // missed animals, and non-Habu captures never become owner catches.
                    result.heldEvents += 1
                    continue
                }
                byNight[night] = item
            }
        }
        result.nights = byNight.values.sorted { $0.id > $1.id }
        return result
    }

    static func operationalNight(_ seconds: Double) -> String {
        // Date formatting in Asia/Tokyo after subtracting the 07:00 boundary.
        // No system locale/timezone or daylight-saving assumptions.
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(identifier: "Asia/Tokyo")
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: Date(timeIntervalSince1970: seconds - 7 * 3600))
    }
}
