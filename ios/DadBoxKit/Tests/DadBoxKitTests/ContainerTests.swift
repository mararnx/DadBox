import CryptoKit
import Foundation
import Testing
@testable import DadBoxKit

let testKey = SymmetricKey(data: Data((0..<32).map { UInt8($0) }))
let testID = ULID("01JAYZ3K7QW9E8RVX2M4N6P8TD")!

@Suite struct ULIDTests {
    @Test func isTwentySixCrockfordCharactersAndSortsByTime() {
        let a = ULID(date: Date(timeIntervalSince1970: 1_000_000))
        let b = ULID(date: Date(timeIntervalSince1970: 1_000_001))
        #expect(a.string.count == 26)
        #expect(ULID(a.string) != nil)
        #expect(a.string < b.string)
    }

    @Test func knownTimestampAndRandomBits() {
        // 1469918176385 ms ↔ 01ARYZ6S41 is the pair every ULID library documents; checked against Python too.
        let u = ULID(date: Date(timeIntervalSince1970: 1_469_918_176.385), random: (UInt64.max, UInt16.max))
        #expect(u.string == "01ARYZ6S41ZZZZZZZZZZZZZZZZ")
        #expect(ULID(date: Date(timeIntervalSince1970: 1_469_922_850.259)).string.hasPrefix("01ARZ3NDEK"))
        #expect(ULID(date: Date(timeIntervalSince1970: 0), random: (1, 0)).string == "00000000000000000000000001")
    }

    @Test func rejectsWrongLengthAndAlphabet() {
        #expect(ULID("01JAYZ3K7QW9E8RVX2M4N6P8T") == nil)
        #expect(ULID("01JAYZ3K7QW9E8RVX2M4N6P8TU") == nil)   // U is not Crockford
        #expect(ULID("81JAYZ3K7QW9E8RVX2M4N6P8TD") == nil)   // overflows 48 bits
    }
}

@Suite struct ContainerTests {
    @Test func crc32MatchesZlib() {
        #expect(CRC32.checksum(Data("123456789".utf8)) == 0xCBF4_3926)
        #expect(CRC32.checksum(Data()) == 0)
    }

    @Test func headerLayoutIsTheProtocols() {
        let h = Container.Header(codec: .aacM4A, durationMs: 14_200).bytes
        #expect(h.count == 16)
        #expect(Array(h) == [0x44, 0x42, 0x58, 0x31, 1, 3, 1, 1, 0x80, 0x3E, 0, 0, 0x78, 0x37, 0, 0])
    }

    @Test func roundTrips() throws {
        let c = Container(header: .init(codec: .oggOpus, durationMs: 2_000), payload: Data(repeating: 7, count: 100))
        let back = try Container(decoding: c.encoded())
        #expect(back == c)
        // A slice with non-zero indices must decode the same.
        let padded = Data([9, 9, 9]) + c.encoded()
        #expect(try Container(decoding: padded.dropFirst(3)) == c)
    }

    @Test func rejectsDamage() {
        var d = Container(header: .init(codec: .oggOpus, durationMs: 1), payload: Data(count: 40)).encoded()
        d[20] ^= 1
        #expect(throws: ContainerError.crcMismatch) { try Container(decoding: d) }
        #expect(throws: ContainerError.tooShort) { try Container(decoding: Data(count: 10)) }
        #expect(throws: ContainerError.badMagic) { try Container(decoding: Data(count: 40)) }
    }

    @Test func rejectsPlaintextContainers() {
        var h = Container.Header(codec: .oggOpus, durationMs: 1)
        h.flags = 0
        let d = Container(header: h, payload: Data(count: 40)).encoded()
        #expect(throws: ContainerError.notEncrypted) { try Container(decoding: d) }
    }
}

@Suite struct EnvelopeTests {
    let audio = Data("OggS not really, but bytes are bytes".utf8)
    let header = Container.Header(codec: .oggOpus, durationMs: 14_200)

    @Test func sealsAndOpens() throws {
        let c = try Envelope.seal(audio: audio, header: header, id: testID, keyID: 1, key: testKey)
        #expect(c.payload.count == audio.count + 29)
        #expect(Envelope.keyID(of: c) == 1)
        let wire = try Container(decoding: c.encoded())
        #expect(try Envelope.open(wire, id: testID, keys: StaticKeys([1: testKey])) == audio)
    }

