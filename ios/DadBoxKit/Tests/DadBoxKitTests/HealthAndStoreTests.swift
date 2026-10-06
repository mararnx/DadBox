import Foundation
import Testing
@testable import DadBoxKit

let t0 = Date(timeIntervalSince1970: 1_789_988_000)   // 2026-09-21T10:53:20Z = 12:53 in Europe/Berlin (CEST)

func status(nextCheckinS: Int = 1800, battery: Int? = 68, mains: Bool = false, fault: Fault? = nil,
            locked: Bool = false, doorbell: Bool? = nil, quiet: (String, String) = ("20:00", "07:00")) -> DeviceStatus {
    DeviceStatus(
        telemetry: Telemetry(batteryPct: battery, charging: false, mains: mains, rssi: -91, fw: "0.1.0", outbox: 0,
                             outboxBytes: 0, outboxOldestS: 0, storagePct: 12, inbox: 0, uptimeS: 100, offlineS: 0,
                             nextCheckinS: nextCheckinS, recording: false, locked: locked, house: "unknown", fault: fault,
                             doorbell: doorbell),
        lastCheckinAt: t0, late: false,
        settings: BoxSettings(poll: .init(activeMinutes: 1, activeWindowMinutes: 90, idleMinutes: 30, backstopMinutes: 10),
                              quietHours: .init(start: quiet.0, end: quiet.1, tz: "Europe/Berlin"),
                              ledBrightness: 40, volume: 70),
        settingsMeta: [:])
}

@Suite struct BoxHealthTests {
    @Test func lateIsTwiceTheBoxsOwnIntervalNotAFixedOne() {
        // Idle on battery: next check-in in 30 min. Quiet for 59 min is fine; 61 min is late.
        #expect(BoxHealth(status: status(), now: t0 + 59 * 60).level == .fine)
        #expect(BoxHealth(status: status(), now: t0 + 61 * 60).level == .trouble)
        // On mains it checks in every minute: three minutes of silence is already late.
        #expect(BoxHealth(status: status(nextCheckinS: 60, mains: true), now: t0 + 180).level == .trouble)
    }

    @Test func headlineGoesFromLateToSilent() {
        #expect(BoxHealth(status: status(), now: t0 + 2 * 3600).headline.hasPrefix("Late since"))
        #expect(BoxHealth(status: status(), now: t0 + 9 * 3600).headline == "Silent for 9 h")
        #expect(BoxHealth(status: status(), now: t0 + 3 * 86400).headline == "Silent for 3 days")
    }

    @Test func amberReasons() {
        #expect(BoxHealth(status: status(battery: 18), now: t0).notes == ["Battery 18 %"])
        #expect(BoxHealth(status: status(battery: 18, mains: true), now: t0).level == .fine)   // low but charging from the wall
        #expect(BoxHealth(status: status(battery: nil, mains: true), now: t0).level == .fine)  // no battery fitted (ADR 0019)
        #expect(BoxHealth(status: status(locked: true), now: t0 + 2 * 60).notes == ["Locked for travel · next check-in in 28 min"])
        #expect(BoxHealth(status: status(locked: true), now: t0).level == .attention)
        #expect(BoxHealth(status: status(fault: .storage), now: t0).level == .trouble)
        #expect(BoxHealth(status: nil, now: t0).headline == "No news yet")
    }

    @Test func lateIsUnknownBeforeTheFirstCheckin() {
        var s = status()
        s.late = nil
        #expect(BoxHealth(status: s, now: t0).level == .fine)
    }

    @Test func deliverySaysDoorbellJustUsedAndLock() {
        func words(_ s: DeviceStatus) -> String { BoxHealth.delivery(s.telemetry!) }
        #expect(words(status(nextCheckinS: 600, mains: true, doorbell: true)) == "At once — the doorbell is connected")
        #expect(words(status(nextCheckinS: 15, mains: true, doorbell: false)) == "Within 15 s — the child just used it")
        #expect(words(status(nextCheckinS: 60, mains: true, doorbell: false)) == "Within 1 min — the doorbell is not connected")
        #expect(words(status(nextCheckinS: 1800, mains: true, locked: true, doorbell: false)) == "At its next check-in — locked, every 30 min")
        #expect(words(status(nextCheckinS: 1800)) == "Within 30 min")      // an older box sends no doorbell
    }

