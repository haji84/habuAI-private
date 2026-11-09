import CryptoKit
import Foundation
import Security

/// Public-key-only encryption for location-bearing, completed native originals.
/// No decryption secret, passphrase, access token, GPS or capture coordinates
/// are embedded here or sent to GitHub. Receiver private key stays in Library.
enum HabuDeviceInboxCrypto {
    static let version = "habu-device-inbox-v1"
    static let payloadVersion = "habu-device-original-v1"
    static let algorithm = "X25519-HKDF-SHA256-AES-256-GCM"
    static let keyID = "4cbbc8bb76cd2d73"
    static let receiverPublicKeyBase64 =
        "0ro82lvgcs5Qub71T6v5O+aKqOkjRimG4fXHBMnNH1g="
    static let maximumSourceBytes = 18 * 1024 * 1024
    private static let aadPrefix = "HABU-DEVICE-INBOX-V1|"

    enum Failure: Error {
        case invalidSource
        case invalidReceiver
        case randomUnavailable
        case encryptionFailed
    }

    struct SealedEnvelope: Codable {
        let schema_version: String
        let algorithm: String
        let recipient_key_id: String
        let ephemeral_public_key_b64: String
        let hkdf_salt_b64: String
        let nonce_b64: String
        let ciphertext_b64: String
    }

    struct Original: Codable {
        let schema_version: String
        let session_id: String
        let source_sha256: String
        let raw_jsonl_b64: String
    }

    private static func random(_ count: Int) throws -> Data {
        var bytes = [UInt8](repeating: 0, count: count)
        guard SecRandomCopyBytes(kSecRandomDefault, count, &bytes) == errSecSuccess else {
            throw Failure.randomUnavailable
        }
        return Data(bytes)
    }

    static func sourceSHA(_ raw: Data) -> String {
        SHA256.hash(data: raw).map { String(format: "%02x", $0) }.joined()
    }

    static func seal(original: Data, sessionID: String,
                     recipientPublicKey: Data? = nil) throws -> Data {
        guard UUID(uuidString: sessionID) != nil,
              !original.isEmpty, original.count <= maximumSourceBytes,
              original.last == 0x0a else { throw Failure.invalidSource }

        let publicData: Data
        if let recipientPublicKey {
            publicData = recipientPublicKey // Synthetic tests only.
        } else {
            guard let standard = Data(base64Encoded: receiverPublicKeyBase64) else {
                throw Failure.invalidReceiver
            }
            publicData = standard
        }
        guard publicData.count == 32 else { throw Failure.invalidReceiver }
        let identifier = SHA256.hash(data: publicData)
            .prefix(8).map { String(format: "%02x", $0) }.joined()
        if recipientPublicKey == nil && identifier != keyID { throw Failure.invalidReceiver }

        let recipient = try Curve25519.KeyAgreement.PublicKey(rawRepresentation: publicData)
        let ephemeral = Curve25519.KeyAgreement.PrivateKey()
        let shared = try ephemeral.sharedSecretFromKeyAgreement(with: recipient)
        let salt = try random(32)
        let nonceBytes = try random(12)
        let additionalData = Data((aadPrefix + identifier).utf8)
        let sessionKey = shared.hkdfDerivedSymmetricKey(
            using: SHA256.self,
            salt: salt,
            sharedInfo: additionalData,
            outputByteCount: 32
        )
        let payload = Original(
            schema_version: payloadVersion, session_id: sessionID.lowercased(),
            source_sha256: sourceSHA(original),
            raw_jsonl_b64: original.base64EncodedString()
        )
        let clear = try JSONEncoder().encode(payload)
        let nonce = try AES.GCM.Nonce(data: nonceBytes)
        let sealed = try AES.GCM.seal(
            clear, using: sessionKey, nonce: nonce, authenticating: additionalData
        )
        var joined = sealed.ciphertext
        joined.append(sealed.tag)
        let result = SealedEnvelope(
            schema_version: version,
            algorithm: algorithm,
            recipient_key_id: identifier,
            ephemeral_public_key_b64: ephemeral.publicKey.rawRepresentation.base64EncodedString(),
            hkdf_salt_b64: salt.base64EncodedString(),
            nonce_b64: nonceBytes.base64EncodedString(),
            ciphertext_b64: joined.base64EncodedString()
        )
        return try JSONEncoder().encode(result)
    }
}

