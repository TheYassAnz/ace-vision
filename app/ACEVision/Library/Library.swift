import Foundation
import Observation

protocol MatchListing: Sendable { func matches() async throws -> [MatchSummary] }
extension APIClient: MatchListing {}

@MainActor @Observable
final class Library {
    var matches: [MatchSummary] = []
    /// Reserved selection id for the Progression row (match ids are "yyyy-MM-dd-slug").
    static let progressionId = "__progression__"
    var selection: String?
    var error: String?
    var onFinished: ((MatchSummary) -> Void)?
    private let api: any MatchListing

    init(api: any MatchListing) { self.api = api }

    nonisolated static func finished(old: [MatchSummary], new: [MatchSummary]) -> [MatchSummary] {
        let wasRunning = Set(old.filter { $0.status == .running }.map(\.id))
        return new.filter { wasRunning.contains($0.id) && ($0.status == .done || $0.status == .failed) }
    }

    func refresh() async {
        do {
            let new = try await api.matches()
            Library.finished(old: matches, new: new).forEach { onFinished?($0) }
            matches = new
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    func poll() async {
        while !Task.isCancelled {
            await refresh()
            let delay: Duration = matches.contains { $0.status == .running } ? .seconds(2) : .seconds(10)
            try? await Task.sleep(for: delay)
        }
    }
}
