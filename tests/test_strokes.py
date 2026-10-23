import numpy as np
import pytest

from ace.domain import Settings
from ace.strokes import detect_hits
from ace.geometry import R_WR
from tests.synthetic import add_swing, make_pose

FPS = 30.0
RIGHT = Settings(handedness="right", backhand_hands=2)
LEFT = Settings(handedness="left", backhand_hands=2)


def test_detects_two_swings():
    kp = make_pose(300)
    add_swing(kp, 100, "right")
    add_swing(kp, 200, "right")
    hits = detect_hits(kp, FPS, RIGHT)
    assert len(hits) == 2
    assert abs(hits[0] - 100) <= 2 and abs(hits[1] - 200) <= 2


def test_ignores_slow_movements():
    kp = make_pose(200)
    add_swing(kp, 100, "right", speed=2.0)
    assert detect_hits(kp, FPS, RIGHT) == []


def test_one_hit_per_swing():
    kp = make_pose(200)
    add_swing(kp, 100, "right")
    assert len(detect_hits(kp, FPS, RIGHT)) == 1


def test_no_crash_on_missing_player():
    kp = make_pose(300)
    add_swing(kp, 100, "right")
    kp[50:150] = np.nan
    assert detect_hits(kp, FPS, RIGHT) == []


def test_all_nan_returns_empty():
    assert detect_hits(np.full((100, 17, 3), np.nan), FPS, RIGHT) == []


def test_left_handed_uses_left_wrist():
    kp = make_pose(200)
    add_swing(kp, 100, "left", handed="left")
    hits = detect_hits(kp, FPS, LEFT)
    assert len(hits) == 1 and abs(hits[0] - 100) <= 2
    kp = make_pose(200)
    add_swing(kp, 100, "right", handed="right")
    assert detect_hits(kp, FPS, LEFT) == []


from ace.strokes import classify_stroke, detect_strokes  # noqa: E402


def _swing(facing, side, handed="right", two_hands=False):
    kp = make_pose(200, facing=facing)
    add_swing(kp, 100, side, handed=handed, two_hands=two_hands)
    return kp


@pytest.mark.parametrize("facing", ["camera", "away"])
def test_forehand_facing_camera_and_back(facing):
    assert classify_stroke(_swing(facing, "right"), 100, FPS, RIGHT, None) == "forehand"


@pytest.mark.parametrize("facing", ["camera", "away"])
def test_backhand_right_hander(facing):
    assert classify_stroke(_swing(facing, "left"), 100, FPS, Settings(backhand_hands=1), None) == "backhand"


def test_left_hander_mirrors():
    kp = _swing("camera", "left", handed="left")
    assert classify_stroke(kp, 100, FPS, LEFT, None) == "forehand"


def test_two_handed_backhand():
    kp = _swing("away", "left", two_hands=True)
    assert classify_stroke(kp, 100, FPS, RIGHT, None) == "backhand"


def test_overhead_after_pause_is_serve():
    assert classify_stroke(_swing("camera", "overhead"), 100, FPS, RIGHT, 100 - 150) == "serve"


def test_overhead_quick_is_other():
    assert classify_stroke(_swing("camera", "overhead"), 100, FPS, RIGHT, 100 - 30) == "other"


def test_first_overhead_is_serve():
    assert classify_stroke(_swing("camera", "overhead"), 100, FPS, RIGHT, None) == "serve"


def test_missing_keypoints_is_other():
    kp = _swing("camera", "right")
    kp[100, R_WR] = np.nan
    assert classify_stroke(kp, 100, FPS, RIGHT, None) == "other"


def test_detect_strokes():
    kp = make_pose(300)
    add_swing(kp, 100, "right")
    add_swing(kp, 200, "left")
    strokes = detect_strokes(kp, FPS, Settings(backhand_hands=1))
    assert [(s.kind, s.metrics, s.defects) for s in strokes] == [("forehand", {}, []), ("backhand", {}, [])]
    assert abs(strokes[0].frame - 100) <= 2 and strokes[0].t == pytest.approx(strokes[0].frame / FPS)
