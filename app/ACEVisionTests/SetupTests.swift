import CryptoKit
import Foundation
import Testing
@testable import ACEVision

private func tempDir() -> URL {
    let d = FileManager.default.temporaryDirectory.appending(path: "ace-setup-\(UUID().uuidString)")
    try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
    return d
}
private func tempFile(contents: String) -> URL {
    let f = tempDir().appending(path: "src.pt")
    try? Data(contents.utf8).write(to: f)
    return f
}
private func exists(_ u: URL) -> Bool { FileManager.default.fileExists(atPath: u.path) }

@Test func downloadRejectsBadChecksum() async throws {
    let src = tempFile(contents: "pas un modèle"), dst = tempDir().appending(path: "m.pt")
    await #expect(throws: SetupError.badChecksum) {
        try await ModelDownload.fetch(from: src, to: dst, expected: String(repeating: "0", count: 64), progress: { _ in })
    }
    #expect(!exists(dst) && !exists(dst.appendingPathExtension("part")))
}

@Test func downloadAcceptsGoodChecksum() async throws {
    let text = "un modèle"
    let src = tempFile(contents: text), dst = tempDir().appending(path: "m.pt")
    let sum = SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined()
    try await ModelDownload.fetch(from: src, to: dst, expected: sum, progress: { _ in })
    #expect(exists(dst) && !exists(dst.appendingPathExtension("part")))
}

@MainActor
@Test func needsSetupUntilVersionWritten() throws {
    let support = tempDir(), bundle = Bundle.main
    let version = try #require(bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String)
    let setup = EngineSetup()
    #expect(setup.needsSetup(support: support, bundle: bundle))
    let fm = FileManager.default
    for dir in ["venv/bin", "models", "engine"] { try fm.createDirectory(at: support.appending(path: dir), withIntermediateDirectories: true) }
    fm.createFile(atPath: support.appending(path: "venv/bin/python").path, contents: Data())
    fm.createFile(atPath: support.appending(path: "models/yolo11m-pose.pt").path, contents: Data())
    let versionFile = support.appending(path: "engine/VERSION")
    try Data(version.utf8).write(to: versionFile)
    #expect(!setup.needsSetup(support: support, bundle: bundle))
    try Data("0.0.0".utf8).write(to: versionFile)
    #expect(setup.needsSetup(support: support, bundle: bundle))
}