/// Selected external Files folder (ideally the connected Google Drive inbox).
/// App writes ONLY authenticated ciphertext to the file provider, without
/// storing the private key or requesting a passphrase. Provider cloud upload
/// happens asynchronously; local readback is NOT server delivery proof.
final class HabuDeviceInboxStager {
    enum Failure: Error {
        case noFolder
        case missingAccess
        case staleBookmark
        case existingDestination
        case coordinationFailed
        case noReadback
    }

    private let preferences: UserDefaults
    private let bookmarkKey = "habu-inbox-folder-bookmark-v1"
    private let completedKey = "habu-inbox-accepted-original-shas-v1"

    init(preferences: UserDefaults = .standard) {
        self.preferences = preferences
    }

    var isConfigured: Bool {
        preferences.data(forKey: bookmarkKey) != nil
    }

    func selectFolder(_ url: URL) throws {
        guard url.startAccessingSecurityScopedResource() else {
            throw Failure.missingAccess
        }
        defer { url.stopAccessingSecurityScopedResource() }
        var error: NSError?
        var directory: Bool = false
        let coordinator = NSFileCoordinator()
        coordinator.coordinate(readingItemAt: url, options: [], error: &error) { candidate in
            directory = (try? candidate.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true
        }
        guard error == nil, directory else { throw Failure.noFolder }
        // This is a File Provider security-scoped bookmark. No original data
        // and no GPS values are placed into app preferences.
        let bookmark = try url.bookmarkData(
            options: [], includingResourceValuesForKeys: nil, relativeTo: nil
        )
        preferences.set(bookmark, forKey: bookmarkKey)
    }

    private func selectedFolder() throws -> URL {
        guard let bookmark = preferences.data(forKey: bookmarkKey) else {
            throw Failure.noFolder
        }
        var stale = false
        let url = try URL(
            resolvingBookmarkData: bookmark, options: [], relativeTo: nil,
            bookmarkDataIsStale: &stale
        )
        guard !stale else { throw Failure.staleBookmark }
        return url
    }

    /// A local file-provider staging receipt, not a claim that Drive or
    /// ChatGPT Library already received the file.
    func stageCompletedOriginal(sessionID: String, original: Data) throws -> Bool {
        let sourceSHA = HabuDeviceInboxCrypto.sourceSHA(original)
        let completed = preferences.dictionary(forKey: completedKey) as? [String: String] ?? [:]
        if completed[sessionID] == sourceSHA { return false }
        let sealed = try HabuDeviceInboxCrypto.seal(
            original: original, sessionID: sessionID
        )
        let encryptedSHA = HabuDeviceInboxCrypto.sourceSHA(sealed)
        let folder = try selectedFolder()
        guard folder.startAccessingSecurityScopedResource() else {
            throw Failure.missingAccess
        }
        defer { folder.stopAccessingSecurityScopedResource() }

        let destination = folder.appendingPathComponent(
            "habu-" + UUID().uuidString.lowercased() + ".habuenc"
        )
        let coordinator = NSFileCoordinator()
        var coordinateError: NSError?
        var writeFailure: Error?
        coordinator.coordinate(writingItemAt: destination, options: [], error: &coordinateError) { item in
            do {
                if FileManager.default.fileExists(atPath: item.path) {
                    throw Failure.existingDestination
                }
                try sealed.write(to: item, options: [])
            } catch { writeFailure = error }
        }
        if let coordinateError { throw coordinateError }
        if let writeFailure { throw writeFailure }

        var readback: Data?
        var readError: NSError?
        var readFailure: Error?
        coordinator.coordinate(readingItemAt: destination, options: [], error: &readError) { item in
            do { readback = try Data(contentsOf: item) }
            catch { readFailure = error }
        }
        if let readError { throw readError }
        if let readFailure { throw readFailure }
        guard let readback, HabuDeviceInboxCrypto.sourceSHA(readback) == encryptedSHA else {
            throw Failure.noReadback
        }
        // Keep only a content-addressed local receipt. No source bytes here.
        var newest = completed
        newest[sessionID] = sourceSHA
        preferences.set(newest, forKey: completedKey)
        return true
    }
}
