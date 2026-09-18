"""NASCAR oval: R4 stadium whose length/width matches the red guide."""
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


def _pca(pts):
    n = max(len(pts), 1)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    sxx = sxy = syy = 0.0
    for x, y in pts:
        dx, dy = x - cx, y - cy
        sxx += dx * dx
        sxy += dx * dy
        syy += dy * dy
    ang = 0.5 * math.atan2(2.0 * sxy, sxx - syy + 1e-12)
    c, s = math.cos(ang), math.sin(ang)
    us = []
    vs = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        us.append(dx * c + dy * s)
        vs.append(-dx * s + dy * c)
    length = max(us) - min(us) if us else 1.0
    width = max(vs) - min(vs) if vs else 1.0
    if width > length:
        length, width = width, length
        ang += math.pi / 2.0
    return cx, cy, math.degrees(ang), max(length, 1.0), max(width, 1.0)


def scale_guide_to_r4(points, get_part):
    pts = [(float(x), float(y)) for x, y in (points or [])]
    if len(pts) < 4:
        return pts, 1.0
    cx, cy, _ang, length, width = _pca(pts)
    r4 = r4_radius_mm(get_part)
    factor = (2.0 * r4) / max(width, 1.0)
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
        return ["C8205"] * max(2, int(max(length_mm, 350) / 350))
    out = []
    left = max(length_mm, 0.0)
    if left < sizes[-1][0] * 0.5:
        return [sizes[-1][1]]
    for ln, code in sizes:
        n = int(left // ln)
        out.extend([code] * n)
        left -= n * ln
    if left > 40 and sizes:
        best = min(sizes, key=lambda t: abs(t[0] - left))
        out.append(best[1])
    return out or [sizes[-1][1]]


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


def _rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def oval_follow(cl, get_part, avail=None, shop=None, profile=None) -> OvalResult:
    pts = list(getattr(cl, "points", []) or [])
    if len(pts) < 8:
        return OvalResult([], {"nascar_oval": False})
    r4 = r4_radius_mm(get_part)
    cx, cy, ang, length, width = _pca(pts)
    # After R4 scale, width ~= 2*R4. Straights carry the leftover length.
    straight_mm = max(length - 2.0 * r4, 0.0)
    side = _straight_pack(straight_mm, get_part)
    if not side:
        side = ["C8236"]
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
    # Place first straight on the major axis, offset by R4 on the minor axis.
    actual_straight = 0.0
    for code in side:
        part = get_part(code)
        if part is not None and isinstance(part.geometry, StraightGeometry):
            actual_straight += float(part.geometry.length)
    ox, oy = _rot(-actual_straight * 0.5, -r4, ang)
    start = Pose(cx + ox, cy + oy, ang)
    built = path_length([get_part(c) for c in seq if get_part(c)]) if seq else 0.0
    poses = compute_track_path([get_part(c) for c in seq if get_part(c)], start=start) if seq else [start]
    end_p = poses[-1]
    pos = math.hypot(end_p.x - start.x, end_p.y - start.y)
    metrics = {
        "nascar_oval": True,
        "n_pieces": len(seq),
        "length_mm": built,
        "pos_mm": pos,
        "straight_mm": actual_straight or straight_mm,
        "r4_mm": r4,
        "guide_length_mm": length,
        "guide_width_mm": width,
        "aspect": length / max(width, 1.0),
        "heading_deg": ang,
        "end_pieces": len(end),
        "side_pieces": len(side),
        "guide_scaled_to_r4": True,
    }
    return OvalResult(seq, metrics)
