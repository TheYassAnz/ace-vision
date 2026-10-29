import SwiftUI

struct LibraryView: View {
    let api: APIClient
    @State private var library: Library
    @SceneStorage("selection") private var stored: String?

    init(api: APIClient) {
        self.api = api
        _library = State(initialValue: Library(api: api))
    }

    var body: some View {
        NavigationSplitView {
            if library.matches.isEmpty {
                ContentUnavailableView {
                    Label("Ajoute ton premier match", systemImage: "video.badge.plus")
                } description: {
                    Text("Dépose une vidéo de match ici ou choisis-la dans le Finder ou Photos.")
                }
            } else {
                List(library.matches, selection: $library.selection) { m in
                    row(m).tag(m.id)
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
        .task {
            if library.selection == nil { library.selection = stored }
            await library.poll()
        }
        .onChange(of: library.selection) { stored = library.selection }
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
