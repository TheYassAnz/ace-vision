import io
import json

import pytest
from fastapi.testclient import TestClient

from ace import store
from ace.domain import Stroke, VideoInfo
from ace.jobs import runner
from ace.notes import Note, score_detection
from ace.web.app import app


def S(t, kind="forehand"):
    return Stroke(t=t, frame=int(t * 30), kind=kind)


def test_perfect_match():
    sc = score_detection([S(1), S(5, "backhand")], [Note(t=1, kind="forehand"), Note(t=5, kind="backhand")])
    assert (sc.found_rate, sc.class_rate, sc.false_hits) == (1.0, 1.0, 0)


def test_tolerance():
    assert score_detection([S(1.25)], [Note(t=1, kind="forehand")]).found_rate == 1.0
    assert score_detection([S(1.5)], [Note(t=1, kind="forehand")]).found_rate == 0.0


def test_misclassified():
    notes = [Note(t=i * 3, kind="forehand") for i in range(10)]
    strokes = [S(i * 3, "forehand" if i < 8 else "backhand") for i in range(10)]
    sc = score_detection(strokes, notes)
    assert sc.n_notes == 10 and sc.n_detected == 10 and sc.found_rate == 1.0 and sc.class_rate == 0.8


def test_false_hits():
    assert score_detection([S(1), S(8), S(20)], [Note(t=1, kind="forehand")]).false_hits == 2


def test_each_note_matched_once():
    sc = score_detection([S(1.0), S(1.1)], [Note(t=1.05, kind="forehand")])
    assert sc.found_rate == 1.0 and sc.false_hits == 1


def test_no_notes_does_not_divide_by_zero():
    sc = score_detection([S(1)], [])
    assert sc.found_rate == 0.0 and sc.class_rate == 0.0 and sc.false_hits == 1


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: VideoInfo(
        width=1116, height=1986, fps=30, duration_s=75, n_frames=30, rotation=-90, created="2026-03-04T10:00:00"))
    monkeypatch.setattr(runner, "start", lambda mid: True)


def test_notes_endpoint_saves_score(env):
    client = TestClient(app, base_url="http://127.0.0.1:8765", headers={"Origin": "http://127.0.0.1:8765"})
    m = store.create_match(io.BytesIO(b"x"), "IMG_1.mov", "net", "")
    m.status, m.strokes = "done", [S(1)]
    store.save(m)
    assert "Noter mes coups" in client.get(f"/matchs/{m.id}/noter").text
    r = client.post(f"/matchs/{m.id}/notes", json=[{"t": 1.1, "kind": "forehand"}, {"t": 9, "kind": "serve"}])
    assert r.status_code == 200
    sc = store.load(m.id).score
    assert sc.n_notes == 2 and sc.found_rate == 0.5 and sc.class_rate == 1.0
    assert json.loads((store.match_dir(m.id) / "notes.json").read_text())[0]["t"] == 1.1
    assert "Fiabilité : 50 % de tes coups trouvés, 100 % bien classés" in client.get(f"/matchs/{m.id}").text
    assert client.post(f"/matchs/{m.id}/notes", json=[{"t": 1, "kind": "nope"}]).status_code == 422
