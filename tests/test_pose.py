import time
from pathlib import Path

import numpy as np
import pytest

from ace.geometry import MIN_CONF, angle_deg
from ace.pose import extract_pose, model_path, select_player
from ace.video import probe

REAL = Path("videos/IMG_2665.mov")


def _kpts(conf=0.9):
    k = np.full((17, 3), 5.0)
    k[:, 2] = conf
    return k


def test_model_path_from_env(monkeypatch):
    monkeypatch.setenv("ACE_MODEL_PATH", "/x/m.pt")
    assert model_path() == "/x/m.pt"
    monkeypatch.delenv("ACE_MODEL_PATH")
    assert model_path().endswith("models/yolo11m-pose.pt")


def test_ultralytics_runs_offline():
    import ultralytics.utils
    from ultralytics.utils.events import events
    assert ultralytics.utils.ONLINE is False and events.enabled is False


def test_select_player_prefers_persistent_track():
    a = [(f, 100.0, _kpts()) for f in range(900)]
    b = [(f, 300.0, _kpts()) for f in range(900, 950)]
    out = select_player({1: a, 2: b}, 1000)
    assert out.shape == (1000, 17, 3)
    assert not np.isnan(out[:900]).any()
    assert np.isnan(out[900:]).all()


def _at(x):
    k = _kpts()
    k[:, 0] = x
    return k


def test_select_player_stitches_tracks_split_by_the_tracker():
    # IMG_7687: the tracker lost the player twice and gave him 3 ids at the same place and size
    tracks = {1: [(f, 100.0, _at(5)) for f in range(0, 50)],
              2: [(f, 100.0, _at(6)) for f in range(60, 200)],
              3: [(f, 110.0, _at(7)) for f in range(205, 300)]}
    out = select_player(tracks, 300)
    seen = ~np.isnan(out[:, 0, 0])
    assert seen[:50].all() and seen[60:200].all() and seen[205:].all() and not seen[50:60].any()


def test_stitching_skips_unreliable_frames_at_the_cut():
    # IMG_7687: the tracker loses the player as he leaves the image, his last points are below confidence
    lost = _at(5)
    lost[:, 2] = 0.1
    tracks = {1: [(f, 100.0, _at(5)) for f in range(60, 300)],
              2: [(f, 100.0, _at(5)) for f in range(0, 48)] + [(f, 100.0, lost) for f in range(48, 50)]}
    out = select_player(tracks, 300)
    assert not np.isnan(out[:48, 0, 0]).any()


def test_select_player_does_not_stitch_someone_else():
    tracks = {1: [(f, 100.0, _at(5)) for f in range(0, 200)],
              2: [(f, 100.0, _at(500)) for f in range(210, 260)],  # same size, far away
              3: [(f, 10.0, _at(5)) for f in range(260, 300)],     # same place, much smaller (opponent)
              4: [(f, 100.0, _at(6)) for f in range(150, 180)]}    # same time as the player
    out = select_player(tracks, 300)
    assert not np.isnan(out[:200, 0, 0]).any() and np.isnan(out[200:, 0, 0]).all()


def test_select_player_nan_when_absent():
    tracks = {1: [(f, 100.0, _kpts()) for f in range(30) if not 10 <= f <= 20]}
    out = select_player(tracks, 30)
    assert np.isnan(out[10:21]).all()
    assert not np.isnan(out[0]).any()


def test_low_confidence_points_become_nan():
    k = _kpts()
    k[7, 2] = 0.1
    out = select_player({1: [(0, 100.0, k)]}, 1)
    assert np.isnan(out[0, 7]).all()
    assert not np.isnan(out[0, 6]).any()
    assert MIN_CONF == 0.3


def test_angle_deg_straight_leg():
    assert angle_deg((0, 0), (1, 0), (2, 0)) == pytest.approx(180, abs=0.1)
    assert angle_deg((1, 0), (0, 0), (0, 1)) == pytest.approx(90, abs=0.1)


@pytest.mark.slow
@pytest.mark.skipif(not REAL.exists(), reason="sample video missing")
def test_extract_pose_real_video():
    info = probe(REAL)
    t = time.time()
    out = extract_pose(REAL, info, lambda p: None)
    fps = info.n_frames / (time.time() - t)
    print(f"pose speed: {fps:.1f} frames/s")
    assert out.shape == (info.n_frames, 17, 3)
    hips = ~np.isnan(out[:, [11, 12], 0]).any(axis=1)
    assert hips.mean() >= 0.9
