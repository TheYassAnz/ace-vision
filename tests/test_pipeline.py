import io
import subprocess
import threading
from pathlib import Path

import numpy as np
import pytest

from ace import audio, jobs, pipeline, store
from ace.domain import VideoInfo
from ace.geometry import L_ANK, L_HIP, L_SH, R_ANK, R_HIP, R_SH
from ace.jobs import JobRunner
from tests.synthetic import add_swing, make_pose

REAL = Path("videos/IMG_2665.mov")
INFO = VideoInfo(width=1116, height=1986, fps=30, duration_s=24, n_frames=720, rotation=-90, created="2026-03-04T10:00:00")


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: INFO)
    monkeypatch.setattr(pipeline, "probe", lambda p: INFO)
    monkeypatch.setattr(audio, "read_audio", lambda p: None)  # the fake video has no ffmpeg-readable sound


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


def test_strokes_timed_on_clicks(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    peaks = [f / INFO.fps for f in range(60, 660, 100)]  # add_swing peaks in _fake_pose
    monkeypatch.setattr(audio, "read_audio", lambda p: np.zeros(10, np.float32))
    monkeypatch.setattr(audio, "impact_clicks", lambda a: np.array([t + 0.05 for t in peaks]))
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "done" and all(s.sound_hit for s in m.strokes)


def test_no_audio_track_analyses_as_before(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    pipeline.analyse(match.id)  # env fixture: read_audio returns None
    m = store.load(match.id)
    assert m.status == "done" and len(m.strokes) == 6 and all(s.sound_hit is None for s in m.strokes)


def test_unreadable_audio_still_done(match, monkeypatch, caplog):
    def bad(p):
        raise subprocess.CalledProcessError(1, ["ffmpeg"])

    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    monkeypatch.setattr(audio, "read_audio", bad)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert (m.status, m.error) == ("done", None) and all(s.sound_hit is None for s in m.strokes)
    assert "sound" in caplog.text


def test_analyse_failure_marks_failed(match, monkeypatch):
    def boom(*a):
        raise RuntimeError("modèle absent")

    monkeypatch.setattr(pipeline, "extract_pose", boom)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "failed" and m.error == "L'analyse a échoué."  # raw exception text stays in the log


def test_unreadable_video_reason_is_french(match, monkeypatch):
    def bad(p):
        raise subprocess.CalledProcessError(1, ["ffprobe"], stderr="moov atom not found")

    monkeypatch.setattr(pipeline, "probe", bad)
    pipeline.analyse(match.id)
    assert store.load(match.id).error == "L'analyse a échoué : vidéo illisible."


def test_nan_metrics_survive_reload_and_match_is_served(match, monkeypatch):
    from fastapi.testclient import TestClient
    from ace.web.app import app

    monkeypatch.setenv("ACE_TOKEN", "t")

    def pose(path, info, on_progress):
        kp = _fake_pose(path, info, on_progress)
        kp[:, [L_ANK, R_ANK]] = np.nan  # ankles hidden: stance_ratio is NaN
        return kp

    monkeypatch.setattr(pipeline, "extract_pose", pose)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.status == "done" and m.strokes and np.isnan(m.strokes[0].metrics["stance_ratio"])
    assert [x.id for x in store.list_matches()] == [match.id]
    r = TestClient(app, base_url="http://127.0.0.1", headers={"Authorization": "Bearer t"}).get(f"/matchs/{match.id}")
    assert r.status_code == 200 and r.json()["status"] == "done"


def test_coverage_and_unmeasured_strokes(match, monkeypatch):
    def pose(path, info, on_progress):
        kp = _fake_pose(path, info, on_progress)
        kp[:180, [L_HIP, R_HIP]] = np.nan  # player not found on the first quarter
        kp[:, [L_ANK, R_ANK]] = np.nan
        for f in range(60, 660, 100):  # shoulders hidden before every hit: no metric is measurable
            kp[f - 35:f + 1, [L_SH, R_SH]] = np.nan
        return kp

    monkeypatch.setattr(pipeline, "extract_pose", pose)
    pipeline.analyse(match.id)
    m = store.load(match.id)
    assert m.coverage == pytest.approx(0.75)
    assert m.n_unmeasured == sum(s.kind != "other" for s in m.strokes) > 0


def test_runner_one_at_a_time(match, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(jobs, "analyse", lambda id, should_stop: gate.wait(5))
    r = JobRunner()
    assert r.start(match.id) is True and r.running_id == match.id
    assert r.start(match.id) is False
    gate.set()
    r._thread.join(5)
    assert r.running_id is None and r.start(match.id) is True
    r._thread.join(5)


def test_stop_resets_match_to_pending(match, monkeypatch):
    monkeypatch.setattr(pipeline, "extract_pose", _fake_pose)
    pipeline.analyse(match.id, should_stop=lambda: True)
    m = store.load(match.id)
    assert (m.status, m.progress, m.error, m.strokes) == ("pending", 0.0, None, [])


def test_runner_stop_only_targets_running_match(match, monkeypatch):
    seen = threading.Event()

    def fake(id, should_stop):
        while not should_stop():
            threading.Event().wait(0.01)
        seen.set()

    monkeypatch.setattr(jobs, "analyse", fake)
    r = JobRunner()
    assert r.stop(match.id) is False
    r.start(match.id)
    assert r.stop("other") is False and r.stop(match.id) is True
    r._thread.join(5)
    assert seen.is_set() and r.running_id is None


def test_recover_interrupted(match):
    match.status = "running"
    store.save(match)
    jobs.recover_interrupted()
    m = store.load(match.id)
    assert m.status == "failed" and m.error == "Analyse interrompue (l'app a été fermée)."


def test_recover_clears_leftover_uploads(match):
    leftover = store._root() / "incoming" / "tmp123.mov"
    leftover.write_bytes(b"half")
    jobs.recover_interrupted()
    assert not leftover.exists()


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
    assert m.status == "failed" and m.strokes == [] and m.error == "L'analyse a échoué."


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
