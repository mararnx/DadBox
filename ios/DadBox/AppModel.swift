import CryptoKit
import DadBoxKit
import Observation
import SwiftUI

@Observable
final class AppModel {
    enum Phase { case loading, setup, ready }

    private(set) var phase = Phase.loading
    private(set) var thread: [Message] = []
    private(set) var heard: Set<String> = []
    private(set) var status: DeviceStatus?
    private(set) var statusReadAt: Date?     // when the server last answered; older than a minute or so, the news is ours to doubt
    private(set) var uploadProgress: [String: Double] = [:]
    private(set) var isDemo = false
    private(set) var me = Identity.parentA
    private(set) var now = Date()            // ticks, so "late" and "checks in ~19:30" stay true on screen
    var focusMessageID: String?              // set by a notification tap
    var openBox = false
    var notice: String?

    let player = AudioPlayer()
    let recorder = Recorder()
    let keychain = Keychain()

    private var backend: Backend?
    private var store: ArchiveStore?
    private var keys: KeyProvider = Keychain()
    private var pumping = false
    private var pushToken: String?
    private var liveActivityToken: String?   // ActivityKit push-to-start (ADR 0027)
    private var ticker: Task<Void, Never>?

    var health: BoxHealth { BoxHealth(status: status, now: now, readAt: statusReadAt) }
    var keyID: UInt8 { me == .parentB ? 2 : 1 }      // PROTOCOL.md § Encryption: the first key of each parent
    var hasKey: Bool { keys.key(id: keyID) != nil }
    var unheardCount: Int { thread.filter { $0.from == .box && $0.state != .played && !heard.contains($0.id) }.count }

    // MARK: Lifecycle

