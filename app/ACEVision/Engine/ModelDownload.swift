import CryptoKit
import Foundation

enum SetupError: Error, Equatable {
    case badChecksum, missingFfprobe, uvFailed, badDownload
}

enum ModelDownload {
    static let url = URL(string: "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m-pose.pt")!
    static let sha256 = "29b17eaf3a3117cbea906090dbedf9159f7c6a49db58ec8b99ed2dfde1cf6eb2"

    private final class Progress: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
        let report: @Sendable (Double) -> Void
        init(_ report: @escaping @Sendable (Double) -> Void) { self.report = report }
        func urlSession(_ s: URLSession, downloadTask: URLSessionDownloadTask, didWriteData _: Int64,
                        totalBytesWritten done: Int64, totalBytesExpectedToWrite total: Int64) {
            if total > 0 { report(Double(done) / Double(total)) }
        }
        func urlSession(_ s: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo _: URL) {}
    }

    static func fetch(from: URL, to: URL, expected: String, progress: @escaping @Sendable (Double) -> Void) async throws {
        let fm = FileManager.default
        let part = to.appendingPathExtension("part")
        try fm.createDirectory(at: to.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? fm.removeItem(at: part)
        let (tmp, response) = try await URLSession.shared.download(from: from, delegate: Progress(progress))
        if let http = response as? HTTPURLResponse, http.statusCode != 200 { throw SetupError.badDownload }
        try fm.moveItem(at: tmp, to: part)
        let reader = try FileHandle(forReadingFrom: part)
        defer { try? reader.close() }
        var hasher = SHA256()
        while let chunk = try reader.read(upToCount: 1 << 20), !chunk.isEmpty { hasher.update(data: chunk) }
        let sum = hasher.finalize().map { String(format: "%02x", $0) }.joined()
        guard sum == expected else {
            try? fm.removeItem(at: part)
            throw SetupError.badChecksum
        }
        try? fm.removeItem(at: to)
        try fm.moveItem(at: part, to: to)
        progress(1)
    }
}
