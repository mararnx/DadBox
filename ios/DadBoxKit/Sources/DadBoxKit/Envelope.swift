import CryptoKit
import Foundation

public enum EnvelopeError: Error, Equatable {
    case payloadTooShort
    case unknownKey(UInt8)
    case authenticationFailed
}

/// Where keys come from. The app backs this with the Keychain; old keys are
/// kept for good, because they read the archive (ADR 0018).
public protocol KeyProvider: Sendable {
    func key(id: UInt8) -> SymmetricKey?
}

public struct StaticKeys: KeyProvider {
    public var keys: [UInt8: SymmetricKey]
    public init(_ keys: [UInt8: SymmetricKey]) { self.keys = keys }
    public func key(id: UInt8) -> SymmetricKey? { keys[id] }
}

/// End-to-end encryption of one message (PROTOCOL.md § Encryption):
///
///     payload = key_id (1) ‖ nonce (12) ‖ AES-256-GCM ciphertext ‖ tag (16)
///     AAD     = the 16 header bytes ‖ the message id (26 ASCII bytes)
public enum Envelope {
    static let overhead = 1 + 12 + 16

    public static func seal(audio: Data, header: Container.Header, id: ULID,
                            keyID: UInt8, key: SymmetricKey,
                            nonce: AES.GCM.Nonce = AES.GCM.Nonce()) throws -> Container {
        let box = try AES.GCM.seal(audio, using: key, nonce: nonce, authenticating: aad(header, id))
        var payload = Data([keyID])
        payload.append(contentsOf: nonce)
        payload.append(box.ciphertext)
        payload.append(box.tag)
        return Container(header: header, payload: payload)
    }

    /// Returns the encoded audio file (Ogg or M4A) exactly as the codec field says.
    /// Fails if the header, the id or the ciphertext were touched.
    public static func open(_ container: Container, id: ULID, keys: KeyProvider) throws -> Data {
        let p = Data(container.payload)
        guard p.count >= overhead else { throw EnvelopeError.payloadTooShort }
        guard let key = keys.key(id: p[0]) else { throw EnvelopeError.unknownKey(p[0]) }
        do {
            let box = try AES.GCM.SealedBox(nonce: AES.GCM.Nonce(data: p[1..<13]),
                                            ciphertext: p[13..<(p.count - 16)],
                                            tag: p.suffix(16))
            return try AES.GCM.open(box, using: key, authenticating: aad(container.header, id))
        } catch {
            throw EnvelopeError.authenticationFailed
        }
    }

    public static func keyID(of container: Container) -> UInt8? { container.payload.first }

    private static func aad(_ header: Container.Header, _ id: ULID) -> Data {
        header.bytes + id.ascii
    }
}

/// The family key as people handle it: 43 base64url characters, on paper and in the box's `.env`.
public enum KeyText {
    public static func encode(_ key: SymmetricKey) -> String {
        key.withUnsafeBytes { Data($0) }.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    public static func decode(_ text: String) -> SymmetricKey? {
        var s = text.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        while s.count % 4 != 0 { s.append("=") }
        guard let d = Data(base64Encoded: s), d.count == 32 else { return nil }
        return SymmetricKey(data: d)
    }
}
