import Foundation
import Testing
@testable import ACEVision

func makeMatch(view: CourtView = .net, status: MatchStatus = .done, strokes: [Stroke] = [], rallies: [Rally]? = nil,
               score: Score? = nil, coverage: Double? = nil, nUnmeasured: Int = 0) -> Match {
    Match(id: "m", title: "t", view: view, status: status, progress: 0, error: nil, videoFile: "v.mov", info: nil,
          settings: Settings(handedness: .right, backhandHands: 2), strokes: strokes, rallies: rallies, findings: [],
          score: score, coverage: coverage, nUnmeasured: nUnmeasured)
}

func rally(_ n: Int) -> Rally {
    Rally(startT: 0, endT: 1, nHits: n, end: .net, lastStroke: nil, userHitLast: true, isServeFault: false)
}

func stroke(_ k: StrokeKind) -> Stroke { Stroke(t: 1, frame: 30, kind: k, defects: [], outcome: .unknown) }

@Test func ofTotalPlural() {
    #expect(ofTotal(1, 25, .forehand) == "1 coup droit sur 25" && ofTotal(11, 25, .forehand) == "11 coups droits sur 25")
}

@Test func rallySummaryIgnoresSingleHits() {
    let r = Report(makeMatch(view: .rear, rallies: [rally(1), rally(3), rally(4)])).rallies
    #expect(r == RallySummary(n: 3, mean: "3,5", max: "4"))
}

@Test func netViewHasNoRallySummary() {
    #expect(Report(makeMatch(view: .net, rallies: [rally(3)])).rallies == nil)
}

@Test func reliabilityUsesFrenchPercent() {
    let s = Score(nNotes: 8, nDetected: 7, foundRate: 0.92, classRate: 0.875, falseHits: 0)
    #expect(Report(makeMatch(score: s)).reliability == "Fiabilité : 92\u{00A0}% de tes coups trouvés, 88\u{00A0}% bien classés")
}

@Test func coverageNoticeBelow80() {
    #expect(Report(makeMatch(coverage: 0.62)).coverageNotice?.contains("que sur 62\u{00A0}% de la vidéo") == true)
    #expect(Report(makeMatch(coverage: 0.85)).coverageNotice == nil)
}

@Test func unmeasuredReplacesNoDefectSentence() {
    let strokes = [stroke(.forehand), stroke(.backhand)]
    #expect(Report(makeMatch(strokes: strokes, nUnmeasured: 2)).noFindingsText.hasPrefix("La vidéo ne permet pas"))
    #expect(Report(makeMatch(strokes: strokes, nUnmeasured: 1)).noFindingsText.hasPrefix("Aucun défaut"))
}

@Test func clockHasNoPaddedMinutes() { #expect(clock(192) == "3:12") }
