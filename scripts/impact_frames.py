"""Contact sheet of the frame at each stroke's time, to check by eye that the ball is on the racket.

Usage: uv run python scripts/impact_frames.py <match_id>   (writes impacts.jpg in the match folder)
"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run as a plain script from anywhere

from ace import store
from ace.audio import match_clicks
from ace.strokes import detect_strokes

COLUMNS = 4
TILE_W = 480


def frame_at(video: Path, t: float) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale={TILE_W}:-1", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                         capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def main(match_id: str) -> None:
    m = store.load(match_id)
    video = store.match_dir(match_id) / m.video_file
    kp = np.load(store.pose_path(match_id))["kp"]
    strokes = detect_strokes(kp, m.info.fps, store.load_settings(), clicks=match_clicks(video, match_id))
    tiles = []
    for s in strokes:
        img = frame_at(video, s.t)
        label = f"{s.t:.2f} s  {'son' if s.sound_hit else 'poignet'}"
        cv2.putText(img, label, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(img, label, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        tiles.append(img)
    if not tiles:
        sys.exit("aucune frappe détectée")
    h, w = tiles[0].shape[:2]
    tiles += [np.zeros((h, w, 3), np.uint8)] * (-len(tiles) % COLUMNS)
    rows = [np.hstack(tiles[i:i + COLUMNS]) for i in range(0, len(tiles), COLUMNS)]
    out = store.match_dir(match_id) / "impacts.jpg"
    cv2.imwrite(str(out), np.vstack(rows))
    print(f"{len(strokes)} frappes -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
