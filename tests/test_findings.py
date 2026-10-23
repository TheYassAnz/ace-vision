from ace.domain import Finding, Stroke
from ace.findings import build_findings, load_advice

ADVICE = {d: {"title": f"T-{d}", "text": "x", "drill": "y"} for d in ("late_prep", "small_turn", "straight_legs", "narrow_stance")}


def strokes(kind, total, n_defect, defects=("late_prep",), t0=0.0):
    return [Stroke(t=t0 + i, frame=i, kind=kind, defects=list(defects) if i < n_defect else []) for i in range(total)]


def test_finding_counts():
    f = build_findings(strokes("forehand", 25, 11), ADVICE)
    assert f == [Finding(kind="forehand", defect="late_prep", count=11, total=25, title="T-late_prep",
                         text="x", drill="y", clip_times=[0.0, 1.0, 2.0, 3.0, 4.0])]


def test_needs_five_occurrences():
    assert build_findings(strokes("forehand", 6, 4), ADVICE) == []


def test_needs_forty_percent():
    assert build_findings(strokes("forehand", 30, 9), ADVICE) == []


def test_max_three_sorted():
    ss = (strokes("forehand", 10, 6, ("late_prep", "small_turn", "straight_legs", "narrow_stance"))
          + strokes("backhand", 10, 9, ("late_prep",)) )
    # forehand: 4 defects x 6 ; backhand late_prep x 9 -> 5 eligible, keep 3
    ss[0].defects = ["late_prep", "small_turn", "straight_legs", "narrow_stance"]
    out = build_findings(ss, ADVICE)
    assert len(out) == 3 and [f.count for f in out] == [9, 6, 6]


def test_clip_times():
    ss = strokes("forehand", 10, 10)
    ss.reverse()
    assert build_findings(ss, ADVICE)[0].clip_times == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_advice_file_complete():
    advice = load_advice()
    assert set(advice) == set(ADVICE)
    assert all(advice[d][k].strip() for d in advice for k in ("title", "text", "drill"))
