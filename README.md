# ACE Vision

Application locale pour Mac qui analyse des vidéos de tennis filmées à l'iPhone. Elle repère chaque coup (coup droit, revers, service), calcule un bilan du match et signale les défauts de technique les plus fréquents avec des conseils. Tout tourne sur votre Mac : rien n'est envoyé sur Internet.

## Installation

```
brew install uv
uv sync
```

## Premier lancement

Double-cliquez sur `ACE Vision.command`. macOS peut demander l'autorisation d'ouvrir le fichier (clic droit > Ouvrir la première fois). Safari s'ouvre sur l'historique des matchs. Pour y accéder plus vite, glissez l'icône dans le Dock.

## Filmer

- **Vue filet** : iPhone près du filet, tourné vers vous (vous de face, en entier) ; portrait ou paysage, 30 ou 60 images/s.
- **Vue arrière** : iPhone en **paysage**, **60 images/s**, placé **derrière soi, en hauteur** (par exemple au fond du court, sur un point haut).
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

Chaque match est copié dans `data/matchs/<id>/`. Ce dossier n'est pas versionné. L'application n'a pas de bouton de suppression, mais importer à nouveau la même vidéo (même nom) remplace la copie et l'analyse précédentes ; si la vidéo a changé, les coups notés sont aussi effacés.

## Calibration

Comparer la détection aux coups notés par le joueur sur un match déjà analysé (réutilise `pose.npz`, pas de YOLO) :

```
uv run python scripts/calibrate.py <id du match>
```

Le script affiche, note par note, le coup détecté le plus proche (écart, type), les coups manqués, les fausses frappes et le score. Deux notes à moins de 0,3 s d'écart sont comptées comme un seul coup (touche pressée deux fois).

Valeurs retenues (`ace/strokes.py`) :

| Réglage | Valeur | Pourquoi |
|---|---|---|
| `HIT_MIN_SPEED` | 6,0 longueurs de buste/s | même score sur IMG_2665 de 5 à 8 |
| `MIN_HIT_GAP_S` | 1,2 s | la préparation d'un revers donnait une fausse frappe 0,84 s avant l'impact |
| côté du coup | médiane de 0,6 s à 0,1 s avant l'impact, orientation du corps fixe pour la vidéo | à l'impact le poignet traverse déjà vers l'autre côté |
| service | poignet au-dessus de la tête autour de l'impact **et** lancer de balle (autre poignet au-dessus de la tête dans les 1,5 s avant) | un revers à deux mains finissait poignet au-dessus de la tête |

`THRESHOLDS` (`ace/technique.py`) n'ont pas été recalibrés : les notes du joueur portent sur les coups, pas sur les défauts.

Score sur IMG_2665 (vue filet, droitier, revers à deux mains, 8 coups notés) :

| | Trouvés | Bien classés | Fausses frappes |
|---|---|---|---|
| Avant | 8/8 (100 %) | 1/8 (12 %) | 1 |
| Après | 8/8 (100 %) | 8/8 (100 %) | 0 |

## Tests

```
uv run pytest            # tests rapides
uv run pytest -m slow    # vraies vidéos et modèles
```
