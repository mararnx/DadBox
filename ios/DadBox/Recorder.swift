import AVFoundation
import Observation

/// idle → recording → review. Nothing here can send: a recording always stops
/// into review, whether by a tap, the five-minute cap, or a phone call.
@Observable
final class Recorder: NSObject, AVAudioRecorderDelegate {
    struct Draft: Equatable {
        let url: URL
        let duration: TimeInterval
    }

    enum State: Equatable { case idle, recording, review }

    static let cap: TimeInterval = 5 * 60        // same as the box (PROTOCOL.md § Audio format)
    static let gentleMark: TimeInterval = 2 * 60  // the timer changes colour; nothing stops
    static let minimum: TimeInterval = 1

    private(set) var state = State.idle
    private(set) var draft: Draft?
    private(set) var elapsed: TimeInterval = 0
    private(set) var level: Double = 0           // 0…1, for the meter
    var denied = false

    private var recorder: AVAudioRecorder?
    private var ticker: Task<Void, Never>?
    private var interruption: NSObjectProtocol?

    private static var draftURL: URL {
        let dir = URL.applicationSupportDirectory.appending(path: "Draft")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appending(path: "draft.m4a")
    }

    override init() {
        super.init()
        // One draft, and it survives the app being killed.
        let url = Self.draftURL
        if let d = try? AVAudioPlayer(contentsOf: url).duration, d >= Self.minimum {
            draft = Draft(url: url, duration: d)
            state = .review
        }
    }

    func start() async {
        guard state == .idle else { return }
        guard await AVAudioApplication.requestRecordPermission() else { denied = true; return }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .spokenAudio, options: [.defaultToSpeaker])
            try session.setActive(true)
            // AAC-LC, 16 kHz mono, 24 kbps → `codec = 3`. Written to disk as it is recorded.
            let r = try AVAudioRecorder(url: Self.draftURL, settings: [
                AVFormatIDKey: kAudioFormatMPEG4AAC, AVSampleRateKey: 16_000, AVNumberOfChannelsKey: 1,
                AVEncoderBitRateKey: 24_000, AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
            ])
            r.delegate = self
            r.isMeteringEnabled = true
            guard r.record(forDuration: Self.cap) else { throw CocoaError(.fileWriteUnknown) }
            recorder = r
            elapsed = 0
            state = .recording
            ticker = Task { [weak self] in
                while !Task.isCancelled, let self, let r = self.recorder {
                    r.updateMeters()
                    self.elapsed = r.currentTime
                    self.level = max(0, min(1, (Double(r.averagePower(forChannel: 0)) + 50) / 50))
                    try? await Task.sleep(for: .milliseconds(60))
                }
            }
            interruption = NotificationCenter.default.addObserver(
                forName: AVAudioSession.interruptionNotification, object: nil, queue: .main
            ) { [weak self] _ in MainActor.assumeIsolated { self?.stop() } }
        } catch {
            finish(keeping: false)
        }
    }

    func stop() {
        guard state == .recording else { return }
        elapsed = recorder?.currentTime ?? elapsed
        recorder?.stop()          // → audioRecorderDidFinishRecording
    }

    func discard() {
        try? FileManager.default.removeItem(at: Self.draftURL)
        draft = nil
        state = .idle
        elapsed = 0
    }

    private func finish(keeping: Bool) {
        ticker?.cancel()
        recorder = nil
        level = 0
        if let interruption { NotificationCenter.default.removeObserver(interruption) }
        interruption = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)

        let url = Self.draftURL
        let duration = (try? AVAudioPlayer(contentsOf: url).duration) ?? 0
        if keeping, duration >= Self.minimum {      // under a second: discarded, same rule as the box
            draft = Draft(url: url, duration: duration)
            state = .review
        } else {
            discard()
        }
    }

    nonisolated func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        Task { @MainActor in self.finish(keeping: flag) }
    }
}
