import io

import pytest
from fastapi.testclient import TestClient

from ace import __main__ as entry
from ace import store
from ace.domain import Stroke, VideoInfo
from ace.jobs import runner
from ace.web.app import app


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: VideoInfo(
        width=1116, height=1986, fps=30, duration_s=75, n_frames=30, rotation=-90, created="2026-03-04T10:00:00"))
    monkeypatch.setattr(runner, "start", lambda mid: True)


client = TestClient(app, base_url="http://127.0.0.1:8765", headers={"Origin": "http://127.0.0.1:8765"})


def make(title="vs Karim", data=b"x" * 1000):
    return store.create_match(io.BytesIO(data), "IMG_1.mov", "net", title)


def test_upload_creates_match_and_redirects(monkeypatch):
    started = []
    monkeypatch.setattr(runner, "start", lambda mid: started.append(mid) or True)
    r = client.post("/matchs", files={"video": ("IMG_2665.mov", b"abc", "video/quicktime")},
                    data={"view": "net", "title": "vs Karim"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/matchs/2026-03-04-img-2665"
    assert (store.match_dir("2026-03-04-img-2665") / "match.json").exists()
    assert started == ["2026-03-04-img-2665"]


def test_upload_while_busy_says_so(monkeypatch):
    monkeypatch.setattr(runner, "start", lambda mid: False)
    r = client.post("/matchs", files={"video": ("a.mov", b"abc", "video/quicktime")}, data={"view": "net"})
    assert "Une analyse est déjà en cours. Celle-ci démarrera quand tu cliqueras sur Relancer." in r.text


def test_upload_bad_extension_shows_message():
    r = client.post("/matchs", files={"video": ("a.txt", b"abc", "text/plain")}, data={"view": "net"})
    assert r.status_code == 200 and "Format de vidéo non pris en charge" in r.text


def test_history_lists_title():
    make()
    r = client.get("/")
    assert "vs Karim" in r.text and "Vue filet" in r.text and '<html lang="fr">' in r.text


def test_status_json():
    m = make()
    assert client.get(f"/matchs/{m.id}/statut").json() == {"status": "pending", "progress": 0.0, "error": None}


def test_failed_page_has_relaunch_button():
    m = make()
    m.status, m.error = "failed", "boom"
    store.save(m)
    r = client.get(f"/matchs/{m.id}")
    assert "Relancer" in r.text and "boom" in r.text


def test_running_and_done_pages(monkeypatch):
    m = make()
    m.status = "running"
    store.save(m)
    monkeypatch.setattr(runner, "running_id", m.id)
    assert "Analyse en cours" in client.get(f"/matchs/{m.id}").text
    monkeypatch.setattr(runner, "running_id", None)
    m.status = "done"
    store.save(m)
    assert "Vue d'ensemble" in client.get(f"/matchs/{m.id}").text


def test_relaunch_redirects(monkeypatch):
    m = make()
    started = []
    monkeypatch.setattr(runner, "start", lambda mid: started.append(mid) or True)
    r = client.post(f"/matchs/{m.id}/relancer", follow_redirects=False)
    assert r.status_code == 303 and started == [m.id]


def test_settings_roundtrip():
    r = client.post("/reglages", data={"handedness": "left", "backhand_hands": "1"}, follow_redirects=False)
    assert r.status_code == 303
    s = store.load_settings()
    assert s.handedness == "left" and s.backhand_hands == 1
    assert client.get("/reglages").status_code == 200


def test_video_range_request():
    m = make(data=bytes(range(256)) * 4)
    r = client.get(f"/matchs/{m.id}/video", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100
    assert r.headers["content-range"] == "bytes 0-99/1024" and r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "video/quicktime"


def test_invalid_or_unknown_id_is_404():
    for path in ("/matchs/..%2Fx", "/matchs/nope", "/matchs/2026-01-01-zz", "/matchs/nope/video", "/matchs/nope/statut"):
        assert client.get(path).status_code == 404
    assert client.post("/matchs/nope/relancer").status_code == 404


def test_server_binds_localhost(monkeypatch):
    calls = []
    monkeypatch.setattr(entry.uvicorn, "run", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(entry, "recover_interrupted", lambda: calls.append("recovered"))
    entry.main()
    assert calls[0] == "recovered" and calls[1]["host"] == "127.0.0.1"


def test_cross_origin_post_is_refused():
    for headers in ({"Origin": "http://evil.example"}, {"Origin": "", "Referer": "http://evil.example/"}, {"Origin": ""}):
        assert client.post("/reglages", data={"handedness": "left", "backhand_hands": "1"}, headers=headers).status_code == 403
    assert not (store._root() / "settings.json").exists()
    ok = client.post("/reglages", data={"handedness": "left", "backhand_hands": "1"},
                     headers={"Origin": "", "Referer": "http://localhost:8765/reglages"}, follow_redirects=False)
    assert ok.status_code == 303


def test_foreign_host_is_refused():
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_unreadable_video_shows_message(monkeypatch):
    def boom(p):
        raise RuntimeError("ffprobe failed")
    monkeypatch.setattr(store, "probe", boom)
    r = client.post("/matchs", files={"video": ("a.mov", b"garbage", "video/quicktime")}, data={"view": "net"})
    assert r.status_code == 200 and "Ce fichier n&#39;est pas une vidéo lisible." in r.text


def test_relaunch_while_busy_says_so(monkeypatch):
    m = make()
    monkeypatch.setattr(runner, "start", lambda mid: False)
    r = client.post(f"/matchs/{m.id}/relancer", follow_redirects=False)
    assert r.headers["location"] == f"/matchs/{m.id}?attente=1"


def test_title_is_escaped():
    make(title="<script>x</script>")
    assert "<script>x</script>" not in client.get("/").text


def test_runner_is_truth_for_running(monkeypatch):
    m = make()  # match.json still says pending: the analysis thread has not saved yet
    monkeypatch.setattr(runner, "running_id", m.id)
    assert "Analyse en cours" in client.get(f"/matchs/{m.id}").text
    assert client.get(f"/matchs/{m.id}/statut").json()["status"] == "running"


def test_stuck_running_shows_interrupted(monkeypatch):
    m = make()
    m.status = "running"  # final save failed: no runner is working on it
    store.save(m)
    monkeypatch.setattr(runner, "running_id", None)
    r = client.get(f"/matchs/{m.id}")
    assert "Analyse interrompue" in r.text and "Relancer" in r.text
    assert client.get(f"/matchs/{m.id}/statut").json()["status"] == "failed"


def test_unexpected_import_error_is_french(monkeypatch):
    def boom(*a):
        raise ValueError("1 validation error for Match")
    monkeypatch.setattr(store, "create_match", boom)
    r = client.post("/matchs", files={"video": ("a.mov", b"abc", "video/quicktime")}, data={"view": "net"})
    assert "validation error" not in r.text and "Ce fichier n&#39;est pas une vidéo lisible." in r.text


def done(**kw):
    m = make()
    m.status = "done"
    for k, v in kw.items():
        setattr(m, k, v)
    store.save(m)
    return client.get(f"/matchs/{m.id}").text


def test_every_stroke_can_be_rewatched():
    assert 'data-t="12.5"' in done(strokes=[Stroke(t=12.5, frame=375, kind="forehand")])


def test_low_coverage_notice():
    assert "Tu n'as été repéré que sur 40 % de la vidéo" in done(coverage=0.4)
    assert "repéré que sur" not in done(coverage=0.9)


def test_unmeasured_strokes_replace_no_defect_sentence():
    strokes = [Stroke(t=i, frame=i * 30, kind="forehand") for i in range(4)]
    text = done(strokes=strokes, n_unmeasured=3)
    assert "ne permet pas de mesurer ta technique" in text and "Aucun défaut" not in text
    assert "Aucun défaut" in done(strokes=strokes, n_unmeasured=1)
