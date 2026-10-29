import numpy as np
import pytest

from ace.geometry import L_ANK, L_SH, R_ANK
from ace.technique import THRESHOLDS, detect_defects, measure, ref_shoulder_width
from tests.synthetic import FPS, bend_knees, make_pose, set_shoulder_width, set_stance

IMPACT = 100


def pose():
    return make_pose(150)  # shoulder width 80 px, hip width 60 px, ankle gap 60 px


def metrics(kp):
    return measure(kp, IMPACT, FPS, ref_shoulder_width(kp))


def test_late_preparation():
    late, early = pose(), pose()
    set_shoulder_width(late, IMPACT - 6, 40)  # 0.2 s before impact
    set_shoulder_width(early, IMPACT - 18, 40)  # 0.6 s before impact
    assert metrics(late)["prep_lead_s"] == pytest.approx(0.2) and "late_prep" in detect_defects(metrics(late), "forehand")
    assert "late_prep" not in detect_defects(metrics(early), "forehand")


def test_no_turn_gives_no_prep_time():
    kp = pose()
    set_shoulder_width(kp, IMPACT - 2, 76)  # 0.95 x ref: noise, not a turn
    m = metrics(kp)
    assert np.isnan(m["prep_lead_s"]) and "late_prep" not in detect_defects(m, "forehand")


def test_held_turn_counts_from_its_start():
    kp = pose()
    for f in range(IMPACT - 18, IMPACT):  # turned 0.6 s before impact and held
        set_shoulder_width(kp, f, 40)
    set_shoulder_width(kp, IMPACT - 2, 39)  # tiny dip just before impact
    m = metrics(kp)
    assert m["prep_lead_s"] == pytest.approx(0.6) and "late_prep" not in detect_defects(m, "forehand")


def test_small_turn():
    small, big = pose(), pose()
    set_shoulder_width(small, IMPACT - 15, 72)  # 0.9 x ref
    set_shoulder_width(big, IMPACT - 15, 40)  # 0.5 x ref
    assert "small_turn" in detect_defects(metrics(small), "backhand")
    assert "small_turn" not in detect_defects(metrics(big), "backhand")


def test_straight_legs():
    straight, bent = pose(), pose()
    bend_knees(straight, slice(80, 101), 165)
    bend_knees(bent, slice(80, 101), 140)
    assert "straight_legs" in detect_defects(metrics(straight), "serve")
    assert "straight_legs" not in detect_defects(metrics(bent), "serve")


def test_narrow_stance():
    narrow, wide = pose(), pose()
    set_stance(narrow, IMPACT, 72)  # 1.2 x hip width
    set_stance(wide, IMPACT, 120)  # 2.0 x
    assert metrics(narrow)["stance_ratio"] == pytest.approx(1.2)
    assert "narrow_stance" in detect_defects(metrics(narrow), "forehand")
    assert "narrow_stance" not in detect_defects(metrics(wide), "forehand")


def test_nan_metric_never_yields_defect():
    kp = pose()
    kp[:, L_ANK] = np.nan
    m = metrics(kp)
    assert np.isnan(m["stance_ratio"])
    assert "narrow_stance" not in detect_defects(m, "forehand")
    kp[:, :, :] = np.nan
    assert all(np.isnan(v) for v in metrics(kp).values())


def test_other_has_no_defects():
    assert detect_defects({"prep_lead_s": 0.0, "turn_ratio": 1.0, "knee_angle_min": 180.0, "stance_ratio": 0.5}, "other") == []


def test_serve_only_legs():
    m = {"prep_lead_s": 0.0, "turn_ratio": 1.0, "knee_angle_min": 180.0, "stance_ratio": 0.5}
    assert detect_defects(m, "serve") == ["straight_legs"]
    assert set(detect_defects(m, "forehand")) == set(THRESHOLDS)


def test_sparse_window_gives_nan_not_defect():
    kp = pose()
    kp[IMPACT - 30:IMPACT, L_SH] = np.nan  # shoulders valid only at impact frame
    kp[IMPACT - 30:IMPACT, L_ANK] = np.nan  # legs valid only at impact frame
    kp[IMPACT - 30:IMPACT, R_ANK] = np.nan
    m = metrics(kp)
    assert np.isnan(m["turn_ratio"]) and np.isnan(m["prep_lead_s"]) and np.isnan(m["knee_angle_min"])
    assert not {"late_prep", "small_turn", "straight_legs"} & set(detect_defects(m, "forehand"))
