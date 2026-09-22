import Foundation
import Testing
@testable import DadBoxKit

/// The JSON here is copied from docs/PROTOCOL.md v0.3. If the document changes, so do these.
@Suite struct WireModelTests {
    @Test func decodesTheProtocolsMessageObject() throws {
        let json = """
        { "id": "01JAYZ3K7QW9E8RVX2M4N6P8TD", "seq": 184, "from": "box", "to": "parent-a",
          "created_at": "2026-09-20T18:04:11Z", "time_ok": true, "duration_ms": 14200, "codec": 2,
          "key_id": 1, "bytes": 113600, "state": "delivered",
          "uploaded_at": "2026-09-20T18:04:31.000Z", "delivered_at": "2026-09-20T18:04:40Z", "played_at": null }
        """
        let m = try WireJSON.decoder().decode(Message.self, from: Data(json.utf8))
        #expect(m.from == .box && m.to == .parentA && m.codec == .oggOpus && m.state == .delivered)
        #expect(m.uploadedAt == m.createdAt.addingTimeInterval(20))   // fractional and plain seconds both parse
        #expect(m.playedAt == nil)
        let again = try WireJSON.decoder().decode(Message.self, from: WireJSON.encoder().encode(m))
        #expect(again == m)
    }

    @Test func decodesDeviceStatusWithNoBatteryFitted() throws {
        let json = """
        { "telemetry": { "battery_pct": null, "charging": null, "mains": true, "rssi": -91, "fw": "0.1.0",
            "outbox": 0, "outbox_bytes": 0, "outbox_oldest_s": 0, "storage_pct": 12, "inbox": 2,
            "uptime_s": 41022, "offline_s": 0, "next_checkin_s": 60, "recording": false, "locked": false,
            "house": "unknown", "fault": null },
          "last_checkin_at": "2026-09-21T10:00:00Z", "late": false,
          "settings": { "poll": { "active_minutes": 1, "active_window_minutes": 90, "idle_minutes": 30 },
            "mute": { "a": false, "b": true },
            "quiet_hours": { "start": "20:00", "end": "07:00", "tz": "Europe/Berlin" },
            "led_brightness": 40, "volume": 70 },
          "settings_meta": { "mute.b": { "by": "parent-b", "at": "2026-09-21T09:30:00Z" } } }
        """
        let s = try WireJSON.decoder().decode(DeviceStatus.self, from: Data(json.utf8))
        #expect(s.telemetry?.batteryPct == nil && s.telemetry?.mains == true)
        #expect(s.settings.mute.b && s.settingsMeta["mute.b"]?.by == .parentB)
    }

    @Test func aPatchCarriesOnlyWhatChanged() throws {
        var p = SettingsPatch()
        p.mute = ["a": true]
        p.volume = 55
        #expect(String(decoding: try WireJSON.encoder().encode(p), as: UTF8.self) == #"{"mute":{"a":true},"volume":55}"#)
    }

    @Test func setupCodeAcceptsOnlyAParentOverHTTPS() {
        #expect(SetupCode(text: #"{"v":1,"url":"https://x.example/api","identity":"parent-a","token":"t"}"#)?.identity == .parentA)
        #expect(SetupCode(text: #"{"v":1,"url":"http://x.example/api","identity":"parent-a","token":"t"}"#) == nil)
        #expect(SetupCode(text: #"{"v":1,"url":"https://x.example/api","identity":"box","token":"t"}"#) == nil)
        #expect(SetupCode(text: #"{"v":1,"url":"http://localhost:8787","identity":"parent-a","token":"t"}"#) != nil)
    }
}

/// A server in a dictionary: enough of PROTOCOL.md § Upload to prove resume and idempotency.
final class FakeServer: HTTPTransport, @unchecked Sendable {
    private let lock = NSLock()
    private(set) var chunks: [String: [Int: Data]] = [:]
    private(set) var completed: [String: Data] = [:]
    private(set) var log: [String] = []
    var failChunkOnce: Int?

    func send(_ request: URLRequest, body: Data?) async throws -> (Data, HTTPURLResponse) {
        lock.withLock { handle(request, body: body) }
    }

