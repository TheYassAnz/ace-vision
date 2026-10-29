import SwiftUI

@main
struct ACEVisionApp: App {
    @NSApplicationDelegateAdaptor private var delegate: AppDelegate

    var body: some Scene {
        WindowGroup { RootView(app: delegate) }
            .commands {
                CommandGroup(replacing: .newItem) {  // one window: the library, notes and engine are app-wide
                    Button("Ajouter depuis un fichier…") { delegate.inbox.showFileImporter = true }.keyboardShortcut("o")
                    Button("Ajouter depuis Photos…") { delegate.inbox.showPhotos = true }.keyboardShortcut("o", modifiers: [.command, .shift])
                }
                CommandGroup(after: .pasteboard) {
                    Button("Supprimer le match…") { delegate.inbox.deleteRequested = true }.keyboardShortcut(.delete, modifiers: .command)
                }
            }
        SwiftUI.Settings { SettingsView(engine: delegate.engine) }
    }
}

struct RootView: View {
    let app: AppDelegate

    var body: some View {
        switch app.engine.state {
        case .starting where app.settingUp: SetupView(setup: app.setup) { Task { await app.launch() } }
        case .starting: Text("Démarrage du moteur…").padding(40)
        case .failed(let message): Text(message).textSelection(.enabled).padding(40)
        case .ready(let api):
            if let library = app.library {
                LibraryView(api: api, library: library, notes: app.notes, inbox: app.inbox, dataDir: app.engine.dataDir)
            } else {
                Text("Démarrage du moteur…").padding(40)
            }
        }
    }
}
