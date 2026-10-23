import logging
import math
import time

import numpy as np

from ace import store
from ace.findings import build_findings, load_advice
from ace.pose import extract_pose
from ace.strokes import detect_strokes
from ace.technique import detect_defects, measure, ref_shoulder_width
from ace.video import probe

log = logging.getLogger(__name__)
POSE_SHARE = 0.9  # pose extraction covers progress 0 -> 0.9
SAVE_EVERY_S = 2.0


def analyse(match_id: str) -> None:
    m = None
    try:
        m = store.load(match_id)
        m.status, m.progress, m.error = "running", 0.0, None
        m.strokes, m.findings, m.rallies = [], [], None
        m.settings = store.load_settings()
        store.save(m)
        info = probe(store.match_dir(match_id) / m.video_file)
        m.info = info
        last_save = time.monotonic()

        def on_progress(p: float) -> None:
            nonlocal last_save
            m.progress = p * POSE_SHARE
            if time.monotonic() - last_save >= SAVE_EVERY_S:
                store.save(m)
                last_save = time.monotonic()

        kp = extract_pose(store.match_dir(match_id) / m.video_file, info, on_progress)
        np.savez_compressed(store.pose_path(match_id), kp=kp)
        m.strokes = detect_strokes(kp, info.fps, m.settings)
        ref = ref_shoulder_width(kp)
        if math.isfinite(ref) and ref > 0:
            for s in m.strokes:
                s.metrics = measure(kp, s.frame, info.fps, ref)
                s.defects = detect_defects(s.metrics, s.kind)
        m.findings = build_findings(m.strokes, load_advice())
        m.rallies = None  # net view: rallies not computable (rear view handled by a later task)
        m.status, m.progress = "done", 1.0
    except Exception as e:
        if m is None:
            log.exception("analysis of %s failed before loading the match", match_id)
            return
        m.status, m.error = "failed", f"L'analyse a échoué : {str(e) or type(e).__name__}"
    try:
        store.save(m)
    except Exception:
        log.exception("could not save analysis result of %s", match_id)
