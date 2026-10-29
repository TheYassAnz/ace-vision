import json
import os
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from ace import store
from ace.domain import Finding, Score, Stroke, VideoInfo
from ace.jobs import runner
from ace.web.app import app

FIXTURE = Path(__file__).parent.parent / "app/ACEVisionTests/Fixtures/match.json"


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ACE_TOKEN", "t")
    monkeypatch.setattr(store, "probe", lambda p: VideoInfo(
        width=1116, height=1986, fps=30, duration_s=75, n_frames=30, rotation=-90, created="2026-03-04T10:00:00"))
    monkeypatch.setattr(runner, "start", lambda mid: True)


client = TestClient(app, base_url="http://127.0.0.1", headers={"Authorization": "Bearer t"})
UNREADABLE = "Ce fichier n'est pas une vidéo lisible."


def make(title="vs Karim", data=b"x" * 1000):
    import io
    return store.create_match(io.BytesIO(data), "IMG_1.mov", "net", title)


def test_request_without_token_is_401():
    assert TestClient(app, base_url="http://127.0.0.1").get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer faux"}).status_code == 401
    assert client.get("/health").json() == {"ok": True}


def test_import_by_path(tmp_path):
    src = tmp_path / "IMG_2665.mov"
    src.write_bytes(b"abc")
    r = client.post("/matchs", json={"path": str(src), "view": "net", "title": "vs Karim"})
    assert r.status_code == 201 and r.json()["match"]["id"] == "2026-03-04-img-2665" and r.json()["queued"] is False
    assert src.exists()  # the original is copied, never moved


def test_import_while_busy_is_queued(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "start", lambda mid: False)
    src = tmp_path / "a.mov"
    src.write_bytes(b"abc")
    r = client.post("/matchs", json={"path": str(src), "view": "net", "title": ""})
    assert r.status_code == 201 and r.json()["queued"] is True


def test_import_missing_file_is_422(tmp_path):
    r = client.post("/matchs", json={"path": str(tmp_path / "absent.mov"), "view": "net", "title": ""})
    assert r.status_code == 422 and r.json()["detail"] == "Fichier introuvable."


def test_import_bad_extension_is_422(tmp_path):
    src = tmp_path / "a.txt"
    src.write_bytes(b"abc")
    r = client.post("/matchs", json={"path": str(src), "view": "net", "title": ""})
    assert r.status_code == 422 and "Format de vidéo non pris en charge" in r.json()["detail"]


def test_unreadable_video_is_422(monkeypatch, tmp_path):
    def boom(p):
        raise RuntimeError("ffprobe failed")
    monkeypatch.setattr(store, "probe", boom)
    src = tmp_path / "a.mov"
    src.write_bytes(b"garbage")
    r = client.post("/matchs", json={"path": str(src), "view": "net", "title": ""})
    assert r.status_code == 422 and r.json()["detail"] == UNREADABLE


def test_unexpected_import_error_is_french(monkeypatch, tmp_path):
    def boom(*a):
        raise ValueError("1 validation error for Match")
    monkeypatch.setattr(store, "create_match", boom)
    src = tmp_path / "a.mov"
    src.write_bytes(b"abc")
    r = client.post("/matchs", json={"path": str(src), "view": "net", "title": ""})
    assert "validation error" not in r.text and r.json()["detail"] == UNREADABLE


def test_list_matches():
    m = make()
    [row] = client.get("/matchs").json()
    assert row["id"] == m.id and row["title"] == "vs Karim" and row["status"] == "pending"
    assert row["created"] == "2026-03-04T10:00:00" and row["duration_s"] == 75 and row["score"] is None


def test_status_in_match_json():
    m = make()
    r = client.get(f"/matchs/{m.id}").json()
    assert (r["status"], r["progress"], r["error"]) == ("pending", 0.0, None)


