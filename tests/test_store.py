import io
import os

import pytest

from ace import store
from ace.domain import Settings, Stroke, VideoInfo


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ACE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "probe", lambda p: VideoInfo(
        width=1116, height=1986, fps=30, duration_s=1, n_frames=30, rotation=-90, created="2026-03-04T10:00:00"))


def test_create_and_load_match():
    m = store.create_match(io.BytesIO(b"x" * 10), "IMG_2665.mov", "net", "vs Karim")
    assert m.id == "2026-03-04-img-2665"
    assert store.load(m.id).title == "vs Karim"
    assert (store.match_dir(m.id) / m.video_file).read_bytes() == b"x" * 10


def test_same_video_reuses_id_and_resets():
    m = store.create_match(io.BytesIO(b"a"), "IMG_2665.mov", "net", "t")
    m.status, m.strokes = "done", [Stroke(t=1, frame=3, kind="serve")]
    store.save(m)
    m2 = store.create_match(io.BytesIO(b"b"), "IMG_2665.mov", "net", "t")
    assert m2.id == m.id and m2.status == "pending" and m2.strokes == []
    assert (store.match_dir(m.id) / m2.video_file).read_bytes() == b"b"


def test_list_sorted_recent_first():
    a = store.create_match(io.BytesIO(b"a"), "a.mov", "net", "a")
    b = store.create_match(io.BytesIO(b"b"), "b.mov", "net", "b")
    os.utime(store.match_dir(a.id) / "match.json", (1, 1))
    assert [m.id for m in store.list_matches()] == [b.id, a.id]


def test_settings_default_and_roundtrip():
    assert store.load_settings() == Settings()
    store.save_settings(Settings(handedness="left", backhand_hands=1))
    assert store.load_settings().handedness == "left"


def test_large_upload_streamed():
    class Src(io.BytesIO):
        def read(self, n=-1):
            if n is None or n < 0:
                raise AssertionError("read() without size")
            return super().read(n)

    store.create_match(Src(b"x" * 100), "big.mov", "rear", "")


def test_untrusted_inputs_stay_inside_data_dir(tmp_path, monkeypatch):
    base = store.probe
    monkeypatch.setattr(store, "probe", lambda p: base(p).model_copy(update={"created": "../../etc"}))
    m = store.create_match(io.BytesIO(b"x"), "../../evil.mov", "net", "")
    assert store.ID_RE.fullmatch(m.id) and m.id.endswith("-evil")
    assert m.video_file == "video.mov"
    assert store.match_dir(m.id).is_relative_to(tmp_path.resolve())
    assert not (tmp_path.parent.parent / "evil.mov").exists()


def test_load_rejects_traversal():
    for bad in ("../x", "..", "2026-03-04-../x"):
        with pytest.raises(ValueError):
            store.load(bad)


def test_concurrent_imports_keep_own_content():
    import threading
    ms = {}

    def go(n):
        ms[n] = store.create_match(io.BytesIO(n.encode() * 1000), f"{n}.mov", "net", "")

    ts = [threading.Thread(target=go, args=(n,)) for n in ("a", "b", "c")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    for n, m in ms.items():
        assert (store.match_dir(m.id) / m.video_file).read_bytes() == n.encode() * 1000


def test_import_of_running_match_refused():
    m = store.create_match(io.BytesIO(b"a"), "a.mov", "net", "")
    m.status = "running"
    store.save(m)
    with pytest.raises(ValueError, match="en cours d'analyse"):
        store.create_match(io.BytesIO(b"b"), "a.mov", "net", "")
    assert (store.match_dir(m.id) / m.video_file).read_bytes() == b"a"


def test_concurrent_saves_never_raise():
    import threading
    m = store.create_match(io.BytesIO(b"a"), "a.mov", "net", "")
    errs = []

    def go():
        try:
            for _ in range(50):
                store.save(m)
        except Exception as e:
            errs.append(e)

    ts = [threading.Thread(target=go) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errs == []
