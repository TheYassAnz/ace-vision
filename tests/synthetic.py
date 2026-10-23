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
    """Move the `handed` wrist to the body `side` ("right"/"left"/"overhead") with a peak of
    `speed` torso-lengths/s at `frame`; the arm returns to rest afterwards."""
    n = len(kp)
    d = np.sign(kp[0, R_HIP, 0] - kp[0, L_HIP, 0])  # image x direction of the player's right
    wr, other = (R_WR, L_WR) if handed == "right" else (L_WR, R_WR)
    rest, rest_o = kp[0, wr, :2].copy(), kp[0, other, :2].copy()
    target = np.array([CX + d * {"right": 70.0, "left": -70.0, "overhead": 0.0}[side],
                       NOSE_Y - 100.0 if side == "overhead" else REST_WRIST_Y])
    # arm position: ramp in, hold, ramp out
    env = np.zeros(n)
    for k in range(n):
        env[k] = np.clip(min(k - (frame - 3 - RAMP), (frame + 3 + RAMP) - k) / RAMP, 0, 1)
    for w, r, t in ((wr, rest, target), *(((other, rest_o, target + [d * 20.0, 0.0]),) if two_hands else ())):
        kp[:, w, :2] += env[:, None] * (t - r)
    # fast lateral wiggle: out and back, zero net displacement; speeds at frames frame-2..frame+3
    step = SHAPE * speed / 0.9 * 100.0 / FPS
    sign = np.array([1, 1, 1, -1, -1, -1])
    pos = np.cumsum(sign * step)
    out = d * (-1.0 if side == "left" else 1.0)  # wiggle goes outward from the body
    pos = np.concatenate([[0.0], pos])  # position at frame-3 .. frame+3
    for i, p in enumerate(pos):
        for w in (wr, other) if two_hands else (wr,):  # two hands travel together
            kp[frame - 3 + i, w, 0] += p * out
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
