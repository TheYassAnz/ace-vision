# ace-vision — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Une appli web locale (Mac) où le joueur ajoute la vidéo iPhone d'un match de simple et obtient un bilan : ses coups (coup droit, revers, service, autre), ses défauts techniques fréquents avec conseils et extraits vidéo, puis — en vue arrière — échanges, fautes et carte du court.

**Architecture:** Un package Python `ace` : un pipeline d'analyse (vidéo → pose du joueur → frappes → coups → mesures/défauts → constats ; en vue arrière : + balle TrackNet → court → échanges → issues) qui écrit un `match.json` par match, et un serveur FastAPI (127.0.0.1) qui génère les pages HTML (Jinja2) et exécute une seule analyse à la fois dans un thread. Lancement par un fichier `ACE Vision.command` qui ouvre Safari.

**Tech Stack:** Python 3.12 (uv), FastAPI + Uvicorn + Jinja2 + python-multipart, Pydantic v2 (via FastAPI) pour les données, Ultralytics YOLO11-pose (MPS), OpenCV (via Ultralytics), NumPy, SciPy, PyTorch (MPS) pour TrackNet ; pytest + httpx. ffprobe/ffmpeg (déjà installés via Homebrew).

**Spec:** `docs/superpowers/specs/2026-10-23-ace-vision-design.md` · Vocabulaire : `GLOSSARY.md` · Décisions : `docs/adr/`

## Global Constraints

