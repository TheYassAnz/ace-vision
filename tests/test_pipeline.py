import io
import threading
from pathlib import Path

import numpy as np
import pytest

from ace import jobs, pipeline, store
from ace.domain import VideoInfo
from ace.jobs import JobRunner
from tests.synthetic import add_swing, make_pose

REAL = Path("videos/IMG_2665.mov")
INFO = VideoInfo(width=1116, height=1986, fps=30, duration_s=24, n_frames=720, rotation=-90, created="2026-03-04T10:00:00")


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: INFO)
    monkeypatch.setattr(pipeline, "probe", lambda p: INFO)


@pytest.fixture
def match():
    return store.create_match(io.BytesIO(b"x"), "a.mov", "net", "t")


def _fake_pose(path, info, on_progress):
    kp = make_pose(info.n_frames)
    for f in range(60, 660, 100):
        add_swing(kp, f, "right")
    on_progress(0.5)
    return kp


def test_analyse_net_view_done(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert (m.status, m.progress, m.error) == ("done", 1.0, None)
    assert len(m.strokes) == 6 and m.rallies is None
    assert store.pose_path(m.id).exists()


def test_analyse_failure_marks_failed(match, monkeypatch):
    def boom(*a):
        raise RuntimeError("modèle absent")

    monkeypatch.setattr(pipeline, "extract_pose", boom)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "failed" and m.error == "L'analyse a échoué : modèle absent"


def test_runner_one_at_a_time(match, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(jobs, "analyse", lambda id: gate.wait(5))
    r = JobRunner()
    assert r.start(match.id) is True and r.running_id == match.id
    assert r.start(match.id) is False
    gate.set()
    r._thread.join(5)
    assert r.running_id is None and r.start(match.id) is True
    r._thread.join(5)


def test_recover_interrupted(match):
    match.status = "running"
    store.save(match)
    jobs.recover_interrupted()
    m = store.load(match.id)
    assert m.status == "failed" and m.error == "Analyse interrompue (l'app a été fermée)."


def test_recover_skips_corrupt_match(match):
    other = store.create_match(io.BytesIO(b"y"), "b.mov", "net", "")
    other.status = "running"
    store.save(other)
    (store.match_dir(match.id) / "match.json").write_text("{not json")
    jobs.recover_interrupted()
    assert store.load(other.id).status == "failed"


def test_failed_retry_clears_stale_results_and_empty_message(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    pipeline.analyse(match.id)

    def boom(*a):
        raise RuntimeError()

    monkeypatch.setattr(pipeline, "extract_pose", boom)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "failed" and m.strokes == [] and m.error == "L'analyse a échoué : RuntimeError"


@pytest.mark.slow
@pytest.mark.skipif(not REAL.exists(), reason="sample video missing")
def test_analyse_real_video(monkeypatch):
    monkeypatch.undo()  # real probe and data dir
    import tempfile
    monkeypatch.setenv("ACE_DATA_DIR", tempfile.mkdtemp())
    with REAL.open("rb") as f:
        m = store.create_match(f, REAL.name, "net", "réel")
    pipeline.analyse(m.id)
    m = store.load(m.id)
    assert m.status == "done", m.error
    assert len(m.strokes) >= 1
