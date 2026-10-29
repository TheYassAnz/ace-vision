import Foundation

let frFR = Locale(identifier: "fr_FR")

extension StrokeKind {
    var label: String {
        switch self { case .forehand: "Coup droit"; case .backhand: "Revers"; case .serve: "Service"; case .other: "Autre" }
    }
    var plural: String {
        switch self { case .forehand: "coups droits"; case .backhand: "revers"; case .serve: "services"; case .other: "autres" }
    }
    var singular: String {
        switch self { case .forehand: "coup droit"; case .backhand: "revers"; case .serve: "service"; case .other: "autre" }
    }
}

extension CourtView {
    var label: String { self == .net ? "Vue filet" : "Vue arrière" }
}

extension DefectId {
    var label: String {
        switch self {
        case .latePrep: "Préparation tardive"
        case .smallTurn: "Épaules peu tournées"
        case .straightLegs: "Jambes tendues"
        case .narrowStance: "Appuis serrés"
        }
    }
}

extension MatchStatus {
    var label: String {
        switch self { case .pending: "Pas encore analysé"; case .running: "En cours"; case .done: "Terminé"; case .failed: "Échec" }
    }
}

func ofTotal(_ count: Int, _ total: Int, _ kind: StrokeKind) -> String {
    "\(count) \(count < 2 ? kind.singular : kind.plural) sur \(total)"
}

extension Double {
    var percentText: String { formatted(.percent.precision(.fractionLength(0)).locale(frFR)) }
}

/// "3:12" (or "1:02:03" from one hour) for a time in seconds; fractional seconds are truncated.
func clock(_ t: Double) -> String {
    let d = Duration.seconds(max(0, t).rounded(.down))
    return t >= 3600 ? d.formatted(.time(pattern: .hourMinuteSecond(padHourToLength: 1)).locale(frFR))
                     : d.formatted(.time(pattern: .minuteSecond(padMinuteToLength: 1)).locale(frFR))
}

/// `created` is a zone-less local time ("2026-03-04T10:00:00"): read it in `zone`, not GMT.
func parseCreated(_ s: String, in zone: TimeZone = .current) -> Date? {
    try? Date(s, strategy: Date.ISO8601FormatStyle(timeZone: zone).year().month().day().dateTimeSeparator(.standard).time(includingFractionalSeconds: false))
}

func dayText(_ d: Date, in zone: TimeZone = .current) -> String {
    d.formatted(Date.FormatStyle(date: .abbreviated, time: .omitted, locale: frFR, timeZone: zone))
}
