import AppKit
import SwiftUI

struct SettingsView: View {
    let engine: Engine
    @State private var settings: Settings?
    @State private var error: String?

    var body: some View {
        Form {
            if case .ready(let api) = engine.state, let current = settings {
                Picker("Main de jeu", selection: bind(\.handedness, api, current)) {
                    Text("Droitier").tag(Handedness.right)
                    Text("Gaucher").tag(Handedness.left)
                }
                Picker("Revers", selection: bind(\.backhandHands, api, current)) {
                    Text("Une main").tag(1)
                    Text("Deux mains").tag(2)
                }
                if let dir = engine.dataDir {
                    Button("Ouvrir le dossier des données") { NSWorkspace.shared.activateFileViewerSelecting([dir]) }
                }
            } else if case .ready = engine.state, error == nil {
                ProgressView()
            } else if error == nil {
                Text("Les réglages seront disponibles quand le moteur d'analyse sera prêt.")
            }
            if let error { Text(error).foregroundStyle(.red) }
        }
        .formStyle(.grouped)
        .frame(width: 420)
        .task(id: engine.dataDir) {
            guard case .ready(let api) = engine.state else { return }
            do { settings = try await api.settings() } catch { self.error = error.localizedDescription }
        }
    }

    private func bind<T: Equatable>(_ key: WritableKeyPath<Settings, T>, _ api: APIClient, _ current: Settings) -> Binding<T> {
        Binding(get: { (settings ?? current)[keyPath: key] }, set: { value in
            var next = settings ?? current
            next[keyPath: key] = value
            let previous = settings
            settings = next
            Task {
                do { settings = try await api.saveSettings(next); error = nil }
                catch { self.error = error.localizedDescription; settings = previous }
            }
        })
    }
}
