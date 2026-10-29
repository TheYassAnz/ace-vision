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
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 110), alignment: .top)], alignment: .leading, spacing: 12) {
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
            // the engine does not track the ball yet, so rallies are never computed (ace/pipeline.py)
            Text("Pas encore disponible : l'app ne suit pas encore la balle, elle ne peut donc pas savoir où finissent tes points (filet, long, large).")
        }
    }
}

struct AdviceSection: View {
    let report: Report
    let onClip: (Double) -> Void
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
                        ForEach(f.clipTimes, id: \.self) { t in
                            Button("Extrait à \(clock(t))") { onClip(t) }
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
    let onClip: (Double) -> Void
    @State private var selection: Int?
    @State private var expanded = false

    var body: some View {
        DisclosureGroup("Tous mes coups", isExpanded: $expanded) {
            Table(strokes.enumerated().map { Row(id: $0.offset, stroke: $0.element) }, selection: $selection) {
                TableColumn("Temps") { Text(clock($0.stroke.t)).monospacedDigit() }
                TableColumn("Type") { Text($0.stroke.kind.label) }
                TableColumn("Défauts") { Text($0.stroke.defects.map(\.label).joined(separator: ", ")) }
            }
            .frame(height: 320)
            .onChange(of: selection) { if let i = selection, strokes.indices.contains(i) { onClip(strokes[i].t) } }  // selecting a row (click or arrows) plays it
        }
    }

    struct Row: Identifiable { let id: Int; let stroke: Stroke }
}
