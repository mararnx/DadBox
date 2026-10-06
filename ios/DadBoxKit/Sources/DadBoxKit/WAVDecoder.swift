import AudioToolbox
import Foundation

/// Decodes compressed audio held in memory (the box's Ogg Opus, the phone's
/// M4A) to a 16-bit mono WAV, also in memory.
///
/// Why: `AVAudioPlayer(data:)` opens an Ogg Opus message shorter than about
/// 15 s but will not play it — `prepareToPlay()` and `play()` return false —
/// while longer ones play (bench, 2026-10-06: 2, 6 and 10 s fail, 20 s and up
/// play). AudioToolbox decodes all of them, so the app plays the WAV instead.
/// Nothing is written to disk: the plaintext stays in memory.
public enum WAVDecoder {
    public enum DecodeError: Error, Equatable {
        case open(OSStatus)
        case read(OSStatus)
        case empty
    }

    public static func wav(from audio: Data, sampleRate: Double = 48_000) throws -> Data {
        let source = MemorySource(audio)
        let client = Unmanaged.passUnretained(source).toOpaque()
        var fileID: AudioFileID?
        var status = AudioFileOpenWithCallbacks(client, MemorySource.read, nil, MemorySource.size, nil, 0, &fileID)
        guard status == noErr, let fileID else { throw DecodeError.open(status) }
        defer { AudioFileClose(fileID) }

        var ext: ExtAudioFileRef?
        status = ExtAudioFileWrapAudioFileID(fileID, false, &ext)
        guard status == noErr, let ext else { throw DecodeError.open(status) }
        defer { ExtAudioFileDispose(ext) }

        var format = AudioStreamBasicDescription(
            mSampleRate: sampleRate, mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kLinearPCMFormatFlagIsSignedInteger | kLinearPCMFormatFlagIsPacked,
            mBytesPerPacket: 2, mFramesPerPacket: 1, mBytesPerFrame: 2, mChannelsPerFrame: 1,
            mBitsPerChannel: 16, mReserved: 0)
        status = ExtAudioFileSetProperty(ext, kExtAudioFileProperty_ClientDataFormat,
                                         UInt32(MemoryLayout.size(ofValue: format)), &format)
        guard status == noErr else { throw DecodeError.open(status) }

        var pcm = Data()
        let chunkFrames: UInt32 = 4096
        var chunk = [Int16](repeating: 0, count: Int(chunkFrames))
        while true {
            var frames = chunkFrames
            let read: OSStatus = chunk.withUnsafeMutableBytes { raw in
                var list = AudioBufferList(mNumberBuffers: 1, mBuffers: AudioBuffer(
                    mNumberChannels: 1, mDataByteSize: UInt32(raw.count), mData: raw.baseAddress))
                return ExtAudioFileRead(ext, &frames, &list)
            }
            guard read == noErr else { throw DecodeError.read(read) }
            if frames == 0 { break }
            chunk.withUnsafeBytes { pcm.append(contentsOf: $0.prefix(Int(frames) * 2)) }
        }
        guard !pcm.isEmpty else { throw DecodeError.empty }
        return header(pcmBytes: pcm.count, sampleRate: UInt32(sampleRate)) + pcm
    }

    static func header(pcmBytes: Int, sampleRate: UInt32) -> Data {
        var d = Data()
        func u32(_ v: UInt32) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        d.append(contentsOf: Array("RIFF".utf8)); u32(UInt32(36 + pcmBytes))
        d.append(contentsOf: Array("WAVEfmt ".utf8)); u32(16); u16(1); u16(1)
        u32(sampleRate); u32(sampleRate * 2); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(UInt32(pcmBytes))
        return d
    }
}

/// AudioFile's read and size callbacks over a `Data`.
private final class MemorySource {
    let bytes: Data
    init(_ bytes: Data) { self.bytes = bytes }

    static let read: AudioFile_ReadProc = { client, position, requestCount, buffer, actualCount in
        let me = Unmanaged<MemorySource>.fromOpaque(client).takeUnretainedValue()
        let start = Int(position)
        guard start >= 0, start <= me.bytes.count else { actualCount.pointee = 0; return kAudioFilePositionError }
        let n = min(Int(requestCount), me.bytes.count - start)
        me.bytes.withUnsafeBytes { src in
            buffer.copyMemory(from: src.baseAddress!.advanced(by: start), byteCount: n)
        }
        actualCount.pointee = UInt32(n)
        return noErr
    }

    static let size: AudioFile_GetSizeProc = { client in
        Int64(Unmanaged<MemorySource>.fromOpaque(client).takeUnretainedValue().bytes.count)
    }
}
