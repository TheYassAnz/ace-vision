import SwiftUI

struct MatchView: View {
    let api: APIClient
    let library: Library
    @State private var match: Match?
    @State private var loadError: String?

    var body: some View {
        Group {
            if let id = library.selection, let summary = library.matches.first(where: { $0.id == id }) {
                content(summary)
                    .task(id: "\(id)-\(summary.status)") { await load(id) }
            } else {
                ContentUnavailableView("Choisis un match dans la liste.", systemImage: "sidebar.left")
            }
        }
        .navigationTitle(library.selection.flatMap { id in library.matches.first { $0.id == id }?.title } ?? "ACE Vision")
    }

    @ViewBuilder private func content(_ s: MatchSummary) -> some View {
        switch s.status {
        case .running:
            VStack(spacing: 12) {
                ProgressView(value: s.progress).frame(maxWidth: 320)
                Text("En cours… \(s.progress.percentText)").monospacedDigit()
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .failed, .pending:
            VStack(spacing: 12) {
                Text(s.status == .failed ? (s.error ?? "L'analyse a échoué. Relance-la ; si ça échoue encore, regarde engine.log.") : "Ce match n'a pas encore été analysé.")
                Button("Relancer l'analyse") { Task { _ = try? await api.relaunch(s.id); await library.refresh() } }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .done:
            if let m = match, m.id == s.id {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        let r = Report(m)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(m.title.isEmpty ? m.id : m.title).font(.largeTitle.bold()).lineLimit(1).truncationMode(.middle)
                            Text(m.view.label).foregroundStyle(.secondary)
                            if let n = r.coverageNotice { Label(n, systemImage: "exclamationmark.triangle") }
                            if let n = r.reliability { Text(n).monospacedDigit() }
                        }
                        OverviewSection(report: r)
                        BreakdownSection(report: r)
                        AdviceSection(report: r)
                        StrokesTable(strokes: m.strokes)
                    }
                    .padding(24)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            } else if let e = loadError {
                Text(e).frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ProgressView("Chargement…").frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    private func load(_ id: String) async {
        guard library.matches.first(where: { $0.id == id })?.status == .done else { return }
        do { match = try await api.match(id); loadError = nil }
        catch { loadError = error.localizedDescription }
    }
}
