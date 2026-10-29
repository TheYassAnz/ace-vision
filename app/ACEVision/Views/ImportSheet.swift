import SwiftUI

struct ImportSheet: View {
    let coordinator: ImportCoordinator
    let onDone: (ImportResult) -> Void
    @State private var view: CourtView?
    @State private var title = ""

    var body: some View {
        Form {
            Picker("D'où filmait l'iPhone ?", selection: $view) {
                Text("Vue filet").tag(CourtView?.some(.net))
                Text("Vue arrière").tag(CourtView?.some(.rear))
            }
            .pickerStyle(.segmented)
            .onChange(of: view) { coordinator.viewError = nil }
            if let e = coordinator.viewError {
                Label(e, systemImage: "exclamationmark.circle").foregroundStyle(.red).font(.callout)
            }
            TextField("Titre (facultatif)", text: $title, prompt: Text("vs Karim, entraînement…"))
                .autocorrectionDisabled()
            Text("Vue filet : iPhone près du filet, tourné vers toi. Vue arrière : iPhone en paysage, à 60 images/s, derrière toi et en hauteur.")
                .font(.caption).foregroundStyle(.secondary)
            HStack {
                Spacer()
                Button("Annuler") { coordinator.cancel() }
                    .keyboardShortcut(.cancelAction).disabled(coordinator.isImporting)
                if coordinator.isImporting {
                    ProgressView("Import…").controlSize(.small)
                } else {
                    Button("Analyser") {
                        Task { if let r = await coordinator.confirm(view: view, title: title, deleteAfter: coordinator.deleteAfter) { onDone(r) } }
                    }.keyboardShortcut(.defaultAction)
                }
            }
        }
        .formStyle(.grouped)
        .frame(width: 440)
        .interactiveDismissDisabled(coordinator.isImporting)
    }
}
