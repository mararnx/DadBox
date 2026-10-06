import Foundation

// The JSON of PROTOCOL.md v0.3, field for field. Keys are spelled out rather
// than converted, so a renamed field is a compile error here and nowhere else.

public enum Identity: String, Codable, Sendable {
    case box
    case parentA = "parent-a"
    case parentB = "parent-b"

    /// The mute flag this identity may set (`PATCH /settings`: only its own).
    public var house: String? {
        switch self {
        case .box: nil
        case .parentA: "a"
        case .parentB: "b"
        }
    }
}

public enum MessageState: String, Codable, Sendable {
    case queued, uploading, uploaded, delivered, played
}

public struct Message: Codable, Identifiable, Equatable, Sendable {
    public var id: String
    public var seq: Int
    public var from: Identity
    public var to: Identity
    public var createdAt: Date
    public var timeOK: Bool
    public var durationMs: Int
    public var codec: Codec
    public var keyID: UInt8
    public var bytes: Int
    public var state: MessageState
    public var uploadedAt: Date?
    public var deliveredAt: Date?
    public var playedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id, seq, from, to, codec, bytes, state
        case createdAt = "created_at", timeOK = "time_ok", durationMs = "duration_ms"
        case keyID = "key_id", uploadedAt = "uploaded_at"
        case deliveredAt = "delivered_at", playedAt = "played_at"
    }

    public init(id: String, seq: Int, from: Identity, to: Identity, createdAt: Date, timeOK: Bool = true,
                durationMs: Int, codec: Codec, keyID: UInt8, bytes: Int, state: MessageState,
                uploadedAt: Date? = nil, deliveredAt: Date? = nil, playedAt: Date? = nil) {
        self.id = id; self.seq = seq; self.from = from; self.to = to
        self.createdAt = createdAt; self.timeOK = timeOK; self.durationMs = durationMs
        self.codec = codec; self.keyID = keyID; self.bytes = bytes; self.state = state
        self.uploadedAt = uploadedAt; self.deliveredAt = deliveredAt; self.playedAt = playedAt
    }

    public var duration: TimeInterval { Double(durationMs) / 1000 }
}

public struct MessagesPage: Codable, Sendable {
    public var messages: [Message]
    public var cursor: String?
    public var maxSeq: Int

    enum CodingKeys: String, CodingKey { case messages, cursor, maxSeq = "max_seq" }

    public init(messages: [Message], cursor: String?, maxSeq: Int) {
        self.messages = messages; self.cursor = cursor; self.maxSeq = maxSeq
    }
}

public enum Fault: String, Codable, Sendable {
    case storage, modem, capture, charger
}

public struct Telemetry: Codable, Equatable, Sendable {
    public var batteryPct: Int?      // null while no battery is fitted (ADR 0019)
    public var charging: Bool?
    public var mains: Bool
    public var rssi: Int?            // null when the modem does not answer
    public var fw: String
    public var outbox: Int
    public var outboxBytes: Int
    public var outboxOldestS: Int
    public var storagePct: Int
    public var inbox: Int
    public var uptimeS: Int
    public var offlineS: Int
    public var nextCheckinS: Int
    public var recording: Bool
    public var locked: Bool
    public var house: String
    public var fault: Fault?
    public var doorbell: Bool?       // joined as this check-in was sent (ADR 0021); absent from an older box

    enum CodingKeys: String, CodingKey {
        case charging, mains, rssi, fw, outbox, inbox, recording, locked, house, fault, doorbell
        case batteryPct = "battery_pct", outboxBytes = "outbox_bytes", outboxOldestS = "outbox_oldest_s"
        case storagePct = "storage_pct", uptimeS = "uptime_s", offlineS = "offline_s"
        case nextCheckinS = "next_checkin_s"
    }

    public init(batteryPct: Int?, charging: Bool?, mains: Bool, rssi: Int?, fw: String, outbox: Int, outboxBytes: Int,
                outboxOldestS: Int, storagePct: Int, inbox: Int, uptimeS: Int, offlineS: Int, nextCheckinS: Int,
                recording: Bool, locked: Bool, house: String, fault: Fault?, doorbell: Bool? = nil) {
        self.batteryPct = batteryPct; self.charging = charging; self.mains = mains; self.rssi = rssi; self.fw = fw
        self.outbox = outbox; self.outboxBytes = outboxBytes; self.outboxOldestS = outboxOldestS
        self.storagePct = storagePct; self.inbox = inbox; self.uptimeS = uptimeS; self.offlineS = offlineS
        self.nextCheckinS = nextCheckinS; self.recording = recording; self.locked = locked
        self.house = house; self.fault = fault; self.doorbell = doorbell
    }
}

