import Foundation

struct EngineLocation {
    let engineDir: URL
    let python: URL
    let environment: [String: String]
    let logFile: URL

    /// Dev mode: engine and venv live in the repo; data and log live in `support`.
    static func development(repo: URL, support: URL) -> EngineLocation {
        let data = support.appending(path: "data")
        try? FileManager.default.createDirectory(at: data, withIntermediateDirectories: true)
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (env["PATH"] ?? "/usr/bin:/bin")
        env["ACE_DATA_DIR"] = data.path
        env["ACE_MODEL_PATH"] = repo.appending(path: "models/yolo11m-pose.pt").path
        return EngineLocation(engineDir: repo, python: repo.appending(path: ".venv/bin/python"),
                              environment: env, logFile: support.appending(path: "engine.log"))
    }
}

extension EngineLocation {
    /// Installed app: engine, venv and model live in `support`, filled by `EngineSetup`.
    static func release(support: URL, bundle: Bundle) -> EngineLocation {
        let data = support.appending(path: "data")
        try? FileManager.default.createDirectory(at: data, withIntermediateDirectories: true)
        var env = ProcessInfo.processInfo.environment
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + (env["PATH"] ?? "/usr/bin:/bin")
        env["ACE_DATA_DIR"] = data.path
        env["ACE_MODEL_PATH"] = support.appending(path: "models/yolo11m-pose.pt").path
        return EngineLocation(engineDir: support.appending(path: "engine"),
                              python: support.appending(path: "venv/bin/python"),
                              environment: env, logFile: support.appending(path: "engine.log"))
    }
}
