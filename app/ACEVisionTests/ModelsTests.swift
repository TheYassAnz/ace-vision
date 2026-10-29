import Foundation
import Testing
@testable import ACEVision

private final class Marker {}

private func fixture(_ name: String) throws -> Data {
    try Data(contentsOf: #require(Bundle(for: Marker.self).url(forResource: name, withExtension: nil, subdirectory: "Fixtures")
        ?? Bundle(for: Marker.self).url(forResource: name, withExtension: nil)))
}

@Test func decodesApiFixture() throws {
    let m = try JSONDecoder.ace.decode(Match.self, from: fixture("match.json"))
    #expect(m.status == .done && m.strokes.count == 2 && m.findings.first?.clipTimes.isEmpty == false)
    #expect(m.strokes[0].defects == [.latePrep] && m.settings.backhandHands == 2)
}

@Test func decodesSummaryDefectRates() throws {
    let json = #"[{"id":"a","title":"t","view":"rear","status":"done","progress":0,"error":null,"created":null,"duration_s":3.5,"score":null,"defect_rates":[{"kind":"forehand","defect":"small_turn","rate":0.5}]}]"#
    let s = try JSONDecoder.ace.decode([MatchSummary].self, from: Data(json.utf8))
    #expect(s[0].defectRates == [DefectRate(kind: .forehand, defect: .smallTurn, rate: 0.5)] && s[0].durationS == 3.5)
}
