import Foundation
import Testing
@testable import ACEVision

private func summary(_ id: String, _ status: MatchStatus, created: String?) -> MatchSummary {
    MatchSummary(id: id, title: id, view: .net, status: status, progress: 1, error: nil, created: created,
                 durationS: 60, score: nil, defectRates: [])
}

@Test func progressionKeepsDoneMatchesInDateOrder() {
    let p = Progression.points([
        summary("a", .done, created: "2026-03-04T10:00:00"),
        summary("b", .failed, created: "2026-03-05T10:00:00"),
        summary("c", .done, created: "2026-02-01T10:00:00"),
    ])
    #expect(p.map(\.id) == ["c", "a"])
}

@Test func progressionFallsBackToIdDate() {
    let p = Progression.points([summary("2026-01-15-x", .done, created: nil)])
    #expect(p.count == 1)
}
