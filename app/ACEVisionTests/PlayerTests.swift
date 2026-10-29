import Foundation
import Testing
@testable import ACEVision

@Test func clipRange() { #expect(Timeline.clip(1.0) == 0...2.0 && Timeline.clip(10) == 8.5...11) }

@Test func timelineX() { #expect(Timeline.x(30, duration: 120, width: 400) == 100) }

@Test func recorderKeysAndUndo() {
    var r = NoteRecorder(notes: [])
    #expect(r.handle(key: "D", at: 1.2) && r.handle(key: "s", at: 3) && !r.handle(key: "x", at: 4))
    r.undo()
    #expect(r.notes == [Note(t: 1.2, kind: .forehand)] && r.countLabel == "1 coup noté" && r.hasUnsaved)
    r.markSaved()
    #expect(!r.hasUnsaved)
}

@Test func recorderCountLabels() {
    var r = NoteRecorder(notes: [])
    #expect(r.countLabel == "0 coup noté")
    _ = r.handle(key: "d", at: 1); _ = r.handle(key: "r", at: 2); _ = r.handle(key: "a", at: 3)
    #expect(r.countLabel == "3 coups notés")
}

@Test func strokeLabel() {
    #expect(Timeline.label(Stroke(t: 192, frame: 5760, kind: .forehand, defects: [.latePrep], outcome: .unknown)) == "Coup droit à 3:12, préparation tardive")
    #expect(Timeline.label(Stroke(t: 5, frame: 150, kind: .serve, defects: [], outcome: .unknown)) == "Service à 0:05, aucun défaut")
}

@Test func neighborStrokes() {
    let s = [10.0, 20, 30].map { Stroke(t: $0, frame: 0, kind: .forehand, defects: [], outcome: .unknown) }
    #expect(Timeline.neighbor(of: 20, in: s, forward: true)?.t == 30)
    #expect(Timeline.neighbor(of: 20, in: s, forward: false)?.t == 10)
    #expect(Timeline.neighbor(of: 30, in: s, forward: true) == nil)
}
