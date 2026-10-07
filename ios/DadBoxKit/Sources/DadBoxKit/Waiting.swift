import Foundation

/// The lock screen's "message waiting" (ADR 0027; PROTOCOL.md § Live Activity).
/// The server starts it with a push; the app ends it once the message is heard.

/// What a tap on it opens: `dadbox://message/<id>`.
public enum MessageLink {
    public static func url(id: String) -> URL {
        URL(string: "dadbox://message/\(id)") ?? URL(string: "dadbox://message")!
    }

    public static func messageID(from url: URL) -> String? {
        guard url.scheme == "dadbox", url.host() == "message" else { return nil }
        let id = url.lastPathComponent
        return ULID(id) == nil ? nil : id
    }
}

#if canImport(ActivityKit) && os(iOS)
import ActivityKit

/// The type's name is the push's `attributes-type`; the property names are its JSON keys.
/// Renaming either is a protocol change.
public struct WaitingAttributes: ActivityAttributes, Sendable {
    public struct ContentState: Codable, Hashable, Sendable {
        /// When the message reached the server, in Unix seconds. An integer on purpose:
        /// ActivityKit decodes a pushed `Date` as seconds since 2001.
        public var since: Int

        public init(since: Int) { self.since = since }
        public var date: Date { Date(timeIntervalSince1970: TimeInterval(since)) }
    }

    /// The message a tap opens. An id, never content (ADR 0017).
    public var id: String

    public init(id: String) { self.id = id }
}

/// ActivityKit's objects stay on this side of the package boundary; the app sees strings.
public enum WaitingActivity {
    /// The push-to-start token as hex: the one iOS holds now, then every rotation.
    public static func startTokens() -> AsyncStream<String> {
        AsyncStream { continuation in
            let task = Task {
                func hex(_ token: Data) -> String { token.map { String(format: "%02x", $0) }.joined() }
                if let token = Activity<WaitingAttributes>.pushToStartToken { continuation.yield(hex(token)) }
                for await token in Activity<WaitingAttributes>.pushToStartTokenUpdates { continuation.yield(hex(token)) }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// Takes "message waiting" off the lock screen for these messages.
    public static func end(for messageIDs: Set<String>) async {
        for activity in Activity<WaitingAttributes>.activities where messageIDs.contains(activity.attributes.id) {
            await activity.end(nil, dismissalPolicy: .immediate)
        }
    }
}
#endif
