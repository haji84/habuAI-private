import Foundation
import CommonCrypto
import CryptoKit
import Security

/// A password-protected, authenticated backup file format also supported by
/// dashboard/field-crypto.js. This DOES NOT change the append-only GPS writer.
/// The passphrase and derived key are never put in app preferences or Git.
enum HabuEncryptedBackup {
    static let version = "habu-encrypted-backup-v1"
    static let rounds: UInt32 = 600_000
    static let maxPlainBytes = 30 * 1024 * 1024
    private static let formats = ["ios-jsonl", "web-session-json"]
    private static let aadPrefix = "HABU-ENCRYPTED-BACKUP-V1|"

    enum Failure: Error {
        case invalidFormat
        case insecurePassphrase
        case randomUnavailable
        case keyDerivationFailed
        case authenticationFailed
        case capacityExceeded
    }

    struct Envelope: Codable {
        let schema_version: String
        let algorithm: String
        let kdf: String
        let iterations: UInt32
        let format: String
        let salt_b64: String
        let nonce_b64: String
        let ciphertext_b64: String
    }

    /// The session id is encrypted, never shown in the ciphertext filename.
    struct Original: Codable {
        let schema_version: String
        let session_id: String
        let raw_jsonl_b64: String
    }

    private static func verifyPassphrase(_ pass: String) throws {
        guard pass.unicodeScalars.count >= 12, pass.utf8.count <= 1024 else {
            throw Failure.insecurePassphrase
        }
    }

    private static func random(_ count: Int) throws -> Data {
        var bytes = [UInt8](repeating: 0, count: count)
        guard SecRandomCopyBytes(kSecRandomDefault, count, &bytes) == errSecSuccess else {
            throw Failure.randomUnavailable
        }
        return Data(bytes)
    }

    private static func derive(_ pass: String, salt: Data) throws -> SymmetricKey {
        try verifyPassphrase(pass)
        guard salt.count == 16 else { throw Failure.invalidFormat }
        let password = Data(pass.utf8)
        var output = [UInt8](repeating: 0, count: 32)
        let status: Int32 = password.withUnsafeBytes { p in
            salt.withUnsafeBytes { s in
                CCKeyDerivationPBKDF(
                    CCPBKDFAlgorithm(kCCPBKDF2),
                    p.bindMemory(to: CChar.self).baseAddress, password.count,
                    s.bindMemory(to: UInt8.self).baseAddress, salt.count,
                    CCPseudoRandomAlgorithm(kCCPRFHmacAlgSHA256),
                    rounds,
                    &output, output.count
                )
            }
        }
        guard status == kCCSuccess else { throw Failure.keyDerivationFailed }
        let key = SymmetricKey(data: Data(output))
        output.withUnsafeMutableBufferPointer { pointer in
            for i in pointer.indices { pointer[i] = 0 }
        }
        return key
    }

    static func seal(_ original: Data, format: String, passphrase: String) throws -> Data {
        guard formats.contains(format) else { throw Failure.invalidFormat }
        guard !original.isEmpty, original.count <= maxPlainBytes else {
            throw Failure.capacityExceeded
        }
        let salt = try random(16), iv = try random(12)
        let key = try derive(passphrase, salt: salt)
        let nonce = try AES.GCM.Nonce(data: iv)
        let sealed = try AES.GCM.seal(original, using: key, nonce: nonce,
                                     authenticating: Data((aadPrefix + format).utf8))
        var ciphertext = sealed.ciphertext
        ciphertext.append(sealed.tag)
        let envelope = Envelope(
            schema_version: version, algorithm: "AES-256-GCM",
            kdf: "PBKDF2-HMAC-SHA256", iterations: rounds,
            format: format, salt_b64: salt.base64EncodedString(),
            nonce_b64: iv.base64EncodedString(),
            ciphertext_b64: ciphertext.base64EncodedString()
        )
        return try JSONEncoder().encode(envelope)
    }

    static func open(_ bytes: Data, passphrase: String) throws -> (format: String, plaintext: Data) {
        guard !bytes.isEmpty, bytes.count <= 42 * 1024 * 1024 else {
            throw Failure.capacityExceeded
        }
        let envelope = try JSONDecoder().decode(Envelope.self, from: bytes)
        guard envelope.schema_version == version,
              envelope.algorithm == "AES-256-GCM",
              envelope.kdf == "PBKDF2-HMAC-SHA256",
              envelope.iterations == rounds,
              formats.contains(envelope.format),
              let salt = Data(base64Encoded: envelope.salt_b64),
              let iv = Data(base64Encoded: envelope.nonce_b64),
              let ciphertext = Data(base64Encoded: envelope.ciphertext_b64),
              salt.count == 16, iv.count == 12,
              ciphertext.count >= 17, ciphertext.count <= maxPlainBytes + 16 else {
            throw Failure.invalidFormat
        }
        let key = try derive(passphrase, salt: salt)
        let nonce = try AES.GCM.Nonce(data: iv)
        let sealed = try AES.GCM.SealedBox(
            nonce: nonce,
            ciphertext: ciphertext.dropLast(16),
            tag: ciphertext.suffix(16)
        )
        let plain: Data
        do {
            plain = try AES.GCM.open(sealed, using: key,
                                     authenticating: Data((aadPrefix + envelope.format).utf8))
        } catch { throw Failure.authenticationFailed }
        guard plain.count <= maxPlainBytes else { throw Failure.capacityExceeded }
        return (envelope.format, plain)
    }
}
