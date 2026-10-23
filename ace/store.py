import filecmp
import json
import os
import re
import shutil
import tempfile
import threading
from datetime import date
from pathlib import Path
from typing import BinaryIO

from ace.domain import Match, Settings, View
from ace.notes import Note
from ace.video import probe

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # overridden at call time by ACE_DATA_DIR


class UserError(ValueError):
    """A French message meant for the user (other exceptions never reach the UI as text)."""


_lock = threading.RLock()  # serialises match.json writes and re-imports


def _root() -> Path:
    return Path(os.environ.get("ACE_DATA_DIR") or DATA_DIR)


ID_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9a-z-]+")
VIDEO_EXTS = {".mov", ".mp4", ".m4v"}


def match_dir(id: str) -> Path:
    if not ID_RE.fullmatch(id):
        raise UserError(f"identifiant de match invalide : {id!r}")
    base = (_root() / "matchs").resolve()
    d = (base / id).resolve()
    if not d.is_relative_to(base):
        raise UserError(f"identifiant de match invalide : {id!r}")
    return d


def pose_path(id: str) -> Path:
    return match_dir(id) / "pose.npz"


def _write_atomic(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, suffix=".tmp", delete=False) as f:
        f.write(text)
    os.replace(f.name, path)


def save(m: Match) -> None:
    with _lock:
        _write_atomic(match_dir(m.id) / "match.json", m.model_dump_json(indent=1))


def load(id: str) -> Match:
    return Match.model_validate_json((match_dir(id) / "match.json").read_text())


def list_matches() -> list[Match]:
    files = sorted((_root() / "matchs").glob("*/match.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    out = []
    for f in files:
        try:
            out.append(Match.model_validate_json(f.read_text()))
        except (OSError, ValueError):  # unreadable match.json: skip, don't hide the others
            continue
    return out


def save_notes(id: str, notes: list) -> None:
    _write_atomic(match_dir(id) / "notes.json", json.dumps([n.model_dump() for n in notes]))


def load_notes(id: str) -> list | None:
    f = match_dir(id) / "notes.json"
    return [Note.model_validate(n) for n in json.loads(f.read_text())] if f.exists() else None


def load_settings() -> Settings:
    f = _root() / "settings.json"
    return Settings.model_validate_json(f.read_text()) if f.exists() else Settings()


def save_settings(s: Settings) -> None:
    _root().mkdir(parents=True, exist_ok=True)
    _write_atomic(_root() / "settings.json", s.model_dump_json(indent=1))


def clear_incoming() -> None:
    """Remove uploads left half-written by an app that was closed mid-import."""
    for f in (_root() / "incoming").glob("*"):
        f.unlink(missing_ok=True)


def create_match(src: BinaryIO, filename: str, view: View, title: str) -> Match:
    """Stream the upload to disk, probe it, and (re)create the match; a re-import resets the analysis."""
    ext = Path(filename).suffix.lower()
    if ext not in VIDEO_EXTS:
        raise UserError("Format de vidéo non pris en charge (.mov, .mp4, .m4v).")
    name = "video" + ext  # never the raw upload name
    tmp_dir = _root() / "incoming"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=tmp_dir, suffix=ext)  # unique per call
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as out:
            shutil.copyfileobj(src, out, 1024 * 1024)
        info = probe(tmp)
        created = (info.created or "")[:10]
        day = created if re.fullmatch(r"\d{4}-\d{2}-\d{2}", created) else date.today().isoformat()
        slug = re.sub(r"[^0-9a-z]+", "-", Path(filename).stem.lower())[:60].strip("-") or "match"
        id = f"{day}-{slug}"
        with _lock:
            d = match_dir(id)
            d.mkdir(parents=True, exist_ok=True)
            try:
                old = load(id)
            except (OSError, ValueError):  # new match, or unreadable match.json: a re-import repairs it
                old = None
            if old and old.status == "running":
                raise UserError("Ce match est en cours d'analyse.")
            old_video = d / old.video_file if old else None
            if not (old_video and old_video.is_file() and filecmp.cmp(tmp, old_video, shallow=False)):
                (d / "notes.json").unlink(missing_ok=True)  # notes belong to the old video
            if old_video and old_video.name != name:
                old_video.unlink(missing_ok=True)
            shutil.move(tmp, d / name)
            pose_path(id).unlink(missing_ok=True)
            m = Match(id=id, title=title, view=view, video_file=name, info=info, settings=load_settings())
            save(m)
    finally:
        tmp.unlink(missing_ok=True)
    return m
