"""Compare stroke detection with the player's notes on one match (no YOLO: reuses pose.npz).

Usage: uv run python scripts/calibrate.py <match_id>
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run as a plain script from anywhere

from ace import store
from ace.notes import NOTE_MERGE_S, match_notes, merge_notes, score_detection
from ace.strokes import detect_strokes


def main(match_id: str) -> None:
    m = store.load(match_id)
    kp = np.load(store.pose_path(match_id))["kp"]
    settings = store.load_settings()
    raw = store.load_notes(match_id) or []
    notes = merge_notes(raw)
    strokes = detect_strokes(kp, m.info.fps, settings)
    print(f"match {match_id} — {settings.handedness}, revers à {settings.backhand_hands} main(s), {m.info.fps:g} i/s")
    if len(notes) < len(raw):
        print(f"{len(raw) - len(notes)} note(s) fusionnée(s) (moins de {NOTE_MERGE_S} s d'écart) : {len(raw)} -> {len(notes)}")
    match = match_notes(strokes, notes)
    used = set(match.values())
    print(f"{'note t':>7} {'note':<9} {'détect t':>8} {'détecté':<9} {'écart':>6}  résultat")
    for i, n in enumerate(notes):
        if i not in match:
            print(f"{n.t:7.2f} {n.kind:<9} {'':>8} {'':<9} {'':>6}  manqué")
            continue
        s = strokes[match[i]]
        res = "ok" if s.kind == n.kind else "mal classé"
        print(f"{n.t:7.2f} {n.kind:<9} {s.t:8.2f} {s.kind:<9} {s.t - n.t:+6.2f}  {res}")
    for j, s in enumerate(strokes):
        if j not in used:
            print(f"{'':>7} {'':<9} {s.t:8.2f} {s.kind:<9} {'':>6}  fausse frappe")
    sc = score_detection(strokes, raw)
    print(f"Score : trouvés {sc.n_detected}/{sc.n_notes} ({sc.found_rate:.0%}), bien classés {sc.class_rate:.0%}, "
          f"fausses frappes {sc.false_hits}")


if __name__ == "__main__":
    main(sys.argv[1])
