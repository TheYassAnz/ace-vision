import os

os.environ.setdefault("YOLO_OFFLINE", "1")  # before ultralytics loads: no analytics or online checks

from collections.abc import Callable
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from ace.domain import VideoInfo
from ace.geometry import MIN_CONF
from ace.video import iter_frames


def model_path() -> str:
    """ACE_MODEL_PATH from the macOS app; else the repo model, resolved from __file__ so it is cwd-independent."""
    return os.environ.get("ACE_MODEL_PATH") or str(Path(__file__).resolve().parent.parent / "models" / "yolo11m-pose.pt")


TRACK_AREA_RATIO = 2.0  # a stitched track's mean box area stays within ×/÷ 2 of the player's (IMG_7687: 0.90-1.01)


def _center(kpts: np.ndarray) -> np.ndarray:
    k = np.asarray(kpts, dtype=float)
    k = k[k[:, 2] >= MIN_CONF, :2]
    return k.mean(axis=0) if len(k) else np.full(2, np.nan)


def _first_center(kpts_in_order) -> np.ndarray:
    """First reliable position: the tracker often loses the player on frames where he is half out of the image."""
    return next((c for k in kpts_in_order if np.isfinite(c := _center(k)).all()), np.full(2, np.nan))


def select_player(tracks: dict[int, list[tuple[int, float, np.ndarray]]], n_frames: int) -> np.ndarray:
    """The track with the largest summed box area (present most, biggest), plus the tracks the tracker split off
    the same player: no overlap in time, a similar box size, and a start/end next to where he was; NaN elsewhere."""
    out = np.full((n_frames, 17, 3), np.nan)
    if not tracks:
        return out
    ranked = sorted(tracks.values(), key=lambda t: -sum(area for _, area, _ in t))
    chosen = {f: k for f, _, k in ranked[0]}
    area = np.mean([a for _, a, _ in ranked[0]])
    reach = np.sqrt(area)  # a box side: how far the player may be from where the tracker lost him
    for t in ranked[1:]:
        frames = [f for f, _, _ in t]
        if chosen.keys() & set(frames) or not 1 / TRACK_AREA_RATIO <= np.mean([a for _, a, _ in t]) / area <= TRACK_AREA_RATIO:
            continue
        before = sorted((f for f in chosen if f < frames[0]), reverse=True)
        after = sorted(f for f in chosen if f > frames[-1])
        own = [k for _, _, k in t]
        ends = ([(_first_center(chosen[f] for f in before), _first_center(own))] if before else []) + \
               ([(_first_center(chosen[f] for f in after), _first_center(reversed(own)))] if after else [])
        if ends and all(np.linalg.norm(a - b) <= reach for a, b in ends):  # NaN distance: not stitched
            chosen.update({f: k for f, _, k in t})
    for frame, kpts in chosen.items():
        if 0 <= frame < n_frames:
            k = np.array(kpts, dtype=float)
            k[k[:, 2] < MIN_CONF] = np.nan
            out[frame] = k
    return out


def extract_pose(path: Path, info: VideoInfo, on_progress: Callable[[float], None]) -> np.ndarray:
    model = YOLO(model_path())
    tracks: dict[int, list[tuple[int, float, np.ndarray]]] = {}
    for i, frame in iter_frames(path):
        if i >= info.n_frames:
            break
        r = model.track(frame, persist=True, device="mps", imgsz=960, verbose=False)[0]
        if r.boxes.id is not None:
            ids = r.boxes.id.int().tolist()
            areas = (r.boxes.xywh[:, 2] * r.boxes.xywh[:, 3]).tolist()
            kp = np.concatenate([r.keypoints.xy.cpu().numpy(), r.keypoints.conf.cpu().numpy()[..., None]], axis=2)
            for tid, area, k in zip(ids, areas, kp):
                tracks.setdefault(tid, []).append((i, area, k))
        on_progress(i / info.n_frames)
    return select_player(tracks, info.n_frames)
