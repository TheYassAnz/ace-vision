import Charts
import SwiftUI

struct ProgressionView: View {
    let matches: [MatchSummary]
    @State private var kind = StrokeKind.forehand

    private var points: [ProgressionPoint] { Progression.points(matches) }

    private struct Sample: Identifiable { let id: String; let point: ProgressionPoint; let series: String; let rate: Double }

    private var scoreSamples: [Sample] {
        points.flatMap { p in
            [p.foundRate.map { Sample(id: p.id + "f", point: p, series: "Coups trouvés", rate: $0) },
             p.classRate.map { Sample(id: p.id + "c", point: p, series: "Bien classés", rate: $0) }].compactMap { $0 }
        }
    }

    private var defectSamples: [Sample] {
        points.flatMap { p in
            p.defectRates.filter { $0.kind == kind }.map { Sample(id: p.id + $0.defect.rawValue, point: p, series: $0.defect.label, rate: $0.rate) }
        }
    }

    var body: some View {
        if points.count < 2 {
            ContentUnavailableView("Il faut au moins deux matchs analysés pour voir ta progression.", systemImage: "chart.line.uptrend.xyaxis")
        } else {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text("Progression").font(.largeTitle.bold())
                    section("Fiabilité de la détection", scoreSamples, empty: "Note des coups dans un match pour voir ta fiabilité.")
                    Picker("Type de coup", selection: $kind) {
                        ForEach([StrokeKind.forehand, .backhand, .serve, .other], id: \.self) { Text($0.label).tag($0) }
                    }
                    .pickerStyle(.segmented).frame(maxWidth: 420)
                    section("Défauts : \(kind.plural), part des coups", defectSamples, empty: "Aucun défaut mesuré pour ce type de coup.")
                }
                .padding(24).frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    @ViewBuilder private func section(_ title: String, _ samples: [Sample], empty: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.title2.bold())
            if samples.isEmpty { Text(empty).foregroundStyle(.secondary) } else {
                Chart(samples) { s in
                    LineMark(x: .value("Date", s.point.date), y: .value("Part", s.rate))
                        .foregroundStyle(by: .value("Courbe", s.series)).symbol(by: .value("Courbe", s.series))
                    PointMark(x: .value("Date", s.point.date), y: .value("Part", s.rate))
                        .foregroundStyle(by: .value("Courbe", s.series)).symbol(by: .value("Courbe", s.series))
                        .accessibilityLabel("\(s.point.title), \(s.series)")
                        .accessibilityValue(s.rate.percentText)
                }
                .chartYScale(domain: 0...1)
                .chartYAxis { AxisMarks(values: [0, 0.25, 0.5, 0.75, 1]) { v in
                    AxisGridLine(); AxisValueLabel { if let d = v.as(Double.self) { Text(d.percentText).monospacedDigit() } }
                } }
                .chartXAxis { AxisMarks { _ in AxisGridLine(); AxisValueLabel(format: Date.FormatStyle(locale: frFR).day().month(.wide)) } }
                .frame(height: 240)
            }
        }
    }
}
