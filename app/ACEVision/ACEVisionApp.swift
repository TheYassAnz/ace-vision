import SwiftUI

@main
struct ACEVisionApp: App {
    @NSApplicationDelegateAdaptor private var delegate: AppDelegate

    var body: some Scene {
        WindowGroup { RootView(engine: delegate.engine, inbox: delegate.inbox) }
            .commands {
                CommandGroup(after: .newItem) {
                    Button("Ajouter depuis un fichier…") { delegate.inbox.showFileImporter = true }.keyboardShortcut("o")
                    Button("Ajouter depuis Photos…") { delegate.inbox.showPhotos = true }.keyboardShortcut("o", modifiers: [.command, .shift])
                }
                CommandGroup(after: .pasteboard) {
                    Button("Supprimer le match…") { delegate.inbox.deleteRequested = true }.keyboardShortcut(.delete, modifiers: .command)
                }
            }
    }
}

struct RootView: View {
    let engine: Engine
    let inbox: Inbox

    var body: some View {
        Group {
            switch engine.state {
            case .starting: Text("Démarrage du moteur…").padding(40)
            case .failed(let message): Text(message).textSelection(.enabled).padding(40)
            case .ready(let api): LibraryView(api: api, inbox: inbox)
            }
        }
        .task {
            // hosted unit tests start their own engine
            guard ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] == nil else { return }
            guard let repo = ProcessInfo.processInfo.environment["ACE_REPO"] else {
                return engine.state = .failed("Moteur d'analyse introuvable. Réinstalle ACE Vision.")
            }
            let support = URL.applicationSupportDirectory.appending(path: "ACE Vision")
            try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            await engine.start(.development(repo: URL(filePath: repo).standardizedFileURL, support: support))
        }
    }
}
