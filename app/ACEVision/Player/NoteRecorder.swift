import SwiftUI
import Foundation
import Observation

struct NoteRecorder {
    var notes: [Note]
    private(set) var hasUnsaved = false

    init(notes: [Note]) { self.notes = notes }

    var countLabel: String { "\(notes.count) \(notes.count < 2 ? "coup noté" : "coups notés")" }

    mutating func handle(key: Character, at t: Double) -> Bool {
        let kind: StrokeKind
        switch key.lowercased() {
        case "d": kind = .forehand
        case "r": kind = .backhand
        case "s": kind = .serve
        case "a": kind = .other
        default: return false
        }
        notes.append(Note(t: t, kind: kind))
        hasUnsaved = true
        return true
    }

    mutating func undo() {
        guard !notes.isEmpty else { return }
        notes.removeLast()
        hasUnsaved = true
    }

    mutating func markSaved() { hasUnsaved = false }
}

/// Note-taking state shared by the sidebar (leaving the match) and the match view.
@MainActor @Observable
final class NotesSession {
    var recorder = NoteRecorder(notes: [])
    var active = false
    var saving = false
    var message: String?
    private(set) var loadError: String?
    private(set) var matchId: String?
    private(set) var saved: [Note] = []

    var hasUnsaved: Bool { active && recorder.hasUnsaved }
    /// Notes shown in the "Mes notes" row.
    var shown: [Note] { active ? recorder.notes : saved }

    func open(_ id: String, saved notes: [Note]) {
        guard id != matchId else { return }
        matchId = id; saved = notes; active = false; message = nil; loadError = nil
        recorder = NoteRecorder(notes: notes)
    }

    /// The saved notes could not be read: refuse note mode, or saving would overwrite them.
    func fail(_ reason: String) {
        matchId = nil; saved = []; active = false; message = nil
        recorder = NoteRecorder(notes: [])
        loadError = "Impossible de charger tes notes (\(reason)) Rouvre le match pour réessayer."
    }

    func start() { recorder = NoteRecorder(notes: saved); message = nil; active = true }
    func discard() { recorder = NoteRecorder(notes: saved); active = false }

    @discardableResult
    func save(_ api: APIClient) async -> Bool {
        guard let id = matchId else { return false }
        saving = true
        defer { saving = false }
        do {
            let s = try await api.saveNotes(id, recorder.notes)
            recorder.markSaved(); saved = recorder.notes
            message = "Enregistré : \(s.foundRate.percentText) trouvés, \(s.classRate.percentText) bien classés."
        } catch {
            message = "Échec de l'enregistrement. Vérifie que l'analyse est terminée puis réessaie."
        }
        AccessibilityNotification.Announcement(message ?? "").post()
        return !recorder.hasUnsaved
    }
}