def test_settings_roundtrip():
    assert client.get("/reglages").json() == {"handedness": "right", "backhand_hands": 2}
    r = client.put("/reglages", json={"handedness": "left", "backhand_hands": 1})
    assert r.status_code == 200 and r.json() == {"handedness": "left", "backhand_hands": 1}
    s = store.load_settings()
    assert s.handedness == "left" and s.backhand_hands == 1
    assert client.put("/reglages", json={"handedness": "x", "backhand_hands": 1}).status_code == 422


def test_invalid_or_unknown_id_is_404():
    for path in ("/matchs/..%2Fx", "/matchs/nope", "/matchs/2026-01-01-zz", "/matchs/nope/notes"):
        assert client.get(path).status_code == 404
    assert client.post("/matchs/nope/relancer").status_code == 404
    assert client.delete("/matchs/nope").status_code == 404


def test_foreign_host_is_refused():
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400


def test_relaunch():
    m = make()
    assert client.post(f"/matchs/{m.id}/relancer").json() == {"queued": False}


def test_relaunch_while_busy_is_queued(monkeypatch):
    m = make()
    monkeypatch.setattr(runner, "start", lambda mid: False)
    assert client.post(f"/matchs/{m.id}/relancer").json() == {"queued": True}


def test_stop(monkeypatch):
    m = make()
    assert client.post("/matchs/nope/arreter").status_code == 404
    assert client.post(f"/matchs/{m.id}/arreter").status_code == 409
    monkeypatch.setattr(runner, "running_id", m.id)
    assert client.post(f"/matchs/{m.id}/arreter").status_code == 202
    runner._stop.clear()


def test_runner_is_truth_for_running(monkeypatch):
    m = make()  # match.json still says pending: the analysis thread has not saved yet
    monkeypatch.setattr(runner, "running_id", m.id)
    assert client.get(f"/matchs/{m.id}").json()["status"] == "running"
    assert client.get("/matchs").json()[0]["status"] == "running"


def test_stuck_running_shows_interrupted(monkeypatch):
    m = make()
    m.status = "running"  # final save failed: no runner is working on it
    store.save(m)
    monkeypatch.setattr(runner, "running_id", None)
    r = client.get(f"/matchs/{m.id}").json()
    assert r["status"] == "failed" and r["error"] == "Analyse interrompue."


def test_delete_match():
    m = make()
    assert client.delete(f"/matchs/{m.id}").status_code == 204
    assert not store.match_dir(m.id).exists() and client.get(f"/matchs/{m.id}").status_code == 404


def test_delete_running_is_409(monkeypatch):
    m = make()
    monkeypatch.setattr(runner, "running_id", m.id)
    r = client.delete(f"/matchs/{m.id}")
    assert r.status_code == 409 and r.json()["detail"] == "Ce match est en cours d'analyse." and store.match_dir(m.id).exists()


def test_delete_stuck_running_on_disk_is_409():
    m = make()
    m.status = "running"
    store.save(m)
    assert client.delete(f"/matchs/{m.id}").status_code == 409 and store.match_dir(m.id).exists()


def test_match_json_is_strict():
    m = make()
    m.status = "done"
    m.strokes = [Stroke(t=1, frame=30, kind="forehand", metrics={"stance_ratio": float("nan")})]
    store.save(m)
    body = client.get(f"/matchs/{m.id}").text
    json.loads(body, parse_constant=lambda c: pytest.fail(c))
    assert "metrics" not in json.loads(body)["strokes"][0]


def test_defect_rates_in_summary():
    m = make()
    m.status = "done"
    m.strokes = [Stroke(t=i, frame=i, kind="forehand", defects=["late_prep"] if i < 3 else []) for i in range(4)]
    store.save(m)
    assert client.get("/matchs").json()[0]["defect_rates"] == [{"kind": "forehand", "defect": "late_prep", "rate": 0.75}]


