import numpy as np

from ace.domain import DefectId, StrokeKind
from ace.geometry import L_ANK, L_HIP, L_KNEE, L_SH, R_ANK, R_HIP, R_KNEE, R_SH, angle_deg

# shortcut: repères d'entraîneur, recalibrés en Task 12
THRESHOLDS: dict[DefectId, float] = {"late_prep": 0.4, "small_turn": 0.8, "straight_legs": 160.0, "narrow_stance": 1.5}
_APPLICABLE: dict[StrokeKind, list[DefectId]] = {
    "forehand": list(THRESHOLDS), "backhand": list(THRESHOLDS), "serve": ["straight_legs"], "other": [],
}
_NAN = float('nan')


def _width(kp: np.ndarray, left: int, right: int) -> np.ndarray:
    return np.linalg.norm(kp[..., left, :2] - kp[..., right, :2], axis=-1)


def ref_shoulder_width(kp: np.ndarray) -> float:
    w = _width(kp, L_SH, R_SH)
    return float(np.nanmedian(w)) if not np.isnan(w).all() else _NAN


def measure(kp: np.ndarray, frame: int, fps: float, ref_shoulder: float) -> dict[str, float]:
    out = {"turn_ratio": _NAN, "prep_lead_s": _NAN, "knee_angle_min": _NAN, "stance_ratio": _NAN}
    lo = max(0, frame - round(1.0 * fps))
    w = _width(kp[lo:frame + 1], L_SH, R_SH) / ref_shoulder  # NaN ref -> all NaN
    if not np.isnan(w).all():
        i = int(np.nanargmin(w))
        out["turn_ratio"], out["prep_lead_s"] = float(w[i]), (frame - (lo + i)) / fps
    knees = [angle_deg(kp[f, h, :2], kp[f, k, :2], kp[f, a, :2])
             for f in range(max(0, frame - round(0.5 * fps)), frame + 1)
             for h, k, a in ((L_HIP, L_KNEE, L_ANK), (R_HIP, R_KNEE, R_ANK))]
    if not np.isnan(knees).all():
        out["knee_angle_min"] = float(np.nanmin(knees))
    hips = _width(kp[frame], L_HIP, R_HIP)
    if hips > 0:  # NaN or zero -> unmeasurable
        out["stance_ratio"] = float(_width(kp[frame], L_ANK, R_ANK) / hips)
    return out


def detect_defects(metrics: dict[str, float], kind: StrokeKind) -> list[DefectId]:
    t = THRESHOLDS
    found = {  # NaN compares False: a missing metric never yields a defect
        "late_prep": metrics["prep_lead_s"] < t["late_prep"],
        "small_turn": metrics["turn_ratio"] > t["small_turn"],
        "straight_legs": metrics["knee_angle_min"] > t["straight_legs"],
        "narrow_stance": metrics["stance_ratio"] < t["narrow_stance"],
    }
    return [d for d in _APPLICABLE[kind] if found[d]]