    @Test func aServerCannotSwapAudioBetweenMessages() throws {
        let c = try Envelope.seal(audio: audio, header: header, id: testID, keyID: 1, key: testKey)
        let other = ULID("01JAYZ3K7QW9E8RVX2M4N6P8TE")!
        #expect(throws: EnvelopeError.authenticationFailed) {
            try Envelope.open(c, id: other, keys: StaticKeys([1: testKey]))
        }
    }

    @Test func aServerCannotAlterTheHeader() throws {
        var c = try Envelope.seal(audio: audio, header: header, id: testID, keyID: 1, key: testKey)
        c.header.durationMs = 1
        #expect(throws: EnvelopeError.authenticationFailed) {
            try Envelope.open(c, id: testID, keys: StaticKeys([1: testKey]))
        }
    }

    @Test func oldKeysStillReadOldMessages() throws {
        let newKey = SymmetricKey(size: .bits256)
        let old = try Envelope.seal(audio: audio, header: header, id: testID, keyID: 1, key: testKey)
        let keys = StaticKeys([1: testKey, 3: newKey])
        #expect(try Envelope.open(old, id: testID, keys: keys) == audio)
        #expect(throws: EnvelopeError.unknownKey(1)) {
            try Envelope.open(old, id: testID, keys: StaticKeys([3: newKey]))
        }
    }

    @Test func keyTextIsFortyThreeCharactersAndRoundTrips() {
        let text = KeyText.encode(testKey)
        #expect(text.count == 43)
        #expect(text == "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8")
        #expect(KeyText.decode(text + "\n")?.withUnsafeBytes { Data($0) } == testKey.withUnsafeBytes { Data($0) })
        #expect(KeyText.decode("too short") == nil)
    }
}

/// docs/testvectors/container-v1.json is shared with the box's Python tests:
/// both ends must produce and accept exactly these bytes.
@Suite struct SharedVectorTests {
    struct Vector: Codable {
        var name: String, id: String, codec: UInt8, duration_ms: UInt32, sample_rate: UInt32
        var key_id: UInt8, key_hex: String, nonce_hex: String, plaintext_hex: String, container_hex: String
    }

    static let url = URL(filePath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent()
        .appending(path: "docs/testvectors/container-v1.json")

    static func build(_ v: Vector) throws -> Data {
        let header = Container.Header(codec: Codec(rawValue: v.codec)!, durationMs: v.duration_ms, sampleRate: v.sample_rate)
        return try Envelope.seal(audio: Data(hex: v.plaintext_hex), header: header, id: ULID(v.id)!,
                                 keyID: v.key_id, key: SymmetricKey(data: Data(hex: v.key_hex)),
                                 nonce: AES.GCM.Nonce(data: Data(hex: v.nonce_hex))).encoded()
    }

    @Test func vectorsMatchByteForByte() throws {
        var vectors = try JSONDecoder().decode([Vector].self, from: Data(contentsOf: Self.url))
        // DADBOX_WRITE_VECTORS=1 swift test — regenerates container_hex. Only when the
        // protocol changes; afterwards the box's tests must be run against the new file.
        if ProcessInfo.processInfo.environment["DADBOX_WRITE_VECTORS"] == "1" {
            for i in vectors.indices { vectors[i].container_hex = try Self.build(vectors[i]).hex }
            let e = JSONEncoder(); e.outputFormatting = [.prettyPrinted, .sortedKeys]
            try e.encode(vectors).write(to: Self.url)
        }
        #expect(vectors.count >= 3)
        for v in vectors {
            #expect(try Self.build(v).hex == v.container_hex, "\(v.name): sealing")
            let c = try Container(decoding: Data(hex: v.container_hex))
            let keys = StaticKeys([v.key_id: SymmetricKey(data: Data(hex: v.key_hex))])
            #expect(try Envelope.open(c, id: ULID(v.id)!, keys: keys).hex == v.plaintext_hex, "\(v.name): opening")
        }
    }
}

extension Data {
    init(hex: String) {
        var d = Data(); var i = hex.startIndex
        while i < hex.endIndex { let j = hex.index(i, offsetBy: 2); d.append(UInt8(hex[i..<j], radix: 16)!); i = j }
        self = d
    }
    var hex: String { map { String(format: "%02x", $0) }.joined() }
}
