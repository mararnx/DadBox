import Foundation

/// Message id: a ULID minted at the recording end before the first byte is sent.
/// It is the idempotency key — the server never mints one (PROTOCOL.md § Message object).
public struct ULID: Hashable, Sendable, CustomStringConvertible {
    public let string: String

    private static let alphabet = Array("0123456789ABCDEFGHJKMNPQRSTVWXYZ".utf8)

    /// 48 bits of milliseconds, then 80 random bits, as 26 Crockford base32 characters.
    public init(date: Date = Date(), random: (UInt64, UInt16)? = nil) {
        var rng = SystemRandomNumberGenerator()
        let r = random ?? (rng.next(), UInt16.random(in: .min ... .max, using: &rng))
        let ms = UInt64((max(0, date.timeIntervalSince1970) * 1000).rounded()) & 0xFFFF_FFFF_FFFF

        var out = [UInt8](repeating: 0, count: 26)
        var t = ms
        for i in stride(from: 9, through: 0, by: -1) {
            out[i] = Self.alphabet[Int(t & 31)]
            t >>= 5
        }
        // 80 random bits = 16 characters: r.1 holds the top 16 bits, r.0 the low 64.
        var low = r.0
        var high = UInt64(r.1)
        for i in stride(from: 25, through: 10, by: -1) {
            out[i] = Self.alphabet[Int(low & 31)]
            low = (low >> 5) | (high << 59)
            high >>= 5
        }
        string = String(decoding: out, as: UTF8.self)
    }

    public init?(_ string: String) {
        let bytes = Array(string.utf8)
        guard bytes.count == 26, bytes[0] <= UInt8(ascii: "7"),
              bytes.allSatisfy({ Self.alphabet.contains($0) }) else { return nil }
        self.string = string
    }

    /// The 26 ASCII bytes that go into the encryption AAD.
    public var ascii: Data { Data(string.utf8) }
    public var description: String { string }
}
