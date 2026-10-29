# Notation au clavier, services fantômes, squelette — Plan de correction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre la notation au clavier fiable, ne plus classer en service les coups de fond filmés en vue arrière, et afficher le squelette du joueur sur la vidéo.

**Architecture:** La notation passe d'un `onKeyPress` lié au focus d'un texte à un moniteur d'événements clavier actif tant que le mode notation est ouvert. La règle du service mesure « au-dessus de la tête » depuis la ligne des épaules plutôt que depuis le nez. Le squelette vient de `pose.npz`, servi en binaire par une nouvelle route, et il est dessiné dans le `videoOverlay` du lecteur.

**Tech Stack:** Python 3.12 (uv), FastAPI, NumPy, pytest ; Swift 6, SwiftUI, AppKit (`NSEvent`), AVKit, Swift Testing ; XcodeGen.

**Spec:** problèmes remontés par le joueur le 2026-10-29 et ses réponses (section ci-dessous) ; contraintes d'interface de `docs/superpowers/plans/2026-10-28-app-macos.md` (Global Constraints).

## Problèmes et décisions (2026-10-29)

1. **Notation** : en mode « Noter mes coups », les lettres D/R/S/A ne sont pas prises. Cause : les touches ne sont lues que si le texte d'aide (`PlayerView.swift:46-55`) a le focus clavier ; un clic sur la vidéo ou un bouton le lui retire.
2. **Services fantômes** : sur IMG_7687 (vue arrière, séance d'échanges, **aucun service**, seulement des mises en jeu à la cuillère), 4 coups sur 9 sont classés service (14,8 s, 25,4 s, 31,6 s, 35,0 s). Cause : en vue arrière le nez n'est vu que sur 7 % des images. La « tête » retombe alors sur la ligne des épaules, et sur ces coups le poignet de la raquette monte jusqu'à 0,55 longueur de buste au-dessus des épaules, l'autre poignet jusqu'à 0,28. Un vrai service monte le poignet bien au-dessus du sommet du crâne (synthétique : 1,5).
3. **Squelette** : bouton « Afficher le squelette » sous la vidéo, **masqué par défaut**, choix retenu d'une session à l'autre ; squelette seul (17 points reliés) du joueur suivi.

## Global Constraints

- Celles du plan précédent s'appliquent : texte visible en français, casse de phrase, un bouton nomme son action, une erreur dit quoi faire, Swift 6 sans avertissement, `uv run pytest` sans avertissement (`filterwarnings = error`).
- Tests Swift : `xcodegen generate --spec app/project.yml && xcodebuild test -project app/ACEVision.xcodeproj -scheme ACEVision -destination 'platform=macOS'`.
- Ne jamais toucher aux données du joueur : lecture seule de `~/Library/Application Support/ACE Vision/data/matchs/2026-10-29-img-7687/` pour vérifier la Task 2 ; aucune donnée réelle n'est copiée dans le dépôt (keypoints personnels, projet public).
- Les matchs déjà analysés gardent leurs anciens coups jusqu'à « Relancer l'analyse » : c'est voulu.

## Review Focus

1. **Le joueur tape dans le champ titre de la feuille d'import pendant que la notation est ouverte** : les lettres vont dans le champ, pas dans les notes. → test `ignoresKeysWhileEditingText` (Task 1).
2. **⌘D, ⌘R, ⌘⌫ pendant la notation** : ce sont des raccourcis système ou de l'app, jamais des notes. → test `modifiedKeysAreNotNotes` (Task 1).
3. **Service filmé de face (vue filet, nez visible)** : il reste un service après le changement de règle. → les tests existants `test_overhead_after_pause_is_serve` et `test_first_overhead_is_serve` restent verts (Task 2).
4. **Match d'une heure à 60 i/s** : le squelette se charge sans geler l'app (environ 29 Mo en binaire, pas de JSON). → test de taille de la route (Task 3), chargement asynchrone.
5. **Match analysé avant que `pose.npz` existe, ou dont l'analyse a échoué** : le bouton du squelette affiche « Squelette indisponible : relance l'analyse. » au lieu de planter. → test `test_pose_missing_is_404` (Task 3).

---

### Task 1: Notation au clavier fiable

**Files:**
- Create: `app/ACEVision/Player/NoteKeys.swift`, `app/ACEVisionTests/NoteKeysTests.swift`
- Modify: `app/ACEVision/Views/PlayerView.swift:46-55` (retirer `.focusable().focused(...)` et `.onKeyPress` du texte d'aide, et l'état `keysFocused`)

**Interfaces:**
- Consumes: `NotesSession` (`active`, `recorder.handle(key:at:)`, `recorder.undo()`), `PlayerModel` (`togglePlay()`, `player.currentTime()`).
- Produces:
  - `enum NoteKey: Equatable { case stroke(Character), undo, playPause }`
  - `enum NoteKeys { static func action(characters: String?, keyCode: UInt16, modifiers: NSEvent.ModifierFlags, editingText: Bool) -> NoteKey? }` : renvoie `nil` si `editingText` est vrai, ou si ⌘, ⌃ ou ⌥ est enfoncé. Sinon : `keyCode == 51` (⌫) → `.undo` ; `keyCode == 49` (espace) → `.playPause` ; une lettre d, r, s ou a (sans tenir compte de la casse) → `.stroke(lettre en minuscule)` ; tout le reste → `nil`.
  - Dans `PlayerView` : tant que `notes.active` est vrai, un moniteur `NSEvent.addLocalMonitorForEvents(matching: .keyDown)` est installé. Il est retiré quand la notation se ferme et quand la vue disparaît : un seul moniteur à la fois. `editingText` = `NSApp.keyWindow?.firstResponder is NSText`. Une action reconnue est appliquée puis l'événement est consommé (retour `nil`), sinon il est rendu tel quel. L'horodatage d'une note utilise `model.player.currentTime().seconds`, qui est exact, et non `currentTime`, mis à jour seulement toutes les 0,1 s.

- [ ] **Step 1: Tests qui échouent** dans `NoteKeysTests.swift`

```swift
@Test func lettersBecomeNotes() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [], editingText: false) == .stroke("d"))
    #expect(NoteKeys.action(characters: "R", keyCode: 15, modifiers: [.shift], editingText: false) == .stroke("r"))
    #expect(NoteKeys.action(characters: "x", keyCode: 7, modifiers: [], editingText: false) == nil)
}
@Test func deleteAndSpace() {
    #expect(NoteKeys.action(characters: "\u{7f}", keyCode: 51, modifiers: [], editingText: false) == .undo)
    #expect(NoteKeys.action(characters: " ", keyCode: 49, modifiers: [], editingText: false) == .playPause)
}
@Test func modifiedKeysAreNotNotes() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [.command], editingText: false) == nil)
    #expect(NoteKeys.action(characters: "\u{7f}", keyCode: 51, modifiers: [.command], editingText: false) == nil)
}
@Test func ignoresKeysWhileEditingText() {
    #expect(NoteKeys.action(characters: "d", keyCode: 2, modifiers: [], editingText: true) == nil)
}
```

- [ ] **Step 2:** Lancer les tests Swift → FAIL (`NoteKeys` absent).
- [ ] **Step 3:** Implémenter `NoteKeys`, puis brancher le moniteur dans `PlayerView` (installé et retiré sur `onChange(of: notes.active, initial: true)` et `onDisappear`).
- [ ] **Step 4:** Tests Swift → PASS, sans avertissement.
- [ ] **Step 5: Commit** `fix(app): note keys work wherever the focus is while note mode is on`

---

### Task 2: Service = poignet au-dessus du sommet du crâne

**Files:**
- Modify: `ace/strokes.py:30-50` (`_head_y` remplacée, constantes)
- Test: `tests/test_strokes.py`, `tests/synthetic.py` si un helper manque
- Modify: `README.md` (tableau des réglages, ligne « service »)

**Interfaces:**
- Produces:
  - `HEAD_TOP_ABOVE_SHOULDERS = 0.8` (en longueurs de buste). Commentaire d'une ligne : sur IMG_7687 (vue arrière), les coups de fond montent jusqu'à 0,55 et l'autre poignet jusqu'à 0,28 ; un service synthétique monte à 1,5.
  - `_head_top_y(kp: np.ndarray) -> np.ndarray` : par image, milieu des épaules moins `HEAD_TOP_ABOVE_SHOULDERS * torso_length(kp)`. Le nez n'est plus utilisé (même règle en vue filet et en vue arrière). `_above_head` l'utilise à la place de `_head_y`.
  - Le reste de `classify_stroke` (écart de 3,0 s, fenêtre du lancer, côté du geste) ne change pas.

- [ ] **Step 1: Tests qui échouent**

```python
def test_rear_forehand_with_raised_arms_is_not_serve():
    # IMG_7687, rear view: racket wrist up to 0.55 torso above the shoulders, free wrist 0.28, no face
    kp = _swing("away", "right")
    kp[:, NOSE] = np.nan
    kp[95:104, R_WR, 1] = SH_Y - 55   # torso = 100 px in tests.synthetic
    kp[60:100, L_WR, 1] = SH_Y - 28
    assert _classify(kp) == "forehand"

def test_wrist_just_above_nose_is_not_overhead():
    kp = _swing("camera", "right")
    kp[95:104, R_WR, 1] = NOSE_Y - 10
    kp[60:100, L_WR, 1] = NOSE_Y - 10
    assert _classify(kp) == "forehand"
```

Les tests de service existants (`test_overhead_after_pause_is_serve`, `test_first_overhead_is_serve`, `test_overhead_without_nose_uses_shoulders`, `test_overhead_quick_is_other`, `test_overhead_without_toss_near_midline_is_other`, `test_high_follow_through_without_toss_is_not_serve`) doivent rester verts sans modification. Renommer seulement `test_overhead_without_nose_uses_shoulders` en `test_overhead_seen_from_behind_is_serve`.

- [ ] **Step 2:** `uv run pytest tests/test_strokes.py -v` → les deux nouveaux tests échouent.
- [ ] **Step 3:** Implémenter.
- [ ] **Step 4:** `uv run pytest` → PASS, sans avertissement.
- [ ] **Step 5: Vérification sur données réelles (lecture seule, rien n'est écrit)**
  - IMG_7687 : un script jetable dans le scratchpad charge `~/Library/Application Support/ACE Vision/data/matchs/2026-10-29-img-7687/pose.npz`, appelle `detect_strokes(kp, 59.94, Settings(handedness="right", backhand_hands=2))` et affiche les types. Attendu : aucun `serve`. Les coups à 14,8, 25,4, 31,6 et 35,0 s doivent devenir `forehand` ou `backhand`. Noter le résultat dans le rapport.
  - IMG_2665 : `uv run python scripts/calibrate.py 2026-03-23-img-2665` (données du dépôt), avant et après. Attendu : score identique (il n'y a aucun service sur cette vidéo).
- [ ] **Step 6:** README : dans le tableau, la ligne service devient « poignet de la raquette au-dessus du sommet du crâne (0,8 longueur de buste au-dessus des épaules) autour de l'impact **et** lancer de balle (autre poignet aussi haut dans les 1,5 s avant) ». Retirer la phrase sur la tête remplacée par les épaules en vue arrière, et ajouter : « Relancez l'analyse d'un match pour appliquer la nouvelle règle. »
- [ ] **Step 7: Commit** `fix: serve needs the wrist above the top of the head, not the shoulders seen from behind`

---

### Task 3: Squelette sur la vidéo

**Files:**
- Modify: `ace/web/app.py` (nouvelle route), `tests/test_api.py`
- Modify: `app/ACEVision/API/APIClient.swift` (`pose(_:)`)
- Create: `app/ACEVision/Player/Skeleton.swift` (type `Pose`, géométrie), `app/ACEVision/Views/SkeletonOverlay.swift`, `app/ACEVisionTests/SkeletonTests.swift`
- Modify: `app/ACEVision/Views/PlayerView.swift` (bouton, `videoOverlay`)

**Interfaces:**
- Produces (HTTP) : `GET /matchs/{id}/pose` → `200`, `Content-Type: application/octet-stream`, corps = `kp[:, :, :2]` de `pose.npz` en `float32` little-endian, ordre (image, point, x/y), NaN conservés ; donc `n_images * 17 * 2 * 4` octets. Les coordonnées sont celles de la vidéo redressée (`VideoInfo.width` × `height`). Si `pose.npz` est absent : `404 {"detail": "Squelette indisponible : relance l'analyse."}`. Jeton requis comme pour les autres routes.
- Produces (Swift) :
  - `struct Pose: Sendable { let frames: Int; func point(frame: Int, joint: Int) -> CGPoint? }` : `nil` si le point est NaN ou hors limites, `init(data: Data)`.
  - `APIClient.pose(_ id: String) async throws -> Pose`
  - `enum Skeleton { static let bones: [(Int, Int)]; static func fitRect(video: CGSize, in container: CGSize) -> CGRect; static func frame(at t: Double, fps: Double, count: Int) -> Int }`
    - `bones` : les arêtes COCO-17 (nez, yeux et oreilles ; épaules ; épaule–coude–poignet de chaque côté ; épaules–hanches ; hanches ; hanche–genou–cheville).
    - `fitRect` : rectangle « aspect fit » centré, comme le lecteur affiche la vidéo.
    - `frame` : `Int(t * fps)` borné à `0...count-1`.
  - `SkeletonOverlay(pose:videoSize:fps:player:)` : un `Canvas` dans `TimelineView(.animation)`. Il lit `player.currentTime().seconds` pour choisir l'image et dessine os et articulations en blanc avec un contour sombre, lisibles sur terrain clair comme foncé. `.allowsHitTesting(false)` et `.accessibilityHidden(true)` : l'information reste accessible par la timeline.
  - `PlayerView` : `VideoPlayer(player:videoOverlay:)` affiche `SkeletonOverlay` quand le squelette est demandé et chargé. Bouton « Afficher le squelette » / « Masquer le squelette », état mémorisé par `@AppStorage("showSkeleton")` (faux par défaut). Le premier affichage charge la pose de façon asynchrone, avec un `ProgressView` « Chargement du squelette… ». En cas d'erreur, le message de l'API s'affiche à côté du bouton. La pose est rechargée quand le match change.

- [ ] **Step 1: Tests Python qui échouent** (`tests/test_api.py`, mêmes fixtures que le reste du fichier)

```python
def test_pose_is_float32_frames(tmp_path):
    m = make(); kp = np.full((3, 17, 3), 1.5); kp[1, 0, :2] = np.nan
    np.savez_compressed(store.pose_path(m.id), kp=kp)
    r = client.get(f"/matchs/{m.id}/pose")
    a = np.frombuffer(r.content, dtype="<f4").reshape(3, 17, 2)
    assert r.headers["content-type"] == "application/octet-stream" and a[0, 0, 0] == 1.5 and np.isnan(a[1, 0, 0])

def test_pose_missing_is_404():
    m = make()
    r = client.get(f"/matchs/{m.id}/pose")
    assert r.status_code == 404 and r.json()["detail"] == "Squelette indisponible : relance l'analyse."
```

- [ ] **Step 2: Tests Swift qui échouent** (`SkeletonTests.swift`)

```swift
@Test func poseDecodesNaNAsMissing()      // Data of 2 frames × 17 × 2 Float32, joint 0 of frame 1 = .nan → point(1,0) == nil, point(0,0) == CGPoint(1.5,1.5), point(5,0) == nil
@Test func fitRectLetterboxes()           // video 1920×1080 in 800×600 → CGRect(x: 0, y: 75, width: 800, height: 450); video 1080×1920 in 800×600 → width 337.5, x 231.25
@Test func frameIndexIsClamped()          // frame(at: 1.0, fps: 60, count: 100) == 60; at 5.0 → 99; at -1 → 0
@Test func bonesAreValidJoints()          // every index in 0..<17, 16 bones
```

- [ ] **Step 3:** Lancer les deux suites → FAIL.
- [ ] **Step 4:** Implémenter la route (lecture de `pose.npz`, `kp[:, :, :2].astype("<f4").tobytes()`), puis le côté Swift.
- [ ] **Step 5:** Deux suites → PASS, sans avertissement. Vérifier aussi que la route renvoie environ 514 Ko pour IMG_7687 : 3777 × 17 × 2 × 4 octets, en lisant le `.npz` réel dans un script jetable, sans l'API.
- [ ] **Step 6: Commit** `feat: show the player's skeleton over the video`
