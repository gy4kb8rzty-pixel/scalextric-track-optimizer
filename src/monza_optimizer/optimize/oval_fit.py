"""NASCAR oval: R4 stadium; tri-ovals close by cutting each end 22.5."""
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
    "homestead_miami", "charlotte", "charlotte_motor_speedway", "cms",
    "chicago", "las_vegas", "vegas",
}

TRI_OVAL_IDS = {
    "kansas", "phoenix", "daytona", "talladega",
    "chicago", "chicagoland", "las_vegas", "las_vegas_nascar", "vegas",
    "nashville", "nashville_superspeedway",
    "charlotte", "charlotte_motor_speedway", "cms",
    "atlanta", "texas", "michigan", "homestead", "homestead_miami",
    "kentucky", "fontana", "pocono", "indianapolis",
    "new_hampshire", "iowa", "world_wide_technology", "wwt", "gateway_oval",
}

PAPERCLIP_IDS = {
    "bristol", "martinsville", "richmond",
}

STRAIGHTS = ("C8205", "C8207", "C8200", "C8236")
R4_CODES = ("C8235L", "C8235R", "C8235")
DEFAULT_R4_MM = 454.0
SHORT_R4 = "C8235L"


def is_nascar_oval(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower().replace("-", "_")
    if not tid or "roval" in tid:
        return False
    if tid in OVAL_IDS or tid.startswith("homestead") or tid.startswith("charlotte"):
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
    if any(k in name for k in ("homestead", "charlotte motor", "chicagoland", "las vegas")):
        return True
    if tid in OVAL_IDS:
        return True
    if "nascar" not in series:
        return False
    if any(k in kind for k in ("road", "street")):
        return False
    return kind in {"oval", "superspeedway", "short_track", "speedway", ""} or "speedway" in name


def is_tri_oval(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower().replace("-", "_")
    if not tid or "roval" in tid:
        return False
    if any(p == tid or p in tid for p in PAPERCLIP_IDS):
        return False
    if tid in TRI_OVAL_IDS:
        return True
    return any(key in tid for key in TRI_OVAL_IDS)


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
    us, vs = [], []
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


def _part_len(code, get_part) -> float:
    part = get_part(code)
    if part is None:
        return 0.0
    geo = part.geometry
    if isinstance(geo, StraightGeometry):
        return float(geo.length)
    return 0.0


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


def _end_pack(get_part, turn_deg: float = 180.0) -> list[str]:
    ang = r4_angle_deg(get_part)
    n = max(3, int(round(float(turn_deg) / max(ang, 10.0))))
    code = _short_r4(get_part)
    return [code] * n


def _short_r4(get_part) -> str:
    for code in ("C8235L", "C8235R"):
        try:
            if get_part(code) is not None:
                return code
        except Exception:
            continue
    return SHORT_R4


def _tri_side(straight_mm: float, get_part) -> list[str]:
    """Two equal half-straights with the shortest R4 between them."""
    kink = _short_r4(get_part)
    half = _straight_pack(max(straight_mm * 0.5, 80.0), get_part) or ["C8236"]
    return list(half) + [kink] + list(half)


def _rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def _gap(seq, start, get_part):
    parts = [get_part(c) for c in seq if get_part(c)]
    if not parts:
        return 9999.0, start
    poses = compute_track_path(parts, start=start)
    end_p = poses[-1]
    return math.hypot(end_p.x - start.x, end_p.y - start.y), end_p


def _close_on_straight(seq, start, get_part) -> list[str]:
    """Pad the first long side with short straights until the join meets."""
    sizes = []
    for code in ("C8236", "C8200", "C8207", "C8205"):
        part = get_part(code)
        if part is not None and isinstance(part.geometry, StraightGeometry):
            sizes.append((float(part.geometry.length), code))
    if not sizes:
        return seq
    sizes.sort()
    best = list(seq)
    best_gap, _ = _gap(best, start, get_part)
    for _ in range(8):
        if best_gap < 35.0:
            break
        improved = False
        for _ln, code in sizes:
            trial = [code] + list(best)
            g, _ = _gap(trial, start, get_part)
            if g + 8.0 < best_gap:
                best, best_gap = trial, g
                improved = True
                break
            trial = list(best) + [code]
            g, _ = _gap(trial, start, get_part)
            if g + 8.0 < best_gap:
                best, best_gap = trial, g
                improved = True
                break
        if not improved:
            break
    return best


def oval_follow(cl, get_part, avail=None, shop=None, profile=None, track_id=None, **_kwargs) -> OvalResult:
    pts = list(getattr(cl, "points", []) or [])
    if len(pts) < 8:
        return OvalResult([], {"nascar_oval": False})
    r4 = r4_radius_mm(get_part)
    mid_ang = r4_angle_deg(get_part)
    cx, cy, ang, length, width = _pca(pts)
    tid = str(track_id or "").strip().lower()
    aspect = length / max(width, 1.0)
    tri = is_tri_oval(tid) or (not tid and aspect >= 1.35)
    if any(p in tid for p in PAPERCLIP_IDS):
        tri = False
    straight_mm = max(length - 2.0 * r4, 0.0)
    if tri:
        # Mid R4 on each long side. Each end loses that same 22.5 so 360 closes.
        side = _tri_side(straight_mm, get_part)
        end = _end_pack(get_part, turn_deg=180.0 - mid_ang)
    else:
        side = _straight_pack(straight_mm, get_part) or ["C8236"]
        end = _end_pack(get_part, turn_deg=180.0)
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
    actual_straight = sum(_part_len(c, get_part) for c in side)
    ox, oy = _rot(-actual_straight * 0.5, -r4, ang)
    start = Pose(cx + ox, cy + oy, ang)
    if tri:
        seq = _close_on_straight(seq, start, get_part)
    built = path_length([get_part(c) for c in seq if get_part(c)]) if seq else 0.0
    pos, _end = _gap(seq, start, get_part)
    metrics = {
        "nascar_oval": True,
        "tri_oval": bool(tri),
        "tri_end_deg": (180.0 - mid_ang) if tri else 180.0,
        "n_pieces": len(seq),
        "length_mm": built,
        "pos_mm": pos,
        "closed": pos < 80.0,
        "straight_mm": actual_straight or straight_mm,
        "r4_mm": r4,
        "guide_length_mm": length,
        "guide_width_mm": width,
        "aspect": aspect,
        "heading_deg": ang,
        "end_pieces": len(end),
        "side_pieces": len(side),
        "guide_scaled_to_r4": True,
    }
    return OvalResult(seq, metrics)
