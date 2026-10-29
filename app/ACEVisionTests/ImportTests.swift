import Foundation
import Testing
@testable import ACEVision

private struct FailingImporter: MatchImporting {
    let message: String
    func importVideo(path: URL, view: CourtView, title: String) async throws -> ImportResult { throw APIError(message: message) }
}

private final class Spy: MatchImporting, @unchecked Sendable {
    var calls = 0
    func importVideo(path: URL, view: CourtView, title: String) async throws -> ImportResult {
        calls += 1
        return ImportResult(match: MatchSummary(id: "m", title: title, view: view, status: .pending, progress: 0, error: nil, created: nil, durationS: nil, score: nil, defectRates: []), queued: false)
    }
}

private func tempMovie(_ ext: String = "mov") -> URL {
    let url = FileManager.default.temporaryDirectory.appending(path: "\(UUID().uuidString).\(ext)")
    try? Data([1, 2, 3]).write(to: url)
    return url
}

@MainActor @Test func importDeletesTempFileOnFailure() async {
    let tmp = tempMovie()
    let c = ImportCoordinator(api: FailingImporter(message: "Ce fichier n'est pas une vidéo lisible."))
    c.offer(tmp, deleteAfter: true)
    #expect(await c.confirm(view: .net, title: "", deleteAfter: true) == nil)
    #expect(c.error == "Ce fichier n'est pas une vidéo lisible." && !FileManager.default.fileExists(atPath: tmp.path))
}

@MainActor @Test func importKeepsUserFile() async {
    let tmp = tempMovie()
    defer { try? FileManager.default.removeItem(at: tmp) }
    let c = ImportCoordinator(api: Spy())
    c.offer(tmp)
    #expect(await c.confirm(view: .rear, title: "t", deleteAfter: false) != nil)
    #expect(FileManager.default.fileExists(atPath: tmp.path) && c.pending == nil)
}

@MainActor @Test func rejectsNonVideo() {
    let c = ImportCoordinator(api: Spy())
    c.offer(URL(filePath: "/tmp/a.txt"))
    #expect(c.pending == nil && c.error == "Format de vidéo non pris en charge (.mov, .mp4, .m4v).")
}

@MainActor @Test func confirmWithoutViewAsksForIt() async {
    let tmp = tempMovie()
    defer { try? FileManager.default.removeItem(at: tmp) }
    let spy = Spy()
    let c = ImportCoordinator(api: spy)
    c.offer(tmp, deleteAfter: true)
    #expect(await c.confirm(view: nil, title: "", deleteAfter: true) == nil)
    #expect(c.viewError == "Choisis d'où filmait l'iPhone." && spy.calls == 0 && FileManager.default.fileExists(atPath: tmp.path))
}
