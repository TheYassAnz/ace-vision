# ACE Vision — application macOS

Remplace l'appli web (pages Jinja servies par FastAPI, ouvertes dans Safari par `ACE Vision.command`) par une vraie application Mac, publiée en open source.

## Décisions (questions du 2026-10-28)

- **Interface en SwiftUI**, macOS **15** minimum, Apple Silicon. Le moteur d'analyse reste en Python (ADR 0002).
- **Pont : API JSON locale.** L'app lance `python -m ace` au démarrage et l'arrête en quittant. FastAPI ne sert plus que du JSON ; les pages Jinja, `app.js` et `ACE Vision.command` disparaissent.
- **Diffusion open source** : un `.app` léger (code Python + `uv`) en release GitHub. Au premier lancement, l'app installe l'environnement Python et télécharge le modèle YOLO dans `~/Library/Application Support/ACE Vision/`, avec un écran de progression.
- **Refonte complète de l'interface** :
  - fenêtre type Mail/Photos : bibliothèque des matchs en barre latérale, match à droite, analyse en cours visible dans la liste ;
  - lecteur vidéo avec **timeline des coups** (couleur par type, défauts), clic pour sauter au coup, boutons d'extraits des conseils ;
  - **notation intégrée** au lecteur (D/R/S/A, retour arrière, espace), notes visibles sur la timeline à côté des détections ;
  - écran **Progression** : fiabilité et fréquence des défauts d'un match à l'autre (graphiques).
- **Nouveautés** : glisser-déposer une vidéo (fenêtre et icône du Dock), import depuis **Photos**, **notification** macOS de fin d'analyse, **suppression** d'un match.

## Ce qui ne change pas

Le pipeline (`ace/pipeline.py` et ses modules), le format `match.json`, une seule analyse à la fois, tout en local (seule l'installation initiale accède à Internet), tout texte visible en français, vocabulaire de `GLOSSARY.md`.

## Choix faits sans question (à confirmer en relisant le plan)

- `ffprobe` reste requis via Homebrew (`brew install ffmpeg`) : l'écran d'installation le vérifie et donne la commande. L'embarquer est un chantier à part.
- Licence **AGPL-3.0**, imposée par Ultralytics (YOLO) pour un projet publié.
- Release signée **ad hoc**, sans notarisation (compte développeur payant) : le README explique l'ouverture la première fois.
- Les matchs déjà dans `data/` du dépôt se déplacent à la main (une commande dans le README).
