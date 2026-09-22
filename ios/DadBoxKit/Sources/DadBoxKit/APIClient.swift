import Foundation

public protocol HTTPTransport: Sendable {
    func send(_ request: URLRequest, body: Data?) async throws -> (Data, HTTPURLResponse)
}

extension URLSession: HTTPTransport {
    public func send(_ request: URLRequest, body: Data?) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = if let body {
            try await upload(for: request, from: body)
        } else {
            try await data(for: request)
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.notHTTP }
        return (data, http)
    }
}

public enum APIError: Error, Equatable {
    case notHTTP
    case status(Int, String)

    /// 4xx other than 408/429 will not get better by trying again.
    public var isPermanent: Bool {
        if case .status(let code, _) = self { return (400..<500).contains(code) && code != 408 && code != 429 }
        return false
    }
}

/// One client for every endpoint a parent may call (PROTOCOL.md v0.3). Every
/// write here is idempotent by the protocol's design, so callers retry blindly.
public struct APIClient: Sendable {
    public let baseURL: URL
    let token: String
    let transport: HTTPTransport

    public init(baseURL: URL, token: String, transport: HTTPTransport = URLSession.shared) {
        self.baseURL = baseURL
        self.token = token
        self.transport = transport
    }

    // MARK: Upload

    public func putMessage(_ m: Message) async throws {
        _ = try await call("PUT", "messages/\(m.id)", json: WireJSON.encoder().encode(m))
    }

    public func putChunk(id: String, seq: Int, total: Int, bytes: Data) async throws {
        _ = try await call("PUT", "messages/\(id)/chunks/\(seq)", body: bytes,
                           headers: ["X-Chunk-Total": "\(total)", "Content-Type": "application/octet-stream"])
    }

    public func uploadState(id: String) async throws -> Set<Int> {
        struct State: Decodable { var received: [Int] }
        return Set(try decode(State.self, try await call("GET", "messages/\(id)/upload-state")).received)
    }

    public func complete(id: String) async throws {
        _ = try await call("POST", "messages/\(id)/complete")
    }

    // MARK: Download

    public func audio(id: String) async throws -> Data { try await call("GET", "messages/\(id)/audio") }
    public func played(id: String) async throws { _ = try await call("POST", "messages/\(id)/played") }

    // MARK: Archive and state

    public func messages(cursor: String?, limit: Int = 100) async throws -> MessagesPage {
        var q = [URLQueryItem(name: "limit", value: "\(limit)")]
        if let cursor { q.append(URLQueryItem(name: "cursor", value: cursor)) }
        return try decode(MessagesPage.self, try await call("GET", "messages", query: q))
    }

    public func message(id: String) async throws -> Message {
        try decode(Message.self, try await call("GET", "messages/\(id)"))
    }

    public func deviceStatus() async throws -> DeviceStatus {
        try decode(DeviceStatus.self, try await call("GET", "device/status"))
    }

    public func patchSettings(_ patch: SettingsPatch) async throws -> DeviceStatus {
        try decode(DeviceStatus.self, try await call("PATCH", "settings", json: WireJSON.encoder().encode(patch)))
    }

    public func putPushToken(apnsHex: String, sandbox: Bool) async throws {
        let body = ["apns": apnsHex, "environment": sandbox ? "sandbox" : "production"]
        _ = try await call("PUT", "push-token", json: JSONEncoder().encode(body))
    }

    // MARK: -

    private func call(_ method: String, _ path: String, query: [URLQueryItem] = [],
                      json: Data? = nil, body: Data? = nil, headers: [String: String] = [:]) async throws -> Data {
        var url = baseURL.appending(path: path)
        if !query.isEmpty { url.append(queryItems: query) }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if json != nil { req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        for (k, v) in headers { req.setValue(v, forHTTPHeaderField: k) }

        let (data, http) = try await transport.send(req, body: json ?? body)
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.status(http.statusCode, String(decoding: data.prefix(200), as: UTF8.self))
        }
        return data
    }

    private func decode<T: Decodable>(_ type: T.Type, _ data: Data) throws -> T {
        try WireJSON.decoder().decode(type, from: data)
    }
}
