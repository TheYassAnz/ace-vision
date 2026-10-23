import json
import subprocess
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

from ace.domain import VideoInfo

_ROTATE = {90: cv2.ROTATE_90_CLOCKWISE, -90: cv2.ROTATE_90_COUNTERCLOCKWISE,
           270: cv2.ROTATE_90_COUNTERCLOCKWISE, -270: cv2.ROTATE_90_CLOCKWISE,
           180: cv2.ROTATE_180, -180: cv2.ROTATE_180}


def parse_ffprobe(d: dict) -> VideoInfo:
    s, fmt = d["streams"][0], d["format"]
    rotation = next((int(x["rotation"]) for x in s.get("side_data_list", []) if "rotation" in x), 0)
    w, h = s["width"], s["height"]
    if abs(rotation) % 180 == 90:
        w, h = h, w
    fps = float(Fraction(s["r_frame_rate"]))
    duration = float(fmt["duration"])
    n_frames = int(s["nb_frames"]) if s.get("nb_frames") else round(duration * fps)
    created = (s.get("tags", {}).get("creation_time") or fmt.get("tags", {}).get("creation_time"))
    return VideoInfo(width=w, height=h, fps=fps, duration_s=duration, n_frames=n_frames,
                     rotation=rotation, created=created[:19] if created else None)


def probe(path: Path) -> VideoInfo:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    return parse_ffprobe(json.loads(out))


def iter_frames(path: Path) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (index, upright BGR frame) lazily; never holds the whole video."""
    info = probe(path)
    cap = cv2.VideoCapture(str(path))
    try:
        i = 0
        while True:
            ok, img = cap.read()
            if not ok:
                return
            # OpenCV usually applies the display matrix itself; fix up only if it did not.
            if img.shape[:2] != (info.height, info.width) and info.rotation in _ROTATE:
                img = cv2.rotate(img, _ROTATE[info.rotation])
            yield i, img
            i += 1
    finally:
        cap.release()
