import Foundation

public enum Codec: UInt8, Codable, Sendable {
    case imaADPCM = 1
    case oggOpus = 2
    case aacM4A = 3
}

public enum ContainerError: Error, Equatable {
    case tooShort, badMagic, unsupportedVersion(UInt8), unknownCodec(UInt8)
    case notEncrypted, crcMismatch
}

/// The "DBX1" container (PROTOCOL.md § Container): 16 header bytes, payload, crc32.
/// This type never sees a key — it is what the server could parse too.
public struct Container: Equatable, Sendable {
    public struct Header: Equatable, Sendable {
        public static let size = 16
        public var codec: Codec
        public var channels: UInt8 = 1
        public var flags: UInt8 = Header.encryptedFlag
        public var sampleRate: UInt32 = 16_000
        public var durationMs: UInt32

        public static let encryptedFlag: UInt8 = 0x01

        public init(codec: Codec, durationMs: UInt32, sampleRate: UInt32 = 16_000) {
            self.codec = codec
            self.durationMs = durationMs
            self.sampleRate = sampleRate
        }

        /// Exactly the bytes on the wire — also the first part of the AAD.
        public var bytes: Data {
            var d = Data("DBX1".utf8)
            d.append(contentsOf: [1, codec.rawValue, channels, flags])
            d.appendLE(sampleRate)
            d.appendLE(durationMs)
            return d
        }
    }

    public var header: Header
    public var payload: Data

    public init(header: Header, payload: Data) {
        self.header = header
        self.payload = payload
    }

    public func encoded() -> Data {
        var d = header.bytes
        d.append(payload)
        d.appendLE(CRC32.checksum(d))
        return d
    }

    public init(decoding data: Data) throws {
        let data = Data(data)  // rebase indices to 0
        guard data.count >= Header.size + 4 else { throw ContainerError.tooShort }
        guard data.prefix(4) == Data("DBX1".utf8) else { throw ContainerError.badMagic }
        guard data[4] == 1 else { throw ContainerError.unsupportedVersion(data[4]) }
        guard let codec = Codec(rawValue: data[5]) else { throw ContainerError.unknownCodec(data[5]) }
        guard data[7] & Header.encryptedFlag != 0 else { throw ContainerError.notEncrypted }

        let body = data.dropLast(4)
        guard CRC32.checksum(Data(body)) == data.readLE(at: data.count - 4) else {
            throw ContainerError.crcMismatch
        }
        var h = Header(codec: codec, durationMs: data.readLE(at: 12), sampleRate: data.readLE(at: 8))
        h.channels = data[6]
        h.flags = data[7]
        header = h
        payload = Data(body.dropFirst(Header.size))
    }
}

extension Data {
    mutating func appendLE(_ v: UInt32) {
        append(contentsOf: [UInt8(v & 0xFF), UInt8((v >> 8) & 0xFF), UInt8((v >> 16) & 0xFF), UInt8(v >> 24)])
    }

    func readLE(at offset: Int) -> UInt32 {
        let i = startIndex + offset
        return UInt32(self[i]) | UInt32(self[i + 1]) << 8 | UInt32(self[i + 2]) << 16 | UInt32(self[i + 3]) << 24
    }
}