    @Test func quietHoursWrapMidnightInTheBoxsTimezone() {
        let q = BoxSettings.QuietHours(start: "20:00", end: "07:00", tz: "Europe/Berlin")
        #expect(!BoxHealth.inQuietHours(q, at: t0))                       // 12:53 local
        #expect(BoxHealth.inQuietHours(q, at: t0 + 8 * 3600))             // 20:53
        #expect(BoxHealth.inQuietHours(q, at: t0 + 17 * 3600))            // 05:53 next day
        #expect(!BoxHealth.inQuietHours(q, at: t0 + 19 * 3600))           // 07:53
        let day = BoxSettings.QuietHours(start: "12:00", end: "14:00", tz: "Europe/Berlin")
        #expect(BoxHealth.inQuietHours(day, at: t0))
        #expect(!BoxHealth.inQuietHours(.init(start: "8pm", end: "07:00", tz: "Europe/Berlin"), at: t0))
    }
}

@Suite struct SentStatusTests {
    func sent(_ state: MessageState, uploaded: Date? = t0, played: Date? = nil) -> Message {
        Message(id: testID.string, seq: 1, from: .parentA, to: .box, createdAt: t0, durationMs: 42_000,
                codec: .aacM4A, keyID: 1, bytes: 1, state: state, uploadedAt: uploaded, playedAt: played)
    }

    func line(_ m: Message, _ s: DeviceStatus, now: Date, progress: Double? = nil) -> String {
        SentStatus.line(for: m, status: s, health: BoxHealth(status: s, now: now), uploadProgress: progress, now: now)
    }

    @Test func tellsTheWholeStory() {
        #expect(line(sent(.uploading, uploaded: nil), status(), now: t0, progress: 0.5) == "Sending… 50 %")
        #expect(line(sent(.uploaded), status(), now: t0 + 60).hasPrefix("Sent · box checks in ~"))
        #expect(line(sent(.uploaded), status(), now: t0 + 2 * 3600) == "Sent · box is late")
        #expect(line(sent(.uploaded), status(nextCheckinS: 600, mains: true, doorbell: true), now: t0 + 60) == "Sent · ringing the box")
        #expect(line(sent(.delivered), status(), now: t0 + 60) == "On the box · glowing")
        #expect(line(sent(.delivered), status(quiet: ("12:00", "14:00")), now: t0 + 60) == "On the box · quiet hours, it glows")
        #expect(line(sent(.delivered), status(), now: t0 + 50 * 3600) == "On the box for 2 days")
        #expect(line(sent(.played, played: t0 + 300), status(), now: t0 + 600).hasPrefix("Played "))
    }
}

@Suite struct ArchiveStoreTests {
    let root = FileManager.default.temporaryDirectory.appending(path: "dadbox-tests-\(UUID().uuidString)")

    func msg(_ id: String, _ seq: Int, from: Identity, uploaded: TimeInterval?, state: MessageState = .uploaded) -> Message {
        Message(id: id, seq: seq, from: from, to: from == .box ? .parentA : .box, createdAt: t0, durationMs: 1000,
                codec: .oggOpus, keyID: 1, bytes: 1, state: state, uploadedAt: uploaded.map { t0 + $0 })
    }

    @Test func ordersBySeqWithinASenderAndUploadTimeBetweenThem() {
        // The box was offline: seq 7 and 8 upload together, *after* the parent's message — but keep their order.
        let thread = ArchiveStore.ordered([
            msg("C", 8, from: .box, uploaded: 101), msg("P", 3, from: .parentA, uploaded: 50),
            msg("B", 7, from: .box, uploaded: 101), msg("A", 6, from: .box, uploaded: 10),
            msg("Q", 4, from: .parentA, uploaded: nil, state: .uploading),
        ])
        #expect(thread.map(\.id) == ["A", "P", "B", "C", "Q"])
    }

