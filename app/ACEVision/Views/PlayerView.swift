import AVKit
import SwiftUI

struct PlayerView: View {
    let match: Match
    let model: PlayerModel
    let notes: NotesSession
    let api: APIClient
    @State private var leaving = false
    @FocusState private var keysFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            VideoPlayer(player: model.player).frame(height: 260)
            if match.strokes.isEmpty {
                Text("Aucun coup détecté sur ce match.").foregroundStyle(.secondary)
            } else {
                StrokeTimeline(strokes: match.strokes, notes: notes.shown, duration: match.info?.durationS ?? (match.strokes.last?.t ?? 1), model: model)
            }
            controls
        }
        .confirmationDialog("Enregistrer tes notes ?", isPresented: $leaving, titleVisibility: .visible) {
            Button("Enregistrer les notes") { Task { if await notes.save(api) { notes.active = false } } }
            Button("Ne pas enregistrer") { notes.discard() }
            Button("Annuler", role: .cancel) {}
        }
    }

    @ViewBuilder private var controls: some View {
        HStack {
            Button(notes.active ? "Quitter la notation" : "Noter mes coups") {
                if !notes.active { notes.start(); keysFocused = true }
                else if notes.hasUnsaved { leaving = true }
                else { notes.discard() }
            }
            .disabled(notes.loadError != nil)
            if notes.active {
                Button("Enregistrer les notes") { Task { await notes.save(api) } }.disabled(notes.saving || !notes.recorder.hasUnsaved || notes.recorder.notes.isEmpty)
                Text(notes.recorder.countLabel).monospacedDigit()
            }
            if let e = notes.loadError { Text(e).foregroundStyle(.red) }
            if notes.saving { ProgressView().controlSize(.small); Text("Enregistrement…") }
            else if let m = notes.message { Text(m).foregroundStyle(.secondary).monospacedDigit() }
        }
        if notes.active {
            Text("Appuie sur D (coup droit), R (revers), S (service) ou A (autre) à chaque coup. ⌫ annule la dernière note, espace lance ou met en pause la vidéo.")
                .font(.callout).foregroundStyle(.secondary)
                .focusable().focused($keysFocused)
                .onKeyPress(phases: .down) { press in
                    if press.key == .delete && press.modifiers.isEmpty { notes.recorder.undo(); return .handled }
                    if press.key == .space && press.modifiers.isEmpty { model.togglePlay(); return .handled }
                    // Shift and Caps Lock only change the case of the letter
                    if press.modifiers.isDisjoint(with: [.command, .control, .option]), let c = press.characters.first, notes.recorder.handle(key: c, at: model.currentTime) { return .handled }
                    return .ignored
                }
        }
    }
}
