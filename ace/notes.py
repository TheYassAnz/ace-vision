from pydantic import BaseModel, Field

from ace.domain import Score, Stroke, StrokeKind


class Note(BaseModel):
    t: float = Field(ge=0, allow_inf_nan=False)
    kind: StrokeKind


def score_detection(strokes: list[Stroke], notes: list[Note], tol_s: float = 0.3) -> Score:
    """Greedy matching of the player's notes to detected strokes, closest pairs first."""
    pairs = sorted(p for i, n in enumerate(notes) for j, s in enumerate(strokes)
                   if (p := (abs(n.t - s.t), i, j))[0] <= tol_s)
    used_n, used_s, good = set(), set(), 0
    for gap, i, j in pairs:
        if i not in used_n and j not in used_s:
            used_n.add(i)
            used_s.add(j)
            good += notes[i].kind == strokes[j].kind
    matched = len(used_n)
    return Score(n_notes=len(notes), n_detected=matched, found_rate=matched / len(notes) if notes else 0.0,
                 class_rate=good / matched if matched else 0.0, false_hits=len(strokes) - matched)
