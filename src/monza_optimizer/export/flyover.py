"""Offline F1 D-level flyover catalog served as static URLs."""
from __future__ import annotations

import os
from pathlib import Path

LEVEL = "D"
SERIES = "f1"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def flyover_dir() -> Path:
    override = os.environ.get("FLYOVER_DIR")
    if override:
        return Path(override)
    return repo_root() / "static" / "flyovers"


def filename(track_id: str, level: str = LEVEL) -> str:
    tid = str(track_id or "").strip().lower()
    return f"{tid}_{str(level).upper()}.mp4"


def local_path(track_id: str, level: str = LEVEL) -> Path:
    return flyover_dir() / filename(track_id, level)


def exists(track_id: str, level: str = LEVEL) -> bool:
    return local_path(track_id, level).is_file()


def public_base() -> str:
    env = os.environ.get("FLYOVER_PUBLIC_BASE")
    if env:
        return env.rstrip("/")
    api = os.environ.get("PUBLIC_API_BASE", "https://scalextric-track-optimizer.onrender.com").rstrip("/")
    return api + "/static/flyovers"


def public_url(track_id: str, level: str = LEVEL) -> str | None:
    if not exists(track_id, level):
        return None
    return f"{public_base()}/{filename(track_id, level)}"


def list_available() -> list[dict]:
    out = []
    folder = flyover_dir()
    if not folder.is_dir():
        return out
    for p in sorted(folder.glob("*_D.mp4")):
        stem = p.stem
        if not stem.endswith("_D"):
            continue
        tid = stem[:-2]
        out.append({
            "track_id": tid,
            "accuracy_level": "D",
            "series": SERIES,
            "filename": p.name,
            "url": f"{public_base()}/{p.name}",
            "bytes": p.stat().st_size,
        })
    return out


def attach_to_track(row: dict) -> dict:
    if (row.get("series") or "").lower() != SERIES:
        return row
    url = public_url(row.get("id") or "", "D")
    if url:
        row["flyover_mp4_url"] = url
        row["flyover_level"] = "D"
    return row
