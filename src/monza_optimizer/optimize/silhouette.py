"""Coarse silhouette + edge walker. Used only by ambition level A."""
from __future__ import annotations
import math
from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path


def _dist_point_seg(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / den))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rdp(points, eps):
    if len(points) < 3:
        return list(points)
    ax, ay = points[0]
    bx, by = points[-1]
    dmax, idx = -1.0, 0
    for i in range(1, len(points) - 1):
        d = _dist_point_seg(points[i][0], points[i][1], ax, ay, bx, by)
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(points[: idx + 1], eps)[:-1] + rdp(points[idx:], eps)
    return [points[0], points[-1]]


def simplify_for_level_a(points_mm, *, min_keep=10, max_keep=16):
    pts = list(points_mm or [])
    if len(pts) < 4:
        return pts
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1.0:
        pts = pts + [pts[0]]
    length = sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    eps = max(250.0, min(span * 0.12, length * 0.05))
    simple = rdp(pts, eps)
    guard = 0
    while len(simple) > max_keep and guard < 8:
        eps *= 1.4
        simple = rdp(pts, eps)
        guard += 1
    if simple and math.hypot(simple[-1][0] - simple[0][0], simple[-1][1] - simple[0][1]) > 1.0:
        simple = simple + [simple[0]]
    return simple


def _heading(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _slen(part):
    g = getattr(part, "geometry", None)
    return float(getattr(g, "length", 0.0) or 0.0) if isinstance(g, StraightGeometry) else 0.0


def _cang(part):
    g = getattr(part, "geometry", None)
    return abs(float(getattr(g, "angle_degrees", 0.0) or 0.0)) if isinstance(g, CurveGeometry) else 0.0


def _find(get_part, *codes):
    for c in codes:
        p = get_part(c)
        if p is not None:
            return c, p
    return None, None


def build_on_silhouette(points_mm, get_part):
    pts = list(points_mm or [])
    if len(pts) < 4:
        return []
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1.0:
        pts = pts + [pts[0]]
    pose = Pose(float(pts[0][0]), float(pts[0][1]), _heading(pts[0], pts[1]))
    seq = []

    long_code, long_part = _find(get_part, "C8205", "c8205")
    half_code, half_part = _find(get_part, "C8207", "c8207")
    qtr_code, qtr_part = _find(get_part, "C8200", "c8200")
    short_code, short_part = _find(get_part, "C8236", "c8236")
    pack = [(long_code, long_part, _slen(long_part) if long_part else 350.0),
            (half_code, half_part, _slen(half_part) if half_part else 175.0),
            (qtr_code, qtr_part, _slen(qtr_part) if qtr_part else 87.5),
            (short_code, short_part, _slen(short_part) if short_part else 78.0)]
    pack = [(c, p, L) for c, p, L in pack if c and p]

    def curve(err):
        side = "L" if err > 0 else "R"
        return _find(get_part, "C8235" + side, "C8010" + side, "C8206" + side, "C8204" + side)

    n = len(pts) - 1
    for i in range(n):
        b = pts[i + 1]
        edge_h = _heading((pose.x, pose.y), b) if i else _heading(pts[i], b)
        for ncur in range(3):
            err = normalize_heading(edge_h - pose.heading_degrees)
            if abs(err) < 18:
                break
            code, part = curve(err)
            if part is None:
                break
            pose = _advance(pose, part)
            seq.append(code)
        edge_len = math.hypot(b[0] - pose.x, b[1] - pose.y)
        # Always spend the edge on the largest straight that fits.
        guard = 0
        while edge_len >= 70 and guard < 24:
            placed = False
            for code, part, L in pack:
                if edge_len + 15 < L * 0.72:
                    continue
                pose = _advance(pose, part)
                seq.append(code)
                placed = True
                break
            if not placed:
                break
            edge_len = math.hypot(b[0] - pose.x, b[1] - pose.y)
            guard += 1
    return seq
