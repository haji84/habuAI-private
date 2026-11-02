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
}
