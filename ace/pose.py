from collections.abc import Callable
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from ace.domain import VideoInfo
from ace.geometry import MIN_CONF
from ace.video import iter_frames

MODEL = "models/yolo11m-pose.pt"


def select_player(tracks: dict[int, list[tuple[int, float, np.ndarray]]], n_frames: int) -> np.ndarray:
    """Keep the track with the largest summed box area (present most, biggest); NaN elsewhere."""
    out = np.full((n_frames, 17, 3), np.nan)
    if not tracks:
        return out
    best = max(tracks.values(), key=lambda t: sum(area for _, area, _ in t))
    for frame, _, kpts in best:
        if 0 <= frame < n_frames:
            k = np.array(kpts, dtype=float)
            k[k[:, 2] < MIN_CONF] = np.nan
            out[frame] = k
    return out


def extract_pose(path: Path, info: VideoInfo, on_progress: Callable[[float], None]) -> np.ndarray:
    model = YOLO(MODEL)
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
