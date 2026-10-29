import Foundation
import Testing
@testable import ACEVision

@Test func parsesReadyLine() {
    #expect(Engine.parseReady("ACE_READY 51234") == 51234)
    #expect(Engine.parseReady("INFO: started") == nil)
}

@MainActor
@Test(.enabled(if: ProcessInfo.processInfo.environment["ACE_REPO"] != nil))
func engineStartsAndAnswers() async throws {
    let repo = URL(filePath: try #require(ProcessInfo.processInfo.environment["ACE_REPO"])).standardizedFileURL
    let support = FileManager.default.temporaryDirectory.appending(path: "ace-test-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: support) }
    try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
    let engine = Engine()
    await engine.start(.development(repo: repo, support: support))
    defer { engine.stop() }
    guard case .ready(let client) = engine.state else { if case .failed(let m) = engine.state { Issue.record(Comment(rawValue: m)) }; return }
    #expect(try await client.matches().isEmpty)
}

@MainActor
@Test func launcherRunsOnceUntilEngineStops() async {
    let launcher = Launcher()
    var up = false, runs = 0
    let body = { runs += 1; try? await Task.sleep(for: .milliseconds(50)); up = true }
    let first = Task { await launcher.run(unless: up, body) }
    let second = Task { await launcher.run(unless: up, body) }  // overlaps the first (setup still running)
    await first.value; await second.value
    await launcher.run(unless: up, body)  // engine already up (window reopened)
    #expect(runs == 1)
    up = false
    await launcher.run(unless: up, body)  // engine stopped after a failure: retry is allowed
    #expect(runs == 2)
}
