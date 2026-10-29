import AppKit
import SwiftUI

struct SetupView: View {
    let setup: EngineSetup
    let retry: () -> Void

    private let steps: [(EngineSetup.Step, String)] = [
        (.checkingFfprobe, "Vérification de ffmpeg…"), (.copyingEngine, "Copie du moteur…"),
        (.installingPython, "Installation de Python…"), (.downloadingModel, "Téléchargement du modèle…"),
    ]
    private let command = "brew install ffmpeg"

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Préparation d'ACE Vision").font(.title2.bold())
            Text("Une seule fois, environ 1 Go à télécharger.").foregroundStyle(.secondary)
            ForEach(steps, id: \.0) { step, label in
                let done = step.rawValue < setup.step.rawValue
                Label {
                    Text(done ? label.replacingOccurrences(of: "…", with: "") : label)
                        .foregroundStyle(step == setup.step || done ? .primary : .secondary)
                } icon: {
                    Image(systemName: done ? "checkmark.circle.fill" : step == setup.step ? "circle.dotted" : "circle")
                }
            }
            if setup.error == nil {
                if let p = setup.progress { ProgressView(value: p) } else { ProgressView().progressViewStyle(.linear) }
                Text(setup.detail).font(.caption.monospaced()).foregroundStyle(.secondary)
                    .lineLimit(1).truncationMode(.middle)
            }
            if let error = setup.error {
                Text(error).foregroundStyle(.red)
                if setup.ffmpegMissing {
                    HStack {
                        Text(command).font(.body.monospaced()).textSelection(.enabled)
                        Button("Copier la commande") {
                            NSPasteboard.general.clearContents()
                            NSPasteboard.general.setString(command, forType: .string)
                        }
                    }
                }
                Button("Réessayer", action: retry).keyboardShortcut(.defaultAction)
            }
        }
        .frame(maxWidth: 460, alignment: .leading)
        .padding(40)
    }
}
