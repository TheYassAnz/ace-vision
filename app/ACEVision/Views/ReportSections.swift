import SwiftUI

struct StatCard: View {
    let value: String
    let caption: String
    var body: some View {
        VStack(alignment: .leading) {
            Text(value).font(.title.bold()).monospacedDigit()
            Text(caption).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
    }
}

struct OverviewSection: View {
    let report: Report
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Vue d'ensemble").font(.title2.bold())
            HStack(alignment: .top) {
                ForEach([StrokeKind.forehand, .backhand, .serve, .other], id: \.self) { k in
                    StatCard(value: report.count(k).formatted(.number.locale(frFR)), caption: k.plural.prefix(1).uppercased() + k.plural.dropFirst())
                }
                if let r = report.rallies {
                    StatCard(value: r.n.formatted(.number.locale(frFR)), caption: "Échanges")
                    StatCard(value: r.mean, caption: "Coups en moyenne (max \(r.max))")
                }
            }
        }
    }
}

struct BreakdownSection: View {
    let report: Report
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Où ça casse").font(.title2.bold())
            Text(report.rallies == nil
                 ? "Disponible en vue arrière : filme depuis derrière toi, en paysage et en 60 i/s, pour voir où finissent tes balles."
                 : "La carte du court et le détail des fautes arrivent bientôt.")
        }
    }
}

struct AdviceSection: View {
    let report: Report
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Conseils").font(.title2.bold())
            if report.match.findings.isEmpty {
                Text(report.noFindingsText)
            }
            ForEach(report.match.findings, id: \.self) { f in
                VStack(alignment: .leading, spacing: 6) {
                    Text(f.title).font(.headline)
                    Text(ofTotal(f.count, f.total, f.kind)).bold().monospacedDigit()
                    Text(f.text)
                    Text("À essayer : \(f.drill)").italic()
                    HStack {
                        // Task 6 wires these to the player
                        ForEach(f.clipTimes, id: \.self) { t in
                            Button("Extrait à \(clock(t))") {}.disabled(true)
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
            }
        }
    }
}

struct StrokesTable: View {
    let strokes: [Stroke]
    @State private var expanded = false

    var body: some View {
        DisclosureGroup("Tous mes coups", isExpanded: $expanded) {
            Table(strokes.enumerated().map { Row(id: $0.offset, stroke: $0.element) }) {
                TableColumn("Temps") { Text(clock($0.stroke.t)).monospacedDigit() }
                TableColumn("Type") { Text($0.stroke.kind.label) }
                TableColumn("Défauts") { Text($0.stroke.defects.map(\.label).joined(separator: ", ")) }
            }
            .frame(height: 320)
        }
    }

    struct Row: Identifiable { let id: Int; let stroke: Stroke }
}