    @Test func survivesARestartAndContinuesTheSeqCounter() async throws {
        let sealed = try Envelope.seal(audio: Data([1, 2, 3]), header: .init(codec: .aacM4A, durationMs: 1000),
                                       id: testID, keyID: 1, key: testKey).encoded()
        do {
            let store = try ArchiveStore(root: root)
            try await store.merge(MessagesPage(messages: [msg("A", 6, from: .box, uploaded: 10)], cursor: "c1", maxSeq: 41))
            let m = try await store.enqueue { seq in
                (Message(id: testID.string, seq: seq, from: .parentA, to: .box, createdAt: t0, durationMs: 1000,
                         codec: .aacM4A, keyID: 1, bytes: sealed.count, state: .queued), sealed)
            }
            #expect(m.seq == 42)   // a reinstalled app continues from the server's max_seq, never reuses one
        }
        let again = try ArchiveStore(root: root)
        #expect(await again.index.outbox == [testID.string])
        #expect(await again.index.cursor == "c1")
        #expect(await again.index.nextSeq == 43)
        #expect(try await again.container(testID.string) == sealed)

        // A stale page from the server must not clobber a message still in the outbox.
        try await again.merge(MessagesPage(messages: [msg(testID.string, 42, from: .parentA, uploaded: nil, state: .uploading)],
                                           cursor: "c2", maxSeq: 42))
        #expect(await again.index.messages[testID.string]?.state == .queued)
        try await again.dequeue(testID.string, as: .uploaded, at: t0)
        #expect(await again.index.outbox.isEmpty)
        #expect(await again.awaitingPlayed(by: .parentA).map(\.id) == [testID.string])
        try? FileManager.default.removeItem(at: root)
    }

    @Test func aTakenSeqIsRenumberedAboveTheServersMax() async throws {
        let sealed = try Envelope.seal(audio: Data([1, 2, 3]), header: .init(codec: .aacM4A, durationMs: 1000),
                                       id: testID, keyID: 1, key: testKey).encoded()
        let store = try ArchiveStore(root: root)
        try await store.merge(MessagesPage(messages: [], cursor: nil, maxSeq: 3))
        _ = try await store.enqueue { seq in
            (Message(id: testID.string, seq: seq, from: .parentA, to: .box, createdAt: t0, durationMs: 1000,
                     codec: .aacM4A, keyID: 1, bytes: sealed.count, state: .queued), sealed)
        }
        let m = try await store.renumber(testID.string, above: 41)    // ADR 0025: the server holds up to 41
        #expect(m.seq == 42)
        #expect(try await ArchiveStore(root: root).index.messages[testID.string]?.seq == 42)   // durable before the retry
        #expect(await store.index.nextSeq == 43)
        try await store.dequeue(testID.string, as: .uploaded)
        await #expect(throws: ArchiveStore.StoreError.notInOutbox) { try await store.renumber(testID.string, above: 50) }
        try? FileManager.default.removeItem(at: root)
    }

    @Test func aFreshInstallMayNotNumberAMessageBeforeItHasSynced() async throws {
        let store = try ArchiveStore(root: root)
        await #expect(throws: ArchiveStore.StoreError.notSyncedYet) {
            try await store.enqueue { _ in fatalError("must not be asked for a message") }
        }
        try await store.merge(MessagesPage(messages: [], cursor: nil, maxSeq: 0))   // a brand-new family: nothing yet
        let index = await store.index
        #expect(index.nextSeq == 1 && index.seqSeeded)
        try? FileManager.default.removeItem(at: root)
    }

    @Test func refusesToKeepADamagedContainer() async throws {
        let store = try ArchiveStore(root: root)
        await #expect(throws: ContainerError.self) { try await store.keep(Data(count: 64), id: "X") }
        #expect(await !store.hasContainer("X"))
        try? FileManager.default.removeItem(at: root)
    }
}
