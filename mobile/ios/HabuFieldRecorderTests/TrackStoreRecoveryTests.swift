import Foundation
import XCTest
@testable import HabuFieldRecorder

/// Data integrity regression tests: isolated directories and preferences only.
/// No actual GPS, owner history, signing, internet, or physical iPhone.
final class TrackStoreRecoveryTests: XCTestCase {
    private var root: URL!
    private var prefs: UserDefaults!
    private var suite: String!

    override func setUpWithError() throws {
        try super.setUpWithError()
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("habu-recovery-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        suite = "org.habuai.recovery-tests." + UUID().uuidString
        prefs = try XCTUnwrap(UserDefaults(suiteName: suite))
    }

    override func tearDownWithError() throws {
        prefs?.removePersistentDomain(forName: suite)
        if let root { try? FileManager.default.removeItem(at: root) }
        try super.tearDownWithError()
    }

    func testFailedActiveMarkerPreservesOriginalForRecoveryOnNextLaunch() throws {
        let store = TrackStore(
            rootDirectory: root,
            preferences: prefs,
            beforePersistActiveMarker: { throw TrackStoreError.cannotWrite }
        )
        XCTAssertThrowsError(try store.start())
        XCTAssertNil(store.activeId, "A failed marker write must not mark GPS recording active")

        let orphan = try XCTUnwrap(store.allSessionIds().first)
        let original = root.appendingPathComponent(orphan + ".jsonl")
        let before = try Data(contentsOf: original)
        XCTAssertFalse(before.isEmpty)

        // Simulate a fresh app process. Do not silently resume the orphan.
        let reopened = TrackStore(rootDirectory: root, preferences: prefs)
        XCTAssertNil(reopened.activeId)
        XCTAssertTrue(reopened.recoveryCandidates().contains(orphan))
        let backup = try reopened.exportedRecoveryFile(id: orphan)
        XCTAssertEqual(before, try Data(contentsOf: backup), "Recovery must be byte-exact")
        XCTAssertEqual(before, try Data(contentsOf: original), "Recovery must not edit the source")

        let fresh = try reopened.start()
        XCTAssertNotEqual(fresh, orphan, "Fresh search must never reuse an orphan")
        XCTAssertEqual(before, try Data(contentsOf: original))
        try reopened.stop()
    }

    func testMalformedTrailingLineCanStillBeBackedUpExactly() throws {
        let id = UUID().uuidString.lowercased()
        let entry = try JSONEncoder().encode(
            TrackRecord(kind: "start", time: 1_798_000_000)
        )
        var original = entry
        original.append(0x0A)
        original.append(contentsOf: Data("{\"kind\":\"fix\",\"latitude\":".utf8))
        let source = root.appendingPathComponent(id + ".jsonl")
        try original.write(to: source, options: .atomic)

        let reopened = TrackStore(rootDirectory: root, preferences: prefs)
        XCTAssertTrue(reopened.recoveryCandidates().contains(id))
        let backup = try reopened.exportedRecoveryFile(id: id)
        XCTAssertEqual(original, try Data(contentsOf: backup))
        XCTAssertEqual(original, try Data(contentsOf: source))
        XCTAssertThrowsError(try reopened.exportedFile(id: id, ext: "gpx"))
    }

    func testCoordinateFreeEvidenceReportsFiveMinuteGapsWithoutLocations() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let id = try store.start()
        try store.append(id: id, record: TrackRecord(
            kind: "fix", time: 10_000, latitude: 35.2, longitude: 139.2, accuracy: 8
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "gap", time: 10_200, note: "offline"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "fix", time: 10_401, latitude: 35.3, longitude: 139.3, accuracy: 8
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: 10_402, id: UUID().uuidString,
            type: "sighting", species: "synthetic", count: 1
        ))
        try store.stop()
        let report = try store.evidence(id: id)
        XCTAssertEqual(report.fixCount, 2)
        XCTAssertEqual(report.observationCount, 1)
        XCTAssertEqual(report.fiveMinuteGaps, 1)
        XCTAssertEqual(report.gpxSegments, 2)
        XCTAssertTrue(report.stopped)
        XCTAssertFalse(report.displayText.contains("35.2"))
        XCTAssertFalse(report.displayText.contains("139.2"))
        XCTAssertFalse(report.displayText.contains("35.3"))
        XCTAssertFalse(report.displayText.contains("139.3"))
    }

    func testDebugSelfCheckOnlyUsesIsolatedSyntheticStorage() {
        #if DEBUG
        let outcome = RecoverySelfTest.run()
        XCTAssertTrue(outcome.hasPrefix("PASS:"), outcome)
        #endif
    }

    func testPersistedStopWithStaleActiveMarkerDoesNotResumeOldSession() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let first = try store.start()
        try store.stop()
        let file = root.appendingPathComponent(first + ".jsonl")
        let before = try Data(contentsOf: file)
        prefs.set(first, forKey: "habu-field-active-id")