public struct BoxSettings: Codable, Equatable, Sendable {
    public struct Poll: Codable, Equatable, Sendable {
        public var activeMinutes: Int
        public var activeWindowMinutes: Int
        public var idleMinutes: Int
        public var backstopMinutes: Int?   // on mains with the doorbell joined (ADR 0021); absent from an older server
        enum CodingKeys: String, CodingKey {
            case activeMinutes = "active_minutes", activeWindowMinutes = "active_window_minutes"
            case idleMinutes = "idle_minutes", backstopMinutes = "backstop_minutes"
        }
        public init(activeMinutes: Int, activeWindowMinutes: Int, idleMinutes: Int, backstopMinutes: Int? = nil) {
            self.activeMinutes = activeMinutes; self.activeWindowMinutes = activeWindowMinutes
            self.idleMinutes = idleMinutes; self.backstopMinutes = backstopMinutes
        }
    }
    public struct QuietHours: Codable, Equatable, Sendable {
        public var start: String   // "20:00", box-local
        public var end: String
        public var tz: String
        public init(start: String, end: String, tz: String) { self.start = start; self.end = end; self.tz = tz }
    }

    // There is no mute (ADR 0020): a `mute` key from the server is ignored, as the box ignores it.
    public var poll: Poll
    public var quietHours: QuietHours
    public var ledBrightness: Int
    public var volume: Int

    enum CodingKeys: String, CodingKey {
        case poll, volume, quietHours = "quiet_hours", ledBrightness = "led_brightness"
    }

    public init(poll: Poll, quietHours: QuietHours, ledBrightness: Int, volume: Int) {
        self.poll = poll; self.quietHours = quietHours
        self.ledBrightness = ledBrightness; self.volume = volume
    }
}

/// `PATCH /settings` body: only what changed.
public struct SettingsPatch: Codable, Equatable, Sendable {
    public struct Poll: Codable, Equatable, Sendable {
        public var idleMinutes: Int?
        public var backstopMinutes: Int?
        enum CodingKeys: String, CodingKey { case idleMinutes = "idle_minutes", backstopMinutes = "backstop_minutes" }
        public init(idleMinutes: Int? = nil, backstopMinutes: Int? = nil) {
            self.idleMinutes = idleMinutes; self.backstopMinutes = backstopMinutes
        }
    }
    public var poll: Poll?
    public var quietHours: BoxSettings.QuietHours?
    public var ledBrightness: Int?
    public var volume: Int?

    enum CodingKeys: String, CodingKey {
        case poll, volume, quietHours = "quiet_hours", ledBrightness = "led_brightness"
    }
    public init() {}
}

public struct DeviceStatus: Codable, Equatable, Sendable {
    public struct Meta: Codable, Equatable, Sendable {
        public var by: Identity
        public var at: Date
        public init(by: Identity, at: Date) { self.by = by; self.at = at }
    }
    public var telemetry: Telemetry?        // nil until the box has checked in once
    public var lastCheckinAt: Date?
    public var late: Bool?                  // nil until the box has checked in once
    public var settings: BoxSettings
    public var settingsMeta: [String: Meta]

    enum CodingKeys: String, CodingKey {
        case telemetry, late, settings, lastCheckinAt = "last_checkin_at", settingsMeta = "settings_meta"
    }

    public init(telemetry: Telemetry?, lastCheckinAt: Date?, late: Bool?, settings: BoxSettings, settingsMeta: [String: Meta]) {
        self.telemetry = telemetry; self.lastCheckinAt = lastCheckinAt; self.late = late
        self.settings = settings; self.settingsMeta = settingsMeta
    }
}

/// What an APNs payload carries: a kind and ids — never content, never a name.
public enum PushKind: String, Codable, Sendable {
    case message, played, fault
    case boxLate = "box_late", batteryLow = "battery_low", unplayed48h = "unplayed_48h"
}

public struct PushPayload: Equatable, Sendable {
    public var kind: PushKind
    public var messageID: String?

    public init?(userInfo: [AnyHashable: Any]) {
        guard let k = userInfo["kind"] as? String, let kind = PushKind(rawValue: k) else { return nil }
        self.kind = kind
        messageID = userInfo["id"] as? String
    }
}

/// The QR the server's token script prints once (ios/DESIGN.md § Setup).
public struct SetupCode: Codable, Equatable, Sendable {
    public var v: Int
    public var url: URL
    public var identity: Identity
    public var token: String

    public init?(text: String) {
        guard let d = text.trimmingCharacters(in: .whitespacesAndNewlines).data(using: .utf8),
              let c = try? JSONDecoder().decode(SetupCode.self, from: d),
              c.v == 1, c.url.scheme == "https" || c.url.host == "localhost" || c.url.host == "127.0.0.1",
              c.identity != .box, !c.token.isEmpty else { return nil }
        self = c
    }
}

public enum WireJSON {
    /// Server timestamps come from JavaScript (`…:31.000Z`) or without fractions (`…:31Z`). Accept both.
    public static func decoder() -> JSONDecoder {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .custom { decoder in
            let s = try decoder.singleValueContainer().decode(String.self)
            if let date = parse(s) { return date }
            throw DecodingError.dataCorrupted(.init(codingPath: decoder.codingPath, debugDescription: "bad date \(s)"))
        }
        return d
    }

    public static func encoder() -> JSONEncoder {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .custom { date, encoder in
            var c = encoder.singleValueContainer()
            try c.encode(date.formatted(.iso8601))
        }
        e.outputFormatting = [.sortedKeys]
        return e
    }

    static func parse(_ s: String) -> Date? {
        (try? Date(s, strategy: .iso8601))
            ?? (try? Date(s, strategy: Date.ISO8601FormatStyle(includingFractionalSeconds: true)))
    }
}
