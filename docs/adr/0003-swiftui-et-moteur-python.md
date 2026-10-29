# Interface SwiftUI, moteur Python

L'interface est une app macOS native en SwiftUI ; l'analyse reste en Python, lancée par l'app comme sous-processus.
L'app parle au moteur par une API JSON locale (127.0.0.1, port libre, jeton aléatoire par lancement) ; le moteur s'arrête quand l'app ferme son stdin.
Une app Swift seule obligerait à convertir les modèles Python (voir 0002) ; pywebview ou Tauri garderaient une interface web, sans rendu natif ni accessibilité VoiceOver aussi fine.
Conséquence : l'app embarque `uv` et un environnement Python à installer au premier lancement.
La licence passe à AGPL-3.0, imposée par Ultralytics.
