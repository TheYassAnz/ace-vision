import os
import re
import shutil
from datetime import date
from pathlib import Path
from typing import BinaryIO

from ace.domain import Match, Settings, View
from ace.video import probe

DATA_DIR = Path("data")  # overridden at call time by ACE_DATA_DIR


def _root() -> Path:
    return Path(os.environ.get("ACE_DATA_DIR") or DATA_DIR)


def match_dir(id: str) -> Path:
    return _root() / "matchs" / id


def pose_path(id: str) -> Path:
    return match_dir(id) / "pose.npz"


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def save(m: Match) -> None:
    _write_atomic(match_dir(m.id) / "match.json", m.model_dump_json(indent=1))


def load(id: str) -> Match:
    return Match.model_validate_json((match_dir(id) / "match.json").read_text())


def list_matches() -> list[Match]:
    files = sorted((_root() / "matchs").glob("*/match.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [Match.model_validate_json(f.read_text()) for f in files]


def load_settings() -> Settings:
    f = _root() / "settings.json"
    return Settings.model_validate_json(f.read_text()) if f.exists() else Settings()


def save_settings(s: Settings) -> None:
    _root().mkdir(parents=True, exist_ok=True)
    _write_atomic(_root() / "settings.json", s.model_dump_json(indent=1))


def create_match(src: BinaryIO, filename: str, view: View, title: str) -> Match:
    """Stream the upload to disk, probe it, and (re)create the match; a re-import resets the analysis."""
    name = Path(filename).name
    tmp_dir = _root() / "incoming"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / name
    with tmp.open("wb") as out:
        shutil.copyfileobj(src, out, 1024 * 1024)
    try:
        info = probe(tmp)
        slug = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-") or "match"
        id = f"{(info.created or date.today().isoformat())[:10]}-{slug}"
        match_dir(id).mkdir(parents=True, exist_ok=True)
        shutil.move(tmp, match_dir(id) / name)
    finally:
        tmp.unlink(missing_ok=True)
    pose_path(id).unlink(missing_ok=True)
    m = Match(id=id, title=title, view=view, video_file=name, info=info, settings=load_settings())
    save(m)
    return m
