import time
from pathlib import Path

import numpy as np
import pytest

from ace.geometry import MIN_CONF, angle_deg
from ace.pose import extract_pose, select_player
from ace.video import probe

REAL = Path("videos/IMG_2665.mov")


def _kpts(conf=0.9):
    k = np.full((17, 3), 5.0)
    k[:, 2] = conf
    return k


def test_select_player_prefers_persistent_track():
    a = [(f, 100.0, _kpts()) for f in range(900)]
    b = [(f, 300.0, _kpts()) for f in range(900, 950)]
    out = select_player({1: a, 2: b}, 1000)
    assert out.shape == (1000, 17, 3)
    assert not np.isnan(out[:900]).any()
    assert np.isnan(out[900:]).all()


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
