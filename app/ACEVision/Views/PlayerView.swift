import AVKit
import SwiftUI

struct PlayerView: View {
    let match: Match
    let model: PlayerModel
    let notes: NotesSession
    let api: APIClient
    @State private var leaving = false
    @State private var keyMonitor: Any?
    @State private var window: NSWindow?
    @AppStorage("showSkeleton") private var showSkeleton = false
    @State private var pose: Pose?
    @State private var poseError: String?
    @State private var poseLoading = false
    @State private var loadedFor: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            PlayerSurface(player: model.player, pose: showSkeleton ? pose : nil,
                          videoSize: CGSize(width: match.info?.width ?? 0, height: match.info?.height ?? 0), fps: match.info?.fps ?? 0)
                .frame(maxWidth: .infinity)
                .containerRelativeFrame(.vertical) { h, _ in max(260, h * 0.55) }
            if match.strokes.isEmpty {
                Text("Aucun coup détecté sur ce match.").foregroundStyle(.secondary)
            } else {
                StrokeTimeline(strokes: match.strokes, notes: notes.shown, duration: match.info?.durationS ?? (match.strokes.last?.t ?? 1), model: model)
            }
            controls
        }
        .task(id: "\(match.id)-\(showSkeleton)") { await loadPose() }
        .onChange(of: notes.active, initial: true) { _, on in on ? installKeys() : removeKeys() }
        .background(WindowReader(window: $window))
        .onAppear { if notes.active { installKeys() } }
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
        HStack {
            Button(showSkeleton ? "Masquer le squelette" : "Afficher le squelette") { showSkeleton.toggle() }
            if poseLoading { ProgressView().controlSize(.small); Text("Chargement du squelette…") }
            if let e = poseError { Text(e).foregroundStyle(.red) }
        }
        if notes.active {
            Text("Appuie sur D (coup droit), R (revers), S (service) ou A (autre) à chaque coup. ⌫ annule la dernière note, espace lance ou met en pause la vidéo.")
                .font(.callout).foregroundStyle(.secondary)
        }
    }

    private func loadPose() async {
        guard showSkeleton else { poseLoading = false; return }  // a hide cancels the load before it can reset the spinner
        poseError = nil
        guard pose == nil || loadedFor != match.id else { return }
        pose = nil
        poseLoading = true
        defer { if !Task.isCancelled { poseLoading = false } }
        do {
            let p = try await api.pose(match.id)
            pose = p
            loadedFor = match.id
        } catch { if !Task.isCancelled { poseError = error.localizedDescription } }
    }

    private func removeKeys() {
        if let m = keyMonitor { NSEvent.removeMonitor(m) }
        keyMonitor = nil
    }

    private func installKeys() {
        removeKeys()
        let notes = notes, model = model, window = $window, leaving = $leaving
        keyMonitor = NSEvent.addLocalMonitorForEvents(matching: .keyDown) { event in
            let chars = event.characters, code = event.keyCode, mods = event.modifierFlags, rep = event.isARepeat
            let eventWindow = event.window
            let handled = MainActor.assumeIsolated {
                let editing = NSApp.keyWindow?.firstResponder is NSText
                let w = window.wrappedValue
                let blocked = w == nil || eventWindow !== w || w?.attachedSheet != nil || leaving.wrappedValue || notes.saving
                switch NoteKeys.action(characters: chars, keyCode: code, modifiers: mods, editingText: editing, isRepeat: rep, blocked: blocked) {
                case .stroke(let c):
                    let t = model.player.currentTime().seconds
                    if t.isFinite { _ = notes.recorder.handle(key: c, at: t) }
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

/// Gives the view its NSWindow, so key events from other windows and sheets are left alone.
private struct WindowReader: NSViewRepresentable {
    @Binding var window: NSWindow?
    final class Probe: NSView {
        var onWindow: (NSWindow?) -> Void = { _ in }
        override func viewDidMoveToWindow() { onWindow(window) }
    }
    func makeNSView(context: Context) -> Probe {
        let v = Probe()
        v.onWindow = { w in DispatchQueue.main.async { window = w } }
        return v
    }
    func updateNSView(_ v: Probe, context: Context) {
        v.onWindow = { w in DispatchQueue.main.async { window = w } }
    }
}
