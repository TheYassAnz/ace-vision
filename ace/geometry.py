import numpy as np

NOSE = 0
L_SH, R_SH = 5, 6
L_EL, R_EL = 7, 8
L_WR, R_WR = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANK, R_ANK = 15, 16
MIN_CONF = 0.3  # below this a keypoint is treated as missing (NaN)


def torso_length(kp: np.ndarray) -> float:
    """Median over the video of the distance shoulder-midpoint -> hip-midpoint; kp is (n, 17, >=2)."""
    sh = (kp[:, L_SH, :2] + kp[:, R_SH, :2]) / 2
    hip = (kp[:, L_HIP, :2] + kp[:, R_HIP, :2]) / 2
    return float(np.nanmedian(np.linalg.norm(sh - hip, axis=1)))


def angle_deg(a, b, c) -> float:
    """Angle at b (degrees) formed by a-b-c."""
    v1, v2 = np.asarray(a, float) - b, np.asarray(c, float) - b
    cos = v1 @ v2 / (np.linalg.norm(v1) * np.linalg.norm(v2))
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
