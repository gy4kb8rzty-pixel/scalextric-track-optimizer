"""Track profile registry for real circuits."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

_DATA = Path(__file__).resolve().parents[3] / "data" / "tracks"


@dataclass
class TrackProfile:
    id: str
    name: str
    official_length_m: float
    points_m: list[tuple[float, float]]
    source: str = ""
    notes: str = ""

    @property
    def length_m(self) -> float:
        pts = self.points_m
        if len(pts) < 2:
            return 0.0
        return sum(
            math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)
        )


def _load_csv_xy(path: Path, unit_scale: float = 1.0) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    with path.open(newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                pts.append((float(row[0]) * unit_scale, float(row[1]) * unit_scale))
            except ValueError:
                continue
    return pts


def _normalize_file(name: str | None) -> str | None:
    if not name:
        return None
    return Path(name).name


def list_tracks() -> list[dict]:
    idx_path = _DATA / "CIRCUITS_INDEX.json"
    if not idx_path.exists():
        return []
    raw = json.loads(idx_path.read_text())
    aliases = raw.get("aliases") or {}
    featured = set(raw.get("featured") or [])
    out = []
    for t in raw.get("circuits") or []:
        fn = _normalize_file(t.get("file"))
        out.append({
            "id": t["id"],
            "name": t.get("name", t["id"]),
            "official_length_m": float(t.get("official_length_m") or t.get("source_length_m") or 0),
            "file": fn,
            "unit": t.get("unit") or "mm",
            "series": t.get("series"),
            "kind": t.get("kind"),
            "calendar": t.get("calendar") or [],
            "featured": bool(t.get("featured") or t["id"] in featured),
            "available": bool(fn) and (_DATA / fn).exists() if fn else False,
            "quality": t.get("quality"),
            "note": t.get("note"),
        })
    for alias, target in aliases.items():
        if any(r["id"] == alias for r in out):
            continue
        src = next((r for r in out if r["id"] == target), None)
        if src:
            out.append({**src, "id": alias, "note": f"alias of {target}"})
    out.sort(key=lambda r: (not r.get("featured"), r.get("series") or "", r["name"]))
    return out


def load_track_centreline(track_id: str) -> TrackProfile:
    meta = {t["id"]: t for t in list_tracks()}
    if track_id not in meta:
        raise KeyError(f"Unknown track_id={track_id!r}. Known: {list(meta)}")
    t = meta[track_id]
    if not t.get("file"):
        raise FileNotFoundError(f"No centreline file for {track_id}")
    path = _DATA / t["file"]
    if not path.exists():
        raise FileNotFoundError(f"Track data missing: {path}")
    unit = t["unit"]
    if path.suffix.lower() == ".csv":
        pts = _load_csv_xy(path, unit_scale=1.0 if unit == "m" else 0.001)
    else:
        raw = json.loads(path.read_text())
        coords = raw.get("scaled") or raw.get("points") or raw.get("coordinates")
        if not coords:
            raise ValueError(f"No points in {path}")
        scale = 1.0 if unit == "m" else 0.001
        pts = [(float(c[0]) * scale, float(c[1]) * scale) for c in coords]
    return TrackProfile(
        id=track_id,
        name=t["name"],
        official_length_m=t["official_length_m"],
        points_m=pts,
        source=str(path.name),
    )


def scale_centreline(
    points_m: Sequence[tuple[float, float]],
    target_length_mm: float,
    *,
    close: bool = False,
) -> list[tuple[float, float]]:
    pts = list(points_m)
    if close and pts and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1e-6:
        pts = pts + [pts[0]]
    length_m = sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    if length_m < 1e-9:
        return [(0.0, 0.0)]
    factor = (target_length_mm / 1000.0) / length_m
    scaled = [(x * factor * 1000.0, y * factor * 1000.0) for x, y in pts]
    sx, sy = scaled[0]
    return [(x - sx, y - sy) for x, y in scaled]
