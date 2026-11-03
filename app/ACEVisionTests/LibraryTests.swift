import Testing
@testable import ACEVision

private func s(_ id: String, _ status: MatchStatus) -> MatchSummary {
    MatchSummary(id: id, title: id, view: .net, status: status, progress: 0, error: nil, created: nil, durationS: nil, score: nil, defectRates: [])
}

@Test func finishedDetectsRunningToDone() {
    #expect(Library.finished(old: [s("a", .running), s("b", .running)], new: [s("a", .done), s("b", .running)]).map(\.id) == ["a"])
}

@Test func finishedDetectsRunningToFailed() {
    #expect(Library.finished(old: [s("a", .running)], new: [s("a", .failed)]).map(\.id) == ["a"])
    #expect(Library.finished(old: [s("a", .pending)], new: [s("a", .done)]).isEmpty)
}

@Test func newTitleSkipsBlankAndUnchanged() {
    #expect(Library.newTitle("  Finale ", old: "a") == "Finale")
    #expect(Library.newTitle("   ", old: "a") == nil)
    #expect(Library.newTitle("a ", old: "a") == nil)
}

private struct Stub: MatchListing { let result: [MatchSummary]; func matches() async throws -> [MatchSummary] { result } }

@MainActor @Test func refreshNotifiesOnFinish() async {
    let lib = Library(api: Stub(result: [s("a", .done)]))
    lib.matches = [s("a", .running)]
    var got: [String] = []
    lib.onFinished = { got.append($0.id) }
    await lib.refresh()
    #expect(got == ["a"] && lib.matches.first?.status == .done)
}
