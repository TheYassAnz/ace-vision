import inspect
from pathlib import Path

import cv2
import pytest

from ace.domain import VideoInfo
from ace.video import iter_frames, parse_ffprobe, probe, rotate_code

REAL = Path("videos/IMG_2665.mov")
needs_real = pytest.mark.skipif(not REAL.exists(), reason="sample video missing")


def _probe_dict(w, h, rate, nb, rotation=None, tags=None):
    stream = {"width": w, "height": h, "r_frame_rate": rate, "nb_frames": nb}
    if rotation is not None:
        stream["side_data_list"] = [{"rotation": rotation}]
    return {"streams": [stream], "format": {"duration": "30.683", "tags": tags or {}}}


def test_parse_ffprobe_portrait_rotated():
    d = _probe_dict(1986, 1116, "30/1", "920", -90,
                    {"creation_time": "2026-03-23T17:12:34.000000Z"})
    assert parse_ffprobe(d) == VideoInfo(
        width=1116, height=1986, fps=30.0, duration_s=30.683, n_frames=920,
        rotation=-90, created="2026-03-23T17:12:34")


def test_parse_ffprobe_landscape_no_rotation():
    info = parse_ffprobe(_probe_dict(1920, 1080, "60000/1001", "100"))
    assert (info.width, info.height, info.rotation, info.created) == (1920, 1080, 0, None)
    assert info.fps == pytest.approx(59.94, abs=0.01)


@pytest.mark.slow
@needs_real
def test_probe_real_video():
    info = probe(REAL)
    assert (info.width, info.height, info.fps) == (1116, 1986, 30)


@pytest.mark.slow
@needs_real
def test_iter_frames_upright_and_lazy():
    frames = iter_frames(REAL)
    assert inspect.isgenerator(frames)
    _, img = next(frames)
    assert img.shape == (1986, 1116, 3)


def test_rotate_code_mapping():
    assert rotate_code(0) is None
    assert rotate_code(-90) == rotate_code(270) == cv2.ROTATE_90_CLOCKWISE
    assert rotate_code(90) == cv2.ROTATE_90_COUNTERCLOCKWISE
    assert rotate_code(180) == cv2.ROTATE_180
