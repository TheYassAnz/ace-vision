import numpy as np
from scipy.signal import find_peaks

from ace.domain import Settings
from ace.geometry import L_WR, R_WR, torso_length

HIT_MIN_SPEED = 6.0  # torso lengths / s; shortcut: valeur de départ, à recalibrer avec les notes du joueur (Task 12)
MIN_HIT_GAP_S = 0.8


def _dominant_wrist(settings: Settings) -> int:
    return R_WR if settings.handedness == "right" else L_WR


def detect_hits(kp: np.ndarray, fps: float, settings: Settings) -> list[int]:
    """Frames of the player's hits: peaks of the dominant wrist's speed (torso lengths / s)."""
    torso = torso_length(kp)
    if not np.isfinite(torso) or torso <= 0:
        return []
    wrist = kp[:, _dominant_wrist(settings), :2]
    speed = np.zeros(len(kp))
    speed[1:] = np.linalg.norm(np.diff(wrist, axis=0), axis=1) * fps / torso
    speed = np.convolve(np.nan_to_num(speed), np.ones(3) / 3, mode="same")
    peaks, _ = find_peaks(speed, height=HIT_MIN_SPEED, distance=round(MIN_HIT_GAP_S * fps))
    return [int(p) for p in peaks]