    private func handle(_ request: URLRequest, body: Data?) -> (Data, HTTPURLResponse) {
        let parts = request.url!.path.split(separator: "/").map(String.init)
        let method = request.httpMethod!
        log.append("\(method) \(parts.dropFirst().joined(separator: "/"))")
        func reply(_ code: Int, _ json: String = "{}") -> (Data, HTTPURLResponse) {
            (Data(json.utf8), HTTPURLResponse(url: request.url!, statusCode: code, httpVersion: nil, headerFields: nil)!)
        }
        guard request.value(forHTTPHeaderField: "Authorization") == "Bearer secret" else { return reply(401) }
        guard parts.count >= 3, parts[1] == "messages" else { return reply(404) }
        let id = parts[2]
        switch (method, parts.dropFirst(3).first, parts.count) {
        case ("PUT", nil, _):
            chunks[id, default: [:]] = chunks[id] ?? [:]
            return reply(200)
        case ("PUT", "chunks"?, 5):
            let seq = Int(parts[4])!
            if failChunkOnce == seq { failChunkOnce = nil; return reply(503) }
            chunks[id, default: [:]][seq] = body!
            return reply(200)
        case ("GET", "upload-state"?, _):
            return reply(200, #"{"received":\#((chunks[id] ?? [:]).keys.sorted())}"#)
        case ("POST", "complete"?, _):
            let got = chunks[id] ?? [:]
            let blob = got.keys.sorted().reduce(Data()) { $0 + got[$1]! }
            guard (try? Container(decoding: blob)) != nil else { return reply(422) }
            completed[id] = blob
            return reply(200)
        default:
            return reply(404)
        }
    }
}

@Suite struct UploadTests {
    let api: APIClient
    let server = FakeServer()
    let container: Data
    let message: Message

    init() throws {
        api = APIClient(baseURL: URL(string: "https://example.test/v1")!, token: "secret", transport: server)
        let audio = Data((0..<100_000).map { UInt8(truncatingIfNeeded: $0 &* 31) })   // → 4 chunks
        container = try Envelope.seal(audio: audio, header: .init(codec: .aacM4A, durationMs: 30_000),
                                      id: testID, keyID: 1, key: testKey).encoded()
        message = Message(id: testID.string, seq: 1, from: .parentA, to: .box, createdAt: Date(),
                          durationMs: 30_000, codec: .aacM4A, keyID: 1, bytes: container.count, state: .queued)
    }

    @Test func planCutsThirtyTwoKilobyteChunks() {
        let plan = UploadPlan(container: container)
        #expect(plan.total == 4)
        #expect((0..<4).reduce(Data()) { $0 + plan.chunk($1) } == container)
        #expect(plan.missing(received: [0, 2]) == [1, 3])
        #expect(UploadPlan(container: Data(count: 32 * 1024)).total == 1)
    }

    @Test func uploadsAndTheServerAssemblesTheSameBytes() async throws {
        try await Uploader(api: api).upload(message, container: container)
        #expect(server.completed[testID.string] == container)
    }

    @Test func resumesFromTheGapsAfterAFailure() async throws {
        server.failChunkOnce = 2
        await #expect(throws: APIError.status(503, "{}")) {
            try await Uploader(api: api).upload(message, container: container)
        }
        #expect(server.completed.isEmpty)
        let before = server.log.count
        try await Uploader(api: api).upload(message, container: container)
        #expect(server.completed[testID.string] == container)
        let second = server.log.dropFirst(before).filter { $0.contains("chunks/") }
        #expect(second == ["PUT messages/\(testID)/chunks/2", "PUT messages/\(testID)/chunks/3"])
    }

    @Test func aBadTokenIsPermanentAndAnOutageIsNot() async {
        let bad = APIClient(baseURL: api.baseURL, token: "wrong", transport: server)
        do { try await bad.complete(id: "x"); Issue.record("should have thrown") } catch let e as APIError {
            #expect(e.isPermanent)
        } catch { Issue.record("\(error)") }
        #expect(!APIError.status(503, "").isPermanent)
    }
}
