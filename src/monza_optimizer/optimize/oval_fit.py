"""NASCAR oval fitter: two long straights + two 180 large-radius ends.

Ignores centreline noise on the sides so Kansas/Bristol cannot sawtooth.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.path import compute_track_path, path_length
from monza_optimizer.geometry.pose import Pose
from monza_optimizer.optimize.accuracy_levels import may_place
from monza_optimizer.reference import list_tracks

OVAL_IDS = {
    "bristol", "kansas", "daytona", "talladega", "michigan", "atlanta",
    "texas", "las_vegas_nascar", "homestead", "kentucky", "chicagoland",
    "fontana", "pocono", "indianapolis", "nashville", "richmond",
    "martinsville", "phoenix", "dover", "new_hampshire", "iowa",
    "world_wide_technology", "wwt", "gateway_oval", "nashville_superspeedway",
}

STRAIGHTS = ("C8205", "C8207", "C8200", "C8236")


def is_nascar_oval(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower()
    if not tid or "roval" in tid:
        return False
    if tid in OVAL_IDS:
        return True
    try:
        row = next((r for r in list_tracks() if r.get("id") == tid), None)
    except Exception:
        row = None
    if not row:
        return False
    series = str(row.get("series") or "").lower()
    kind = str(row.get("kind") or "").lower()
    if "nascar" not in series:
        return False
    if any(k in kind for k in ("road", "roval", "street")):
        return False
    if kind in {"oval", "superspeedway", "short_track", "speedway", ""}:
        return True
    name = str(row.get("name") or "").lower()
    return "speedway" in name and "roval" not in name


@dataclass
class OvalResult:
    sequence: list
    metrics: dict = field(default_factory=dict)


def _straight_pack(length_mm: float, get_part) -> list[str]:
    sizes = []
    for code in STRAIGHTS:
        part = get_part(code)
        if part is None or not isinstance(part.geometry, StraightGeometry):
            continue
        sizes.append((float(part.geometry.length), code))
    sizes.sort(reverse=True)
    if not sizes:
        return ["C8205"] * max(2, int(length_mm / 350))
    out = []
    left = max(length_mm, sizes[-1][0])
    for ln, code in sizes:
        n = int(left // ln)
        out.extend([code] * n)
        left -= n * ln
    if left > 40 and sizes:
        out.append(sizes[-1][1])
    return out or [sizes[0][1], sizes[0][1]]


def _end_pack(get_part) -> list[str]:
    options = []
    for code in ("C8235L", "C8204L", "C8206L", "C187L", "C8234L"):
        part = get_part(code)
        if part is None or not isinstance(part.geometry, CurveGeometry):
            continue
        ang = abs(float(part.geometry.angle_degrees))
        if ang < 10:
            continue
        options.append((float(part.geometry.radius), ang, code))
    options.sort(reverse=True)
    if not options:
        return ["C8235L"] * 8
    _r, ang, code = options[0]
    n = max(4, int(round(180.0 / ang)))
    return [code] * n


def oval_follow(cl, get_part, avail=None, shop=None, profile=None) -> OvalResult:
    pts = list(getattr(cl, "points", []) or [])
    if len(pts) < 8:
        return OvalResult([], {"nascar_oval": False})
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    long_mm = max(w, h)
    short_mm = min(w, h)
    radius = max(short_mm * 0.40, 480.0)
    straight_mm = max(long_mm - 2.0 * radius, 800.0)
    side = _straight_pack(straight_mm, get_part)
    end = _end_pack(get_part)
    seq = list(side) + list(end) + list(side) + list(end)
    if shop is not None or avail:
        used = Counter()
        avail = avail or {}
        kept = []
        for code in seq:
            ok = True
            if shop is not None:
                ok = may_place(code, used, avail, shop)
            elif used[base_id(code)] >= avail.get(base_id(code), 999):
                ok = False
            if not ok:
                continue
            kept.append(code)
            used[base_id(code)] += 1
        if len(kept) >= 20:
            seq = kept
    start = Pose(float(pts[0][0]), float(pts[0][1]), 0.0)
    try:
        start = Pose(float(pts[0][0]), float(pts[0][1]), float(cl.heading(0)))
    except Exception:
        pass
    built = path_length([get_part(c) for c in seq if get_part(c)]) if seq else 0.0
    poses = compute_track_path([get_part(c) for c in seq if get_part(c)], start=start) if seq else [start]
    end_p = poses[-1]
    pos = math.hypot(end_p.x - start.x, end_p.y - start.y)
    metrics = {
        "nascar_oval": True,
        "n_pieces": len(seq),
        "length_mm": built,
        "pos_mm": pos,
        "straight_mm": straight_mm,
        "end_pieces": len(end),
        "side_pieces": len(side),
    }
    return OvalResult(seq, metrics)
