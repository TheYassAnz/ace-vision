from pydantic import BaseModel, Field

from ace.domain import Score, Stroke, StrokeKind

MATCH_TOL_S = 0.3  # a note matches a detected stroke this close
NOTE_MERGE_S = 0.3  # two notes closer than this are one stroke whose key was pressed twice


class Note(BaseModel):
    t: float = Field(ge=0, allow_inf_nan=False)
    kind: StrokeKind


def merge_notes(notes: list[Note]) -> list[Note]:
    out: list[Note] = []
    for n in sorted(notes, key=lambda n: n.t):
        if not out or n.t - out[-1].t >= NOTE_MERGE_S:
            out.append(n)
    return out


def match_notes(strokes: list[Stroke], notes: list[Note], tol_s: float = MATCH_TOL_S) -> dict[int, int]:
    """Greedy matching of note index -> stroke index, closest pairs first."""
    pairs = sorted(p for i, n in enumerate(notes) for j, s in enumerate(strokes)
                   if (p := (abs(n.t - s.t), i, j))[0] <= tol_s)
    match: dict[int, int] = {}
    for _, i, j in pairs:
        if i not in match and j not in match.values():
            match[i] = j
    return match


def score_detection(strokes: list[Stroke], notes: list[Note], tol_s: float = MATCH_TOL_S) -> Score:
    """Score of the detection against the player's notes (double key presses merged first)."""
    notes = merge_notes(notes)
    match = match_notes(strokes, notes, tol_s)
    good = sum(notes[i].kind == strokes[j].kind for i, j in match.items())
    matched = len(match)
    return Score(n_notes=len(notes), n_detected=matched, found_rate=matched / len(notes) if notes else 0.0,
                 class_rate=good / matched if matched else 0.0, false_hits=len(strokes) - matched)
