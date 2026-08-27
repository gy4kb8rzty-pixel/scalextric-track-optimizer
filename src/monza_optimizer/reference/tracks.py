"""Track profile registry for real circuits.

Profiles are centreline polylines in metres (or mm). They can be scaled to
match a Scalextric inventory path length for optimization.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Package-relative data directory (repo data/tracks)
_DATA = Path(__file__).resolve().parents[3] / "data" / "tracks"


@dataclass
class TrackProfile:
    id: str
    name: str
    official_length_m: float
    points_m: list[tuple[float, float]]  # metres, closed or open
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
    """Load x,y columns; unit_scale converts file units to metres."""
    pts: list[tuple[float, float]] = []
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                x, y = float(row[0]), float(row[1])
            except ValueError:
                continue
            pts.append((x * unit_scale, y * unit_scale))
    return pts


def list_tracks() -> list[dict]:
    """Available track ids and metadata (for Lovable UI pickers)."""
    catalog = [
        {
            "id": "monza",
            "name": "Autodromo Nazionale Monza",
            "official_length_m": 5793.0,
            "file": "monza_centerline_m.csv",
            "unit": "m",
        },
        {
            "id": "silverstone",
            "name": "Silverstone Circuit",
            "official_length_m": 5891.0,
            "file": "silverstone_centerline_mm.csv",
            "unit": "mm",
        },
        {
            "id": "monaco",
            "name": "Circuit de Monaco",
            "official_length_m": 3337.0,
            "file": "monaco_centerline_mm.json",
            "unit": "mm",
        },
        {
            "id": "nordschleife",
            "name": "Nürburgring Nordschleife",
            "official_length_m": 20832.0,
            "file": "nordschleife_outline_mm.json",
            "unit": "mm",
        },
        {
            "id": "charlotte_roval",
            "name": "Charlotte Roval",
            "official_length_m": 3700.0,
            "file": "charlotte_roval_centerline_mm.json",
            "unit": "mm",
        },
    ]
    out = []
    for t in catalog:
        path = _DATA / t["file"]
        out.append({**t, "available": path.exists()})
    return out


def load_track_centreline(track_id: str) -> TrackProfile:
    """Load a named track centreline as a TrackProfile (metres)."""
    meta = {t["id"]: t for t in list_tracks()}
    if track_id not in meta:
        raise KeyError(f"Unknown track_id={track_id!r}. Known: {list(meta)}")
    t = meta[track_id]
    path = _DATA / t["file"]
    if not path.exists():
        raise FileNotFoundError(
            f"Track data missing: {path}. Add centreline CSV/JSON under data/tracks/."
        )
    unit = t["unit"]
    if path.suffix.lower() == ".csv":
        scale = 1.0 if unit == "m" else 0.001
        pts = _load_csv_xy(path, unit_scale=scale)
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
    """Scale polyline so path length equals target_length_mm; origin at first point."""
    pts = list(points_m)
    if close and pts and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1e-6:
        pts = pts + [pts[0]]
    length_m = sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    if length_m < 1e-9:
        return [(0.0, 0.0)]
    # metres -> mm, then scale to target
    factor = (target_length_mm / 1000.0) / length_m
    scaled = [(x * factor * 1000.0, y * factor * 1000.0) for x, y in pts]
    sx, sy = scaled[0]
    return [(x - sx, y - sy) for x, y in scaled]
