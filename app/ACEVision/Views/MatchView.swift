import SwiftUI

struct MatchView: View {
    let api: APIClient
    let library: Library
    let notes: NotesSession
    let dataDir: URL?
    @State private var match: Match?
    @State private var player: PlayerModel?
    @State private var loadError: String?
    @State private var relaunchMessage: String?

    var body: some View {
        Group {
            if library.selection == Library.progressionId {
                ProgressionView(matches: library.matches)
            } else if let id = library.selection, let summary = library.matches.first(where: { $0.id == id }) {
                content(summary)
                    .task(id: "\(id)-\(summary.status)") { await load(id) }
            } else {
                ContentUnavailableView("Choisis un match dans la liste.", systemImage: "sidebar.left")
            }
        }
        .navigationTitle(library.selection == Library.progressionId ? "Progression" : library.selection.flatMap { id in library.matches.first { $0.id == id }?.title } ?? "ACE Vision")
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
                Button("Relancer l'analyse") { Task { await relaunch(s.id) } }
                if let m = relaunchMessage { Text(m).foregroundStyle(.secondary) }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .done:
            if let m = match, m.id == s.id {
                VStack(spacing: 0) {
                    if let player {
                        PlayerView(match: m, model: player, notes: notes, api: api).padding([.horizontal, .top], 24).padding(.bottom, 12)
                        Divider()
                    }
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            let r = Report(m)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(m.title.isEmpty ? m.id : m.title).font(.largeTitle.bold()).lineLimit(1).truncationMode(.middle).help(m.title)
                                Text(m.view.label).foregroundStyle(.secondary)
                                if let n = r.coverageNotice { Label(n, systemImage: "exclamationmark.triangle") }
                                if let n = r.reliability { Text(n).monospacedDigit() }
                            }
                            OverviewSection(report: r)
                            BreakdownSection(report: r)
                            AdviceSection(report: r) { player?.playClip(at: $0) }
                            StrokesTable(strokes: m.strokes) { player?.playClip(at: $0) }
                        }
                        .padding(24)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
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
        do {
            let m = try await api.match(id)
            if match?.id != id || player == nil, let dataDir {
                player = PlayerModel(url: dataDir.appending(path: "matchs/\(id)/\(m.videoFile)"))
            }
            notes.open(id, saved: (try? await api.notes(id)) ?? [])
            match = m; loadError = nil
        }
        catch { loadError = error.localizedDescription }
    }

    private func relaunch(_ id: String) async {
        do {
            let started = try await api.relaunch(id)
            relaunchMessage = started ? nil : "Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer l'analyse."
        } catch {
            relaunchMessage = error.localizedDescription
        }
        await library.refresh()
    }
}
