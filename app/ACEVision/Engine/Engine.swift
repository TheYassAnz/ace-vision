import Foundation
import Observation

@MainActor @Observable
final class Engine {
    enum State { case starting, ready(APIClient), failed(String) }

    var state = State.starting
    private(set) var dataDir: URL?
    @ObservationIgnored private var process: Process?
    @ObservationIgnored private var stdin: Pipe?

    nonisolated static func parseReady(_ line: String) -> Int? {
        let parts = line.split(separator: " ")
        return parts.count == 2 && parts[0] == "ACE_READY" ? Int(parts[1]) : nil
    }

    func start(_ loc: EngineLocation) async {
        state = .starting
        dataDir = loc.environment["ACE_DATA_DIR"].map { URL(filePath: $0) }
        let token = (0..<32).map { _ in String(format: "%02x", UInt8.random(in: .min ... .max)) }.joined()
        let out = Pipe(), inp = Pipe(), p = Process()
        FileManager.default.createFile(atPath: loc.logFile.path, contents: nil)
        guard let log = try? FileHandle(forWritingTo: loc.logFile) else {
            return state = .failed("Impossible d'écrire engine.log. Vérifie les droits du dossier de l'app.")
        }
        p.executableURL = loc.python
        p.arguments = ["-m", "ace"]
        p.currentDirectoryURL = loc.engineDir
        p.environment = loc.environment.merging(["ACE_TOKEN": token, "YOLO_OFFLINE": "1"]) { $1 }
        p.standardOutput = out
        p.standardInput = inp
        p.standardError = log
        do { try p.run() } catch {
            return state = .failed("Le moteur d'analyse ne démarre pas. Vérifie l'installation ; le détail est dans engine.log.")
        }
        process = p
        stdin = inp
        let pid = p.processIdentifier
        let reading = out.fileHandleForReading
        let port = await withTaskGroup(of: Int?.self) { group in
            group.addTask {
                do {
                    for try await line in reading.bytes.lines {
                        if let port = Engine.parseReady(line) { return port }
                    }
                } catch {}
                return nil
            }
            group.addTask {  // on timeout, killing the engine ends the reader above with EOF
                guard (try? await Task.sleep(for: .seconds(60))) != nil else { return nil }  // cancelled: engine is up
                kill(pid, SIGTERM)
                return nil
            }
            let first = await group.next() ?? nil
            group.cancelAll()
            return first
        }
        guard let port else { return fail(loc) }
        let client = APIClient(port: port, token: token)
        for _ in 0..<50 {  // the port is printed just before uvicorn listens
            if (try? await client.health()) != nil { return state = .ready(client) }
            try? await Task.sleep(for: .milliseconds(100))
        }
        fail(loc)
    }

    private func fail(_ loc: EngineLocation) {
        stop()
        let text = (try? String(contentsOf: loc.logFile, encoding: .utf8)) ?? ""
        let tail = text.split(separator: "\n").suffix(20).joined(separator: "\n")
        state = .failed("Le moteur d'analyse ne démarre pas. Quitte et relance ACE Vision ; le détail est dans engine.log.\n\n" + tail)
    }

    func stop() {
        try? stdin?.fileHandleForWriting.close()  // the engine exits when its stdin closes
        process?.terminate()
        process = nil
        stdin = nil
    }
}
