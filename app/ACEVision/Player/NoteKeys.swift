import AppKit

enum NoteKey: Equatable { case stroke(Character), undo, playPause }

enum NoteKeys {
    /// `blocked`: another window/sheet is key, or a dialog or save is in progress.
    /// Maps a key press to a note action; nil when the key is not ours.
    static func action(characters: String?, keyCode: UInt16, modifiers: NSEvent.ModifierFlags, editingText: Bool, isRepeat: Bool = false, blocked: Bool = false) -> NoteKey? {
        // Shift and Caps Lock only change the case of the letter
        guard !editingText, !isRepeat, !blocked, modifiers.isDisjoint(with: [.command, .control, .option]) else { return nil }
        switch keyCode {
        case 51: return .undo
        case 49: return .playPause
        default:
            guard let c = characters?.lowercased().first, "drsa".contains(c) else { return nil }
            return .stroke(c)
        }
    }
}
