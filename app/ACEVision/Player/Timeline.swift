import Foundation

enum Timeline {
    static func x(_ t: Double, duration: Double, width: Double) -> Double { duration > 0 ? t / duration * width : 0 }

    /// Advice clip around a stroke: 1.5 s before to 1.0 s after.
    static func clip(_ t: Double) -> ClosedRange<Double> { max(0, t - 1.5)...(t + 1.0) }

    /// Spoken by the tooltip and VoiceOver.
    static func label(_ s: Stroke) -> String {
        let defects = s.defects.isEmpty ? "aucun défaut" : s.defects.map { $0.label.prefix(1).lowercased() + $0.label.dropFirst() }.joined(separator: ", ")
        return "\(s.kind.label) à \(clock(s.t)), \(defects)"
    }

    /// Strictly after (or before) `t`; `strokes` are in time order.
    static func neighbor(of t: Double, in strokes: [Stroke], forward: Bool) -> Stroke? {
        forward ? strokes.first { $0.t > t } : strokes.last { $0.t < t }
    }
}
