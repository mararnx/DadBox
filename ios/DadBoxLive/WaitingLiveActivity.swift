import ActivityKit
import DadBoxKit
import SwiftUI
import WidgetKit

/// "Message waiting · 12:04" — on the lock screen and in the Dynamic Island from the moment a
/// message from the box reaches the server until it has been heard (ADR 0027).
///
/// It knows an id and a second. The minutes are counted here; nothing on it is content, and
/// nothing on it needs a push to stay true.
struct WaitingLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: WaitingAttributes.self) { context in
            LockScreen(since: context.state.date)
                .activityBackgroundTint(Color.black.opacity(0.8))
                .activitySystemActionForegroundColor(.white)
                .widgetURL(MessageLink.url(id: context.attributes.id))
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    Glyph().font(.title2).padding(.leading, 4)
                }
                DynamicIslandExpandedRegion(.center) {
                    VStack(spacing: 2) {
                        Text("Message waiting").font(.headline)
                        Text("since \(context.state.date, style: .time)").font(.caption).foregroundStyle(.secondary)
                    }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    Waited(since: context.state.date).font(.title3).padding(.trailing, 4)
                }
            } compactLeading: {
                Glyph()
            } compactTrailing: {
                Waited(since: context.state.date).frame(maxWidth: 52)
            } minimal: {
                Glyph()
            }
            .keylineTint(Color.boxAmber)
            .widgetURL(MessageLink.url(id: context.attributes.id))
        }
    }
}

private struct LockScreen: View {
    let since: Date

    var body: some View {
        HStack(spacing: 14) {
            Glyph()
                .font(.title2)
                .frame(width: 44, height: 44)
                .background(Color.boxAmber.opacity(0.2), in: Circle())
            VStack(alignment: .leading, spacing: 2) {
                Text("Message waiting").font(.headline).foregroundStyle(.white)
                Text("since \(since, style: .time)").font(.subheadline).foregroundStyle(.white.opacity(0.7))
            }
            Spacer(minLength: 8)
            Waited(since: since).font(.title2)
        }
        .padding(16)
    }
}

/// How long it has been waiting. Counts up by itself; the system redraws it.
private struct Waited: View {
    let since: Date

    var body: some View {
        Text(since, style: .timer)
            .monospacedDigit()
            .multilineTextAlignment(.trailing)
            .foregroundStyle(Color.boxAmber)
    }
}

private struct Glyph: View {
    var body: some View {
        Image(systemName: "waveform").foregroundStyle(Color.boxAmber)
    }
}

private extension Color {
    /// The box's bubbles in the conversation.
    static let boxAmber = Color(red: 0.91, green: 0.66, blue: 0.36)
}
