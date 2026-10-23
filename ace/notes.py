from pydantic import BaseModel

from ace.domain import Score, Stroke, StrokeKind


class Note(BaseModel):
    t: float
    kind: StrokeKind


def score_detection(strokes: list[Stroke], notes: list[Note], tol_s: float = 0.3) -> Score:
    """Greedy matching of the player's notes to detected strokes, closest pairs first."""
    pairs = sorted((abs(n.t - s.t), i, j) for i, n in enumerate(notes) for j, s in enumerate(strokes))
    used_n, used_s, good = set(), set(), 0
    for gap, i, j in pairs:
        if gap <= tol_s and i not in used_n and j not in used_s:
            used_n.add(i)
            used_s.add(j)
            good += notes[i].kind == strokes[j].kind
    matched = len(used_n)
    return Score(n_notes=len(notes), n_detected=matched, found_rate=matched / len(notes) if notes else 0.0,
                 class_rate=good / matched if matched else 0.0, false_hits=len(strokes) - matched)
