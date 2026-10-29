import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct LibraryView: View {
    let api: APIClient
    let inbox: Inbox
    @State private var library: Library
    @State private var importer: ImportCoordinator
    @State private var isTargeted = false
    @State private var queuedAlert = false
    @State private var photoItem: PhotosPickerItem?
    @State private var deleteTarget: String?
    @State private var deleteError: String?
    @SceneStorage("selection") private var stored: String?

    init(api: APIClient, inbox: Inbox) {
        self.api = api
        self.inbox = inbox
        _library = State(initialValue: Library(api: api))
        _importer = State(initialValue: ImportCoordinator(api: api))
    }

    var body: some View {
        @Bindable var b = inbox
        NavigationSplitView {
            if library.matches.isEmpty {
                ContentUnavailableView {
                    Label("Ajoute ton premier match", systemImage: "video.badge.plus")
                } description: {
                    Text("Dépose une vidéo de match ici ou choisis-la dans le Finder ou Photos.")
                } actions: {
                    Button("Ajouter un match") { inbox.showFileImporter = true }
                }
            } else {
                List(library.matches, selection: $library.selection) { m in
                    row(m).tag(m.id)
                        .contextMenu { Button("Supprimer le match…", role: .destructive) { deleteTarget = m.id } }
                }
                .safeAreaInset(edge: .bottom) {
                    if let e = library.error {
                        Label(e, systemImage: "exclamationmark.triangle").font(.caption).padding(8)
                            .frame(maxWidth: .infinity, alignment: .leading).background(.bar)
                    }
                }
            }
        } detail: {
            MatchView(api: api, library: library)
        }
        .frame(minWidth: 800, minHeight: 500)
        .toolbar {
            ToolbarItem {
                Menu("Ajouter", systemImage: "plus") {
                    Button("Depuis un fichier…") { inbox.showFileImporter = true }
                    Button("Depuis Photos…") { inbox.showPhotos = true }
                }
            }
        }
        .fileImporter(isPresented: $b.showFileImporter, allowedContentTypes: [.movie]) { result in
            if case .success(let url) = result { importer.offer(url) }
        }
        .photosPicker(isPresented: $b.showPhotos, selection: $photoItem, matching: .videos)
        .onChange(of: photoItem) {
            guard let item = photoItem else { return }
            photoItem = nil
            Task { await importer.offerPhotosItem(item) }
        }
        .dropDestination(for: URL.self) { urls, _ in
            guard let u = urls.first else { return false }
            importer.offer(u)
            return true
        } isTargeted: { isTargeted = $0 }
        .overlay { if isTargeted { RoundedRectangle(cornerRadius: 8).stroke(Color.accentColor, lineWidth: 4).padding(4).allowsHitTesting(false) } }
        .sheet(isPresented: Binding(get: { importer.pending != nil }, set: { if !$0 { importer.cancel() } })) {
            ImportSheet(coordinator: importer) { r in
                Notifier.requestAuthorization()
                Task {
                    await library.refresh()
                    library.selection = r.match.id
                    queuedAlert = r.queued
                    AccessibilityNotification.Announcement("Import terminé").post()
                }
            }
        }
        .alert("Import impossible", isPresented: Binding(get: { importer.error != nil }, set: { if !$0 { importer.error = nil } })) {
            Button("OK") { importer.error = nil }
        } message: { Text(importer.error ?? "") }
        .alert("Analyse en attente", isPresented: $queuedAlert) {
            Button("OK") {}
        } message: { Text("Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer l'analyse.") }
        .confirmationDialog("Supprimer ce match ?", isPresented: Binding(get: { deleteTarget != nil }, set: { if !$0 { deleteTarget = nil } }), titleVisibility: .visible) {
            Button("Supprimer le match", role: .destructive) { if let id = deleteTarget { Task { await delete(id) } } }
            Button("Annuler", role: .cancel) {}
        } message: { Text("La copie de la vidéo et l'analyse seront effacées. La vidéo d'origine n'est pas touchée.") }
        .alert("Suppression impossible", isPresented: Binding(get: { deleteError != nil }, set: { if !$0 { deleteError = nil } })) {
            Button("OK") {}
        } message: { Text(deleteError ?? "") }
        .onChange(of: inbox.opened) {
            inbox.opened.first.map { importer.offer($0) }
        }
        .onChange(of: inbox.notifiedMatch) {
            if let id = inbox.notifiedMatch { library.selection = id; inbox.notifiedMatch = nil }
        }
        .onChange(of: inbox.deleteRequested) {
            if inbox.deleteRequested { deleteTarget = library.selection; inbox.deleteRequested = false }
        }
        .task {
            library.onFinished = { Notifier.post($0) }
            if library.selection == nil { library.selection = stored }
            await library.poll()
        }
        .onChange(of: library.selection) { stored = library.selection }
    }

    private func delete(_ id: String) async {
        do {
            try await api.delete(id)
            if library.selection == id { library.selection = nil }
            await library.refresh()
        } catch {
            let m = error.localizedDescription
            deleteError = m == "Ce match est en cours d'analyse." ? m + " Attends la fin de l'analyse puis réessaie." : m
        }
    }

    private func row(_ m: MatchSummary) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(m.title.isEmpty ? m.id : m.title).lineLimit(1).truncationMode(.middle).help(m.title)
            HStack {
                if let d = m.created.flatMap({ parseCreated($0) }) {
                    Text(dayText(d))
                }
                Text(m.view.label)
            }.font(.caption).foregroundStyle(.secondary)
            if m.status == .running {
                ProgressView(value: m.progress)
                Text("En cours… \(m.progress.percentText)").font(.caption).monospacedDigit()
            } else {
                Text(m.status.label).font(.caption)
            }
        }
        .accessibilityElement(children: .combine)
    }

}
