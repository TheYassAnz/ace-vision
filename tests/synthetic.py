"""Synthetic pose builders (pixels, torso ~100 px, 30 fps assumed by the tests)."""
import numpy as np

from ace.geometry import L_ANK, L_EL, L_HIP, L_KNEE, L_SH, L_WR, NOSE, R_ANK, R_EL, R_HIP, R_KNEE, R_SH, R_WR

FPS = 30.0
CX, SH_Y, HIP_Y, NOSE_Y, REST_WRIST_Y = 500.0, 200.0, 300.0, 150.0, 300.0
RAMP = 26  # frames to bring the arm to / from the swing position (slow, below any hit speed)
# raw per-frame speed shape (in units); smoothed over 3 frames its peak is 0.9
SHAPE = np.array([0.4, 0.7, 1.0, 1.0, 0.7, 0.4])


def _right_dir(facing: str) -> float:
    """Image x direction of the player's right side."""
    return -1.0 if facing == "camera" else 1.0


def make_pose(n_frames: int, facing: str = "camera") -> np.ndarray:
    """Standing player at rest."""
    d = _right_dir(facing)
    # (joint, dx toward the player's right, y)
    pts = [
        (NOSE, 0, NOSE_Y), (L_SH, -40, SH_Y), (R_SH, 40, SH_Y), (L_HIP, -30, HIP_Y), (R_HIP, 30, HIP_Y),
        (L_EL, -45, 250), (R_EL, 45, 250), (L_WR, -45, REST_WRIST_Y), (R_WR, 45, REST_WRIST_Y),
        (L_KNEE, -30, 380), (R_KNEE, 30, 380), (L_ANK, -30, 460), (R_ANK, 30, 460),
    ]
    kp = np.full((n_frames, 17, 3), np.nan)
    for j, dx, y in pts:
        kp[:, j] = (CX + d * dx, y, 1.0)
    return kp


def add_swing(kp, frame, side="right", speed=12.0, two_hands=False, handed="right"):
    """Swing of the `handed` wrist: backswing on the body `side` ("right"/"left"/"overhead") held from
    0.6 s to 0.1 s before `frame`, then a fast cross through impact (speed peak `speed` torso-lengths/s at
    `frame`) to a follow-through on the other side, then back to rest. An overhead swing also raises the
    other wrist above the head beforehand (ball toss); `two_hands` keeps both hands on the racket."""
    n = len(kp)
    d = np.sign(kp[0, R_HIP, 0] - kp[0, L_HIP, 0])  # image x direction of the player's right
    wr, other = (R_WR, L_WR) if handed == "right" else (L_WR, R_WR)
    rest, rest_o = kp[0, wr, :2].copy(), kp[0, other, :2].copy()
    out = d * (-1.0 if side == "left" else 1.0)  # image x direction of the stroke side
    back = np.array([CX + (0.0 if side == "overhead" else out * 70.0),
                     NOSE_Y - 100.0 if side == "overhead" else REST_WRIST_Y])
    # cross through impact: speeds at frames frame-2..frame+3 follow SHAPE (smoothed peak = speed)
    cross = np.concatenate([[0.0], np.cumsum(SHAPE * speed / 0.9 * 100.0 / FPS)])
    k = np.arange(n)
    path = np.tile(back, (n, 1))
    path[:, 0] -= out * cross[np.clip(k - (frame - 3), 0, 6)]
    # arm position: ramp in to the backswing (done at frame-18 = 0.6 s), hold, cross, ramp out
    env = np.clip(np.minimum(k - (frame - 18 - RAMP), (frame + 3 + RAMP) - k) / RAMP, 0, 1)[:, None]
    kp[:, wr, :2] += env * (path - rest)
    if two_hands:
        kp[:, other, :2] += env * (path + [d * 20.0, 0.0] - rest_o)
    elif side == "overhead":
        kp[:, other, :2] += env * (np.array([CX - d * 20.0, NOSE_Y - 120.0]) - rest_o)
    return kp


def set_shoulder_width(kp, frame, width):
    """Shrink the apparent shoulder width (px, centred on the body) at one frame."""
    kp[frame, R_SH, 0] = CX + np.sign(kp[0, R_SH, 0] - CX) * width / 2
    kp[frame, L_SH, 0] = CX + np.sign(kp[0, L_SH, 0] - CX) * width / 2
    return kp


def bend_knees(kp, frames, angle):
    """Displace both knees sideways so the hip-knee-ankle angle equals `angle` degrees on `frames`."""
    dx = 80.0 / np.tan(np.radians(angle) / 2)
    for k in (L_KNEE, R_KNEE):
        kp[frames, k, 0] += dx
    return kp


def set_stance(kp, frame, ankle_gap):
    """Set the ankle distance (px) at one frame."""
    for a in (L_ANK, R_ANK):
        kp[frame, a, 0] = CX + np.sign(kp[0, a, 0] - CX) * ankle_gap / 2
    return kp
