import SwiftUI

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate {
    let engine = Engine()
    func applicationWillTerminate(_ notification: Notification) { engine.stop() }
}

@main
struct ACEVisionApp: App {
    @NSApplicationDelegateAdaptor private var delegate: AppDelegate

    var body: some Scene {
        WindowGroup { RootView(engine: delegate.engine) }
    }
}

struct RootView: View {
    let engine: Engine
    @State private var count: Int?

    var body: some View {
        Group {
            switch engine.state {
            case .starting: Text("Démarrage du moteur…")
            case .failed(let message): Text(message).textSelection(.enabled)
            case .ready: Text(count.map { "\($0) matchs" } ?? "Chargement…")
            }
        }
        .padding(40)
        .frame(minWidth: 400, minHeight: 200)
        .task {
            // hosted unit tests start their own engine
            guard ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] == nil else { return }
            guard let repo = ProcessInfo.processInfo.environment["ACE_REPO"] else {
                return engine.state = .failed("Moteur d'analyse introuvable. Réinstalle ACE Vision.")
            }
            let support = URL.applicationSupportDirectory.appending(path: "ACE Vision")
            try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
            await engine.start(.development(repo: URL(filePath: repo).standardizedFileURL, support: support))
            if case .ready(let client) = engine.state { count = try? await client.matches().count }
        }
    }
}