def test_defect_rates_order():
    m = make()
    m.strokes = [Stroke(t=1, frame=1, kind="serve", defects=["narrow_stance"]),
                 Stroke(t=2, frame=2, kind="backhand", defects=["straight_legs", "late_prep"]),
                 Stroke(t=3, frame=3, kind="forehand", defects=["small_turn"])]
    assert [(r["kind"], r["defect"]) for r in store.defect_rates(m)] == [
        ("forehand", "small_turn"), ("backhand", "late_prep"), ("backhand", "straight_legs"), ("serve", "narrow_stance")]


def test_notes_roundtrip():
    m = make()
    m.status, m.strokes = "done", [Stroke(t=1, frame=30, kind="forehand")]
    store.save(m)
    assert client.get(f"/matchs/{m.id}/notes").json() == []
    r = client.post(f"/matchs/{m.id}/notes", json=[{"t": 1.1, "kind": "forehand"}, {"t": 9, "kind": "serve"}])
    assert r.status_code == 200 and r.json()["found_rate"] == 0.5
    assert client.get(f"/matchs/{m.id}/notes").json()[0] == {"t": 1.1, "kind": "forehand"}


def test_api_fixture_matches_swift_fixture():  # contract with app/ACEVisionTests/Fixtures/match.json
    m = make()
    m.status = "done"
    m.strokes = [Stroke(t=1.5, frame=45, kind="forehand", defects=["late_prep"], metrics={"stance_ratio": float("nan")}),
                 Stroke(t=6.2, frame=186, kind="backhand", outcome="in", metrics={"stance_ratio": 1.1})]
    m.findings = [Finding(kind="forehand", defect="late_prep", count=1, total=1, title="Préparation tardive",
                          text="Prépare plus tôt.", drill="Raquette en arrière dès le rebond.", clip_times=[1.5])]
    m.score = Score(n_notes=2, n_detected=2, found_rate=1.0, class_rate=0.5, false_hits=0)
    store.save(m)
    got = client.get(f"/matchs/{m.id}").json()
    if os.environ.get("UPDATE_FIXTURES"):
        FIXTURE.write_text(json.dumps(got, indent=2, ensure_ascii=False) + "\n")
    assert got == json.loads(FIXTURE.read_text())


def test_server_prints_port_and_exits_when_stdin_closes(tmp_path):
    p = subprocess.Popen([sys.executable, "-m", "ace"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                         env={**os.environ, "ACE_TOKEN": "t", "ACE_DATA_DIR": str(tmp_path)})
    port = int(p.stdout.readline().split()[1])
    assert httpx.get(f"http://127.0.0.1:{port}/health", headers={"Authorization": "Bearer t"}).json() == {"ok": True}
    p.stdin.close()
    assert p.wait(timeout=10) == 0
    p.stdout.close()


def test_output_after_ready_goes_to_stderr():
    r = subprocess.run([sys.executable, "-c", "from ace.__main__ import announce; announce(1); print('plus tard')"],
                       capture_output=True, text=True, check=True)
    assert r.stdout == "ACE_READY 1\n"
    assert "plus tard" in r.stderr


def test_server_without_token_exits_2(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "ACE_TOKEN"}
    assert subprocess.run([sys.executable, "-m", "ace"], env={**env, "ACE_DATA_DIR": str(tmp_path)}, stdin=subprocess.DEVNULL).returncode == 2


def test_pose_is_float32_frames():
    import numpy as np
    m = make(); kp = np.full((3, 17, 3), 1.5); kp[1, 0, :2] = np.nan
    np.savez_compressed(store.pose_path(m.id), kp=kp)
    r = client.get(f"/matchs/{m.id}/pose")
    a = np.frombuffer(r.content, dtype="<f4").reshape(3, 17, 2)
    assert r.headers["content-type"] == "application/octet-stream" and a[0, 0, 0] == 1.5 and np.isnan(a[1, 0, 0])


def test_pose_missing_is_404():
    m = make()
    r = client.get(f"/matchs/{m.id}/pose")
    assert r.status_code == 404 and r.json()["detail"] == "Squelette indisponible : relance l'analyse."
