import AVFoundation
import Foundation
import Testing
@testable import DadBoxKit

/// A 6 s Ogg Opus tone made by the box's own encoder (ffmpeg libopus, 16 kbit/s, voip):
/// short enough that `AVAudioPlayer(data:)` refuses to play it as Ogg.
private func shortOgg() throws -> Data {
    let url = try #require(Bundle.module.url(forResource: "tone-6s", withExtension: "ogg", subdirectory: "Fixtures"))
    return try Data(contentsOf: url)
}

@Test func aShortBoxMessageDecodesToAPlayableWAV() throws {
    let wav = try WAVDecoder.wav(from: try shortOgg())
    #expect(wav.prefix(4) == Data("RIFF".utf8))
    let seconds = Double(wav.count - 44) / 2 / 48_000
    #expect(abs(seconds - 6.0) < 0.05)
    let player = try AVAudioPlayer(data: wav)
    #expect(player.prepareToPlay())
}

@Test func garbageIsAnErrorNotACrash() {
    #expect(throws: WAVDecoder.DecodeError.self) { try WAVDecoder.wav(from: Data(repeating: 7, count: 200)) }
}
