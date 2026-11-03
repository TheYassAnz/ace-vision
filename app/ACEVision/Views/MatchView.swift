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
    @State private var stopping = false

    var body: some View {
        Group {
            if library.selection == Library.progressionId {
                ProgressionView(matches: library.matches)
            } else if let id = library.selection, let summary = library.matches.first(where: { $0.id == id }) {
                content(summary)
                    .task(id: "\(id)-\(summary.status)-\(notes.revision)") { await load(id) }
            } else {
                ContentUnavailableView("Choisis un match dans la liste.", systemImage: "sidebar.left")
            }
        }
        .onChange(of: notes.revision) { Task { await library.refresh() } }
        .navigationTitle(library.selection == Library.progressionId ? "Progression" : library.selection.flatMap { id in library.matches.first { $0.id == id }?.title } ?? "ACE Vision")
    }

    @ViewBuilder private func content(_ s: MatchSummary) -> some View {
        switch s.status {
        case .running:
            VStack(spacing: 12) {
                ProgressView(value: s.progress).frame(maxWidth: 320)
                Text("En cours… \(s.progress.percentText)").monospacedDigit()
                Button("Arrêter l'analyse", role: .destructive) { Task { await stop(s.id) } }
                    .disabled(stopping)
                if let m = relaunchMessage { Text(m).foregroundStyle(.secondary) }
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
                        HStack(alignment: .top, spacing: 16) {
                            PlayerView(match: m, model: player, notes: notes, api: api) { Task { await relaunch(m.id) } }
                                .containerRelativeFrame(.horizontal) { w, _ in w * 0.6 }
                            OverviewSection(report: Report(m)).frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .fixedSize(horizontal: false, vertical: true)  // the video's height follows its width instead of the leftover space
                        .padding([.horizontal, .top], 24).padding(.bottom, 12)
                        Divider()
                    }
                    ScrollView {
                        VStack(alignment: .leading, spacing: 24) {
                            let r = Report(m)
                            if player == nil || relaunchMessage != nil || r.coverageNotice != nil || r.reliability != nil {  // an empty stack still takes the 24 pt spacing
                            VStack(alignment: .leading, spacing: 4) {
                                if player == nil {  // otherwise it sits with the player's buttons
                                    Button("Relancer l'analyse") { Task { await relaunch(m.id) } }
                                        .disabled(notes.hasUnsaved)
                                        .help(notes.hasUnsaved ? "Enregistre ou abandonne tes notes avant de relancer l'analyse." : "")
                                }
                                if let msg = relaunchMessage { Text(msg).foregroundStyle(.secondary) }
                                if let n = r.coverageNotice { Label(n, systemImage: "exclamationmark.triangle") }
                                if let n = r.reliability { Text(n).monospacedDigit() }
                            }
                            }
                            if player == nil { OverviewSection(report: r) }
                            StrokesTable(strokes: m.strokes) { player?.playClip(at: $0) }
                        }
                        .padding([.horizontal, .bottom], 24).padding(.top, player == nil ? 24 : 12)
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
        stopping = false  // the status changed: the stop went through
        guard library.matches.first(where: { $0.id == id })?.status == .done else { return }
        do {
            let m = try await api.match(id)
            if match?.id != id || player == nil, let dataDir {
                player = PlayerModel(url: dataDir.appending(path: "matchs/\(id)/\(m.videoFile)"))
            }
            do { notes.open(id, saved: try await api.notes(id)) } catch { notes.fail(error.localizedDescription) }
            match = m; loadError = nil
        }
        catch { loadError = error.localizedDescription }
    }

    private func stop(_ id: String) async {
        stopping = true
        relaunchMessage = nil
        do { try await api.stop(id) } catch { relaunchMessage = error.localizedDescription; stopping = false }
        await library.refresh()
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