- Python **3.12** via `uv` (`brew install uv`) ; jamais le Python 3.14 système.
- Tout tourne en local : serveur lié à **127.0.0.1** uniquement ; aucun appel réseau à l'exécution (seul le téléchargement initial des poids de modèles est permis).
- **Pas d'IA générative en V1** ; pas de clé API.
- Code et identifiants en **anglais** ; **tout texte visible par l'utilisateur en français**.
- Correspondance vocabulaire (GLOSSARY.md → code) : frappe=`hit`, coup=`Stroke`, échange=`Rally`, point=`point`, défaut=`defect`, constat=`Finding`, conseil=`Advice`, faute=`fault`, match=`Match`, vue=`view`.
- Types de coup (valeurs) : `forehand`, `backhand`, `serve`, `other` ; libellés : « Coup droit », « Revers », « Service », « Autre ».
- Vues : `net` (« Vue filet »), `rear` (« Vue arrière »), choisie par l'utilisateur à l'import ; pas de détection automatique.
- **Service** = coup bras au-dessus de la tête précédé d'**au moins 3,0 s sans frappe**, sinon `other`.
- **Défauts V1** (ids) : `late_prep` (rotation des épaules finie **< 0,4 s** avant l'impact), `small_turn`, `straight_legs`, `narrow_stance`.
- **Constat** : défaut présent sur **≥ 40 %** des coups de ce type **et ≥ 5** coups ; **3 constats max**, les plus fréquents d'abord.
- **Un match = une vidéo** ; copie gardée dans `data/matchs/<id>/` ; ré-analyser remplace l'analyse ; **pas de suppression** dans l'app ; `data/` hors git.
- **Une analyse à la fois** ; analyse interrompue → statut `failed` + bouton « Relancer ».
- Réglages globaux : droitier/gaucher (`right`/`left`), revers à 1 ou 2 mains (`1`/`2`).
- Navigateur cible : **Safari** (lecture HEVC native, aucune conversion vidéo).
- Objectif de fiabilité V1 (notes du joueur) : **≥ 90 %** des coups trouvés, **≥ 85 %** bien classés.
- Les blocs du bilan non calculables (issue, carte, échanges en vue filet) sont **masqués avec une phrase d'explication**, jamais remplis de chiffres inventés.
- Tests lents (vraies vidéos, modèles) marqués `@pytest.mark.slow` et sautés si le fichier requis manque. Commande : `uv run pytest` (rapides) / `uv run pytest -m slow`.

## Review Focus

1. **Vidéo iPhone en portrait stockée « couchée »** (matrice de rotation −90°, comme `IMG_2665.mov`) : images, points du corps et affichage doivent être droits (1116 × 1986). → test dans Task 1.
2. **Autres personnes dans l'image** (adversaire, joueurs du court voisin, ramasseurs) : l'analyse suit toujours le même joueur, celui présent le plus et le plus grand. → test dans Task 2.
3. **Match d'1 h en 4K (10 Go+)** : l'envoi est écrit sur disque par morceaux et les images lues en flux, jamais tout en mémoire. → tests dans Task 1 (générateur) et Task 9 (upload par morceaux).
4. **Gestes qui ne sont pas des coups** (faire rebondir la balle avant de servir, swing à vide lent, ramasser une balle, marcher) : pas comptés comme coups. → test dans Task 3, mesuré en vrai dans Task 12.
5. **Points du corps douteux** (joueur à moitié hors champ, confiance faible) : aucune mesure ni défaut affirmé à partir de valeurs manquantes. → test dans Task 5.

---

## Structure des fichiers

```
pyproject.toml                 # uv, Python 3.12, deps, pytest markers
ACE Vision.command             # double-clic : démarre le serveur + ouvre Safari
.gitignore                     # data/ videos/ models/ .superpowers/ .venv/
ace/
  __main__.py                  # python -m ace → serveur + Safari
  domain.py                    # modèles Pydantic : Settings, VideoInfo, Stroke, Rally, Finding, Match
  video.py                     # probe(), iter_frames()
  pose.py                      # extract_pose(), select_player()  (COCO-17)
  geometry.py                  # helpers points du corps (torso_length, angle, ...)
  strokes.py                   # detect_hits(), classify_stroke(), detect_strokes()
  technique.py                 # measure(), detect_defects(), THRESHOLDS
  findings.py                  # build_findings()
  advice.fr.json               # conseils pré-rédigés par défaut
  notes.py                     # Note, Score, score_detection()
  store.py                     # dossiers de matchs, match.json, réglages
  pipeline.py                  # analyse() : orchestre les étapes, progression
  jobs.py                      # JobRunner : une analyse à la fois, recover_interrupted()
  web/app.py                   # routes FastAPI
  web/templates/*.html         # base, history, add, match_running, match_failed, match_report, notes, settings, ball_labels
  web/static/app.js            # progression, extraits, notation clavier
  # Partie 2 (vue arrière)
  ball.py                      # TrackNet : track_ball(), interpolate_gaps()
  tracknet_model.py            # définition du réseau (vendorisée, avec attribution)
  court.py                     # detect_court(), to_court()  (repère en mètres)
  rallies.py                   # detect_bounces(), detect_opponent_hits(), segment_rallies()
  outcome.py                   # rally_end(), serve_stats()
scripts/finetune_tracknet.py   # Partie 3
tests/                         # un fichier de test par module
```

Repère du court (Parties 2-3) : mètres, origine = centre du filet, `x` en travers (positif à droite vu de la caméra), `y` le long du court, **positif vers le côté adverse**. Simple : |x| ≤ 4,115 ; fond de court : |y| = 11,885 ; carrés de service : 0 < y ≤ 6,40.

---

# Partie 1 — Vue filet (les vidéos actuelles du joueur)

### Task 0: Projet, outillage et modèle de données

**Files:**
- Create: `.gitignore`, `pyproject.toml`, `ace/__init__.py`, `ace/domain.py`, `tests/test_domain.py`

**Interfaces:**
- Produces (`ace/domain.py`, Pydantic `BaseModel`) :
  - `StrokeKind = Literal["forehand","backhand","serve","other"]`, `View = Literal["net","rear"]`, `Status = Literal["pending","running","done","failed"]`, `DefectId = Literal["late_prep","small_turn","straight_legs","narrow_stance"]`, `Outcome = Literal["net","long","wide","in","unknown"]`, `RallyEnd = Literal["net","long","wide","not_returned","unknown"]`
  - `Settings(handedness: Literal["right","left"]="right", backhand_hands: Literal[1,2]=2)`
  - `VideoInfo(width: int, height: int, fps: float, duration_s: float, n_frames: int, rotation: int, created: str | None)` — `width/height` déjà redressés
  - `Stroke(t: float, frame: int, kind: StrokeKind, metrics: dict[str, float] = {}, defects: list[DefectId] = [], outcome: Outcome = "unknown")`
  - `Rally(start_t: float, end_t: float, n_hits: int, end: RallyEnd, last_stroke: StrokeKind | None, user_hit_last: bool, is_serve_fault: bool = False)`
  - `Finding(kind: StrokeKind, defect: DefectId, count: int, total: int, title: str, text: str, drill: str, clip_times: list[float])`
  - `Match(id: str, title: str = "", view: View, status: Status = "pending", progress: float = 0.0, error: str | None = None, video_file: str, info: VideoInfo | None = None, settings: Settings = Settings(), strokes: list[Stroke] = [], rallies: list[Rally] | None = None, findings: list[Finding] = [], score: "Score | None" = None)` (`Score` défini en Task 11 ; mettre `dict | None` jusque-là puis typer)
  - `STROKE_LABELS: dict[StrokeKind, str]` (libellés français des Global Constraints)

- [ ] **Step 1:** `brew install uv` ; `git init` ; `.gitignore` avec `data/`, `videos/`, `models/`, `.superpowers/`, `.venv/`, `__pycache__/`, `*.pt`.
- [ ] **Step 2:** `pyproject.toml` : `requires-python = "==3.12.*"`, deps `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, `ultralytics`, `numpy`, `scipy` ; groupe dev `pytest`, `httpx` ; `[tool.pytest.ini_options] markers = ["slow: vraies vidéos/modèles"]`, `addopts = "-m 'not slow'"`. Run `uv python install 3.12 && uv sync`.
- [ ] **Step 3: test qui échoue** — `tests/test_domain.py::test_match_roundtrip_json` : un `Match` avec 1 `Stroke(kind="forehand", defects=["late_prep"])` → `Match.model_validate_json(m.model_dump_json()) == m` ; `test_rallies_none_by_default` : `Match(id="x", view="net", video_file="v.mov").rallies is None`.
- [ ] **Step 4:** `uv run pytest` → FAIL (module absent). Implémenter `ace/domain.py`. → PASS.
- [ ] **Step 5: Commit** (inclut `docs/`, `GLOSSARY.md`) : `git add -A && git commit -m "chore: scaffold ace package and domain model"`

### Task 1: Lecture vidéo (rotation iPhone, flux d'images)

**Files:** Create `ace/video.py`, `tests/test_video.py`

**Interfaces:**
- Produces: `probe(path: Path) -> VideoInfo` ; `parse_ffprobe(d: dict) -> VideoInfo` (pur, testable) ; `iter_frames(path: Path) -> Iterator[tuple[int, np.ndarray]]` (BGR, redressée).

- [ ] **Step 1: tests qui échouent**
  - `test_parse_ffprobe_portrait_rotated` : dict ffprobe `-show_streams -show_format -of json` avec `width=1986, height=1116, r_frame_rate="30/1", nb_frames="920", side_data_list=[{"rotation": -90}]`, `format.duration="30.683"`, `tags.creation_time="2026-03-23T17:12:34.000000Z"` → `VideoInfo(width=1116, height=1986, fps=30.0, n_frames=920, rotation=-90, created="2026-03-23T17:12:34")`.
  - `test_parse_ffprobe_landscape_no_rotation` : 1920×1080, `60000/1001` → `fps≈59.94`, `rotation=0`, `created=None` sans tag.
  - `@slow test_probe_real_video` (skip si `videos/IMG_2665.mov` absent) : `width==1116, height==1986, fps==30`.
  - `@slow test_iter_frames_upright_and_lazy` : `iter_frames` renvoie un générateur (`inspect.isgenerator`) ; 1re image `shape == (1986, 1116, 3)`.
- [ ] **Step 2:** `uv run pytest tests/test_video.py` → FAIL.
- [ ] **Step 3:** `probe` lance `ffprobe -v error -select_streams v:0 -show_streams -show_format -of json` puis `parse_ffprobe` (inverser w/h si |rotation| = 90). `iter_frames` via `cv2.VideoCapture` (qui applique la rotation par défaut ; si l'image sort couchée, `cv2.rotate` selon `rotation`).
- [ ] **Step 4:** `uv run pytest tests/test_video.py -m "slow or not slow"` → PASS.
- [ ] **Step 5: Commit** `feat: video probing with iPhone rotation`

### Task 2: Pose du joueur

**Files:** Create `ace/pose.py`, `ace/geometry.py`, `tests/test_pose.py`

**Interfaces:**
- Consumes: `iter_frames`, `VideoInfo`.
- Produces:
  - `select_player(tracks: dict[int, list[tuple[int, float, np.ndarray]]], n_frames: int) -> np.ndarray` — `tracks[id] = [(frame, box_area, kpts(17,3)), ...]` → tableau `(n_frames, 17, 3)` (x, y, confiance), `NaN` sans joueur.
  - `extract_pose(path: Path, info: VideoInfo, on_progress: Callable[[float], None]) -> np.ndarray` (même forme).
  - `geometry.py` : indices COCO `NOSE=0, L_SH=5, R_SH=6, L_EL=7, R_EL=8, L_WR=9, R_WR=10, L_HIP=11, R_HIP=12, L_KNEE=13, R_KNEE=14, L_ANK=15, R_ANK=16` ; `torso_length(kp) -> float` (médiane, sur toute la vidéo, de la distance milieu épaules → milieu hanches) ; `angle_deg(a, b, c) -> float` (angle en b) ; `MIN_CONF = 0.3` (en dessous, le point vaut NaN).

- [ ] **Step 1: tests qui échouent**
  - `test_select_player_prefers_persistent_track` : piste A aire 100 sur 900 images, piste B aire 300 sur 50 images → les images de A sont remplies, celles de B seules restent NaN.
  - `test_select_player_nan_when_absent` : aucune piste aux images 10-20 → `np.isnan(out[10:21]).all()`.
  - `test_low_confidence_points_become_nan` : un point de confiance 0.1 → NaN dans la sortie.
  - `test_angle_deg_straight_leg` : points alignés → 180 ± 0.1 ; angle droit → 90.
  - `@slow test_extract_pose_real_video` : sur `IMG_2665.mov`, ≥ 90 % des images ont les hanches non NaN ; affiche la vitesse (images/s).
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** `select_player` : score d'une piste = **somme des aires de boîte** sur ses images ; on garde la meilleure. `extract_pose` : `YOLO("yolo11m-pose.pt").track(frame, persist=True, device="mps", imgsz=960, verbose=False)` image par image depuis `iter_frames`, accumule les pistes, appelle `on_progress(i / n_frames)`. Sauvegarde gérée par le pipeline (Task 8).
- [ ] **Step 4:** → PASS. Noter la vitesse mesurée dans le message de commit ; si < 15 images/s, passer à `yolo11s-pose.pt` et re-mesurer.
- [ ] **Step 5: Commit** `feat: player pose extraction`

### Task 3: Détection des frappes du joueur

**Files:** Create `ace/strokes.py`, `tests/test_strokes.py`, `tests/synthetic.py` (fabrique de poses de test)

**Interfaces:**
- Consumes: `geometry.*`, `Settings`.
- Produces: `detect_hits(kp: np.ndarray, fps: float, settings: Settings) -> list[int]` (images d'impact, croissantes) ; `tests/synthetic.py: make_pose(n_frames, facing="camera"|"away", handedness="right") -> np.ndarray` et `add_swing(kp, frame, side="right"|"left"|"overhead", speed=12.0, two_hands=False)` (vitesse en longueurs de torse/s).

- [ ] **Step 1: tests qui échouent**
  - `test_detects_two_swings` : swings à 100 et 200 (30 i/s) → résultat à ±2 images de `[100, 200]`.
  - `test_ignores_slow_movements` : swing `speed=2.0` (balle qu'on fait rebondir) → `[]`.
  - `test_one_hit_per_swing` : un swing qui accélère sur 6 images → 1 seule frappe (écart min 0,8 s).
  - `test_no_crash_on_missing_player` : images 50-150 NaN + swing à 100 → `[]`.
  - `test_left_handed_uses_left_wrist` : gaucher, swing du poignet gauche à 100 → `[≈100]` ; poignet droit seul → `[]`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** vitesse du poignet dominant (`R_WR` droitier, `L_WR` gaucher) en longueurs de torse/s, lissée sur 3 images, NaN → 0 ; `scipy.signal.find_peaks(height=HIT_MIN_SPEED, distance=round(0.8 * fps))` avec `HIT_MIN_SPEED = 6.0` et le commentaire `# shortcut: valeur de départ, à recalibrer avec les notes du joueur (Task 12)`.
- [ ] **Step 4:** → PASS. **Step 5: Commit** `feat: hit detection from wrist speed`

### Task 4: Type de coup

**Files:** Modify `ace/strokes.py`, `tests/test_strokes.py`

**Interfaces:**
- Produces: `classify_stroke(kp: np.ndarray, frame: int, fps: float, settings: Settings, prev_hit: int | None) -> StrokeKind` ; `detect_strokes(kp: np.ndarray, fps: float, settings: Settings) -> list[Stroke]` (`t = frame / fps`, `metrics`/`defects` vides).

- [ ] **Step 1: tests qui échouent**
  - `test_forehand_facing_camera` / `test_forehand_back_to_camera` : droitier, swing côté droit du corps → `forehand` dans les deux orientations (`facing="camera"` et `"away"`).
  - `test_backhand_right_hander` : swing côté gauche → `backhand`.
  - `test_left_hander_mirrors` : gaucher, swing côté gauche → `forehand`.
  - `test_two_handed_backhand` : `backhand_hands=2`, poignets à < 0,6 torse l'un de l'autre à l'impact → `backhand`.
  - `test_overhead_after_pause_is_serve` : `prev_hit` 5 s avant → `serve` ; `test_overhead_quick_is_other` : 1 s avant → `other` ; `test_first_overhead_is_serve` : `prev_hit=None` → `serve`.
  - `test_missing_keypoints_is_other` : poignet NaN à l'impact → `other`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** règles, dans cet ordre :
  ```
  si poignet dominant ou hanches NaN à l'impact → other
  si poignet dominant au-dessus du nez (y plus petit) → serve si prev_hit is None ou (frame-prev_hit)/fps >= 3.0, sinon other
  si backhand_hands == 2 et distance(poignets) < 0.6 * torse → backhand
  droite_du_corps = signe(x(R_HIP) - x(L_HIP)) moyenné sur les 0,5 s avant l'impact
  s = (x(poignet dominant) - x(milieu hanches)) * droite_du_corps   # > 0 : côté droit du joueur
  droitier : forehand si s > 0 sinon backhand ; gaucher : inversé
  ```
- [ ] **Step 4:** → PASS. **Step 5: Commit** `feat: stroke classification rules`

### Task 5: Mesures techniques et défauts

**Files:** Create `ace/technique.py`, `tests/test_technique.py`

**Interfaces:**
- Produces: `measure(kp: np.ndarray, frame: int, fps: float, ref_shoulder: float) -> dict[str, float]` avec les clés `turn_ratio`, `prep_lead_s`, `knee_angle_min`, `stance_ratio` (NaN si non mesurable) ; `ref_shoulder_width(kp: np.ndarray) -> float` (médiane de la largeur d'épaules apparente) ; `detect_defects(metrics: dict[str, float], kind: StrokeKind) -> list[DefectId]` ; `THRESHOLDS: dict[DefectId, float]`.

Définitions (fenêtre = 1,0 s avant l'impact) :
- `turn_ratio` = min sur la fenêtre de (largeur d'épaules apparente / `ref_shoulder`) — plus c'est petit, plus les épaules ont tourné.
- `prep_lead_s` = (impact − image de ce minimum) / fps.
- `knee_angle_min` = plus petit angle hanche-genou-cheville (deux jambes) sur les 0,5 s avant l'impact, en degrés.
- `stance_ratio` = distance chevilles / largeur de hanches, à l'impact.

`THRESHOLDS = {"late_prep": 0.4, "small_turn": 0.8, "straight_legs": 160.0, "narrow_stance": 1.5}` (commentaire `# shortcut: repères d'entraîneur, recalibrés en Task 12`). Défaut si `prep_lead_s < 0.4`, `turn_ratio > 0.8`, `knee_angle_min > 160`, `stance_ratio < 1.5`. Coups concernés : `forehand`/`backhand` → les 4 ; `serve` → `straight_legs` seul ; `other` → aucun.

- [ ] **Step 1: tests qui échouent**
  - `test_late_preparation` : épaules au plus tourné 0,2 s avant l'impact → `"late_prep" in defects` ; 0,6 s avant → absent.
  - `test_small_turn` : largeur min = 0,9 × réf → `small_turn` ; 0,5 × réf → absent.
  - `test_straight_legs` / `test_narrow_stance` : cas limites 165° vs 140°, ratio 1,2 vs 2,0.
  - `test_nan_metric_never_yields_defect` : chevilles NaN → `stance_ratio` NaN et pas de `narrow_stance` (Review Focus 5).
  - `test_other_has_no_defects`, `test_serve_only_legs`.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat: technique metrics and defects`

### Task 6: Constats et conseils

**Files:** Create `ace/findings.py`, `ace/advice.fr.json`, `tests/test_findings.py`

**Interfaces:**
- Consumes: `Stroke`, `DefectId`.
- Produces: `load_advice() -> dict[DefectId, dict[str, str]]` (clés `title`, `text`, `drill`) ; `build_findings(strokes: list[Stroke], advice: dict) -> list[Finding]`.

`advice.fr.json` : une entrée par défaut, en français, avec `title`, `text`, `drill`. Exemple à suivre pour le ton :
```json
"late_prep": {"title": "Tu prépares trop tard",
  "text": "Tes épaules finissent de tourner juste avant l'impact : tu frappes en retard et la balle part dans le filet ou trop court.",
  "drill": "Au panier : tourne les épaules dès que la balle passe le filet, avant même qu'elle rebondisse. 20 coups droits « épaule d'abord »."}
```

- [ ] **Step 1: tests qui échouent**
  - `test_finding_counts` : 25 coups droits dont 11 `late_prep` → 1 `Finding(kind="forehand", defect="late_prep", count=11, total=25)`, `title` = celui du JSON.
  - `test_needs_five_occurrences` : 4/6 → aucun constat.
  - `test_needs_forty_percent` : 9/30 → aucun constat.
  - `test_max_three_sorted` : 5 défauts éligibles → 3, triés par `count` décroissant.
  - `test_clip_times` : `clip_times` = les 5 premiers `t` des coups concernés, croissants.
  - `test_advice_file_complete` : chaque `DefectId` a `title`, `text`, `drill` non vides.
- [ ] **Step 2:** → FAIL. **Step 3:** grouper par `(kind, defect)`, filtrer `count >= 5 and count / total >= 0.4`, trier, garder 3. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat: findings and French advice library`

### Task 7: Stockage des matchs et réglages

**Files:** Create `ace/store.py`, `tests/test_store.py`

**Interfaces:**
- Produces: `DATA_DIR: Path` (défaut `Path("data")`, surchargeable par la variable d'env `ACE_DATA_DIR` — utilisée par les tests) ; `match_dir(id) -> Path` ; `create_match(src: BinaryIO, filename: str, view: View, title: str) -> Match` (copie par morceaux via `shutil.copyfileobj`, `probe`, id = `"<AAAA-MM-JJ>-<slug du nom>"` avec la date de `info.created` sinon aujourd'hui ; si l'id existe déjà, la vidéo est remplacée et l'analyse remise à `pending`) ; `save(m: Match) -> None` (écriture atomique : fichier temporaire puis `os.replace`) ; `load(id: str) -> Match` ; `list_matches() -> list[Match]` (plus récents d'abord) ; `load_settings() -> Settings` / `save_settings(s: Settings)` (`data/settings.json`, défauts si absent) ; `pose_path(id) -> Path` (`pose.npz`).

- [ ] **Step 1: tests qui échouent** (tous avec `ACE_DATA_DIR=tmp_path`, `probe` monkeypatché)
  - `test_create_and_load_match` : `create_match(io.BytesIO(b"x"*10), "IMG_2665.mov", "net", "vs Karim")` → `load(m.id).title == "vs Karim"`, la vidéo copiée existe.
  - `test_same_video_reuses_id_and_resets` : 2e import du même nom → même id, `status == "pending"`, `strokes == []`.
  - `test_list_sorted_recent_first`.
  - `test_settings_default_and_roundtrip`.
  - `test_large_upload_streamed` : un `src` dont `read()` sans argument lève une erreur → l'import passe quand même (copie par morceaux, Review Focus 3).
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS. **Step 5: Commit** `feat: match storage and settings`

### Task 8: Pipeline et exécution des analyses

**Files:** Create `ace/pipeline.py`, `ace/jobs.py`, `tests/test_pipeline.py`

**Interfaces:**
- Consumes: Tasks 1-7.
- Produces:
  - `analyse(match_id: str) -> None` : `status="running"` → probe → `extract_pose` (progression 0 → 0,9, enregistrée dans `match.json` au plus toutes les 2 s) → `np.savez_compressed(pose_path)` → `detect_strokes` → pour chaque coup `measure` + `detect_defects` → `build_findings` → `rallies=None` en vue `net` → `status="done"`, `progress=1.0`. Toute exception → `status="failed"`, `error` = message français court (« L'analyse a échoué : <raison> »).
  - `JobRunner` : `start(match_id: str) -> bool` (False si une analyse tourne déjà), `running_id: str | None` ; un seul `threading.Thread` à la fois.
  - `recover_interrupted() -> None` : tout match `running` au démarrage → `failed`, `error="Analyse interrompue (l'app a été fermée)."`

- [ ] **Step 1: tests qui échouent** (`extract_pose` monkeypatché → `make_pose` + 6 swings)
  - `test_analyse_net_view_done` : statut `done`, 6 coups, `rallies is None`, `pose.npz` existe.
  - `test_analyse_failure_marks_failed` : `extract_pose` lève → `failed`, `error` commence par « L'analyse a échoué ».
  - `test_runner_one_at_a_time` : 2e `start` pendant la 1re → `False`.
  - `test_recover_interrupted`.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS.
- [ ] **Step 5:** `@slow test_analyse_real_video` : `IMG_2665.mov` → `done` avec ≥ 1 coup. **Commit** `feat: analysis pipeline and single job runner`

### Task 9: Appli web — import, progression, historique, réglages

**Files:** Create `ace/web/app.py`, `ace/web/templates/{base,history,add,match_running,match_failed,settings}.html`, `ace/web/static/app.js`, `ace/__main__.py`, `tests/test_web.py`

**Interfaces:**
- Consumes: `store.*`, `JobRunner`, `recover_interrupted`.
- Produces: `app: FastAPI` ; `main()` dans `__main__.py` (`recover_interrupted()`, Uvicorn sur `127.0.0.1:8765`). Routes :
  - `GET /` historique : date, durée, vue, titre, statut, et pour `done` : nb de coups + nb de constats.
  - `GET /ajouter` formulaire : fichier, vue (radio « Vue filet » / « Vue arrière »), titre facultatif.
  - `POST /matchs` → `create_match` puis `runner.start` ; si une analyse tourne déjà : la vidéo est enregistrée et la page dit « Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer. » ; redirection 303 vers `/matchs/{id}`.
  - `GET /matchs/{id}` → selon le statut : progression (`running` → `match_running`), échec ou pas encore lancé + bouton « Relancer » (`failed`/`pending` → `match_failed`, avec le message d'erreur s'il y en a un), bilan (`done`, Task 10).
  - `GET /matchs/{id}/statut` → JSON `{"status", "progress", "error"}` (sondé toutes les 2 s par `app.js`, recharge la page à la fin).
  - `POST /matchs/{id}/relancer` → `runner.start`, 303.
  - `GET /matchs/{id}/video` → la vidéo avec **gestion des requêtes `Range` (réponse 206)**, indispensable à Safari ; vérifier si `FileResponse` de la version installée de Starlette les gère, sinon implémenter la réponse 206.
  - `GET /reglages`, `POST /reglages` (droitier/gaucher, revers 1/2 mains).

- [ ] **Step 1: tests qui échouent** (`TestClient`, `ACE_DATA_DIR=tmp_path`, `probe` et `runner.start` monkeypatchés)
  - `test_upload_creates_match_and_redirects` : POST multipart → 303 vers `/matchs/<id>`, `match.json` existe, `runner.start` appelé.
  - `test_history_lists_title` : GET `/` contient « vs Karim » et « Vue filet ».
  - `test_status_json`.
  - `test_failed_page_has_relaunch_button` : contient « Relancer ».
  - `test_settings_roundtrip` : POST gaucher → `load_settings().handedness == "left"`.
  - `test_video_range_request` : header `Range: bytes=0-99` → 206, 100 octets.
  - `test_server_binds_localhost` : `main` utilise l'hôte `127.0.0.1`.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter (HTML sobre ; tous les textes en français). **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat: local web app with upload, progress, history, settings`

### Task 10: Le bilan (version « B »)

**Files:** Create `ace/web/templates/match_report.html` ; Modify `ace/web/app.py`, `ace/web/static/app.js` ; Test `tests/test_report.py`

**Interfaces:**
- Consumes: `Match` terminé.
- Produces: rendu HTML de `GET /matchs/{id}` quand `status == "done"`.

Contenu, de haut en bas :
1. **Vue d'ensemble** : nombre de coups par type (coup droit, revers, service, autre) ; si `rallies` est présent : nombre d'échanges, longueur moyenne (échanges ≥ 2 frappes seulement) et max, % de fautes par type, % de 1res balles et doubles fautes (Task 18).
2. **Où ça casse** : en vue filet ou si `rallies is None`, bloc remplacé par « Disponible en vue arrière : filme depuis derrière toi, en paysage et en 60 i/s, pour voir où finissent tes balles. »
3. **Conseils** : chaque `Finding` → titre, « 11 coups droits sur 25 », texte, exercice, et un bouton par `clip_time` qui place le lecteur vidéo à `t − 1,5 s`, lance la lecture et la met en pause à `t + 1,0 s`. Sans constat : « Aucun défaut ne revient assez souvent sur ce match pour en tirer un conseil. »
4. Lecteur `<video>` sur `/matchs/{id}/video` ; liste complète des coups (temps, type, défauts) repliée sous « Tous mes coups ».

- [ ] **Step 1: tests qui échouent**
  - `test_report_net_view` : contient « Vue d'ensemble », le `title` du constat, « 11 coups droits sur 25 », la phrase « Disponible en vue arrière ».
  - `test_report_no_findings_message`.
  - `test_report_clip_buttons` : un `data-t="12.3"` par `clip_time`.
  - `test_report_rear_view_shows_breakdown` : match `rear` avec `rallies` → contient « Où ça casse » sans la phrase « Disponible en vue arrière ».
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS.
- [ ] **Step 5:** vérification manuelle dans Safari sur le match `IMG_2665` (vidéo lisible, boutons d'extraits). **Commit** `feat: match report (layout B)`

### Task 11: « Noter mes coups » et score de fiabilité

**Files:** Create `ace/notes.py`, `ace/web/templates/notes.html`, `tests/test_notes.py` ; Modify `ace/domain.py` (typer `Match.score`), `ace/web/app.py`, `ace/web/static/app.js`, `match_report.html`

**Interfaces:**
- Produces: `Note(t: float, kind: StrokeKind)` ; `Score(n_notes: int, n_detected: int, found_rate: float, class_rate: float, false_hits: int)` ; `score_detection(strokes: list[Stroke], notes: list[Note], tol_s: float = 0.3) -> Score` ; routes `GET /matchs/{id}/noter`, `POST /matchs/{id}/notes` (JSON `[{"t":..,"kind":..}]` → `notes.json`, calcule et enregistre `match.score`).
- Page de notation : vidéo + touches **D** (coup droit), **R** (revers), **S** (service), **A** (autre), **Retour arrière** (annule la dernière note), **Espace** (pause), bouton « Enregistrer ». Le bilan affiche « Fiabilité : X % de tes coups trouvés, Y % bien classés » si un score existe.

- [ ] **Step 1: tests qui échouent**
  - `test_perfect_match` : mêmes temps et types → `found_rate == 1.0`, `class_rate == 1.0`, `false_hits == 0`.
  - `test_tolerance` : écart 0,25 s → trouvé ; 0,5 s → pas trouvé.
  - `test_misclassified` : 10 notes, 10 trouvés dont 8 bons types → `class_rate == 0.8`.
  - `test_false_hits` : 2 coups détectés sans note → `false_hits == 2`.
  - `test_each_note_matched_once` : 2 détections proches d'une seule note → 1 seule appariée.
  - `test_notes_endpoint_saves_score`.
- [ ] **Step 2:** → FAIL.
- [ ] **Step 3:** appariement glouton : paires (note, coup) triées par écart croissant, on garde une paire si les deux sont libres et l'écart ≤ `tol_s`. `found_rate` = notes appariées / notes ; `class_rate` = paires de même type / paires.
- [ ] **Step 4:** → PASS. **Step 5: Commit** `feat: stroke notes and detection score`

### Task 12: Lanceur et calibration avec le joueur

**Files:** Create `ACE Vision.command`, `README.md` ; Modify `ace/strokes.py`, `ace/technique.py` (valeurs de seuils uniquement)

- [ ] **Step 1:** `ACE Vision.command` (`chmod +x`) : `cd` dans son dossier ; si `http://127.0.0.1:8765` répond, juste `open -a Safari http://127.0.0.1:8765` ; sinon lancer `uv run python -m ace` en arrière-plan, attendre que le port réponde (10 s max), puis ouvrir Safari. `README.md` : installation (`brew install uv`, `uv sync`), glisser l'icône dans le Dock, coller plusieurs vidéos d'un match avec `ffmpeg -f concat -safe 0 -i liste.txt -c copy match.mov`.
- [ ] **Step 2: vérification manuelle** : double-clic → Safari s'ouvre sur l'historique ; ajouter `IMG_2665.mov` en vue filet → progression → bilan.
- [ ] **Step 3 (avec le joueur) :** il note ses coups sur `IMG_2665.mov` via « Noter mes coups ». Lire le score.
- [ ] **Step 4 :** ajuster `HIT_MIN_SPEED` (trop de `false_hits` → monter ; `found_rate` trop bas → descendre) et les règles de Task 4, relancer, jusqu'à **≥ 90 % trouvés et ≥ 85 % bien classés** ; puis confirmer sur un vrai match noté. Le joueur revoit les extraits de chaque constat et dit si le défaut est réel ; ajuster `THRESHOLDS` en conséquence. Consigner les valeurs finales et les scores dans le README.
- [ ] **Step 5: Commit** `feat: launcher and calibrated thresholds`

---

# Partie 2 — Vue arrière sur données publiques

### Task 13: Données et modèles pré-entraînés (licences)

**Files:** Create `docs/adr/0003-donnees-et-modeles-publics.md` ; Modify `README.md`

- [ ] **Step 1:** Récupérer le jeu de données tennis de TrackNet (images télé annotées balle par balle) et des poids TrackNet tennis pré-entraînés ; récupérer un détecteur de lignes de court pré-entraîné (ex. projet open source « TennisCourtDetector », 14 points du court). Ranger sous `data/public/` et `models/` (hors git).
- [ ] **Step 2:** Lire la licence de chacun. Écrire l'ADR 0003 : ce qui est pris, d'où, sous quelle licence, et pourquoi c'est compatible avec un usage personnel. Si une licence l'interdit, chercher une alternative avant de continuer.
- [ ] **Step 3:** Noter dans l'ADR le format exact des annotations (colonnes, visibilité, statut frappe/rebond s'il existe) : les tests des Tasks 14 et 16 s'appuient dessus.
- [ ] **Step 4: Commit** `docs: public datasets and pretrained models`

### Task 14: Suivi de balle TrackNet

**Files:** Create `ace/tracknet_model.py` (réseau repris du projet source, en-tête d'attribution et licence), `ace/ball.py`, `tests/test_ball.py`

**Interfaces:**
- Produces: `track_ball(path: Path, info: VideoInfo, on_progress: Callable[[float], None], weights: Path | None = None) -> np.ndarray` — `(n_frames, 2)` en pixels de l'image redressée, NaN sans balle ; utilise `models/tracknet_user.pt` s'il existe, sinon les poids publics ; `interpolate_gaps(track: np.ndarray, max_gap: int = 5) -> np.ndarray`.

- [ ] **Step 1: tests qui échouent**
  - `test_interpolate_short_gap` : trou de 3 images entre deux positions → interpolation linéaire ; `test_keep_long_gap` : trou de 8 → reste NaN.
  - `@slow test_tracknet_public_clip` : sur un clip annoté du jeu de données, précision ≥ 0,90 et rappel ≥ 0,75 à 5 px près (en 1280×720).
- [ ] **Step 2:** → FAIL. **Step 3:** entrée = 3 images consécutives redimensionnées en 640×360 ; position = maximum de la carte de chaleur si ≥ seuil, ramenée à la taille d'origine ; `device="mps"`. **Step 4:** → PASS.
- [ ] **Step 5: Commit** `feat: TrackNet ball tracking`

### Task 15: Détection du court et repère en mètres

**Files:** Create `ace/court.py`, `tests/test_court.py`

**Interfaces:**
- Produces: `COURT_POINTS_M: np.ndarray` (14 points de référence du court en mètres, dans le repère défini plus haut) ; `detect_court(frame: np.ndarray) -> np.ndarray` (homographie 3×3 image → court, via les 14 points détectés + `cv2.findHomography(..., cv2.RANSAC)`) ; `to_court(H: np.ndarray, pts: np.ndarray) -> np.ndarray` (N×2 → N×2 mètres).
- La caméra étant fixe, `detect_court` est appelée sur quelques images (ex. 10 réparties) et on garde l'homographie médiane.

- [ ] **Step 1: tests qui échouent**
  - `test_to_court_identity_like` : homographie construite à partir de 4 coins connus → les coins retombent à 1 cm près.
  - `test_far_baseline_y` : un point sur le fond de court adverse → `y ≈ +11.885`.
  - `@slow test_detect_court_public_frame` : sur une image du jeu public, les 4 coins du simple retombent à ≤ 0,5 m.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS. **Step 5: Commit** `feat: court detection and metric projection`

### Task 16: Rebonds, frappes adverses et échanges

**Files:** Create `ace/rallies.py`, `tests/test_rallies.py`

**Interfaces:**
- Consumes: track balle (Task 14), `H` (Task 15), frappes du joueur (`detect_hits`, Task 3).
- Produces: `detect_bounces(ball: np.ndarray, fps: float) -> list[int]` ; `detect_opponent_hits(ball: np.ndarray, H: np.ndarray, fps: float) -> list[int]` ; `segment_rallies(user_hits: list[int], opp_hits: list[int], ball: np.ndarray, fps: float) -> list[tuple[int, int, list[tuple[int, str]]]]` (début, fin, frappes `(image, "user"|"opp")`).

Règles :
- **Rebond** : la vitesse verticale de la balle dans l'image passe de « descend » à « monte » sans frappe du joueur à ± 0,2 s.
- **Frappe adverse** : la balle, du côté adverse (`y > 0` projeté), change de sens (s'éloignait → revient) sans rebond à cet instant.
- **Nouvel échange** : plus de **2,5 s** sans balle détectée ni frappe ; un échange commence par une frappe.

- [ ] **Step 1: tests qui échouent** (trajectoires synthétiques paraboliques)
  - `test_single_bounce_detected` ; `test_hit_is_not_bounce`.
  - `test_opponent_hit_far_side`.
  - `test_rallies_split_on_pause` : deux séries de frappes séparées de 4 s → 2 échanges ; frappes alternées dans chacun.
  - `@slow test_events_public_clip` : si le jeu public annote frappes/rebonds (voir ADR 0003), F1 ≥ 0,8 à ± 2 images ; sinon test sauté avec la raison.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS. **Step 5: Commit** `feat: bounces, opponent hits and rally segmentation`

### Task 17: Issue des échanges et statistiques de service

**Files:** Create `ace/outcome.py`, `tests/test_outcome.py`

**Interfaces:**
- Produces: `rally_end(hits: list[tuple[int, str]], bounces_m: list[tuple[int, np.ndarray]], ball_m: np.ndarray) -> tuple[RallyEnd, Outcome]` (issue de l'échange, et résultat de la dernière frappe du joueur) ; `serve_stats(rallies: list[Rally]) -> dict[str, float]` (`first_serve_in_pct`, `double_faults`).

Règles (après la dernière frappe) :
- pas de rebond côté adverse et la balle ne franchit pas `y = 0` → `net` ;
- 1er rebond avec |x| > 4,115 → `wide` ; avec y > 11,885 → `long` ;
- 1er rebond dans le court adverse et pas de frappe adverse ensuite → `not_returned` ;
- sinon `unknown`.
- Service : 1er rebond dans un des deux carrés de service adverses (|x| ≤ 4,115, 0 < y ≤ 6,40) → bon ; un échange de 1 frappe dont le service est faute → `is_serve_fault=True` ; deux échanges consécutifs `is_serve_fault` → 1 double faute.
- Les échanges dont la dernière frappe est adverse sont traités de façon symétrique (`y < 0`) pour savoir si le joueur a gagné le point.

- [ ] **Step 1: tests qui échouent** : un cas par règle (`test_net`, `test_wide`, `test_long`, `test_not_returned`, `test_unknown_when_no_bounce_data`), `test_first_serve_pct`, `test_double_fault_counted_once`.
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS. **Step 5: Commit** `feat: rally outcomes and serve stats`

### Task 18: Vue arrière dans le pipeline et le bilan complet

**Files:** Modify `ace/pipeline.py`, `ace/findings.py`, `ace/web/templates/match_report.html` ; Tests `tests/test_pipeline.py`, `tests/test_report.py`, `tests/test_findings.py`

**Interfaces:**
- `analyse` en vue `rear` : pose (0 → 0,6), balle (0,6 → 0,9), court, échanges, issues → `rallies` rempli, `Stroke.outcome` rempli pour la dernière frappe du joueur de chaque échange.
- `build_findings` : quand des coups ont une issue connue, le constat ajoute le lien avec les fautes : `fault_count`/`fault_total` (nouveaux champs de `Finding`, `None` par défaut), affiché « dont 11 de tes 14 coups droits fautifs ».
- Bilan bloc 2 « Où ça casse » : carte du court en SVG (points rouges = 1er rebond des fautes du joueur ; fautes au filet listées à part) ; fautes par longueur d'échange (1-3, 4-6, 7+ frappes) ; coup qui termine les points perdus.

- [ ] **Step 1: tests qui échouent**
  - `test_analyse_rear_view` (balle, court et pose monkeypatchés) : `rallies` non vide, statut `done`.
  - `test_finding_links_faults` : 14 coups droits fautifs dont 11 `late_prep` → `fault_count=11, fault_total=14`.
  - `test_report_rear_court_map` : un `<circle>` par faute avec rebond connu ; les buckets 1-3/4-6/7+.
  - `test_mean_rally_length_ignores_single_hit` (Q2 du cadrage).
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS.
- [ ] **Step 5:** `@slow` : un clip public complet de bout en bout → bilan cohérent (vérification visuelle). **Commit** `feat: rear view analysis and full report`

---

# Partie 3 — La première vidéo arrière du joueur

### Task 19: Annotation de balle et réentraînement de TrackNet

**Files:** Create `ace/web/templates/ball_labels.html`, `scripts/finetune_tracknet.py` ; Modify `ace/web/app.py`, `ace/web/static/app.js` ; Test `tests/test_ball_labels.py`

**Interfaces:**
- Routes `GET /matchs/{id}/balle` et `POST /matchs/{id}/balle` : affiche une image sur 10 ; le joueur clique sur la balle ou appuie sur **N** (« pas visible ») ; enregistre `ball_labels.csv` au format du jeu public (ADR 0003).
- `scripts/finetune_tracknet.py --labels <csv>... --out models/tracknet_user.pt` : part des poids publics, 80 % entraînement / 20 % validation, sur MPS ; affiche précision et rappel de validation.

- [ ] **Step 1: test qui échoue** `test_ball_labels_saved_in_dataset_format` (clic → ligne avec visibilité, x, y à l'échelle de l'image d'origine ; « N » → visibilité 0).
- [ ] **Step 2:** → FAIL. **Step 3:** implémenter. **Step 4:** → PASS. **Commit** `feat: ball labeling page and TrackNet fine-tuning script`
- [ ] **Step 5 (avec le joueur) :** il filme un match **de derrière lui, en paysage, en 60 i/s, en hauteur**, l'importe en vue arrière, annote ~500 images, puis on lance le réentraînement. Critère : sur les 20 % de validation, **précision ≥ 0,90 et rappel ≥ 0,75**. Sinon, annoter 500 images de plus et recommencer.

### Task 20: Validation de bout en bout sur la vidéo du joueur

**Files:** Modify seuils si besoin ; `README.md`

- [ ] **Step 1:** Relancer l'analyse du match arrière avec `models/tracknet_user.pt`.
- [ ] **Step 2:** Le joueur note ses coups (« Noter mes coups ») → **≥ 90 % trouvés, ≥ 85 % bien classés** ; sinon recalibrer comme en Task 12 (pour la vue arrière, les orientations du corps sont inversées : les tests de Task 4 `facing="away"` le couvrent déjà).
- [ ] **Step 3:** Le joueur relit le bilan complet : la carte des fautes correspond-elle à ce qu'il voit dans les extraits ? Chaque constat est-il réel ? Corriger les règles fautives (Task 17) ou les seuils (Task 5).
- [ ] **Step 4:** Consigner les scores finaux dans le README. **Commit** `chore: validate rear view on user's footage`
