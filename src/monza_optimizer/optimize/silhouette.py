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


def simplify_for_level_a(points_mm, *, min_keep=12, max_keep=20):
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
    eps = max(180.0, min(span * 0.07, length * 0.03))
    simple = rdp(pts, eps)
    guard = 0
    while len(simple) > max_keep and guard < 8:
        eps *= 1.3
        simple = rdp(pts, eps)
        guard += 1
    while len(simple) < min_keep and eps > 50 and guard < 16:
        eps *= 0.75
        simple = rdp(pts, eps)
        guard += 1
    if simple and math.hypot(simple[-1][0] - simple[0][0], simple[-1][1] - simple[0][1]) > 1.0:
        simple = simple + [simple[0]]
    return simple


def _heading(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


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
    longs = []
    for code in ("C8205", "C8207", "C8200", "C8236"):
        c, p = _find(get_part, code)
        if p is not None:
            g = p.geometry
            L = float(getattr(g, "length", 0) or 0) if isinstance(g, StraightGeometry) else 0.0
            if L > 0:
                longs.append((c, p, L))
    longs.sort(key=lambda t: -t[2])

    def curve(err):
        side = "L" if err > 0 else "R"
        return _find(get_part, "C8235" + side, "C8010" + side, "C8206" + side)

    for i in range(len(pts) - 1):
        b = pts[i + 1]
        for _ in range(3):
            err = normalize_heading(_heading((pose.x, pose.y), b) - pose.heading_degrees)
            if abs(err) < 16:
                break
            code, part = curve(err)
            if part is None:
                break
            nxt = _advance(pose, part)
            if math.hypot(b[0] - nxt.x, b[1] - nxt.y) > math.hypot(b[0] - pose.x, b[1] - pose.y) + 40:
                break
            pose = nxt
            seq.append(code)
        for _ in range(20):
            remain = math.hypot(b[0] - pose.x, b[1] - pose.y)
            if remain < 70:
                break
            placed = False
            for code, part, L in longs:
                if L > remain + 40:
                    continue
                nxt = _advance(pose, part)
                new_r = math.hypot(b[0] - nxt.x, b[1] - nxt.y)
                if new_r >= remain - 25:
                    continue
                pose = nxt
                seq.append(code)
                placed = True
                break
            if not placed:
                break
    return seq
