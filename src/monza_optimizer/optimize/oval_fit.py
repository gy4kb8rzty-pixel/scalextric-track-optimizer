"""NASCAR oval: shrink the red guide to Sport R4, then lay two straights + two 180 R4 ends."""
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
    "homestead_miami",
}

STRAIGHTS = ("C8205", "C8207", "C8200", "C8236")
R4_CODES = ("C8235L", "C8235R", "C8235")
DEFAULT_R4_MM = 454.0


def is_nascar_oval(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower().replace("-", "_")
    if not tid or "roval" in tid:
        return False
    if tid in OVAL_IDS or tid.startswith("homestead"):
        return True
    try:
        row = next((r for r in list_tracks() if str(r.get("id") or "").lower().replace("-", "_") == tid), None)
    except Exception:
        row = None
    if not row:
        return False
    series = str(row.get("series") or "").lower()
    kind = str(row.get("kind") or "").lower()
    name = str(row.get("name") or "").lower()
    if "roval" in name or "roval" in kind:
        return False
    if "homestead" in name or tid in OVAL_IDS:
        return True
    if "nascar" not in series:
        return False
    if any(k in kind for k in ("road", "street")):
        return False
    return kind in {"oval", "superspeedway", "short_track", "speedway", ""} or "speedway" in name


def r4_radius_mm(get_part) -> float:
    for code in R4_CODES:
        try:
            part = get_part(code)
        except Exception:
            part = None
        if part is not None and isinstance(getattr(part, "geometry", None), CurveGeometry):
            r = float(part.geometry.radius)
            if r > 50:
                return r
    return DEFAULT_R4_MM


def r4_angle_deg(get_part) -> float:
    for code in R4_CODES:
        try:
            part = get_part(code)
        except Exception:
            part = None
        if part is not None and isinstance(getattr(part, "geometry", None), CurveGeometry):
            return abs(float(part.geometry.angle_degrees)) or 22.5
    return 22.5


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def scale_guide_to_r4(points, get_part):
    pts = [(float(x), float(y)) for x, y in (points or [])]
    if len(pts) < 4:
        return pts, 1.0
    minx, miny, maxx, maxy = _bbox(pts)
    w, h = maxx - minx, maxy - miny
    short = min(w, h)
    if short < 1:
        return pts, 1.0
    r4 = r4_radius_mm(get_part)
    factor = (2.0 * r4) / short
    cx = (minx + maxx) * 0.5
    cy = (miny + maxy) * 0.5
    out = [((x - cx) * factor, (y - cy) * factor) for x, y in pts]
    return out, factor


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
        return ["C8205"] * max(2, int(max(length_mm, 700) / 350))
    out = []
    left = max(length_mm, sizes[-1][0])
    for ln, code in sizes:
        n = int(left // ln)
        out.extend([code] * n)
        left -= n * ln
    if left > 50 and sizes:
        best = min(sizes, key=lambda t: abs(t[0] - left))
        out.append(best[1])
    return out or [sizes[0][1], sizes[0][1]]


def _end_pack(get_part) -> list[str]:
    ang = r4_angle_deg(get_part)
    n = max(4, int(round(180.0 / max(ang, 10.0))))
    code = "C8235L"
    try:
        if get_part("C8235L") is None:
            code = "C8235R"
    except Exception:
        pass
    return [code] * n


def oval_follow(cl, get_part, avail=None, shop=None, profile=None) -> OvalResult:
    pts = list(getattr(cl, "points", []) or [])
    if len(pts) < 8:
        return OvalResult([], {"nascar_oval": False})
    r4 = r4_radius_mm(get_part)
    minx, miny, maxx, maxy = _bbox(pts)
    w, h = maxx - minx, maxy - miny
    long_mm = max(w, h)
    straight_mm = max(long_mm - 2.0 * r4, 700.0)
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
        if len(kept) >= 16:
            seq = kept
    heading0 = 0.0 if w >= h else 90.0
    start = Pose(float(pts[0][0]), float(pts[0][1]), heading0)
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
        "r4_mm": r4,
        "end_pieces": len(end),
        "side_pieces": len(side),
        "guide_scaled_to_r4": True,
    }
    return OvalResult(seq, metrics)
