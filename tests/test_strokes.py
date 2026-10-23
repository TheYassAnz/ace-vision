import numpy as np
import pytest

from ace.domain import Settings
from ace.strokes import detect_hits
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
