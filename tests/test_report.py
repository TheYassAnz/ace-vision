import io

import pytest
from fastapi.testclient import TestClient

from ace import store
from ace.domain import Finding, Rally, Stroke, VideoInfo
from ace.jobs import runner
from ace.web.app import app


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: VideoInfo(
        width=1116, height=1986, fps=30, duration_s=75, n_frames=30, rotation=-90, created="2026-03-04T10:00:00"))
    monkeypatch.setattr(runner, "start", lambda mid: True)


client = TestClient(app, base_url="http://127.0.0.1:8765", headers={"Origin": "http://127.0.0.1:8765"})
FINDING = Finding(kind="forehand", defect="late_prep", count=11, total=25, title="Tu prépares trop tard",
                  text="Épaules pas tournées.", drill="Tourne dès le filet.", clip_times=[12.3, 40.0])


def done_match(view="net", findings=(), rallies=None):
    m = store.create_match(io.BytesIO(b"x" * 100), "IMG_1.mov", view, "vs Karim")
    m.status, m.findings, m.rallies = "done", list(findings), rallies
    m.strokes = [Stroke(t=12.3, frame=369, kind="forehand", defects=["late_prep"])]
    store.save(m)
    return m


def page(m):
    return client.get(f"/matchs/{m.id}").text


def test_report_net_view():
    t = page(done_match(findings=[FINDING]))
    for s in ("Vue d'ensemble", "Tu prépares trop tard", "11 coups droits sur 25", "Disponible en vue arrière"):
        assert s in t.replace("&#39;", "'")


def test_report_no_findings_message():
    assert "Aucun défaut ne revient assez souvent sur ce match pour en tirer un conseil." in page(done_match())


def test_report_clip_buttons():
    t = page(done_match(findings=[FINDING]))
    assert 'data-t="12.3"' in t and 'data-t="40.0"' in t


def test_report_rear_view_shows_breakdown():
    r = Rally(start_t=1, end_t=5, n_hits=3, end="net", last_stroke="forehand", user_hit_last=True)
    t = page(done_match(view="rear", rallies=[r]))
    assert "Où ça casse" in t and "Disponible en vue arrière" not in t
