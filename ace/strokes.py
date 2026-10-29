import numpy as np
from scipy.signal import find_peaks

from ace.domain import Settings, Stroke, StrokeKind
from ace.geometry import L_HIP, L_SH, L_WR, R_HIP, R_SH, R_WR, torso_length

HIT_MIN_SPEED = 6.0  # torso lengths / s; IMG_2665 scores the same from 5 to 8 (calibrated Task 12)
MIN_HIT_GAP_S = 1.2  # a backswing can peak ~0.85 s before its impact (IMG_2665); find_peaks keeps the stronger
# shortcut: strokes closer than 1.2 s merge (fast volley exchanges), revisit with rear-view data


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
BACKSWING_START_S, BACKSWING_END_S = 0.6, 0.1  # side read before impact: at impact the wrist is already crossing
MIN_VALID_SHARE = 0.5  # of backswing frames with wrist and hips seen
OVERHEAD_BEFORE_S, OVERHEAD_AFTER_S = 0.15, 0.1  # around impact, racket wrist above the head
TOSS_WINDOW_S = 1.5  # free wrist above the head before a serve; a high follow-through has no toss
# serve rule validated only on synthetic serves and one real backhand follow-through (IMG_2665, no serve);
CLEAR_SIDE_MIN = 0.3  # torso lengths; IMG_2665 backswings sit 0.33-0.84 from the hips (high-finish BH 16.53: 0.70)
HEAD_TOP_ABOVE_SHOULDERS = 0.8  # torso lengths; IMG_7687 rear view: forehands rise to 0.55, free wrist to 0.28; synthetic serve 1.5


def body_right_dir(kp: np.ndarray) -> float:
    """Image x direction of the player's right side, fixed for the whole video: the player never changes
    side and faces one way per video, while the per-frame hip order flips whenever he turns side-on."""
    d = kp[:, R_HIP, 0] - kp[:, L_HIP, 0]
    return float(np.sign(np.nanmedian(d))) if np.isfinite(d).any() else float("nan")


def _head_top_y(kp: np.ndarray) -> np.ndarray:
    """Per-frame top of the head, from the shoulders only: the face is hidden ~93% of the time in rear view."""
    l, r = kp[:, L_SH, 1], kp[:, R_SH, 1]
    shoulders = (np.fmin(l, r) + np.fmax(l, r)) / 2  # nanmean without the all-NaN warning
    return shoulders - HEAD_TOP_ABOVE_SHOULDERS * torso_length(kp)


def _above_head(kp: np.ndarray, wrist: int, a: int, b: int) -> bool:
    w = kp[max(0, a) : b + 1]
    return bool(np.any(w[:, wrist, 1] < _head_top_y(w)))  # image y grows downward: smaller = higher; NaN is False


def classify_stroke(kp: np.ndarray, frame: int, fps: float, settings: Settings, prev_hit: int | None,
                    right_dir: float) -> StrokeKind:
    wr = _dominant_wrist(settings)
    other = L_WR if wr == R_WR else R_WR
    if not np.isfinite(right_dir) or right_dir == 0:
        return "other"
    # no separate two-hand rule: on IMG_2665 forehand backswings also keep the hands together (free hand
    # on the racket throat), and a two-handed backhand's backswing is on the backhand side anyway
    w = kp[max(0, frame - round(BACKSWING_START_S * fps)) : frame - round(BACKSWING_END_S * fps) + 1]
    s = (w[:, wr, 0] - w[:, [L_HIP, R_HIP], 0].mean(axis=1)) * right_dir  # > 0: player's right side
    s = s[np.isfinite(s)]
    side = float(np.median(s)) if len(w) and len(s) >= MIN_VALID_SHARE * len(w) else float("nan")
    if _above_head(kp, wr, frame - round(OVERHEAD_BEFORE_S * fps), frame + round(OVERHEAD_AFTER_S * fps)):
        if _above_head(kp, other, frame - round(TOSS_WINDOW_S * fps), frame):
            return "serve" if prev_hit is None or (frame - prev_hit) / fps >= SERVE_MIN_GAP_S else "other"
        if not abs(side) >= CLEAR_SIDE_MIN * torso_length(kp):  # NaN-safe
            return "other"  # overhead, no toss, backswing near the midline: FH/BH would be arbitrary
    if np.isnan(side):
        return "other"
    return "forehand" if (side > 0) == (settings.handedness == "right") else "backhand"

def detect_strokes(kp: np.ndarray, fps: float, settings: Settings) -> list[Stroke]:
    strokes, prev = [], None
    right_dir = body_right_dir(kp)
    for f in detect_hits(kp, fps, settings):
        strokes.append(Stroke(t=f / fps, frame=f, kind=classify_stroke(kp, f, fps, settings, prev, right_dir)))
        prev = f
    return strokes
