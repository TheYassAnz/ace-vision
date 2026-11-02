import shutil
import subprocess

import numpy as np
import pytest

from ace.audio import SAMPLE_RATE, impact_clicks, read_audio

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg absent")
SR = 48000


def _clicks_at(times, dur=4.0, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 0.002, int(dur * SR)).astype(np.float32)  # room noise floor
    for t in times:
        i = int(t * SR)
        a[i:i + 240] += rng.normal(0, 0.3, 240) * np.exp(-np.arange(240) / 60)  # 5 ms broadband crack
    return a


def test_finds_each_click_to_the_millisecond():
    got = impact_clicks(_clicks_at([0.5, 1.7, 3.1]), SR)
    assert len(got) == 3 and np.allclose(got, [0.5, 1.7, 3.1], atol=0.006)


def test_silence_has_no_click():
    assert impact_clicks(np.zeros(SR * 2, np.float32), SR).size == 0


def test_low_thump_is_not_a_click():  # footstep / ball bounce on a hard floor: energy below 2 kHz
    t = np.arange(SR * 2) / SR
    a = (0.5 * np.sin(2 * np.pi * 120 * t) * np.exp(-((t - 1.0) / 0.01) ** 2)).astype(np.float32)
    assert impact_clicks(a, SR).size == 0


def test_clicks_closer_than_150_ms_count_once():
    assert len(impact_clicks(_clicks_at([1.0, 1.08]), SR)) == 1


@needs_ffmpeg
def test_read_audio_none_without_audio_track(tmp_path):
    p = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1", "-an", str(p)], check=True)
    assert read_audio(p) is None


@needs_ffmpeg
def test_read_audio_mono_48k(tmp_path):
    p = tmp_path / "sound.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=1",
                    "-f", "lavfi", "-i", "sine=f=1000:d=1", "-ac", "2", str(p)], check=True)
    a = read_audio(p)
    assert a.dtype == np.float32 and a.ndim == 1 and abs(len(a) - SAMPLE_RATE) < SAMPLE_RATE * 0.05
