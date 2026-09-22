import Foundation

/// The status chip, and the sentence on every message you sent. Pure functions
/// of what the server last said and the clock — so they are tested on the Mac.
public struct BoxHealth: Equatable, Sendable {
    public enum Level: Int, Comparable, Sendable {
        case fine, attention, trouble
        public static func < (a: Level, b: Level) -> Bool { a.rawValue < b.rawValue }
    }

    public var level: Level
    public var headline: String      // "Fine", "Late since 14:10", "Silent for 9 h"
    public var notes: [String]       // amber reasons: battery, mute, quiet hours, travel lock
    public var nextCheckin: Date?

    public init(status: DeviceStatus?, now: Date = Date(), calendar: Calendar = .current) {
        guard let status, let t = status.telemetry, let last = status.lastCheckinAt else {
            level = .attention
            headline = status == nil ? "No news yet" : "Never checked in"
            notes = []
            return
        }
        var level = Level.fine
        var notes: [String] = []
        let next = last.addingTimeInterval(Double(t.nextCheckinS))
        // Late after 2 × next_checkin_s — never after a fixed interval (PROTOCOL.md § Telemetry).
        let lateAt = last.addingTimeInterval(2 * Double(t.nextCheckinS))
        let silent = now.timeIntervalSince(last)

        if now > lateAt || status.late {
            level = .trouble
            headline = silent > 3 * 3600
                ? "Silent for \(Self.span(silent))"
                : "Late since \(lateAt.formatted(date: .omitted, time: .shortened))"
        } else {
            headline = "Fine"
            nextCheckin = next
        }
        if let fault = t.fault {
            level = .trouble
            notes.append("Fault: \(fault.rawValue)")
        }
        if let pct = t.batteryPct, !t.mains, pct < 20 { notes.append("Battery \(pct) %") }
        if t.locked { notes.append("Locked for travel") }
        if status.settings.mute.a || status.settings.mute.b { notes.append("Muted") }
        if Self.inQuietHours(status.settings.quietHours, at: now) { notes.append("Quiet hours") }
        if !notes.isEmpty { level = max(level, .attention) }

        self.level = level
        self.notes = notes
    }

    public static func inQuietHours(_ q: BoxSettings.QuietHours, at now: Date) -> Bool {
        guard let tz = TimeZone(identifier: q.tz), let s = minutes(q.start), let e = minutes(q.end), s != e else {
            return false
        }
        var cal = Calendar(identifier: .gregorian)
        cal.timeZone = tz
        let c = cal.dateComponents([.hour, .minute], from: now)
        let m = (c.hour ?? 0) * 60 + (c.minute ?? 0)
        return s < e ? (s..<e).contains(m) : (m >= s || m < e)   // 20:00–07:00 wraps midnight
    }

    static func minutes(_ hhmm: String) -> Int? {
        let p = hhmm.split(separator: ":").compactMap { Int($0) }
        guard p.count == 2, (0..<24).contains(p[0]), (0..<60).contains(p[1]) else { return nil }
        return p[0] * 60 + p[1]
    }

    public static func span(_ seconds: TimeInterval) -> String {
        let s = Int(seconds)
        if s < 90 { return "1 min" }
        if s < 3600 { return "\(s / 60) min" }
        if s < 48 * 3600 { return "\(s / 3600) h" }
        return "\(s / 86400) days"
    }
}

/// "Did it arrive" — the question a parent actually has (ios/DESIGN.md § Conversation).
public enum SentStatus {
    public static func line(for m: Message, status: DeviceStatus?, health: BoxHealth,
                            uploadProgress: Double? = nil, now: Date = Date()) -> String {
        let time: (Date) -> String = { $0.formatted(date: .omitted, time: .shortened) }
        switch m.state {
        case .queued:
            return "Waiting to send"
        case .uploading:
            return uploadProgress.map { "Sending… \(Int($0 * 100)) %" } ?? "Sending…"
        case .uploaded:
            if health.level == .trouble, health.headline != "Fine" { return "Sent · box is late" }
            if let next = health.nextCheckin, next > now { return "Sent · box checks in ~\(time(next))" }
            return "Sent · box checks in soon"
        case .delivered:
            if let at = m.uploadedAt, now.timeIntervalSince(at) > 48 * 3600 {
                return "On the box for \(BoxHealth.span(now.timeIntervalSince(at)))"
            }
            guard let s = status?.settings else { return "On the box" }
            if s.mute.a || s.mute.b { return "On the box · muted, it glows" }
            if BoxHealth.inQuietHours(s.quietHours, at: now) { return "On the box · quiet hours, it glows" }
            return "On the box · glowing"
        case .played:
            return m.playedAt.map { "Played \(time($0))" } ?? "Played"
        }
    }
}