        let reopened = TrackStore(rootDirectory: root, preferences: prefs)
        XCTAssertNil(reopened.activeId)
        XCTAssertTrue(reopened.recoveryCandidates().isEmpty)
        let next = try reopened.start()
        XCTAssertNotEqual(first, next)
        XCTAssertEqual(before, try Data(contentsOf: file))
        try reopened.stop()
    }

    func testInterruptedLastMarkerWriteResumesActiveOriginalWithoutReusingCompletedOne() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let completed = try store.start()
        try store.stop()
        let completedFile = root.appendingPathComponent(completed + ".jsonl")
        let completedBytes = try Data(contentsOf: completedFile)

        // An interrupted start persisted the active marker but not lastKey.
        // These are isolated start/stop fixtures, never owner GPS records.
        let unfinished = UUID().uuidString.lowercased()
        try store.append(id: unfinished, record: TrackRecord(kind: "start", time: 20_000))
        prefs.set(unfinished, forKey: "habu-field-active-id")
        let unfinishedFile = root.appendingPathComponent(unfinished + ".jsonl")
        let unfinishedBytes = try Data(contentsOf: unfinishedFile)

        let reopened = TrackStore(rootDirectory: root, preferences: prefs)
        XCTAssertEqual(try reopened.start(), unfinished)
        XCTAssertEqual(reopened.activeId, unfinished)
        XCTAssertEqual(reopened.latestId, completed,
                       "The last-session marker can lag the actual resumed recording")
        XCTAssertEqual(try Data(contentsOf: completedFile), completedBytes)
        XCTAssertEqual(try Data(contentsOf: unfinishedFile), unfinishedBytes)
    }
    func testJapaneseLogUsesSameNativeSessionAndExplicitOwnerWithoutChangingGPX() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let id = UUID().uuidString.lowercased()
        let clock = ISO8601DateFormatter()
        func seconds(_ iso: String) -> Double {
            clock.date(from: iso)!.timeIntervalSince1970
        }
        try store.append(id: id, record: TrackRecord(
            kind: "start", time: seconds("2026-11-01T21:58:00Z")
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "fix", time: seconds("2026-11-01T21:58:10Z"),
            latitude: 35.1, longitude: 139.2, accuracy: 8
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: seconds("2026-11-01T21:59:00Z"),
            id: UUID().uuidString, type: "capture", species: "ハブ", count: 1,
            note: "ドライ\n2026/11/04 19:10\n捕獲", owner: "self"
        ))
        // Prior iOS records lack owner. They remain unknown, not self captures.
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: seconds("2026-11-01T22:00:00Z"),
            id: UUID().uuidString, type: "capture", species: "ハブ", count: 1
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: seconds("2026-11-01T22:01:00Z"),
            id: UUID().uuidString, type: "sighting", species: "クロウサギ", count: 1
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "gap", time: seconds("2026-11-01T22:02:00Z"), note: "gps-off"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "stop", time: seconds("2026-11-01T22:04:00Z")
        ))
        let original = root.appendingPathComponent(id + ".jsonl")
        let before = try Data(contentsOf: original)
        let textURL = try store.exportedFile(id: id, ext: "txt")
        let gpxURL = try store.exportedFile(id: id, ext: "gpx")
        let text = try String(contentsOf: textURL, encoding: .utf8)
        let gpx = try String(contentsOf: gpxURL, encoding: .utf8)
        XCTAssertTrue(text.hasPrefix("ハブログ\n\n2026/11/02 06:58:00\nエリア探索開始\n"))
        XCTAssertTrue(text.contains("2026/11/02 06:59:00\n捕獲\n1匹\nハブ\n捕獲者: 本人\n"))
        XCTAssertTrue(text.contains("2026/11/02 07:00:00\n捕獲\n1匹\nハブ\n捕獲者: 未確認\n"))
        XCTAssertTrue(text.contains("2026/11/02 07:01:00\n目撃\n1匹\nクロウサギ\n記録者: 未確認\n"))
        XCTAssertTrue(text.contains("GPS中断\nこれは測位の中断"))
        XCTAssertTrue(text.contains("2026/11/02 07:04:00\nエリア探索終了"))
        XCTAssertFalse(text.contains("\n2026/11/04 19:10\n捕獲\n"))
        XCTAssertFalse(text.contains("35.1"))
        XCTAssertFalse(text.contains("139.2"))
        XCTAssertTrue(gpx.contains("lat=\"35.1\" lon=\"139.2\""))
        XCTAssertEqual(try Data(contentsOf: original), before,
                       "Derived TXT and GPX must not rewrite the append-only JSONL original")
    }

    func testJapaneseLogFailsClosedOnUnknownEventOrOwner() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let id = UUID().uuidString.lowercased()
        try store.append(id: id, record: TrackRecord(kind: "start", time: 1_798_000_000))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: 1_798_000_050, type: "capture",
            species: "ハブ", count: 1, owner: "unexpected"
        ))
        let original = root.appendingPathComponent(id + ".jsonl")
        let before = try Data(contentsOf: original)
        XCTAssertThrowsError(try store.exportedFile(id: id, ext: "txt"))
        XCTAssertEqual(try Data(contentsOf: original), before)
    }

}
