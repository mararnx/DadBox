import Foundation

/// The status chip, and the sentence on every message you sent. Pure functions
/// of what the server last said and the clock — so they are tested on the Mac.
public struct BoxHealth: Equatable, Sendable {
    public enum Level: Int, Comparable, Sendable {
        case fine, attention, trouble
        public static func < (a: Level, b: Level) -> Bool { a.rawValue < b.rawValue }
    }

    public var level: Level
    public var headline: String      // "Fine", "Late since 14:10", "Silent for 9 h", "No news since 22:00"
    public var notes: [String]       // amber reasons: battery, quiet hours, travel lock
    public var nextCheckin: Date?

    /// How long a status read may be old before the phone stops judging the box by it.
    /// The app reads every 5-20 s, so two missed reads plus slack.
    public static let staleRead: TimeInterval = 90

    /// `readAt` is when this phone last got a status from the server. When it is older than
    /// `staleRead`, the phone, not the box, is out of touch: say so, and never call the box late.
    public init(status: DeviceStatus?, now: Date = Date(), readAt: Date? = nil, calendar: Calendar = .current) {
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

        if let readAt, now.timeIntervalSince(readAt) > Self.staleRead {
            level = .attention
            headline = "No news since \(readAt.formatted(date: .omitted, time: .shortened))"
            notes.append("This phone can't read the box's status from the server")
        } else if now > lateAt || status.late == true {
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
        if t.locked {
            // A locked box checks in only every idle_minutes, on any power: say when, not "offline" (ADR 0015).
            notes.append(nextCheckin.map { "Locked for travel · next check-in in \(Self.span($0.timeIntervalSince(now)))" }
                         ?? "Locked for travel")
        }
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

    /// How soon a message sent now reaches the box: the doorbell and the cadence in words
    /// (PROTOCOL.md § Check-in; ADR 0015, 0021).
    public static func delivery(_ t: Telemetry) -> String {
        let every = span(Double(t.nextCheckinS))
        if t.locked { return "At its next check-in — locked, every \(every)" }
        if t.doorbell == true { return "At once — the doorbell is connected" }
        if t.nextCheckinS <= 20 { return "Within 15 s — the child just used it" }
        if t.doorbell == false, t.mains { return "Within \(every) — the doorbell is not connected" }
        return "Within \(every)"
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
            if let t = status?.telemetry, t.doorbell == true, !t.locked { return "Sent · ringing the box" }
            if let next = health.nextCheckin, next > now { return "Sent · box checks in ~\(time(next))" }
            return "Sent · box checks in soon"
        case .delivered:
            if let at = m.uploadedAt, now.timeIntervalSince(at) > 48 * 3600 {
                return "On the box for \(BoxHealth.span(now.timeIntervalSince(at)))"
            }
            guard let s = status?.settings else { return "On the box" }
            if BoxHealth.inQuietHours(s.quietHours, at: now) { return "On the box · quiet hours, it glows" }
            return "On the box · glowing"
        case .played:
            return m.playedAt.map { "Played \(time($0))" } ?? "Played"
        }
    }
}
