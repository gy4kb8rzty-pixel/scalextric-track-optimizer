"""NASCAR oval / rounded-rect / tri-oval builders."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.geometry.path import compute_track_path, path_length
from monza_optimizer.geometry.pose import Pose
from monza_optimizer.reference import list_tracks

OVAL_IDS = {
    "bristol", "kansas", "daytona", "talladega", "michigan", "atlanta",
    "texas", "las_vegas_nascar", "homestead", "kentucky", "chicagoland",
    "fontana", "pocono", "indianapolis", "nashville", "richmond",
    "martinsville", "phoenix", "dover", "new_hampshire", "iowa",
    "world_wide_technology", "wwt", "gateway_oval", "nashville_superspeedway",
    "homestead_miami", "charlotte", "charlotte_motor_speedway", "cms",
    "chicago", "las_vegas", "vegas", "indy", "ims", "indianapolis_oval",
}

TRI_OVAL_IDS = {
    "kansas", "phoenix", "daytona", "talladega",
    "chicago", "chicagoland", "las_vegas", "las_vegas_nascar", "vegas",
    "nashville", "nashville_superspeedway",
    "charlotte", "charlotte_motor_speedway", "cms",
    "atlanta", "texas", "michigan", "homestead", "homestead_miami",
    "kentucky", "fontana", "pocono",
    "new_hampshire", "iowa", "world_wide_technology", "wwt", "gateway_oval",
}

RECT_IDS = {
    "indianapolis", "indy", "ims", "indianapolis_motor_speedway", "indianapolis_oval",
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
    if tid in OVAL_IDS or tid.startswith("homestead") or tid.startswith("charlotte") or "indianap" in tid:
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
    if "indianap" in name or tid in OVAL_IDS:
        return True
    if "nascar" not in series:
        return False
    if any(k in kind for k in ("road", "street")):
        return False
    return kind in {"oval", "superspeedway", "short_track", "speedway", ""} or "speedway" in name


def is_rounded_rect(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower().replace("-", "_")
    return tid in RECT_IDS or "indianap" in tid


def is_tri_oval(track_id: str) -> bool:
    tid = str(track_id or "").strip().lower().replace("-", "_")
    if not tid or "roval" in tid or is_rounded_rect(tid):
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


def _bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


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


def _rotate90(pts):
    if not pts:
        return pts
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return [(-(y - cy) + cx, (x - cx) + cy) for x, y in pts]


def scale_guide_to_r4(points, get_part, track_id=None):
    pts = [(float(x), float(y)) for x, y in (points or [])]
    if len(pts) < 4:
        return pts, 1.0
    if is_rounded_rect(track_id):
        minx, miny, maxx, maxy = _bbox(pts)
        if (maxy - miny) > (maxx - minx):
            pts = _rotate90(pts)
    cx, cy, _ang, length, width = _pca(pts)
    r4 = r4_radius_mm(get_part)
    extra = 350.0 if is_rounded_rect(track_id) else 0.0
    factor = (2.0 * r4 + extra) / max(width, 1.0)
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
        return ["C8205"] * max(1, int(max(length_mm, 350) / 350))
    out = []
    left = max(length_mm, 0.0)
    if left < sizes[-1][0] * 0.45:
        return [sizes[-1][1]]
    for ln, code in sizes:
        n = int(left // ln)
        out.extend([code] * n)
        left -= n * ln
    if left > 40 and sizes:
        best = min(sizes, key=lambda t: abs(t[0] - left))
        out.append(best[1])
    return out or [sizes[-1][1]]


def _plus_c8205(side: list[str], get_part) -> list[str]:
    extra = "C8205"
    try:
        if get_part("C8205") is None:
            extra = side[-1] if side else "C8205"
    except Exception:
        extra = "C8205"
    return list(side) + [extra]


def _short_r4(get_part) -> str:
    for code in ("C8235L", "C8235R"):
        try:
            if get_part(code) is not None:
                return code
        except Exception:
            continue
    return SHORT_R4


def _end_n(get_part, n: int) -> list[str]:
    return [_short_r4(get_part)] * max(3, int(n))


def _corner90(get_part) -> list[str]:
    ang = r4_angle_deg(get_part)
    n = max(3, int(round(90.0 / max(ang, 10.0))))
    return _end_n(get_part, n)


def _tri_side(straight_mm: float, get_part) -> list[str]:
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


def oval_follow(cl, get_part, avail=None, shop=None, profile=None, track_id=None, **_kwargs) -> OvalResult:
    pts = list(getattr(cl, "points", []) or [])
    if len(pts) < 8:
        return OvalResult([], {"nascar_oval": False})
    r4 = r4_radius_mm(get_part)
    mid_ang = r4_angle_deg(get_part)
    cx, cy, pca_ang, length, width = _pca(pts)
    tid = str(track_id or "").strip().lower()
    aspect = length / max(width, 1.0)
    rect = is_rounded_rect(tid)
    tri = (not rect) and (is_tri_oval(tid) or (not tid and aspect >= 1.35))
    if any(p in tid for p in PAPERCLIP_IDS):
        tri = False
    # Indy plastic is laid landscape; guide is rotated to match before we get here.
    ang = 0.0 if rect else pca_ang
    long_s = max(length - 2.0 * r4, 80.0)
    short_s = max(width - 2.0 * r4, 80.0)
    if rect:
        long_side = _plus_c8205(_straight_pack(long_s, get_part) or ["C8205"], get_part)
        short_side = _plus_c8205(_straight_pack(short_s, get_part) or ["C8236"], get_part)
        corner = _corner90(get_part)
        seq = list(long_side) + corner + list(short_side) + corner + list(long_side) + corner + list(short_side) + corner
        kind = "rounded_rect"
        actual = sum(_part_len(c, get_part) for c in long_side)
        ox, oy = _rot(-actual * 0.5, -width * 0.5, ang)
        start = Pose(cx + ox, cy + oy, ang)
        pos, _ = _gap(seq, start, get_part)
        end_pieces = len(corner)
        side_n = len(long_side)
    elif tri:
        side = _tri_side(long_s, get_part)
        actual = sum(_part_len(c, get_part) for c in side)
        ox, oy = _rot(-actual * 0.5, -r4, ang)
        start = Pose(cx + ox, cy + oy, ang)
        seq = list(side) + _end_n(get_part, 7) + list(side) + _end_n(get_part, 7)
        pos, _ = _gap(seq, start, get_part)
        best, best_g = seq, pos
        for n1 in (6, 7, 8):
            for n2 in (6, 7, 8):
                trial = list(side) + _end_n(get_part, n1) + list(side) + _end_n(get_part, n2)
                g, _ = _gap(trial, start, get_part)
                if g < best_g:
                    best, best_g = trial, g
        seq, pos = best, best_g
        kind = "tri_oval"
        end_pieces = 7
        side_n = len(side)
    else:
        side = _straight_pack(long_s, get_part) or ["C8236"]
        end = _end_n(get_part, max(4, int(round(180.0 / max(mid_ang, 10.0)))))
        seq = list(side) + list(end) + list(side) + list(end)
        actual = sum(_part_len(c, get_part) for c in side)
        ox, oy = _rot(-actual * 0.5, -r4, ang)
        start = Pose(cx + ox, cy + oy, ang)
        pos, _ = _gap(seq, start, get_part)
        kind = "stadium"
        end_pieces = len(end)
        side_n = len(side)
    built = path_length([get_part(c) for c in seq if get_part(c)]) if seq else 0.0
    metrics = {
        "nascar_oval": True,
        "tri_oval": kind == "tri_oval",
        "rounded_rect": kind == "rounded_rect",
        "oval_kind": kind,
        "n_pieces": len(seq),
        "length_mm": built,
        "pos_mm": pos,
        "closed": pos < 80.0,
        "r4_mm": r4,
        "guide_length_mm": length,
        "guide_width_mm": width,
        "aspect": aspect,
        "heading_deg": ang,
        "end_pieces": end_pieces,
        "side_pieces": side_n,
        "guide_scaled_to_r4": True,
    }
    return OvalResult(seq, metrics)
