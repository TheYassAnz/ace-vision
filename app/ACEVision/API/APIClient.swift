import Foundation

struct APIError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
    static let unreachable = APIError(message: "Le moteur d'analyse ne répond pas. Quitte et relance ACE Vision ; le détail est dans engine.log.")
}

final class APIClient: Sendable {
    private let base: URL
    private let token: String

    init(port: Int, token: String) {
        base = URL(string: "http://127.0.0.1:\(port)")!
        self.token = token
    }

    private struct Detail: Decodable { let detail: String }
    private struct Queued: Decodable { let queued: Bool }

    private func send(_ method: String, _ path: String, body: (any Encodable & Sendable)? = nil, timeout: TimeInterval = 30) async throws -> Data {
        var req = URLRequest(url: base.appending(path: path))
        req.httpMethod = method
        req.timeoutInterval = timeout
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            req.httpBody = try JSONEncoder.ace.encode(body)
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let data: Data, resp: URLResponse
        do { (data, resp) = try await URLSession.shared.data(for: req) } catch { throw APIError.unreachable }
        guard let http = resp as? HTTPURLResponse else { throw APIError.unreachable }
        guard (200..<300).contains(http.statusCode) else {
            throw (try? JSONDecoder().decode(Detail.self, from: data)).map { APIError(message: $0.detail) } ?? APIError.unreachable
        }
        return data
    }

    private func get<T: Decodable>(_ path: String) async throws -> T {
        try decode(await send("GET", path))
    }

    private func decode<T: Decodable>(_ data: Data) throws -> T {
        do { return try JSONDecoder.ace.decode(T.self, from: data) } catch { throw APIError.unreachable }
    }

    func health() async throws { _ = try await send("GET", "/health") }
    func matches() async throws -> [MatchSummary] { try await get("/matchs") }
    func match(_ id: String) async throws -> Match { try await get("/matchs/\(id)") }

    func importVideo(path: URL, view: CourtView, title: String) async throws -> ImportResult {
        struct Body: Encodable, Sendable { let path: String; let view: CourtView; let title: String }
        return try decode(await send("POST", "/matchs", body: Body(path: path.path, view: view, title: title), timeout: 3600))  // the engine copies the whole video first
    }

    func relaunch(_ id: String) async throws -> Bool {
        let q: Queued = try decode(await send("POST", "/matchs/\(id)/relancer"))
        return q.queued
    }

    func delete(_ id: String) async throws { _ = try await send("DELETE", "/matchs/\(id)") }
    func notes(_ id: String) async throws -> [Note] { try await get("/matchs/\(id)/notes") }

    func saveNotes(_ id: String, _ notes: [Note]) async throws -> Score {
        try decode(await send("POST", "/matchs/\(id)/notes", body: notes))
    }

    func settings() async throws -> Settings { try await get("/reglages") }
    func saveSettings(_ s: Settings) async throws -> Settings { try decode(await send("PUT", "/reglages", body: s)) }
}
