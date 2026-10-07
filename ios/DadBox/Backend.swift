import CryptoKit
import DadBoxKit
import Foundation

/// What the app asks of the world. `LiveBackend` is PROTOCOL.md over HTTPS;
/// `DemoBackend` is a box and a server in memory, for the simulator and for
/// looking at the app before either exists.
protocol Backend: Sendable {
    func messages(cursor: String?) async throws -> MessagesPage
    func message(id: String) async throws -> Message
    func audio(id: String) async throws -> Data
    func played(id: String) async throws
    func deviceStatus() async throws -> DeviceStatus
    func patchSettings(_ patch: SettingsPatch) async throws -> DeviceStatus
    func putPushToken(apnsHex: String, sandbox: Bool, liveActivityHex: String?) async throws
    func upload(_ message: Message, container: Data, progress: @escaping @Sendable (Double) -> Void) async throws
}

nonisolated struct LiveBackend: Backend {
    let api: APIClient

    func messages(cursor: String?) async throws -> MessagesPage { try await api.messages(cursor: cursor) }
    func message(id: String) async throws -> Message { try await api.message(id: id) }
    func audio(id: String) async throws -> Data { try await api.audio(id: id) }
    func played(id: String) async throws { try await api.played(id: id) }
    func deviceStatus() async throws -> DeviceStatus { try await api.deviceStatus() }
    func patchSettings(_ patch: SettingsPatch) async throws -> DeviceStatus { try await api.patchSettings(patch) }
    func putPushToken(apnsHex: String, sandbox: Bool, liveActivityHex: String?) async throws {
        try await api.putPushToken(apnsHex: apnsHex, sandbox: sandbox, liveActivityHex: liveActivityHex)
    }
    func upload(_ message: Message, container: Data, progress: @escaping @Sendable (Double) -> Void) async throws {
        try await Uploader(api: api).upload(message, container: container, progress: progress)
    }
}

/// A pretend family. Everything goes through the real container and the real
/// envelope — the demo clips are genuine Ogg Opus, sealed with a throwaway key.
actor DemoBackend: Backend {
    nonisolated static let key = SymmetricKey(data: Data(repeating: 0xDB, count: 32))
    nonisolated static let keys = StaticKeys([1: key])

    private var messages: [Message] = []
    private var blobs: [String: Data] = [:]
    private var settings = BoxSettings(poll: .init(activeMinutes: 1, activeWindowMinutes: 90, idleMinutes: 30, backstopMinutes: 10),
                                       quietHours: .init(start: "20:00", end: "07:00", tz: TimeZone.current.identifier),
                                       ledBrightness: 40, volume: 70)
    private var meta: [String: DeviceStatus.Meta] = [:]
    private let started = Date()

    init() {
        let now = Date()
        func clip(_ n: Int) -> Data {
            Bundle.main.url(forResource: "demo\(n)", withExtension: "opus").flatMap { try? Data(contentsOf: $0) } ?? Data()
        }
        // (clip, seconds ago recorded, seconds ago uploaded, time_ok)
        let fromBox: [(Int, TimeInterval, TimeInterval, Bool)] = [
            (1, 26 * 3600, 26 * 3600 - 20, true), (2, 5 * 3600, 3 * 3600, false), (3, 240, 200, true),
        ]
        for (i, (n, recorded, uploaded, timeOK)) in fromBox.enumerated() {
            let id = ULID(date: now - recorded)
            let audio = clip(n)
            let ms = [4860, 4200, 1800][n - 1]
            let sealed = (try? Envelope.seal(audio: audio, header: .init(codec: .oggOpus, durationMs: UInt32(ms)),
                                             id: id, keyID: 1, key: Self.key).encoded()) ?? Data()
            blobs[id.string] = sealed
            messages.append(Message(id: id.string, seq: 181 + i, from: .box, to: .parentA, createdAt: now - recorded,
                                    timeOK: timeOK, durationMs: ms, codec: .oggOpus, keyID: 1, bytes: sealed.count,
                                    state: i == 0 ? .played : .delivered, uploadedAt: now - uploaded,
                                    deliveredAt: now - uploaded + 5, playedAt: i == 0 ? now - 25 * 3600 : nil))
        }
    }

    func messages(cursor: String?) async throws -> MessagesPage {
        advance()
        return MessagesPage(messages: messages, cursor: "demo", maxSeq: messages.filter { $0.from == .parentA }.map(\.seq).max() ?? 0)
    }

    func message(id: String) async throws -> Message {
        advance()
        guard let m = messages.first(where: { $0.id == id }) else { throw APIError.status(404, "") }
        return m
    }

    func audio(id: String) async throws -> Data {
        guard let d = blobs[id] else { throw APIError.status(404, "") }
        return d
    }

    func played(id: String) async throws {
        guard let i = messages.firstIndex(where: { $0.id == id }) else { return }
        messages[i].state = .played
        messages[i].playedAt = Date()
    }

    func deviceStatus() async throws -> DeviceStatus {
        let up = Int(Date().timeIntervalSince(started))
        return DeviceStatus(
            telemetry: Telemetry(batteryPct: 82, charging: false, mains: true, rssi: -87, fw: "0.1.0-demo", outbox: 0,
                                 outboxBytes: 0, outboxOldestS: 0, storagePct: 12,
                                 inbox: messages.filter { $0.to == .box && $0.state == .delivered }.count,
                                 uptimeS: 41_022 + up, offlineS: 0, nextCheckinS: 60, recording: false, locked: false,
                                 house: "unknown", fault: nil, doorbell: true),
            lastCheckinAt: Date().addingTimeInterval(-Double(up % 60)), late: false, settings: settings, settingsMeta: meta)
    }

    func patchSettings(_ patch: SettingsPatch) async throws -> DeviceStatus {
        let stamp = DeviceStatus.Meta(by: .parentA, at: Date())
        if let v = patch.quietHours { settings.quietHours = v; meta["quiet_hours"] = stamp }
        if let v = patch.volume { settings.volume = v; meta["volume"] = stamp }
        if let v = patch.ledBrightness { settings.ledBrightness = v; meta["led_brightness"] = stamp }
        if let v = patch.poll?.idleMinutes { settings.poll.idleMinutes = v; meta["poll"] = stamp }
        if let v = patch.poll?.backstopMinutes { settings.poll.backstopMinutes = v; meta["poll"] = stamp }
        return try await deviceStatus()
    }

    func putPushToken(apnsHex: String, sandbox: Bool, liveActivityHex: String?) async throws {}

    func upload(_ message: Message, container: Data, progress: @escaping @Sendable (Double) -> Void) async throws {
        _ = try Container(decoding: container)
        for step in 1...5 {
            try await Task.sleep(for: .milliseconds(250))
            progress(Double(step) / 5)
        }
        var m = message
        m.state = .uploaded
        m.uploadedAt = Date()
        blobs[m.id] = container
        messages.removeAll { $0.id == m.id }
        messages.append(m)
    }

    /// The pretend box checks in, fetches, and a pretend child presses play.
    private func advance() {
        let now = Date()
        for i in messages.indices where messages[i].to == .box {
            guard let up = messages[i].uploadedAt else { continue }
            if messages[i].state == .uploaded, now.timeIntervalSince(up) > 6 {
                messages[i].state = .delivered
                messages[i].deliveredAt = up + 6
            }
            if messages[i].state == .delivered, now.timeIntervalSince(up) > 20 {
                messages[i].state = .played
                messages[i].playedAt = up + 20
            }
        }
    }
}