    func start() async {
        guard phase == .loading else { return }
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-demo") {
            await enterDemo()
            await runDebugHooks()
            return
        }
        #endif
        guard let setup = keychain.setup, hasKey else { phase = .setup; return }
        await enter(setup)
    }

    func enter(_ setup: SetupCode) async {
        me = setup.identity
        keys = keychain
        isDemo = false
        await open(LiveBackend(api: APIClient(baseURL: setup.url, token: setup.token)), folder: "live")
    }

    func enterDemo() async {
        me = .parentA
        keys = DemoBackend.keys
        isDemo = true
        // The demo's archive is thrown away each time; the real one never is.
        try? FileManager.default.removeItem(at: Self.root("demo"))
        await open(DemoBackend(), folder: "demo")
    }

    func signOut() {
        ticker?.cancel()
        player.stop()
        if !isDemo { keychain.forgetSetup() }
        backend = nil; store = nil; thread = []; status = nil; statusReadAt = nil
        phase = .setup
    }

    private static func root(_ folder: String) -> URL {
        URL.documentsDirectory.appending(path: folder)     // in Documents: rides in the phone's backup (ADR 0018)
    }

    private func open(_ backend: Backend, folder: String) async {
        do {
            let store = try ArchiveStore(root: Self.root(folder))
            self.store = store
            self.backend = backend
            await reload()
            phase = .ready                      // show the archive we have at once; the news follows
            await refresh()
            if let pushToken { await register(pushToken: pushToken) }
            ticker?.cancel()
            ticker = Task { [weak self] in
                // Pushes are hints; the truth is what the server says when asked (PROTOCOL.md § Push).
                while !Task.isCancelled {
                    try? await Task.sleep(for: .seconds(self?.refreshInterval ?? 20))
                    await self?.refresh()
                }
            }
        } catch {
            notice = "Can't open the archive: \(error.localizedDescription)"
            phase = .setup
        }
    }

    private func reload() async {
        guard let store else { return }
        thread = await store.thread()
        heard = await store.index.heard
    }

    // MARK: Sync

    /// While one of my messages is on its way and not yet played, ask every 5 s, so
    /// "On the box" and "Played" show up while the parent is watching. Foreground only.
    var refreshInterval: Int {
        if isDemo { return 3 }
        return thread.contains { $0.from == me && $0.state != .played } ? 5 : 20
    }

    func refresh() async {
        guard let backend, let store else { now = Date(); return }
        // Status on its own: a status the app can't read must not stop the messages, and must
        // show as stale news rather than as a late box (BoxHealth.staleRead). The clock moves
        // after the read, so a return to the foreground doesn't flash "No news" while it runs.
        let fresh = try? await backend.deviceStatus()
        now = Date()
        if let fresh {
            status = fresh
            statusReadAt = now
        }
        do {
            var cursor = await store.index.cursor
            for _ in 0..<50 {
                let page = try await backend.messages(cursor: cursor)
                try await store.merge(page)
                if page.messages.isEmpty || page.cursor == nil || page.cursor == cursor { break }
                cursor = page.cursor
            }
            for m in await store.awaitingPlayed(by: me) {
                if let fresh = try? await backend.message(id: m.id), fresh != m { try await store.update(fresh) }
            }
            await reload()
            // Our `played` may not have reached the server last time. Say it again; it is idempotent.
            for m in thread where m.from == .box && m.state != .played && heard.contains(m.id) {
                try? await backend.played(id: m.id)
            }
            await fetchMissingAudio()
            await pumpOutbox()
        } catch {
            // Offline is not an event. The chip goes amber by itself when the news gets old.
        }
        await settleWaiting()
    }

    /// The server puts "message waiting" on the lock screen; the phone takes it off once nothing
    /// from the box is left unheard (ADR 0027). Only for messages this phone already knows, so
    /// one that arrived a moment ago keeps its place until the thread has caught up with it.
    private func settleWaiting() async {
        guard !isDemo, unheardCount == 0 else { return }
        await WaitingActivity.end(for: Set(thread.map(\.id)))
    }

    /// The phone keeps its own copy of every message (ADR 0018). Newest first, so what you want to hear is there first.
    private func fetchMissingAudio() async {
        guard let backend, let store else { return }
        for m in thread.reversed() where await !store.hasContainer(m.id) && m.state != .queued && m.state != .uploading {
            guard let data = try? await backend.audio(id: m.id) else { continue }
            try? await store.keep(data, id: m.id)
        }
    }

    // MARK: Listening

    func toggle(_ m: Message) async {
        if player.playingID == m.id { player.stop(); return }
        guard let backend, let store else { return }
        if await !store.hasContainer(m.id) {
            do { try await store.keep(try await backend.audio(id: m.id), id: m.id) } catch {
                notice = "Can't fetch this message right now — it will be fetched when there's a connection."
                return
            }
        }
        do {
            guard let id = ULID(m.id) else { return }
            // Decrypted in memory, played from memory. Plaintext never touches the disk.
            let audio = try Envelope.open(try Container(decoding: try await store.container(m.id)), id: id, keys: keys)
            try player.play(id: m.id, audio: audio) { [weak self] in
                Task { await self?.finishedListening(to: m) }
            }
        } catch EnvelopeError.unknownKey(let k) {
            notice = "This message needs key \(k), which isn't on this phone."
        } catch EnvelopeError.authenticationFailed {
            notice = "This message failed its integrity check and was not played."
        } catch {
            notice = "This message is on the phone but couldn't be played."
        }
    }

    private func finishedListening(to m: Message) async {
        guard m.from == .box, !heard.contains(m.id), let store else { return }
        try? await store.markHeard(m.id)
        heard.insert(m.id)
        try? await backend?.played(id: m.id)
        await refresh()
    }

    // MARK: Sending

    /// Seal the draft, put it in the outbox durably, and only then let the draft go.
    func sendDraft() async {
        guard let store, let draft = recorder.draft, let key = keys.key(id: keyID) else {
            notice = "No key on this phone — messages can't be sealed."
            return
        }
        do {
            let audio = try Data(contentsOf: draft.url)
            let id = ULID()
            let from = me, keyID = keyID
            let header = Container.Header(codec: .aacM4A, durationMs: UInt32(draft.duration * 1000))
            let sealed = try Envelope.seal(audio: audio, header: header, id: id, keyID: keyID, key: key).encoded()
            _ = try await store.enqueue { seq in
                (Message(id: id.string, seq: seq, from: from, to: .box, createdAt: Date(), durationMs: Int(header.durationMs),
                         codec: .aacM4A, keyID: keyID, bytes: sealed.count, state: .queued), sealed)
            }
            recorder.discard()
            await reload()
            focusMessageID = id.string
            await pumpOutbox()
        } catch ArchiveStore.StoreError.notSyncedYet {
            notice = "This phone hasn't reached the server yet. Your recording is kept — send it once there's a connection."
        } catch {
            notice = "Couldn't prepare the message. Your recording is still here."
        }
    }

    private func pumpOutbox() async {
        guard !pumping, let backend, let store else { return }
        pumping = true
        defer { pumping = false }
        let task = UIApplication.shared.beginBackgroundTask(withName: "upload")
        defer { UIApplication.shared.endBackgroundTask(task) }

        for id in await store.index.outbox {
            guard var m = await store.index.messages[id], let container = try? await store.container(id) else { continue }
            m.state = .uploading
            try? await store.update(m)
            await reload()
            let progress: @Sendable (Double) -> Void = { [weak self] p in
                Task { @MainActor in self?.uploadProgress[id] = p }
            }
            do {
                do {
                    try await backend.upload(m, container: container, progress: progress)
                } catch APIError.seqTaken(let maxSeq) {
                    // A reinstall reused a seq the server holds (ADR 0025): renumber, durably, and send once more.
                    m = try await store.renumber(id, above: maxSeq)
                    try await backend.upload(m, container: container, progress: progress)
                }
                try await store.dequeue(id, as: .uploaded)
            } catch let e as APIError where e.isPermanent {
                notice = "The server refused a message (\(e)). It stays in the outbox."
                break
            } catch {
                m.state = .queued                       // no link: it goes when there is one
                try? await store.update(m)
                await reload()
                break
            }
            uploadProgress[id] = nil
            await reload()
        }
    }

    // MARK: Box

    func patch(_ build: (inout SettingsPatch) -> Void) async {
        guard let backend else { return }
        var p = SettingsPatch()
        build(&p)
        do { status = try await backend.patchSettings(p); statusReadAt = Date() } catch {
            notice = "The setting wasn't saved — no connection to the server."
        }
    }

    // MARK: Push

    func register(pushToken hex: String) async {
        pushToken = hex
        #if DEBUG
        let sandbox = true
        #else
        let sandbox = false
        #endif
        try? await backend?.putPushToken(apnsHex: hex, sandbox: sandbox, liveActivityHex: liveActivityToken)
    }

    /// iOS hands out the token that lets the server start "message waiting", and rotates it when
    /// it likes. It travels with the device token; until there is one, it waits here.
    func watchLiveActivityToken() async {
        for await hex in WaitingActivity.startTokens() where hex != liveActivityToken {
            liveActivityToken = hex
            if let pushToken { await register(pushToken: pushToken) }
        }
    }

    /// A tap on "message waiting" (`dadbox://message/<id>`): the conversation, at the message.
    func open(_ url: URL) async {
        guard let id = MessageLink.messageID(from: url) else { return }
        await refresh()
        focusMessageID = id
    }

    func handle(push: PushPayload, tapped: Bool) async {
        await refresh()
        guard tapped else { return }
        switch push.kind {
        case .message, .unplayed48h, .played: focusMessageID = push.messageID ?? thread.last?.id
        case .boxLate, .fault, .batteryLow: openBox = true
        }
    }
}
