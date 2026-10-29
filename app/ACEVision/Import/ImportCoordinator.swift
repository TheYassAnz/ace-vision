import Foundation
import Observation
import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

protocol MatchImporting: Sendable {
    func importVideo(path: URL, view: CourtView, title: String) async throws -> ImportResult
}
extension APIClient: MatchImporting {}

struct PhotosMovie: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(importedContentType: .movie) { received in
            let dir = FileManager.default.temporaryDirectory.appending(path: "ACEVision")
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            let dest = dir.appending(path: "\(UUID().uuidString).\(received.file.pathExtension)")
            try FileManager.default.copyItem(at: received.file, to: dest)
            return PhotosMovie(url: dest)
        }
    }
}

@MainActor @Observable
final class ImportCoordinator {
    var pending: URL?
    var isImporting = false
    var error: String?
    var viewError: String?
    private(set) var deleteAfter = false
    private let api: any MatchImporting

    init(api: any MatchImporting) { self.api = api }

    static let extensions: Set<String> = ["mov", "mp4", "m4v"]

    func offer(_ url: URL, deleteAfter: Bool = false) {
        error = nil
        viewError = nil
        guard Self.extensions.contains(url.pathExtension.lowercased()) else {
            if deleteAfter { try? FileManager.default.removeItem(at: url) }
            error = "Format de vidéo non pris en charge (.mov, .mp4, .m4v)."
            return
        }
        pending = url
        self.deleteAfter = deleteAfter
    }

    func offerPhotosItem(_ item: PhotosPickerItem) async {
        if let movie = try? await item.loadTransferable(type: PhotosMovie.self) {
            offer(movie.url, deleteAfter: true)
        } else {
            error = "Impossible de récupérer cette vidéo depuis Photos. Vérifie qu'elle est téléchargée depuis iCloud, ou exporte-la dans le Finder et importe le fichier."
        }
    }

    func cancel() {
        if deleteAfter, let url = pending { try? FileManager.default.removeItem(at: url) }
        pending = nil
    }

    func confirm(view: CourtView?, title: String, deleteAfter: Bool) async -> ImportResult? {
        guard let url = pending else { return nil }
        guard let view else {
            viewError = "Choisis d'où filmait l'iPhone."
            return nil
        }
        isImporting = true
        error = nil
        defer {
            isImporting = false
            if deleteAfter { try? FileManager.default.removeItem(at: url) }  // success or failure
        }
        do {
            let result = try await api.importVideo(path: url, view: view, title: title)
            pending = nil
            return result
        } catch {
            self.error = error.localizedDescription
            pending = nil
            return nil
        }
    }
}
