import SwiftUI

struct StatCard: View {
    let value: String
    let caption: String
    var tint: Color = .purple
    var body: some View {
        VStack(alignment: .leading) {
            Text(value).font(.title.bold()).monospacedDigit().foregroundStyle(tint)
            Text(caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(tint.opacity(0.15), in: RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
    }
}

struct OverviewSection: View {
    let report: Report
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Vue d'ensemble").font(.title2.bold())
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 110), alignment: .top)], alignment: .leading, spacing: 12) {
                ForEach([StrokeKind.forehand, .backhand, .serve, .other], id: \.self) { k in
                    StatCard(value: report.count(k).formatted(.number.locale(frFR)), caption: k.plural.prefix(1).uppercased() + k.plural.dropFirst(), tint: k.color)
                }
                if let r = report.rallies {
                    StatCard(value: r.n.formatted(.number.locale(frFR)), caption: "Échanges")
                    StatCard(value: r.mean, caption: "Coups en moyenne (max \(r.max))")
                }
            }
        }
    }
}

struct StrokesTable: View {
    let strokes: [Stroke]
    let onClip: (Double) -> Void
    @State private var selection: Int?
    @State private var expanded = true

    var body: some View {
        DisclosureGroup("Tous mes coups", isExpanded: $expanded) {
            Table(strokes.enumerated().map { Row(id: $0.offset, stroke: $0.element) }, selection: $selection) {
                TableColumn("Temps") { Text(clock($0.stroke.t)).monospacedDigit() }
                TableColumn("Type") { Text($0.stroke.kind.label) }
                TableColumn("Défauts") { Text($0.stroke.defects.map(\.label).joined(separator: ", ")) }
                TableColumn("Vitesse bras") { Text(relativeSpeed($0.stroke)).monospacedDigit() }
            }
            .frame(height: 480)
            .onChange(of: selection) { if let i = selection, strokes.indices.contains(i) { onClip(strokes[i].t) } }  // selecting a row (click or arrows) plays it
        }
    }

    /// Share of the match's fastest arm: the raw value is a 2D image-plane speed, not a real-world one.
    private func relativeSpeed(_ s: Stroke) -> String {
        guard let v = s.wristSpeed, let top = strokes.compactMap(\.wristSpeed).max(), top > 0 else { return "—" }
        return "\(Int((v / top * 100).rounded())) %"
    }

    struct Row: Identifiable { let id: Int; let stroke: Stroke }
}
