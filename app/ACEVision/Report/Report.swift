import Foundation

struct RallySummary: Equatable {
    let n: Int
    let mean: String
    let max: String
}

struct Report {
    let match: Match
    let counts: [StrokeKind: Int]
    let rallies: RallySummary?

    init(_ m: Match) {
        match = m
        counts = Dictionary(grouping: m.strokes, by: \.kind).mapValues(\.count)
        if m.view == .rear, let r = m.rallies {
            let long = r.map(\.nHits).filter { $0 >= 2 }  // a lone hit is not an exchange length
            let mean = long.isEmpty ? "—" : (Double(long.reduce(0, +)) / Double(long.count)).formatted(.number.precision(.fractionLength(1)).locale(frFR))
            rallies = RallySummary(n: r.count, mean: mean, max: long.max().map { $0.formatted(.number.locale(frFR)) } ?? "—")
        } else {
            rallies = nil
        }
    }

    func count(_ k: StrokeKind) -> Int { counts[k] ?? 0 }

    var coverageNotice: String? {
        guard let c = match.coverage, c < 0.8 else { return nil }
        return "Tu n'as été repéré que sur \(c.percentText) de la vidéo : les chiffres ne portent que sur cette partie."
    }

    var noFindingsText: String {
        match.nUnmeasured * 2 > count(.forehand) + count(.backhand) + count(.serve)
            ? "La vidéo ne permet pas de mesurer ta technique de façon fiable sur ce match."
            : "Aucun défaut ne revient assez souvent sur ce match pour en tirer un conseil."
    }

    var reliability: String? {
        match.score.map { "Fiabilité : \($0.foundRate.percentText) de tes coups trouvés, \($0.classRate.percentText) bien classés" }
    }
}
