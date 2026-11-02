import logging
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

log = logging.getLogger(__name__)
SAMPLE_RATE = 48000

HIGHPASS_HZ = 2000      # the racket crack is broadband; footsteps, bounces and voices sit lower
ENV_MS = 3              # RMS window of the envelope
RISE_MS = 5             # an impact rises within a few ms
MIN_RISE_DB = 12.0      # rise over RISE_MS that counts as a click (prototype 2026-11-02: real hits 14-31 dB)
MIN_CLICK_GAP_S = 0.15  # one click per impact, its echo merged


def read_audio(path: Path) -> np.ndarray | None:
    """Mono float32 in [-1, 1] at SAMPLE_RATE, or None when the file has no audio track."""
    has_audio = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip()
    if not has_audio:
        return None
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def impact_clicks(samples: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Times (s, sorted) of sharp broadband attacks: the ball-racket crack."""
    a = sosfilt(butter(4, HIGHPASS_HZ, "highpass", fs=sr, output="sos"), samples)
    hop = sr // 1000  # envelope sampled every 1 ms
    win = hop * ENV_MS
    env = np.sqrt(np.convolve(a ** 2, np.ones(win) / win, mode="same"))[::hop]
    db = 20 * np.log10(env + 1e-6)
    rise = np.concatenate([np.zeros(RISE_MS), np.maximum(0, db[RISE_MS:] - db[:-RISE_MS])])
    peaks, _ = find_peaks(rise, height=MIN_RISE_DB, distance=MIN_CLICK_GAP_S * 1000)
    return peaks / 1000.0


def match_clicks(video: Path, match_id: str) -> np.ndarray | None:
    """Impact clicks of a match video; None when it has no sound or the sound is unreadable."""
    try:
        samples = read_audio(video)
        return impact_clicks(samples) if samples is not None else None
    except Exception:
        log.warning("sound of %s unreadable, strokes stay on the wrist peak", match_id, exc_info=True)
        return None
