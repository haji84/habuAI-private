import Foundation

struct TrackRecord: Codable {
    let kind: String
    let time: Double
    var id: String? = nil
    var latitude: Double? = nil
    var longitude: Double? = nil
    var accuracy: Double? = nil
    var altitude: Double? = nil
    var type: String? = nil
    var species: String? = nil
    var count: Int? = nil
    var note: String? = nil
}

enum TrackStoreError: Error {
    case cannotWrite
    case invalidSession
}

/** Append-only local trace. No network calls. File protection permits writes when locked. */
final class TrackStore {
    private let root: URL
    private let prefs = UserDefaults.standard
    private let key = "habu-field-active-id"
    private let lastKey = "habu-field-last-id"

    init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        root = base.appendingPathComponent("observations", isDirectory: true)
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try? FileManager.default.setAttributes(
            [.protectionKey: FileProtectionType.completeUntilFirstUserAuthentication],
            ofItemAtPath: root.path
        )
    }
    var activeId: String? { prefs.string(forKey: key) }
    var latestId: String? { prefs.string(forKey: lastKey) }

    func start() throws -> String {
        if let id = activeId { return id }
        let id = UUID().uuidString.lowercased()
        try append(id: id, record: TrackRecord(kind: "start", time: Date().timeIntervalSince1970))
        prefs.set(id, forKey: key)
        prefs.set(id, forKey: lastKey)
        return id
    }
    func stop() throws {
        guard let id = activeId else { return }
        try append(id: id, record: TrackRecord(kind: "stop", time: Date().timeIntervalSince1970))
        prefs.removeObject(forKey: key)
    }
    func append(id: String, record: TrackRecord) throws {
        guard UUID(uuidString: id) != nil else { throw TrackStoreError.invalidSession }
        let path = root.appendingPathComponent(id + ".jsonl")
        var data = try JSONEncoder().encode(record)
        data.append(0x0A)
        if !FileManager.default.fileExists(atPath: path.path) {
            guard FileManager.default.createFile(atPath: path.path, contents: nil, attributes: [
                .protectionKey: FileProtectionType.completeUntilFirstUserAuthentication
            ]) else { throw TrackStoreError.cannotWrite }
        }
        let handle = try FileHandle(forWritingTo: path)
        defer { try? handle.close() }
        try handle.seekToEnd()
        try handle.write(contentsOf: data)
        try handle.synchronize()
    }
    func read(id: String) throws -> [TrackRecord] {
        guard UUID(uuidString: id) != nil else { throw TrackStoreError.invalidSession }
        let path = root.appendingPathComponent(id + ".jsonl")
        let text = try String(contentsOf: path, encoding: .utf8)
        return try text.split(whereSeparator: \.isNewline).map {
            try JSONDecoder().decode(TrackRecord.self, from: Data($0.utf8))
        }
    }
    func exportedFile(id: String, ext: String) throws -> URL {
        let entries = try read(id: id)
        let contents: String
        switch ext {
        case "gpx": contents = TrackExporter.gpx(entries)
        case "jsonl":
            contents = entries.map { record in
                let encoded = try? JSONEncoder().encode(record)
                return encoded.flatMap { String(data: $0, encoding: .utf8) } ?? ""
            }.joined(separator: "\n") + "\n"
        default: throw TrackStoreError.cannotWrite
        }
        let path = FileManager.default.temporaryDirectory.appendingPathComponent("habu-" + id + "." + ext)
        try contents.write(to: path, atomically: true, encoding: .utf8)
        return path
    }
}

enum TrackExporter {
    static func gpx(_ records: [TrackRecord]) -> String {
        var text = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        text += "<gpx version=\"1.1\" creator=\"HABU FIELD iOS\" xmlns=\"http://www.topografix.com/GPX/1/1\"><trk><name>Recorded GPS</name>"
        var open = false
        var gap = false
        var previous: Double? = nil
        let formatter = ISO8601DateFormatter()
        for item in records {
            if item.kind == "gap" { gap = true; continue }
            guard item.kind == "fix",
                  let lat = item.latitude, let lon = item.longitude, let accuracy = item.accuracy,
                  lat.isFinite, lon.isFinite, accuracy.isFinite, accuracy >= 0,
                  abs(lat) <= 90, abs(lon) <= 180, item.time > 0 else { continue }
            if let p = previous, item.time <= p || item.time - p >= 300 { gap = true }
            if open && gap { text += "</trkseg>"; open = false }
            if !open { text += "<trkseg>"; open = true }
            text += "<trkpt lat=\"\(lat)\" lon=\"\(lon)\">"
            if let ele = item.altitude, ele.isFinite { text += "<ele>\(ele)</ele>" }
            text += "<time>\(formatter.string(from: Date(timeIntervalSince1970: item.time)))</time></trkpt>"
            previous = item.time
            gap = false
        }
        if open { text += "</trkseg>" }
        return text + "</trk></gpx>\n"
    }
}
