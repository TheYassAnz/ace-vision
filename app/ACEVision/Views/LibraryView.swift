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
                if let d = m.created.flatMap(Self.parse) {
                    Text(d.formatted(Date.FormatStyle(date: .abbreviated, time: .omitted).locale(frFR)))
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

    // created is a local ISO time without zone ("2026-03-04T10:00:00")
    private static let parse: (String) -> Date? = { try? Date($0, strategy: .iso8601.year().month().day().dateTimeSeparator(.standard).time(includingFractionalSeconds: false)) }
}
