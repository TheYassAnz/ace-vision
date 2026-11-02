# Calage de l'impact par le son — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** caler l'instant de chaque frappe sur le claquement balle-raquette de la bande son, au lieu du pic de vitesse du poignet.

**Architecture:** `ace/audio.py` décode la piste son avec ffmpeg et en tire la liste des claquements (attaques brusques au-dessus de 2 kHz). `detect_strokes` garde le pic du poignet pour trouver et classer les frappes, puis déplace `t` et `frame` sur le claquement le plus proche à ±0,1 s. L'analyse calcule les claquements après la pose ; sans son ou en cas d'erreur de décodage, elle continue sans calage.

**Tech Stack:** Python 3.12, numpy, scipy (`scipy.signal`, déjà utilisé), ffmpeg/ffprobe en sous-processus, pytest.

**Spec :** pas de document de spécification ; les décisions ci-dessous viennent de la conversation du 2026-11-02 et remplacent le plan `2026-11-01-suivi-de-balle.md` (PR #8), abandonné après échec de TrackNet, YOLO11 et WASB sur la vidéo arrière.

**Décisions de départ (prototype du 2026-11-02, échange `2026-10-29-echange-3`, 60 i/s) :**
- Sur les 6 frappes nettes, le claquement tombe sur l'image où la balle touche le cordage ; écart avec le pic du poignet : −62, −51, −30, −4, +31, +41 ms.
- Les frappes de l'adversaire s'entendent environ 1,5 s après les nôtres ; la fenêtre de ±0,1 s autour du pic les écarte.
- Un rebond au sol à −110 ms d'un pic (24,02 s) est écarté par cette même fenêtre ; c'est ce qui fixe ±0,1 s plutôt que ±0,15 s.
- La pose garde la main : le son ne crée ni ne supprime aucune frappe, il ne fait que déplacer l'instant.

## Global Constraints

- Branche `feature/sound-impact` partie de `main` ; Conventional Commits ; chaque commit finit par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Aucune nouvelle dépendance : numpy, scipy et ffmpeg suffisent.
- `uv run pytest` sans avertissement (les warnings sont des erreurs) ; les tests qui lancent ffmpeg sont sautés si `shutil.which("ffmpeg")` est `None` (la CI macOS n'installe que xcodegen).
- Textes visibles par l'utilisateur en français ; noms de code et commentaires en anglais, comme le reste du dépôt.
- Une vidéo sans piste son s'analyse exactement comme aujourd'hui.

## Review Focus

1. Vidéo sans piste son (enregistrement d'écran, export muet) : l'analyse finit `done`, frappes au pic du poignet, `sound_hit` à `None` — test dans la tâche 3.
2. Piste son illisible ou ffmpeg en erreur : l'analyse finit `done` sans calage, l'erreur va dans le log, jamais dans l'UI — test dans la tâche 3.
3. Claquement calé après la dernière image (frappe en toute fin de vidéo) : `frame` reste dans `[0, len(kp) - 1]` — test dans la tâche 2 ; le début de vidéo passe par le même `clip`.
4. Deux claquements dans la fenêtre (frappe + rebond) : le plus proche du pic gagne, le plus tôt à égalité — test dans la tâche 2.
5. Vidéo à 59,94 i/s (`2026-10-29-img-7687`) : `frame = round(t_click * fps)` et `t = frame / fps`, sans dérive — couvert par le test de calage de la tâche 2 avec `fps = 59.94`.

---

### Task 1: Claquements de la bande son

**Files:**
- Create: `ace/audio.py`
- Test: `tests/test_audio.py`

**Interfaces:**
- Produces:
  - `SAMPLE_RATE = 48000`
  - `read_audio(path: Path) -> np.ndarray | None` : mono float32 dans [−1, 1] à `SAMPLE_RATE` ; `None` si le fichier n'a aucune piste son ; lève `subprocess.CalledProcessError` si ffmpeg échoue.
  - `impact_clicks(samples: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray` : instants des claquements en secondes, float64, triés ; tableau vide sur du silence.

- [ ] **Step 1: Écrire les tests**

```python
SR = 48000

def _clicks_at(times, dur=4.0, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 0.002, int(dur * SR)).astype(np.float32)  # room noise floor
    for t in times:
        i = int(t * SR)
        a[i:i + 240] += rng.normal(0, 0.3, 240) * np.exp(-np.arange(240) / 60)  # 5 ms broadband crack
    return a

def test_finds_each_click_to_the_millisecond():
    got = impact_clicks(_clicks_at([0.5, 1.7, 3.1]), SR)
    assert len(got) == 3 and np.allclose(got, [0.5, 1.7, 3.1], atol=0.003)

def test_silence_has_no_click():
    assert impact_clicks(np.zeros(SR * 2, np.float32), SR).size == 0

def test_low_thump_is_not_a_click():  # footstep / ball bounce on a hard floor: energy below 2 kHz
    t = np.arange(SR * 2) / SR
    a = (0.5 * np.sin(2 * np.pi * 120 * t) * np.exp(-((t - 1.0) / 0.01) ** 2)).astype(np.float32)
    assert impact_clicks(a, SR).size == 0

def test_clicks_closer_than_150_ms_count_once():
    assert len(impact_clicks(_clicks_at([1.0, 1.08]), SR)) == 1

@needs_ffmpeg
def test_read_audio_none_without_audio_track(tmp_path):  # ffmpeg -f lavfi -i testsrc=d=1 -an
    ...
    assert read_audio(p) is None

@needs_ffmpeg
def test_read_audio_mono_48k(tmp_path):  # testsrc=d=1 + sine=f=1000:d=1, stereo
    ...
    a = read_audio(p)
    assert a.dtype == np.float32 and a.ndim == 1 and abs(len(a) - SAMPLE_RATE) < SAMPLE_RATE * 0.05
```

`needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg absent")`. Les deux vidéos de test sont générées dans `tmp_path` par `subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", ...], check=True)`.

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `uv run pytest tests/test_audio.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'ace.audio'`

- [ ] **Step 3: Implémenter `ace/audio.py`**

`read_audio` : `ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0` ; sortie vide → `None`. Sinon `ffmpeg -v error -i <path> -vn -ac 1 -ar 48000 -f s16le -` (`capture_output=True, check=True`), puis `np.frombuffer(..., np.int16).astype(np.float32) / 32768`.

`impact_clicks`, constantes au début du module avec une ligne de pourquoi chacune :

```python
HIGHPASS_HZ = 2000      # the racket crack is broadband; footsteps, bounces and voices sit lower
ENV_MS = 3              # RMS window of the envelope
RISE_MS = 5             # an impact rises within a few ms
MIN_RISE_DB = 12.0      # rise over RISE_MS that counts as a click (prototype 2026-11-02: real hits 14-31 dB)
MIN_CLICK_GAP_S = 0.15  # one click per impact, its echo merged
```

Algorithme (celui du prototype validé) : filtre `butter(4, HIGHPASS_HZ, "highpass", fs=sr, output="sos")` + `sosfilt` ; enveloppe RMS sur `ENV_MS` échantillonnée toutes les 1 ms ; `db = 20 * log10(env + 1e-6)` ; montée `max(0, db[k] - db[k - RISE_MS])` ; `find_peaks(rise, height=MIN_RISE_DB, distance=MIN_CLICK_GAP_S * 1000)` ; renvoyer `peaks / 1000.0`.

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `uv run pytest tests/test_audio.py -v`
Expected: 6 passed (ou 4 passed, 2 skipped sans ffmpeg)

- [ ] **Step 5: Commit**

```bash
git add ace/audio.py tests/test_audio.py
git commit -m "feat(audio): find racket impact clicks in the soundtrack"
```

### Task 2: Caler les frappes sur le claquement

**Files:**
- Modify: `ace/domain.py` (`Stroke`)
- Modify: `ace/strokes.py` (`detect_strokes`, nouvelle `sound_impact`)
- Modify: `app/ACEVisionTests/Fixtures/match.json` (régénéré)
- Test: `tests/test_strokes.py`, `tests/test_api.py`

**Interfaces:**
- Consumes: `impact_clicks(...) -> np.ndarray` (tâche 1), sous la forme d'un tableau de secondes.
- Produces:
  - `Stroke.sound_hit: bool | None = None` — `True` calée sur un claquement, `False` aucun claquement dans la fenêtre, `None` analysé sans son.
  - `SOUND_SEARCH_S = 0.1` dans `ace/strokes.py`.
  - `sound_impact(clicks: np.ndarray, t: float) -> float | None` : le claquement le plus proche de `t` à `SOUND_SEARCH_S` près, le plus tôt à égalité ; `None` sinon.
  - `detect_strokes(kp, fps, settings, clicks: np.ndarray | None = None) -> list[Stroke]`.

Règle : la frappe est toujours trouvée au pic du poignet `p`. `kind` et `wrist_speed` restent calculés au pic (leurs seuils ont été calibrés là). Si un claquement `c = sound_impact(clicks, p / fps)` existe : `frame = clip(round(c * fps), 0, len(kp) - 1)`, `t = frame / fps`, `sound_hit = True`. Sinon `frame = p`, `t = p / fps`, et `sound_hit = False` si `clicks` n'est pas `None`, `None` sinon.

- [ ] **Step 1: Écrire les tests**

```python
def test_sound_impact_picks_closest_then_earliest():
    clicks = np.array([0.95, 1.05, 1.3])
    assert sound_impact(clicks, 1.0) == 0.95          # tie at 50 ms: earlier wins
    assert sound_impact(clicks, 1.04) == 1.05
    assert sound_impact(clicks, 1.2) == 1.3           # bound included: abs(c - t) <= SOUND_SEARCH_S
    assert sound_impact(clicks, 1.5) is None
    assert sound_impact(np.array([]), 1.0) is None

def test_strokes_move_to_the_click():
    kp = make_pose(300); add_swing(kp, 150)
    peak = detect_strokes(kp, FPS, RIGHT)[0]
    s = detect_strokes(kp, FPS, RIGHT, clicks=np.array([peak.t + 0.05]))[0]
    assert s.frame == peak.frame + round(0.05 * FPS) and s.t == s.frame / FPS
    assert s.sound_hit is True and s.kind == peak.kind and s.wrist_speed == peak.wrist_speed

def test_strokes_at_5994_fps_frame_and_t_agree():
    kp = make_pose(600); add_swing(kp, 300)
    fps = 59.94
    peak = detect_strokes(kp, fps, RIGHT)[0]
    s = detect_strokes(kp, fps, RIGHT, clicks=np.array([peak.t - 0.04]))[0]
    assert s.frame == round((peak.t - 0.04) * fps) and s.t == s.frame / fps

def test_no_click_in_window_keeps_the_peak():
    kp = make_pose(300); add_swing(kp, 150)
    peak = detect_strokes(kp, FPS, RIGHT)[0]
    s = detect_strokes(kp, FPS, RIGHT, clicks=np.array([peak.t + 1.5]))[0]  # opponent's hit
    assert (s.frame, s.sound_hit) == (peak.frame, False)

def test_without_sound_sound_hit_is_none():
    kp = make_pose(300); add_swing(kp, 150)
    assert detect_strokes(kp, FPS, RIGHT)[0].sound_hit is None

def test_click_after_last_frame_is_clamped():
    kp = make_pose(300); add_swing(kp, 150)
    peak = detect_strokes(kp, FPS, RIGHT)[0]
    short = kp[: peak.frame + 2]  # the video ends one frame after the peak
    s = detect_strokes(short, FPS, RIGHT, clicks=np.array([peak.t + 0.09]))
    assert s[0].frame == len(short) - 1 and s[0].sound_hit is True
```

Si `detect_hits` ne trouve plus le pic sur la pose coupée, couper une image plus loin (`peak.frame + 3`) et garder le claquement à `peak.t + 0.09` (2,7 images après le pic à 30 i/s, donc toujours hors de la vidéo).

Dans `tests/test_api.py::test_api_fixture_matches_swift_fixture`, donner `sound_hit=True` au second `Stroke`.

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `uv run pytest tests/test_strokes.py tests/test_api.py -v`
Expected: FAIL, `ImportError: cannot import name 'sound_impact'` et écart de fixture.

- [ ] **Step 3: Implémenter**

`Stroke.sound_hit: bool | None = None  # impact timed on the racket click; None when analysed without sound` dans `ace/domain.py`, après `wrist_speed`. `SOUND_SEARCH_S` et `sound_impact` dans `ace/strokes.py`, près de `detect_strokes` ; `detect_strokes` suit la règle ci-dessus.

- [ ] **Step 4: Régénérer la fixture et lancer les tests**

Run: `UPDATE_FIXTURES=1 uv run pytest tests/test_api.py::test_api_fixture_matches_swift_fixture -q && uv run pytest -q`
Expected: tout passe ; `git diff app/ACEVisionTests/Fixtures/match.json` n'ajoute que `"sound_hit": null` et `"sound_hit": true`. L'app Swift ignore la nouvelle clé (Decodable), aucun code Swift ne change.

- [ ] **Step 5: Commit**

```bash
git add ace/domain.py ace/strokes.py tests/test_strokes.py tests/test_api.py app/ACEVisionTests/Fixtures/match.json
git commit -m "feat(strokes): time each stroke on the racket click when one is heard"
```

### Task 3: Brancher le son dans l'analyse et les outils

**Files:**
- Modify: `ace/pipeline.py`
- Modify: `scripts/calibrate.py`
- Create: `scripts/impact_frames.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `read_audio`, `impact_clicks` (tâche 1) ; `detect_strokes(..., clicks=)` (tâche 2).
- Produces: `pipeline.analyse` remplit `sound_hit` ; `scripts/impact_frames.py <match_id>` écrit `impacts.jpg` dans le dossier du match.

- [ ] **Step 1: Écrire les tests** (dans `tests/test_pipeline.py`, avec `_fake_pose` existant)

```python
def test_strokes_timed_on_clicks(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    peaks = [f / INFO.fps for f in range(60, 660, 100)]  # add_swing peaks in _fake_pose
    monkeypatch.setattr(pipeline, "read_audio", lambda p: np.zeros(10, np.float32))
    monkeypatch.setattr(pipeline, "impact_clicks", lambda a: np.array([t + 0.05 for t in peaks]))
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "done" and all(s.sound_hit for s in m.strokes)

def test_no_audio_track_analyses_as_before(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    monkeypatch.setattr(pipeline, "read_audio", lambda p: None)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "done" and len(m.strokes) == 6 and all(s.sound_hit is None for s in m.strokes)

def test_unreadable_audio_still_done(match, monkeypatch, caplog):
    def bad(p):
        raise subprocess.CalledProcessError(1, ["ffmpeg"])
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    monkeypatch.setattr(pipeline, "read_audio", bad)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert (m.status, m.error) == ("done", None) and all(s.sound_hit is None for s in m.strokes)
    assert "son" in caplog.text or "audio" in caplog.text
```

Ajouter `monkeypatch.setattr(pipeline, "read_audio", lambda p: None)` à la fixture `env` (autouse) pour que les tests existants ne lancent pas ffmpeg sur le faux fichier `b"x"` ; les trois tests ci-dessus la redéfinissent.

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL, `AttributeError: <module 'ace.pipeline'> has no attribute 'read_audio'`

- [ ] **Step 3: Implémenter**

`ace/pipeline.py` : importer `read_audio, impact_clicks` depuis `ace.audio`. Juste après `np.savez_compressed(store.pose_path(...))` :

```python
clicks = None
try:
    audio = read_audio(store.match_dir(match_id) / m.video_file)
    clicks = impact_clicks(audio) if audio is not None else None
except Exception:
    log.warning("sound of %s unreadable, strokes stay on the wrist peak", match_id, exc_info=True)
```

puis `detect_strokes(kp, info.fps, m.settings, clicks=clicks)`. La progression ne change pas (le son prend moins d'une seconde).

`scripts/calibrate.py` : lire le son de la vidéo du match comme le pipeline (même `try`, `None` en cas d'échec) ; si `clicks` n'est pas `None`, imprimer la ligne `Score` deux fois, préfixée `sans son :` puis `avec son :`, suivie de `calées sur le son : <n>/<total>` et `décalage moyen : <x> ms` (moyenne de `|t_son - t_pic|` sur les frappes calées). Le tableau détaillé utilise les frappes avec son.

`scripts/impact_frames.py <match_id>` : recalcule les frappes comme `calibrate.py` (pose.npz + son), extrait l'image à `s.t` de chaque frappe avec `ffmpeg -ss <t> -i <video> -frames:v 1 -vf scale=480:-1`, écrit sur chacune `"<t> s  son"` ou `"<t> s  poignet"` avec `cv2.putText` (le ffmpeg de Homebrew n'a pas `drawtext`), assemble une grille de 4 colonnes et l'écrit dans `<dossier du match>/impacts.jpg`. Usage dans la docstring, même en-tête `sys.path` que `calibrate.py`.

- [ ] **Step 4: Lancer tous les tests**

Run: `uv run pytest -q`
Expected: tout passe, aucun avertissement.

- [ ] **Step 5: Commit**

```bash
git add ace/pipeline.py scripts/calibrate.py scripts/impact_frames.py tests/test_pipeline.py
git commit -m "feat(pipeline): time strokes on the soundtrack, fall back to the wrist peak"
```

### Task 4: Vérifier sur les vraies vidéos et calibrer

**Files:**
- Modify: `ace/audio.py` et `ace/strokes.py` (constantes seulement, si la mesure le demande)
- Modify: `README.md` (une courte section « Calage par le son »)

Données (`ACE_DATA_DIR=~/Library/Application\ Support/ACE\ Vision/data`) :
- `2026-10-29-echange-3` : 33,5 s, 60 i/s, vue arrière, pas de notes.
- `2026-10-29-img-7687` : 62,7 s, 59,94 i/s, vue arrière, notes du joueur ; `pose.npz` complet mais statut `failed` (« Analyse interrompue ») : `calibrate.py` lit `pose.npz` directement, pas besoin de relancer l'analyse.

- [ ] **Step 1: Contrôle à l'image sur les deux vidéos**

Run: `uv run python scripts/impact_frames.py 2026-10-29-echange-3` puis la même chose pour `2026-10-29-img-7687`.
Expected : sur chaque vignette marquée « son », la balle touche ou vient de toucher le cordage. Compter les vignettes « son » fausses ; si plus d'une sur dix, ajuster `MIN_RISE_DB` ou `SOUND_SEARCH_S` et recommencer.

- [ ] **Step 2: Score sur les notes**

Run: `uv run python scripts/calibrate.py 2026-10-29-img-7687`
Expected : « trouvés » et « bien classés » avec son ≥ sans son. Les notes sont tapées à la main (latence humaine), donc l'écart frappe-note ne mesure pas la précision du calage : seul le contrôle à l'image de l'étape 1 la mesure.

- [ ] **Step 3: Noter le résultat**

README, section « Calage par le son » : le principe en deux phrases, la part de frappes calées et l'écart moyen mesurés sur les deux vidéos, et la limite connue (vidéo sans son ou très bruitée → instant du poignet). Mettre à jour le commentaire de `MIN_RISE_DB` / `SOUND_SEARCH_S` si elles ont changé, avec le nom de la vidéo qui les a fixées.

- [ ] **Step 4: Commit**

```bash
git add README.md ace/audio.py ace/strokes.py
git commit -m "chore(strokes): calibrate sound timing on rear-view videos"
```

- [ ] **Step 5: PR**

Pousser `feature/sound-impact`, ouvrir la PR vers `main` avec les chiffres de l'étape 1 et 2 ; le corps finit par `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
