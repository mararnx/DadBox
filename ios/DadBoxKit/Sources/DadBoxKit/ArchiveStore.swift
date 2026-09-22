import Foundation

/// The phone's copy of the archive (ADR 0018): every container as received —
/// **ciphertext only** — plus an index that can be rebuilt from `GET /messages`
/// at any time. Lives in the app's documents, so it rides in the phone's backup.
public actor ArchiveStore {
    public struct Index: Codable, Equatable, Sendable {
        public var messages: [String: Message] = [:]
        public var heard: Set<String> = []       // box → parent messages listened to the end
        public var outbox: [String] = []         // own messages not yet confirmed by `complete`
        public var cursor: String?
        public var nextSeq = 1
        public var seqSeeded = false             // true once the server's `max_seq` has been seen
    }

    public enum StoreError: Error, Equatable {
        /// A fresh install must hear the server's `max_seq` once before it may number a message,
        /// or a reinstalled app would reuse a `seq` (PROTOCOL.md § Archive and state).
        case notSyncedYet
    }

    public private(set) var index: Index
    private let root: URL
    private var indexURL: URL { root.appending(path: "index.json") }

    public init(root: URL) throws {
        self.root = root
        try FileManager.default.createDirectory(at: root.appending(path: "Archive"), withIntermediateDirectories: true)
        let url = root.appending(path: "index.json")
        index = (try? Data(contentsOf: url)).flatMap { try? WireJSON.decoder().decode(Index.self, from: $0) } ?? Index()
    }

    // MARK: Index

    /// The conversation: between senders by the server's `uploaded_at`, within
    /// a sender by `seq` — never by `created_at`, the box may not know the time.
    public func thread() -> [Message] { Self.ordered(Array(index.messages.values)) }

    public static func ordered(_ messages: [Message]) -> [Message] {
        messages.sorted { a, b in
            if a.from == b.from { return a.seq < b.seq }
            switch (a.uploadedAt, b.uploadedAt) {
            case let (x?, y?): return x != y ? x < y : a.id < b.id
            case (nil, _?): return false           // not yet uploaded: at the bottom
            case (_?, nil): return true
            case (nil, nil): return a.id < b.id
            }
        }
    }

    /// Merge a page from the server. The server's view of state and times wins,
    /// except that a message still in our outbox stays ours until `complete`.
    public func merge(_ page: MessagesPage) throws {
        for m in page.messages where !index.outbox.contains(m.id) { index.messages[m.id] = m }
        index.cursor = page.cursor ?? index.cursor
        index.nextSeq = max(index.nextSeq, page.maxSeq + 1)
        index.seqSeeded = true
        try save()
    }

    public func update(_ m: Message) throws {
        index.messages[m.id] = m
        try save()
    }

    public func markHeard(_ id: String) throws {
        index.heard.insert(id)
        try save()
    }

    /// Own messages the box has not played yet: the few worth re-asking the server about.
    public func awaitingPlayed(by me: Identity) -> [Message] {
        index.messages.values.filter { $0.from == me && ($0.state == .uploaded || $0.state == .delivered) }
    }

    // MARK: Outbox

    /// Mint the next `seq`, keep the container, queue it — in that order, durably,
    /// before anything is sent. The caller deletes its draft only after this returns.
    public func enqueue(_ build: @Sendable (Int) throws -> (Message, Data)) throws -> Message {
        guard index.seqSeeded else { throw StoreError.notSyncedYet }
        let (message, container) = try build(index.nextSeq)
        try write(container, id: message.id)
        index.nextSeq += 1
        index.messages[message.id] = message
        index.outbox.append(message.id)
        try save()
        return message
    }

    public func dequeue(_ id: String, as state: MessageState, at: Date = Date()) throws {
        index.outbox.removeAll { $0 == id }
        index.messages[id]?.state = state
        if index.messages[id]?.uploadedAt == nil { index.messages[id]?.uploadedAt = at }
        try save()
    }

    // MARK: Containers

    public func hasContainer(_ id: String) -> Bool { FileManager.default.fileExists(atPath: url(id).path) }
    public func container(_ id: String) throws -> Data { try Data(contentsOf: url(id)) }

    /// Verifies magic, flags and CRC before keeping anything.
    public func keep(_ data: Data, id: String) throws {
        _ = try Container(decoding: data)
        try write(data, id: id)
    }

    private func write(_ data: Data, id: String) throws {
        try data.write(to: url(id), options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }

    private func url(_ id: String) -> URL { root.appending(path: "Archive/\(id).dbx") }

    private func save() throws {
        try WireJSON.encoder().encode(index)
            .write(to: indexURL, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }
}
