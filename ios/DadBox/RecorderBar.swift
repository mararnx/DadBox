import DadBoxKit
import SwiftUI

/// Tap, tap, review, send. Red means the microphone is on — the same word the box uses.
struct RecorderBar: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let r = model.recorder
        VStack(spacing: 10) {
            switch r.state {
            case .idle: idle
            case .recording: recording
            case .review: review
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.top, 12).padding(.bottom, 6)
        .background(.bar)
        .animation(.snappy, value: r.state)
        .alert("Microphone is off for DadBox", isPresented: Bindable(r).denied) {
            Button("Open Settings") { UIApplication.shared.open(URL(string: UIApplication.openSettingsURLString)!) }
            Button("Cancel", role: .cancel) {}
        } message: { Text("Allow the microphone in Settings to record a message.") }
    }

    private var idle: some View {
        Button { model.player.stop(); Task { await model.recorder.start() } } label: {
            Circle().fill(.red).frame(width: 62, height: 62)
                .overlay(Circle().strokeBorder(.white.opacity(0.9), lineWidth: 3).padding(5))
        }
        .accessibilityLabel("Record a message")
    }

    private var recording: some View {
        let r = model.recorder
        return VStack(spacing: 10) {
            HStack(spacing: 10) {
                LevelMeter(level: r.level)
                Text(clock(r.elapsed))
                    .font(.title3.monospacedDigit().weight(.medium))
                    .foregroundStyle(r.elapsed >= Recorder.gentleMark ? .orange : .primary)
                Text("of 5:00").font(.footnote).foregroundStyle(.secondary)
            }
            Button { r.stop() } label: {
                RoundedRectangle(cornerRadius: 8).fill(.red).frame(width: 28, height: 28)
                    .frame(width: 62, height: 62)
                    .overlay(Circle().strokeBorder(.red, lineWidth: 3))
            }
            .accessibilityLabel("Stop recording")
        }
    }

    private var review: some View {
        let playing = model.player.playingID == "draft"
        return VStack(spacing: 10) {
            if let hint = deliveryHint {
                Label(hint, systemImage: "moon.zzz").font(.footnote).foregroundStyle(.secondary)
            }
            HStack(spacing: 14) {
                Button(role: .destructive) { model.player.stop(); model.recorder.discard() } label: {
                    Image(systemName: "trash").frame(width: 44, height: 44)
                }
                .accessibilityLabel("Discard and record again")

                Button { listen() } label: {
                    HStack(spacing: 8) {
                        Image(systemName: playing ? "stop.fill" : "play.fill")
                        ProgressTrack(progress: playing ? model.player.progress : 0, tint: .secondary).frame(minWidth: 40, maxWidth: 90)
                        Text(clock(model.recorder.draft?.duration ?? 0)).monospacedDigit().fixedSize()
                    }
                    .padding(.horizontal, 14).frame(height: 44)
                    .background(Color(.tertiarySystemFill), in: .capsule)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(playing ? "Stop" : "Listen to your recording")

                Button { model.player.stop(); Task { await model.sendDraft() } } label: {
                    Label("Send", systemImage: "arrow.up").fontWeight(.semibold).padding(.horizontal, 6).frame(height: 30)
                }
                .buttonStyle(.borderedProminent)
                .buttonBorderShape(.capsule)
            }
        }
    }

    private func listen() {
        if model.player.playingID == "draft" { model.player.stop(); return }
        guard let url = model.recorder.draft?.url, let data = try? Data(contentsOf: url) else { return }
        try? model.player.play(id: "draft", audio: data) {}
    }

    /// What the box will do with it. Sending is never blocked — quiet hours are the device's job.
    private var deliveryHint: String? {
        guard let s = model.status else { return nil }
        if model.health.level == .trouble { return "The box is out of touch — this arrives when it's back." }
        if s.settings.mute.a || s.settings.mute.b { return "The box is muted — it will glow, not chime." }
        if BoxHealth.inQuietHours(s.settings.quietHours, at: model.now) {
            return "Quiet hours until \(s.settings.quietHours.end) — it will glow, not chime."
        }
        return nil
    }
}

private struct LevelMeter: View {
    let level: Double
    var body: some View {
        HStack(spacing: 3) {
            ForEach(0..<5, id: \.self) { i in
                Capsule().fill(.red.opacity(level > Double(i) / 5 ? 1 : 0.25))
                    .frame(width: 4, height: 8 + CGFloat(i) * 3)
            }
        }
        .accessibilityHidden(true)
    }
}
