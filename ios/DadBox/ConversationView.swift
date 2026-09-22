import DadBoxKit
import SwiftUI

/// The one screen: both directions in one timeline, the archive above it,
/// the recorder below it, the box in one line on top (ios/DESIGN.md).
struct ConversationView: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        @Bindable var model = model
        NavigationStack {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 10) {
                        if model.thread.isEmpty { EmptyThread() }
                        ForEach(Array(model.thread.enumerated()), id: \.element.id) { i, m in
                            if i == 0 || !Calendar.current.isDate(day(m), inSameDayAs: day(model.thread[i - 1])) {
                                DayHeader(date: day(m))
                            }
                            Bubble(message: m).id(m.id)
                        }
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                }
                .defaultScrollAnchor(.bottom)
                .onChange(of: model.focusMessageID) { _, id in
                    guard let id else { return }
                    withAnimation { proxy.scrollTo(id, anchor: .center) }
                    model.focusMessageID = nil
                }
            }
            .background(Color(.systemGroupedBackground))
            .safeAreaInset(edge: .top, spacing: 0) { StatusChip().padding(.vertical, 8) }
            .safeAreaInset(edge: .bottom, spacing: 0) { RecorderBar() }
            .navigationDestination(isPresented: $model.openBox) { BoxView() }
            .toolbar(.hidden, for: .navigationBar)
            .alert("DadBox", isPresented: .constant(model.notice != nil), presenting: model.notice) { _ in
                Button("OK") { model.notice = nil }
            } message: { Text($0) }
        }
    }

    private func day(_ m: Message) -> Date { m.uploadedAt ?? m.createdAt }
}

private struct EmptyThread: View {
    var body: some View {
        ContentUnavailableView("Nothing yet", systemImage: "waveform",
                               description: Text("Messages from the box appear here. Say something first — tap the red button."))
            .padding(.top, 120)
    }
}

private struct DayHeader: View {
    let date: Date
    var body: some View {
        Text(date.formatted(.dateTime.weekday(.wide).day().month(.wide)))
            .font(.caption.weight(.medium))
            .foregroundStyle(.secondary)
            .padding(.top, 10)
    }
}

/// The Box screen in one line and one colour.
struct StatusChip: View {
    @Environment(AppModel.self) private var model

    var body: some View {
        let h = model.health
        Button { model.openBox = true } label: {
            HStack(spacing: 8) {
                Circle().fill(h.level.color).frame(width: 9, height: 9)
                Text(summary(h)).font(.subheadline.weight(.medium)).lineLimit(1)
                if model.isDemo { Text("DEMO").font(.caption2.bold()).foregroundStyle(.secondary) }
                Image(systemName: "chevron.right").font(.caption2.bold()).foregroundStyle(.tertiary)
            }
            .padding(.horizontal, 14).padding(.vertical, 8)
            .glassEffect(.regular.interactive(), in: .capsule)
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Box status: \(summary(h))")
    }

    private func summary(_ h: BoxHealth) -> String {
        var parts = ["Box", h.notes.first ?? h.headline]
        if h.level != .trouble, let t = model.status?.telemetry {
            if let pct = t.batteryPct { parts.append("\(pct) %") }
            if let last = model.status?.lastCheckinAt {
                let ago = max(0, model.now.timeIntervalSince(last))
                parts.append(ago < 90 ? "just now" : BoxHealth.span(ago) + " ago")
            }
        }
        return parts.joined(separator: " · ")
    }
}

extension BoxHealth.Level {
    var color: Color {
        switch self {
        case .fine: .green
        case .attention: .orange
        case .trouble: .red
        }
    }
}

struct Bubble: View {
    @Environment(AppModel.self) private var model
    let message: Message

    private var mine: Bool { message.from != .box }
    private var playing: Bool { model.player.playingID == message.id }
    // Heard on this phone, or the server already knows it was played (another phone, a reinstall).
    private var unheard: Bool { !mine && message.state != .played && !model.heard.contains(message.id) }

    var body: some View {
        VStack(alignment: mine ? .trailing : .leading, spacing: 4) {
            HStack(spacing: 12) {
                Button { Task { await model.toggle(message) } } label: {
                    Image(systemName: playing ? "stop.fill" : "play.fill")
                        .font(.system(size: 17, weight: .semibold))
                        .frame(width: 44, height: 44)
                        .background(mine ? Color(.tertiarySystemFill) : Color.accentColor, in: .circle)
                        .foregroundStyle(mine ? Color.primary : Color.white)
                }
                .buttonStyle(.plain)
                .accessibilityLabel(playing ? "Stop" : "Play")

                ProgressTrack(progress: playing ? model.player.progress : 0, tint: mine ? .secondary : .accentColor)
                    .frame(width: 120)
                Text(clock(message.duration)).font(.subheadline.monospacedDigit()).foregroundStyle(.secondary).fixedSize()
                if unheard { Circle().fill(Color.accentColor).frame(width: 9, height: 9).accessibilityLabel("Not heard yet") }
            }
            .padding(.horizontal, 12).padding(.vertical, 10)
            .background(mine ? Color(.secondarySystemGroupedBackground) : Color.accentColor.opacity(0.16),
                        in: .rect(cornerRadius: 22))

            Text(caption)
                .font(.caption)
                .fontWeight(message.state == .played && mine ? .semibold : .regular)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 8)
        }
        .frame(maxWidth: .infinity, alignment: mine ? .trailing : .leading)
    }

    private var caption: String {
        if mine {
            return SentStatus.line(for: message, status: model.status, health: model.health,
                                   uploadProgress: model.uploadProgress[message.id], now: model.now)
        }
        // The box has no clock battery: never invent a time it did not know (PROTOCOL.md § Message object).
        guard message.timeOK else { return "Recorded while offline" }
        let recorded = message.createdAt.formatted(date: .omitted, time: .shortened)
        if let up = message.uploadedAt, up.timeIntervalSince(message.createdAt) > 30 * 60 {
            return "\(recorded) · waited \(BoxHealth.span(up.timeIntervalSince(message.createdAt))) for a connection"
        }
        return recorded
    }
}

struct ProgressTrack: View {
    let progress: Double
    let tint: Color
    var body: some View {
        GeometryReader { g in
            ZStack(alignment: .leading) {
                Capsule().fill(tint.opacity(0.25))
                Capsule().fill(tint).frame(width: max(4, g.size.width * progress))
            }
        }
        .frame(height: 4)
    }
}

func clock(_ t: TimeInterval) -> String {
    let s = Int(t.rounded())
    return "\(s / 60):" + String(format: "%02d", s % 60)
}
