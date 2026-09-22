import Foundation

/// A container cut into the protocol's 32 KB chunks.
public struct UploadPlan: Equatable, Sendable {
    public static let chunkSize = 32 * 1024
    public let total: Int
    private let data: Data

    public init(container: Data) {
        data = Data(container)
        total = max(1, (data.count + Self.chunkSize - 1) / Self.chunkSize)
    }

    public func chunk(_ seq: Int) -> Data {
        let start = seq * Self.chunkSize
        return data.subdata(in: start..<min(start + Self.chunkSize, data.count))
    }

    /// What is still to send, given what the server says it has.
    public func missing(received: Set<Int>) -> [Int] {
        (0..<total).filter { !received.contains($0) }
    }
}

/// metadata → ask what arrived → the gaps → complete. Safe to run again from
/// the top at any time, from any process: every step is idempotent.
public struct Uploader: Sendable {
    let api: APIClient
    public init(api: APIClient) { self.api = api }

    public func upload(_ message: Message, container: Data,
                       progress: (@Sendable (Double) -> Void)? = nil) async throws {
        let plan = UploadPlan(container: container)
        try await api.putMessage(message)
        let todo = plan.missing(received: try await api.uploadState(id: message.id))
        for (n, seq) in todo.enumerated() {
            try await api.putChunk(id: message.id, seq: seq, total: plan.total, bytes: plan.chunk(seq))
            progress?(Double(plan.total - todo.count + n + 1) / Double(plan.total))
        }
        try await api.complete(id: message.id)
    }
}
