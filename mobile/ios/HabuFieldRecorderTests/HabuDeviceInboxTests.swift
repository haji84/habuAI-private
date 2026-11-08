import CryptoKit
import Foundation
import XCTest
@testable import HabuFieldRecorder

/// Synthetic-only asymmetric upload encryption tests. Never use the real
/// owner's receiver private key, GPX files or personal coordinates in CI.
final class HabuDeviceInboxTests: XCTestCase {
    func testSyntheticReceiverDecryptsNativeEncryptedOriginal() throws {
        let receiver = Curve25519.KeyAgreement.PrivateKey()
        let sourceID = UUID().uuidString.lowercased()
        let source = Data(
            "{\"kind\":\"start\",\"time\":1790000000}\n" +
            "{\"kind\":\"fix\",\"time\":1790000001,\"latitude\":28.123456789,\"longitude\":129.345678901,\"accuracy\":7}\n" +
            "{\"kind\":\"event\",\"time\":1790000002,\"type\":\"capture\",\"species\":\"ハブ\",\"count\":1,\"owner\":\"self\"}\n" +
            "{\"kind\":\"stop\",\"time\":1790000003}\n"
        .utf8)
        let ciphertext = try HabuDeviceInboxCrypto.seal(
            original: source, sessionID: sourceID,
            recipientPublicKey: receiver.publicKey.rawRepresentation
        )
        let publicText = try XCTUnwrap(String(data: ciphertext, encoding: .utf8))
        XCTAssertFalse(publicText.contains("28.123456789"))
        XCTAssertFalse(publicText.contains("129.345678901"))
        XCTAssertFalse(publicText.contains(sourceID))

        let env = try JSONDecoder().decode(
            HabuDeviceInboxCrypto.SealedEnvelope.self, from: ciphertext
        )
        XCTAssertEqual(env.schema_version, "habu-device-inbox-v1")
        XCTAssertEqual(env.algorithm, "X25519-HKDF-SHA256-AES-256-GCM")
        let ephemeral = try Curve25519.KeyAgreement.PublicKey(
            rawRepresentation: try XCTUnwrap(Data(base64Encoded: env.ephemeral_public_key_b64))
        )
        let salt = try XCTUnwrap(Data(base64Encoded: env.hkdf_salt_b64))
        let nonceBytes = try XCTUnwrap(Data(base64Encoded: env.nonce_b64))
        let combined = try XCTUnwrap(Data(base64Encoded: env.ciphertext_b64))
        let secret = try receiver.sharedSecretFromKeyAgreement(with: ephemeral)
        let aad = Data(("HABU-DEVICE-INBOX-V1|" + env.recipient_key_id).utf8)
        let derived = secret.hkdfDerivedSymmetricKey(
            using: SHA256.self, salt: salt, sharedInfo: aad, outputByteCount: 32
        )
        let nonce = try AES.GCM.Nonce(data: nonceBytes)
        let box = try AES.GCM.SealedBox(
            nonce: nonce, ciphertext: combined.dropLast(16),
            tag: combined.suffix(16)
        )
        let plaintext = try AES.GCM.open(box, using: derived, authenticating: aad)
        let original = try JSONDecoder().decode(
            HabuDeviceInboxCrypto.Original.self, from: plaintext
        )
        XCTAssertEqual(original.session_id, sourceID)
        XCTAssertEqual(original.source_sha256, HabuDeviceInboxCrypto.sourceSHA(source))
        XCTAssertEqual(try XCTUnwrap(Data(base64Encoded: original.raw_jsonl_b64)), source)

        var invalid = combined
        invalid[invalid.count - 2] ^= 1
        let corrupted = try AES.GCM.SealedBox(
            nonce: nonce, ciphertext: invalid.dropLast(16), tag: invalid.suffix(16)
        )
        XCTAssertThrowsError(
            try AES.GCM.open(corrupted, using: derived, authenticating: aad)
        )
    }

    func testDefaultReceiverPublicKeyIsValidAndBoundToKeyId() throws {
        let publicKey = try XCTUnwrap(
            Data(base64Encoded: HabuDeviceInboxCrypto.receiverPublicKeyBase64)
        )
        XCTAssertEqual(publicKey.count, 32)
        let hash = SHA256.hash(data: publicKey)
            .prefix(8).map { String(format: "%02x", $0) }.joined()
        XCTAssertEqual(hash, HabuDeviceInboxCrypto.keyID)
        let source = Data("{\"kind\":\"start\",\"time\":1790000000}\n".utf8)
        let sealed = try HabuDeviceInboxCrypto.seal(
            original: source, sessionID: UUID().uuidString
        )
        let env = try JSONDecoder().decode(
            HabuDeviceInboxCrypto.SealedEnvelope.self, from: sealed
        )
        XCTAssertEqual(env.recipient_key_id, hash)
        XCTAssertThrowsError(try HabuDeviceInboxCrypto.seal(
            original: source, sessionID: "invalid id"
        ))
        XCTAssertThrowsError(try HabuDeviceInboxCrypto.seal(
            original: Data(), sessionID: UUID().uuidString
        ))
    }
}
