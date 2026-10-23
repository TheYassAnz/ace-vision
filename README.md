# ACE Vision

Application locale pour Mac qui analyse des vidéos de tennis filmées à l'iPhone. Elle repère chaque coup (coup droit, revers, service), regroupe les échanges, calcule un bilan du match et signale les défauts de technique les plus fréquents avec des conseils. Tout tourne sur votre Mac : rien n'est envoyé sur Internet.

## Installation

```
brew install uv
uv sync
```

## Premier lancement

Double-cliquez sur `ACE Vision.command`. macOS peut demander l'autorisation d'ouvrir le fichier (clic droit > Ouvrir la première fois). Safari s'ouvre sur l'historique des matchs. Pour y accéder plus vite, glissez l'icône dans le Dock.

## Filmer

- **Vue filet** et **vue arrière** : iPhone en **paysage**, **60 images/s**.
- Vue arrière : placez-vous **derrière soi, en hauteur** (par exemple au fond du court, sur un point haut).
- Choisissez la vue à l'import ; elle n'est pas détectée automatiquement.

## Assembler plusieurs vidéos d'un match

Un match = une vidéo. Pour en assembler plusieurs, créez `liste.txt` :

```
file 'IMG_0001.mov'
file 'IMG_0002.mov'
file 'IMG_0003.mov'
```

puis :

```
ffmpeg -f concat -safe 0 -i liste.txt -c copy match.mov
```

## Arrêter le serveur

```
pkill -f "python -m ace"
```

Les journaux sont dans `data/server.log`.

## Données

Chaque match est copié dans `data/matchs/<id>/`. Ce dossier n'est pas versionné. L'application ne supprime jamais rien.

## Calibration

À compléter après les étapes de calibration avec le joueur (valeurs finales de `HIT_MIN_SPEED`, `THRESHOLDS` et scores obtenus).

## Tests

```
uv run pytest            # tests rapides
uv run pytest -m slow    # vraies vidéos et modèles
```
