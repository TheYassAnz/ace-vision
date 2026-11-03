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
    var renameError: String?
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

    /// The title to send, or nil when it is blank or unchanged.
    nonisolated static func newTitle(_ typed: String, old: String) -> String? {
        let t = typed.trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty || t == old ? nil : t
    }

    func rename(_ id: String, to typed: String, api: APIClient) async {
        guard let m = matches.first(where: { $0.id == id }), let title = Library.newTitle(typed, old: m.title) else { return }
        do {
            try await api.rename(id, title: title)
            await refresh()
        } catch {
            let e = error.localizedDescription
            renameError = e == "Ce match est en cours d'analyse." ? e + " Attends la fin de l'analyse puis réessaie." : e
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
