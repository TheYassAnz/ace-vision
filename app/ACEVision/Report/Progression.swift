import Foundation

struct ProgressionPoint: Identifiable, Hashable {
    let id: String
    let title: String
    let date: Date
    let foundRate: Double?
    let classRate: Double?
    let defectRates: [DefectRate]
}

enum Progression {
    /// Done matches in date order; the date is `created`, else the "yyyy-MM-dd" prefix of the id.
    /// Matches with no readable date are left out (they cannot be placed on the axis).
    static func points(_ ms: [MatchSummary]) -> [ProgressionPoint] {
        ms.compactMap { m -> ProgressionPoint? in
            guard m.status == .done,
                  let date = m.created.flatMap({ parseCreated($0) }) ?? idDate(m.id) else { return nil }
            return ProgressionPoint(id: m.id, title: m.title.isEmpty ? m.id : m.title, date: date,
                                    foundRate: m.score?.foundRate, classRate: m.score?.classRate, defectRates: m.defectRates)
        }
        .sorted { ($0.date, $0.id) < ($1.date, $1.id) }
    }

    private static func idDate(_ id: String) -> Date? {
        try? Date(String(id.prefix(10)), strategy: Date.ISO8601FormatStyle(timeZone: .current).year().month().day())
    }
}
