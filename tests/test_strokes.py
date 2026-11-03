import numpy as np
import pytest

from ace.domain import Settings
from ace.strokes import HIT_MIN_SPEED, body_right_dir, classify_stroke, detect_hits, detect_strokes, sound_impact
from ace.geometry import L_HIP, L_WR, NOSE, R_HIP, R_WR
from tests.synthetic import NOSE_Y, SH_Y, add_swing, make_pose

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
    assert all(s.wrist_speed >= HIT_MIN_SPEED for s in detect_strokes(kp, FPS, RIGHT))


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


def test_backswing_shortly_before_hit_is_not_a_hit():
    # real video: the backswing of a backhand peaked 0.84 s before its impact
    kp = make_pose(250)
    add_swing(kp, 100, "right", speed=8.0)
    add_swing(kp, 125, "left")
    hits = detect_hits(kp, FPS, RIGHT)
    assert len(hits) == 1 and abs(hits[0] - 125) <= 2


def _swing(facing, side, handed="right", two_hands=False):
    kp = make_pose(200, facing=facing)
    add_swing(kp, 100, side, handed=handed, two_hands=two_hands)
    return kp


def _classify(kp, settings=RIGHT, prev_hit=None):
    return classify_stroke(kp, 100, FPS, settings, prev_hit, body_right_dir(kp))


@pytest.mark.parametrize("facing", ["camera", "away"])
def test_forehand_facing_camera_and_back(facing):
    assert _classify(_swing(facing, "right")) == "forehand"


@pytest.mark.parametrize("facing", ["camera", "away"])
def test_backhand_right_hander(facing):
    assert _classify(_swing(facing, "left"), Settings(backhand_hands=1)) == "backhand"


def test_left_hander_mirrors():
    kp = _swing("camera", "left", handed="left")
    assert _classify(kp, LEFT) == "forehand"


def test_two_handed_backhand():
    assert _classify(_swing("away", "left", two_hands=True)) == "backhand"


def test_forehand_with_free_hand_on_racket_during_backswing():
    # real video: the free hand holds the racket throat during the forehand unit turn
    assert _classify(_swing("camera", "right", two_hands=True)) == "forehand"


def test_one_handed_swing_right_side_is_forehand_with_two_hand_setting():
    assert _classify(_swing("away", "right", two_hands=False)) == "forehand"


def test_side_ignores_hips_swapping_when_side_on():
    kp = _swing("camera", "right")
    kp[70:100, [L_HIP, R_HIP], 0] = kp[70:100, [R_HIP, L_HIP], 0]  # turned side-on: hip order flips
    assert _classify(kp) == "forehand"


def test_overhead_after_pause_is_serve():
    assert _classify(_swing("camera", "overhead"), prev_hit=100 - 150) == "serve"


def test_overhead_quick_is_other():
    assert _classify(_swing("camera", "overhead"), prev_hit=100 - 30) == "other"


def test_first_overhead_is_serve():
    assert _classify(_swing("camera", "overhead")) == "serve"


def test_overhead_seen_from_behind_is_serve():
    kp = _swing("away", "overhead")
    kp[:, NOSE] = np.nan  # seen from behind: no face
    assert _classify(kp) == "serve"


def test_rear_forehand_with_raised_arms_is_not_serve():
    # IMG_7687, rear view: racket wrist up to 0.55 torso above the shoulders, free wrist 0.28, no face
    kp = _swing("away", "right")
    kp[:, NOSE] = np.nan
    kp[95:104, R_WR, 1] = SH_Y - 55  # torso = 100 px in tests.synthetic
    kp[60:100, L_WR, 1] = SH_Y - 28
    assert _classify(kp) == "forehand"


def test_wrist_just_above_nose_is_not_overhead():
    kp = _swing("camera", "right")
    kp[95:104, R_WR, 1] = NOSE_Y - 10
    kp[60:100, L_WR, 1] = NOSE_Y - 10
    assert _classify(kp) == "forehand"


def test_high_follow_through_without_toss_is_not_serve():
    # real video: a two-handed backhand finishing with the racket wrist above the head
    kp = _swing("camera", "left", two_hands=True)
    kp[100:104, R_WR, 1] = NOSE_Y - 30
    assert _classify(kp) == "backhand"


def test_overhead_without_toss_near_midline_is_other():
    kp = _swing("camera", "overhead")  # backswing at the body's midline
    kp[:, L_WR] = kp[0, L_WR]  # free hand stays down
    assert _classify(kp) == "other"


def test_missing_backswing_is_other():
    kp = _swing("camera", "right")
    kp[82:91, R_WR] = np.nan  # 9 of the 16 backswing frames
    assert _classify(kp) == "other"


def test_unknown_orientation_is_other():
    kp = _swing("camera", "right")
    assert classify_stroke(kp, 100, FPS, RIGHT, None, float("nan")) == "other"


def test_detect_strokes():
    kp = make_pose(300)
    add_swing(kp, 100, "right")
    add_swing(kp, 200, "left")
    strokes = detect_strokes(kp, FPS, Settings(backhand_hands=1))
    assert [(s.kind, s.metrics, s.defects) for s in strokes] == [("forehand", {}, []), ("backhand", {}, [])]
    assert abs(strokes[0].frame - 100) <= 2 and strokes[0].t == pytest.approx(strokes[0].frame / FPS)


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
