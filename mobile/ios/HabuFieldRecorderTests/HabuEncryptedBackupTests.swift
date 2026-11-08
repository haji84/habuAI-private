import Foundation
import XCTest
@testable import HabuFieldRecorder

/// Entirely synthetic GPS. No owner material, passphrase or data leaves tests.
final class HabuEncryptedBackupTests: XCTestCase {
    private let passphrase = "synthetic-long-passphrase-for-test-only"

    func testEncryptDecryptGPSAndAuthenticatedTamperRejection() throws {
        let plain = Data("""
            {"kind":"event","species":"ハブ","latitude":28.123456789,"longitude":129.345678901}
            """.utf8)
        let first = try HabuEncryptedBackup.seal(
            plain, format: "ios-jsonl", passphrase: passphrase)
        let second = try HabuEncryptedBackup.seal(
            plain, format: "ios-jsonl", passphrase: passphrase)
        XCTAssertNotEqual(first, second, "fresh random salts and nonces are required")
        let readable = try XCTUnwrap(String(data: first, encoding: .utf8))
        XCTAssertFalse(readable.contains("28.123456789"))
        XCTAssertFalse(readable.contains("129.345678901"))
        XCTAssertFalse(readable.contains(passphrase))
        let reopened = try HabuEncryptedBackup.open(first, passphrase: passphrase)
        XCTAssertEqual(reopened.format, "ios-jsonl")
        XCTAssertEqual(reopened.plaintext, plain)
        XCTAssertThrowsError(try HabuEncryptedBackup.open(
            first, passphrase: "different-wrong-passphrase"))
        XCTAssertThrowsError(try HabuEncryptedBackup.seal(
            plain, format: "ios-jsonl", passphrase: "short"))
        let header = try JSONDecoder().decode(
            HabuEncryptedBackup.Envelope.self, from: first
        )
        XCTAssertEqual(header.algorithm, "AES-256-GCM")
        XCTAssertEqual(header.kdf, "PBKDF2-HMAC-SHA256")
        XCTAssertEqual(header.iterations, 600_000)
        XCTAssertEqual(header.schema_version, "habu-encrypted-backup-v1")
        let old = HabuEncryptedBackup.Envelope(
            schema_version: "wrong-schema", algorithm: header.algorithm,
            kdf: header.kdf, iterations: header.iterations, format: header.format,
            salt_b64: header.salt_b64, nonce_b64: header.nonce_b64,
            ciphertext_b64: header.ciphertext_b64
        )
        XCTAssertThrowsError(try HabuEncryptedBackup.open(
            JSONEncoder().encode(old), passphrase: passphrase
        ))
        var encrypted = try XCTUnwrap(Data(base64Encoded: header.ciphertext_b64))
        encrypted[encrypted.count - 2] ^= 0x01
        let corrupt = HabuEncryptedBackup.Envelope(
            schema_version: header.schema_version, algorithm: header.algorithm,
            kdf: header.kdf, iterations: header.iterations, format: header.format,
            salt_b64: header.salt_b64, nonce_b64: header.nonce_b64,
            ciphertext_b64: encrypted.base64EncodedString()
        )
        XCTAssertThrowsError(try HabuEncryptedBackup.open(
            JSONEncoder().encode(corrupt), passphrase: passphrase
        ))
    }

    func testRestoreOriginalRoundTripNeverOverwritesExistingSession() throws {
        let base = FileManager.default.temporaryDirectory
            .appendingPathComponent("habu-encrypted-recovery-" + UUID().uuidString, isDirectory: true)
        defer { try? FileManager.default.removeItem(at: base) }
        let rootA = base.appendingPathComponent("source", isDirectory: true)
        let rootB = base.appendingPathComponent("restored", isDirectory: true)
        try FileManager.default.createDirectory(at: rootA, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: rootB, withIntermediateDirectories: true)
        let prefsA = try XCTUnwrap(UserDefaults(suiteName: "habu-encrypted-a-" + UUID().uuidString))
        let prefsB = try XCTUnwrap(UserDefaults(suiteName: "habu-encrypted-b-" + UUID().uuidString))
        let storeA = TrackStore(rootDirectory: rootA, preferences: prefsA)
        let storeB = TrackStore(rootDirectory: rootB, preferences: prefsB)
        let id = try storeA.start()
        try storeA.append(id: id, record: TrackRecord(
            kind: "fix", time: Date().timeIntervalSince1970,
            latitude: 28.123456789, longitude: 129.345678901, accuracy: 6
        ))
        try storeA.append(id: id, record: TrackRecord(
            kind: "event", time: Date().timeIntervalSince1970,
            id: UUID().uuidString, type: "capture", species: "ハブ", count: 1, owner: "self"
        ))
        try storeA.stop()
        let original = try storeA.originalBytes(id: id)
        let wrapped = HabuEncryptedBackup.Original(
            schema_version: "habu-ios-original-v1", session_id: id,
            raw_jsonl_b64: original.base64EncodedString()
        )
        let encrypted = try HabuEncryptedBackup.seal(
            JSONEncoder().encode(wrapped), format: "ios-jsonl", passphrase: passphrase)
        let opened = try HabuEncryptedBackup.open(encrypted, passphrase: passphrase)
        XCTAssertEqual(opened.format, "ios-jsonl")
        let payload = try JSONDecoder().decode(
            HabuEncryptedBackup.Original.self, from: opened.plaintext
        )
        XCTAssertEqual(payload.session_id, id)
        let recovered = try XCTUnwrap(Data(base64Encoded: payload.raw_jsonl_b64))
        XCTAssertEqual(recovered, original)
        try storeB.restoreEncryptedOriginal(id: id, bytes: recovered)
        XCTAssertEqual(try storeB.originalBytes(id: id), original)
        XCTAssertThrowsError(try storeB.restoreEncryptedOriginal(id: id, bytes: recovered))
        XCTAssertEqual(try storeB.originalBytes(id: id), original)
        XCTAssertEqual(try storeA.originalBytes(id: id), original)
        let other = UUID().uuidString
        XCTAssertThrowsError(try storeB.restoreEncryptedOriginal(
            id: other, bytes: Data("{not-json}\n".utf8)))
        XCTAssertFalse(storeB.allSessionIds().contains(other))
    }    func testWebCompatiblePasswordEnvelopeFromIndependentOpenSSLVector() throws {
        let envelope = #"{"schema_version":"habu-encrypted-backup-v1","algorithm":"AES-256-GCM","kdf":"PBKDF2-HMAC-SHA256","iterations":600000,"format":"ios-jsonl","salt_b64":"ExMTExMTExMTExMTExMTEw==","nonce_b64":"Ly8vLy8vLy8vLy8v","ciphertext_b64":"SCgpZSjCfAiE3hRUfXfctfF5Co32/mWB3db+rElYoBH84xVywM47KCCnYYy8Egj5ictArPQQMW8/94/z7JZzyQNndWc="}"#
        let output = try HabuEncryptedBackup.open(
            Data(envelope.utf8), passphrase: "synthetic-cross-platform-passphrase"
        )
        XCTAssertEqual(output.format, "ios-jsonl")
        XCTAssertEqual(String(data: output.plaintext, encoding: .utf8),
            "SYNTHETIC GPS backup test bytes; not a real location")
    }


}
