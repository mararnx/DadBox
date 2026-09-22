import AVFoundation
import Observation
import UIKit

/// Plays one message from memory. The box's Ogg Opus and the phone's own M4A
/// both go straight into `AVAudioPlayer` — iOS 26 reads Ogg natively.
@Observable
final class AudioPlayer: NSObject, AVAudioPlayerDelegate {
    private(set) var playingID: String?
    private(set) var progress: Double = 0

    private var player: AVAudioPlayer?
    private var onFinish: (() -> Void)?
    private var ticker: Task<Void, Never>?
    private var proximity: NSObjectProtocol?

    func play(id: String, audio: Data, onFinish: @escaping () -> Void) throws {
        stop()
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playback, mode: .spokenAudio)
        try session.setActive(true)

        let p = try AVAudioPlayer(data: audio)
        p.delegate = self
        guard p.play() else { throw CocoaError(.fileReadCorruptFile) }
        player = p
        playingID = id
        self.onFinish = onFinish
        ticker = Task { [weak self] in
            while !Task.isCancelled, let self, let p = self.player {
                self.progress = p.duration > 0 ? p.currentTime / p.duration : 0
                try? await Task.sleep(for: .milliseconds(50))
            }
        }
        watchProximity()
    }

    func stop() {
        ticker?.cancel()
        player?.stop()
        player = nil
        playingID = nil
        progress = 0
        onFinish = nil
        UIDevice.current.isProximityMonitoringEnabled = false
        if let proximity { NotificationCenter.default.removeObserver(proximity) }
        proximity = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    /// Raise to the ear → earpiece. The receiver route needs `.playAndRecord`, so the
    /// session only takes that category while the phone is actually at an ear —
    /// an app about a child's voice should not hold a recording category idly.
    private func watchProximity() {
        UIDevice.current.isProximityMonitoringEnabled = true
        proximity = NotificationCenter.default.addObserver(
            forName: UIDevice.proximityStateDidChangeNotification, object: nil, queue: .main
        ) { _ in
            MainActor.assumeIsolated {
                let near = UIDevice.current.proximityState
                try? AVAudioSession.sharedInstance().setCategory(near ? .playAndRecord : .playback, mode: .spokenAudio)
            }
        }
    }

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in
            let done = flag ? self.onFinish : nil
            self.stop()
            done?()
        }
    }
}
