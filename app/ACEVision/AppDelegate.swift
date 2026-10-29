import Observation
import SwiftUI
import UserNotifications

/// Events from outside the view tree (Dock, notifications, menu commands).
@MainActor @Observable
final class Inbox {
    var opened: [URL] = []
    var notifiedMatch: String?
    var showFileImporter = false
    var showPhotos = false
    var deleteRequested = false

    /// Hands over pending Dock/"Open with" URLs once; a later identical open is delivered again.
    func takeOpened() -> [URL] { defer { opened = [] }; return opened }
    func takeNotifiedMatch() -> String? { defer { notifiedMatch = nil }; return notifiedMatch }
}

/// Runs one launch at a time, and none once the engine is up: reopening a window must not restart it.
@MainActor
final class Launcher {
    private var busy = false

    func run(unless isUp: Bool, _ body: () async -> Void) async {
        guard !busy, !isUp else { return }
        busy = true
        defer { busy = false }
        await body()
    }
}

/// Owns everything that must outlive the window: engine, first-launch setup, library polling, notes.
@MainActor @Observable
final class AppDelegate: NSObject, NSApplicationDelegate, @MainActor UNUserNotificationCenterDelegate {
    @ObservationIgnored let engine = Engine()
    @ObservationIgnored let inbox = Inbox()
    @ObservationIgnored let setup = EngineSetup()
    @ObservationIgnored let notes = NotesSession()
    @ObservationIgnored private let launcher = Launcher()
    private(set) var settingUp = false
    private(set) var library: Library?

    func applicationDidFinishLaunching(_ notification: Notification) {
        UNUserNotificationCenter.current().delegate = self
        Task { await launch() }
    }

    func application(_ application: NSApplication, open urls: [URL]) { inbox.opened = urls }
    func applicationWillTerminate(_ notification: Notification) { engine.stop() }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard notes.hasUnsaved, case .ready(let api) = engine.state else { return .terminateNow }
        let alert = NSAlert()
        alert.messageText = "Enregistrer tes notes ?"
        alert.informativeText = "Les coups notés sur ce match ne sont pas encore enregistrés."
        alert.addButton(withTitle: "Enregistrer les notes")
        alert.addButton(withTitle: "Ne pas enregistrer")
        alert.addButton(withTitle: "Annuler").keyEquivalent = "\u{1b}"
        switch alert.runModal() {
        case .alertFirstButtonReturn:
            // a failed save keeps the app open: the player shows why
            Task { NSApp.reply(toApplicationShouldTerminate: await notes.save(api)) }
            return .terminateLater
        case .alertSecondButtonReturn: return .terminateNow
        default: return .terminateCancel
        }
    }

    func launch() async {
        await launcher.run(unless: engine.isRunning) { await start() }
    }

    private func start() async {
        // hosted unit tests start their own engine
        guard ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] == nil else { return }
        let support = URL.applicationSupportDirectory.appending(path: "ACE Vision")
        try? FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        #if DEBUG
        if let repo = ProcessInfo.processInfo.environment["ACE_REPO"] {
            await engine.start(.development(repo: URL(filePath: repo).standardizedFileURL, support: support))
            return startLibrary()
        }
        #endif
        if setup.needsSetup(support: support, bundle: .main) {
            settingUp = true
            await setup.run(support: support, bundle: .main)
            guard setup.step == .done, setup.error == nil else { return }
            settingUp = false
        }
        await engine.start(.release(support: support, bundle: .main))
        startLibrary()
    }

    private func startLibrary() {
        guard library == nil, case .ready(let api) = engine.state else { return }
        let l = Library(api: api)
        l.onFinished = { Notifier.post($0) }
        library = l
        Task { await l.poll() }
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        let id = response.notification.request.content.userInfo["matchId"] as? String
        await MainActor.run { inbox.notifiedMatch = id }
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .sound]
    }
}
