import Foundation
import XCTest
@testable import HabuFieldRecorder

/// Synthetic-only integration for the native unified dashboard. Historical
/// dashboard totals, owner coordinates and live Google Drive are untouched.
final class HabuLocalSummaryTests: XCTestCase {
    private var root: URL!
    private var suite: String!
    private var prefs: UserDefaults!

    override func setUpWithError() throws {
        try super.setUpWithError()
        root = FileManager.default.temporaryDirectory
            .appendingPathComponent("habu-summary-" + UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        suite = "org.habuai.local-summary-tests." + UUID().uuidString
        prefs = try XCTUnwrap(UserDefaults(suiteName: suite))
    }

    override func tearDownWithError() throws {
        prefs?.removePersistentDomain(forName: suite)
        if let root { try? FileManager.default.removeItem(at: root) }
        try super.tearDownWithError()
    }

    private func epoch(_ text: String) -> Double {
        ISO8601DateFormatter().date(from: text)!.timeIntervalSince1970
    }

    func testCompletedNativeSessionFeedsDashboardWithoutInventingOtherCaptures() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let id = UUID().uuidString.lowercased()
        let beforeSeven = epoch("2026-11-01T21:59:30Z") // 06:59:30 JST, previous night
        let afterSeven = epoch("2026-11-01T22:00:30Z")  // 07:00:30 JST, next night

        try store.append(id: id, record: TrackRecord(kind: "start", time: beforeSeven - 70))
        try store.append(id: id, record: TrackRecord(
            kind: "fix", time: beforeSeven - 40,
            latitude: 35.1, longitude: 139.2, accuracy: 8
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: beforeSeven, id: UUID().uuidString,
            type: "capture", species: "ハブ", count: 2, owner: "self"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: afterSeven, id: UUID().uuidString,
            type: "sighting", species: "ハブ", count: 1, owner: "self"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: afterSeven + 1, id: UUID().uuidString,
            type: "sighting", species: "クロウサギ", count: 1, owner: "self"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: afterSeven + 2, id: UUID().uuidString,
            type: "capture", species: "ハブ", count: 4, owner: "other"
        ))
        try store.append(id: id, record: TrackRecord(
            kind: "event", time: afterSeven + 3, id: UUID().uuidString,
            type: "roadkill", species: "ハブ", count: 1
        ))
        try store.append(id: id, record: TrackRecord(kind: "stop", time: afterSeven + 10))

        let summary = HabuLocalSummary.from(store: store)
        XCTAssertEqual(summary.completedSessions, 1)
        XCTAssertEqual(summary.gpsFixes, 1)
        XCTAssertEqual(summary.ownerHabuCaptures, 2)
        XCTAssertEqual(summary.habuSightings, 1)
        XCTAssertEqual(summary.wildlifeSightings, 1)
        XCTAssertEqual(summary.nights.map(\.id), ["2026-11-02", "2026-11-01"])
        XCTAssertEqual(summary.nights[0].captures, 0)
        XCTAssertEqual(summary.nights[1].captures, 2)
        XCTAssertEqual(summary.heldEvents, 2)
    }

    func testIncompleteAndUnknownOwnerCannotBecomeConfirmedTotals() throws {
        let store = TrackStore(rootDirectory: root, preferences: prefs)
        let pending = UUID().uuidString.lowercased()
        let complete = UUID().uuidString.lowercased()
        let t = epoch("2026-11-02T12:00:00Z")
        let sameEvent = UUID().uuidString

        try store.append(id: pending, record: TrackRecord(kind: "start", time: t))
        try store.append(id: pending, record: TrackRecord(
            kind: "event", time: t + 1, id: UUID().uuidString,
            type: "capture", species: "ハブ", count: 10, owner: "self"
        ))
        try store.append(id: complete, record: TrackRecord(kind: "start", time: t))
        try store.append(id: complete, record: TrackRecord(
            kind: "event", time: t + 1, id: UUID().uuidString,
            type: "capture", species: "ハブ", count: 2
        ))
        try store.append(id: complete, record: TrackRecord(
            kind: "event", time: t + 2, id: sameEvent,
            type: "capture", species: "ハブ", count: 1, owner: "self"
        ))
        try store.append(id: complete, record: TrackRecord(
            kind: "event", time: t + 3, id: sameEvent,
            type: "capture", species: "ハブ", count: 1, owner: "self"
        ))
        try store.append(id: complete, record: TrackRecord(kind: "stop", time: t + 5))

        let summary = HabuLocalSummary.from(store: store)
        XCTAssertEqual(summary.completedSessions, 1)
        XCTAssertEqual(summary.unfinishedSessions, 1)
        XCTAssertEqual(summary.ownerHabuCaptures, 1)
        XCTAssertEqual(summary.heldEvents, 2)
        // This is an unconfirmed device-local summary, never a Negative.
    }
}
