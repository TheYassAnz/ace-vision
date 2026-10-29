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
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, @MainActor UNUserNotificationCenterDelegate {
    let engine = Engine()
    let inbox = Inbox()

    func applicationDidFinishLaunching(_ notification: Notification) {
        UNUserNotificationCenter.current().delegate = self
    }

    func application(_ application: NSApplication, open urls: [URL]) { inbox.opened = urls }
    func applicationWillTerminate(_ notification: Notification) { engine.stop() }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        let id = response.notification.request.content.userInfo["matchId"] as? String
        await MainActor.run { inbox.notifiedMatch = id }
    }

    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .sound]
    }
}
