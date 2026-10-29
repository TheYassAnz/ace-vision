import AppKit
import Testing
@testable import ACEVision

@Test func lettersBecomeNotes() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [], editingText: false) == .stroke("d"))
    #expect(NoteKeys.action(characters: "R", keyCode: 15, modifiers: [.shift], editingText: false) == .stroke("r"))
    #expect(NoteKeys.action(characters: "x", keyCode: 7, modifiers: [], editingText: false) == nil)
}
@Test func deleteAndSpace() {
    #expect(NoteKeys.action(characters: "\u{7f}", keyCode: 51, modifiers: [], editingText: false) == .undo)
    #expect(NoteKeys.action(characters: " ", keyCode: 49, modifiers: [], editingText: false) == .playPause)
}
@Test func modifiedKeysAreNotNotes() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [.command], editingText: false) == nil)
    #expect(NoteKeys.action(characters: "\u{7f}", keyCode: 51, modifiers: [.command], editingText: false) == nil)
}
@Test func ignoresKeysWhileEditingText() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [], editingText: true) == nil)
}
@Test func ignoresRepeatsAndBlockedKeys() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [], editingText: false, isRepeat: true) == nil)
    #expect(NoteKeys.action(characters: "\u{7f}", keyCode: 51, modifiers: [], editingText: false, isRepeat: true) == nil)
    #expect(NoteKeys.action(characters: " ", keyCode: 49, modifiers: [], editingText: false, blocked: true) == nil)
}
