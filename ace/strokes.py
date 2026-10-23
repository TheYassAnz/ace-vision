import numpy as np
from scipy.signal import find_peaks

from ace.domain import Settings, Stroke, StrokeKind
from ace.geometry import L_HIP, L_WR, NOSE, R_HIP, R_WR, torso_length

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


SERVE_MIN_GAP_S = 3.0
TWO_HAND_MAX_DIST = 0.6  # torso lengths between wrists
SIDE_WINDOW_S = 0.5


def classify_stroke(kp: np.ndarray, frame: int, fps: float, settings: Settings, prev_hit: int | None) -> StrokeKind:
    wr = _dominant_wrist(settings)
    hips = kp[frame, [L_HIP, R_HIP], :2]
    if np.isnan(kp[frame, wr, :2]).any() or np.isnan(hips).any():
        return "other"
    if kp[frame, wr, 1] < kp[frame, NOSE, 1]:  # image y grows downward: smaller = higher
        return "serve" if prev_hit is None or (frame - prev_hit) / fps >= SERVE_MIN_GAP_S else "other"
    torso = torso_length(kp)
    other = L_WR if wr == R_WR else R_WR
    if settings.backhand_hands == 2 and np.linalg.norm(kp[frame, wr, :2] - kp[frame, other, :2]) < TWO_HAND_MAX_DIST * torso:
        return "backhand"
    window = kp[max(0, frame - round(SIDE_WINDOW_S * fps)) : frame + 1]
    right_dir = np.sign(np.nanmean(window[:, R_HIP, 0] - window[:, L_HIP, 0]))
    s = (kp[frame, wr, 0] - hips[:, 0].mean()) * right_dir  # > 0: player's right side
    return "forehand" if (s > 0) == (settings.handedness == "right") else "backhand"


def detect_strokes(kp: np.ndarray, fps: float, settings: Settings) -> list[Stroke]:
    strokes, prev = [], None
    for f in detect_hits(kp, fps, settings):
        strokes.append(Stroke(t=f / fps, frame=f, kind=classify_stroke(kp, f, fps, settings, prev)))
        prev = f
    return strokes
