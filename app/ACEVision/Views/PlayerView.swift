import AVKit
import SwiftUI

struct PlayerView: View {
    let match: Match
    let model: PlayerModel
    let notes: NotesSession
    let api: APIClient
    @State private var leaving = false
    @State private var keyMonitor: Any?

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
        .onChange(of: notes.active, initial: true) { _, on in on ? installKeys() : removeKeys() }
        .onDisappear { removeKeys() }
        .confirmationDialog("Enregistrer tes notes ?", isPresented: $leaving, titleVisibility: .visible) {
            Button("Enregistrer les notes") { Task { if await notes.save(api) { notes.active = false } } }
            Button("Ne pas enregistrer") { notes.discard() }
            Button("Annuler", role: .cancel) {}
        }
    }

    @ViewBuilder private var controls: some View {
        HStack {
            Button(notes.active ? "Quitter la notation" : "Noter mes coups") {
                if !notes.active { notes.start() }
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
        }
    }

    private func removeKeys() {
        if let m = keyMonitor { NSEvent.removeMonitor(m) }
        keyMonitor = nil
    }

    private func installKeys() {
        removeKeys()
        let notes = notes, model = model
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            let chars = event.characters, code = event.keyCode, mods = event.modifierFlags
            let handled = MainActor.assumeIsolated {
                let editing = NSApp.keyWindow?.firstResponder is NSText
                switch NoteKeys.action(characters: chars, keyCode: code, modifiers: mods, editingText: editing) {
                case .stroke(let c): _ = notes.recorder.handle(key: c, at: model.player.currentTime().seconds)
                case .undo: notes.recorder.undo()
                case .playPause: model.togglePlay()
                case nil: return false
                }
                return true
            }
            return handled ? nil : event
        }
    }
}
