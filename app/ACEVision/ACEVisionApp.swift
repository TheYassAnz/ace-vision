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
        SwiftUI.Settings { SettingsView(engine: delegate.engine) }
    }
}

struct RootView: View {
    let engine: Engine
    let inbox: Inbox
    @State private var setup = EngineSetup()
    @State private var settingUp = false

    var body: some View {
        Group {
            switch engine.state {
            case .starting where settingUp: SetupView(setup: setup) { Task { await launch() } }
            case .starting: Text("Démarrage du moteur…").padding(40)
            case .failed(let message): Text(message).textSelection(.enabled).padding(40)
            case .ready(let api): LibraryView(api: api, inbox: inbox, dataDir: engine.dataDir)
            }
        }
        .task { await launch() }
    }

    private func launch() async {
        // hosted unit tests start their own engine
        guard ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] == nil else { return }
        let support = URL.applicationSupportDirectory.appending(path: "ACE Vision")
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        #if DEBUG
        if let repo = ProcessInfo.processInfo.environment["ACE_REPO"] {
            return await engine.start(.development(repo: URL(filePath: repo).standardizedFileURL, support: support))
        }
        #endif
        if setup.needsSetup(support: support, bundle: .main) {
            settingUp = true
            await setup.run(support: support, bundle: .main)
            guard setup.step == .done, setup.error == nil else { return }
            settingUp = false
        }
        await engine.start(.release(support: support, bundle: .main))
    }
}
