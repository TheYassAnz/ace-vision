import Foundation
import Observation

@MainActor @Observable
final class EngineSetup {
    enum Step: Int { case checkingFfprobe, copyingEngine, installingPython, downloadingModel, done }

    var step = Step.checkingFfprobe
    var detail = ""
    var progress: Double?
    var error: String?
    var ffmpegMissing = false

    static let ffmpegMessage = "ffmpeg est nécessaire. Installe-le dans le Terminal avec la commande ci-dessous, puis clique sur Réessayer."
    static let genericMessage = "L'installation s'est arrêtée. Vérifie ta connexion à Internet puis clique sur Réessayer."

    private static func version(_ bundle: Bundle) -> String {
        bundle.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
    }

    func needsSetup(support: URL, bundle: Bundle) -> Bool {
        let fm = FileManager.default
        let installed = try? String(contentsOf: support.appending(path: "engine/VERSION"), encoding: .utf8)
        return installed != Self.version(bundle)
            || !fm.fileExists(atPath: support.appending(path: "venv/bin/python").path)
            || !fm.fileExists(atPath: support.appending(path: "models/yolo11m-pose.pt").path)
    }

    func run(support: URL, bundle: Bundle) async {
        error = nil
        ffmpegMissing = false
        progress = nil
        let fm = FileManager.default
        do {
            step = .checkingFfprobe
            guard ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"].contains(where: fm.isExecutableFile(atPath:)) else {
                throw SetupError.missingFfprobe
            }
            step = .copyingEngine
            let engine = support.appending(path: "engine")
            try fm.createDirectory(at: support, withIntermediateDirectories: true)
            try? fm.removeItem(at: engine)  // also drops the old VERSION: an interrupted install restarts
            guard let source = bundle.resourceURL?.appending(path: "engine") else { throw SetupError.badDownload }
            try fm.copyItem(at: source, to: engine)

            step = .installingPython
            try await sync(support: support, bundle: bundle)

            let model = support.appending(path: "models/yolo11m-pose.pt")
            if !fm.fileExists(atPath: model.path) {
                step = .downloadingModel
                progress = 0
                detail = ""
                let report: @Sendable (Double) -> Void = { [weak self] p in Task { @MainActor in self?.progress = p } }
                try await ModelDownload.fetch(from: ModelDownload.url, to: model, expected: ModelDownload.sha256, progress: report)
                progress = nil
            }
            try Data(Self.version(bundle).utf8).write(to: engine.appending(path: "VERSION"))  // last
            step = .done
        } catch SetupError.missingFfprobe {
            ffmpegMissing = true
            error = Self.ffmpegMessage
        } catch {
            self.error = Self.genericMessage
        }
    }

    private func sync(support: URL, bundle: Bundle) async throws {
        let p = Process(), pipe = Pipe()
        p.executableURL = bundle.resourceURL?.appending(path: "bin/uv")
        p.arguments = ["sync", "--frozen", "--project", support.appending(path: "engine").path]
        var env = ProcessInfo.processInfo.environment
        env["UV_PROJECT_ENVIRONMENT"] = support.appending(path: "venv").path
        env["UV_PYTHON_INSTALL_DIR"] = support.appending(path: "python").path
        env["UV_CACHE_DIR"] = support.appending(path: "cache").path
        env["UV_PYTHON_PREFERENCE"] = "only-managed"
        p.environment = env
        p.standardOutput = pipe
        p.standardError = pipe
        pipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let text = String(decoding: h.availableData, as: UTF8.self)
            guard let line = text.split(whereSeparator: \.isNewline).last.map(String.init) else { return }
            Task { @MainActor in self?.detail = line }
        }
        defer { pipe.fileHandleForReading.readabilityHandler = nil }
        let status: Int32 = try await withCheckedThrowingContinuation { cont in
            p.terminationHandler = { cont.resume(returning: $0.terminationStatus) }
            do { try p.run() } catch { cont.resume(throwing: error) }
        }
        guard status == 0 else { throw SetupError.uvFailed }
    }
}
