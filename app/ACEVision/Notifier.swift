import UserNotifications

enum Notifier {
    static func requestAuthorization() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    static func post(_ s: MatchSummary) {
        let content = UNMutableNotificationContent()
        content.title = s.title.isEmpty ? s.id : s.title
        content.body = s.status == .done ? "Analyse terminée" : "L'analyse a échoué"
        content.userInfo = ["matchId": s.id]
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "done-\(s.id)", content: content, trigger: nil))
    }
}
