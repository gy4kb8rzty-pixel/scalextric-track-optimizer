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


def simplify_for_level_a(points_mm, *, min_keep=10, max_keep=18):
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
    eps = max(220.0, min(span * 0.10, length * 0.04))
    simple = rdp(pts, eps)
    guard = 0
    while len(simple) > max_keep and guard < 8:
        eps *= 1.35
        simple = rdp(pts, eps)
        guard += 1
    while len(simple) < min_keep and eps > 40 and guard < 16:
        eps *= 0.72
        simple = rdp(pts, eps)
        guard += 1
    if simple and math.hypot(simple[-1][0] - simple[0][0], simple[-1][1] - simple[0][1]) > 1.0:
        simple = simple + [simple[0]]
    return simple


def _heading(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _straight_len(part):
    g = getattr(part, "geometry", None)
    return float(g.length) if isinstance(g, StraightGeometry) else 0.0


def _curve_ang(part):
    g = getattr(part, "geometry", None)
    return abs(float(g.angle_degrees)) if isinstance(g, CurveGeometry) else 0.0


def build_on_silhouette(points_mm, get_part):
    """Align heading to each edge, lay longs, then turn only as much as the corner."""
    pts = list(points_mm or [])
    if len(pts) < 4:
        return []
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1.0:
        pts = pts + [pts[0]]
    pose = Pose(pts[0][0], pts[0][1], _heading(pts[0], pts[1]))
    seq = []
    straights = []
    for code in ("C8205", "C8207", "C8200", "C8236"):
        p = get_part(code)
        if p is not None and _straight_len(p) > 0:
            straights.append((code, _straight_len(p)))
    straights.sort(key=lambda t: -t[1])

    def curve_for(err):
        side = "L" if err > 0 else "R"
        prefer = ("C8235" + side, "C8010" + side, "C8206" + side, "C8204" + side)
        if abs(err) >= 40:
            prefer = ("C8206" + side, "C8204" + side, "C8010" + side, "C8235" + side)
        for sku in prefer:
            p = get_part(sku)
            if p is not None and _curve_ang(p) > 0:
                return sku, p
        return None, None

    def align(target_heading, budget_deg):
        used = 0.0
        for _ in range(8):
            err = normalize_heading(target_heading - pose.heading_degrees)
            if abs(err) < 16 or used >= budget_deg:
                return
            code, part = curve_for(err)
            if part is None:
                return
            ang = _curve_ang(part)
            if used + ang > budget_deg + 8 and ang > 24:
                mild = "C8235L" if err > 0 else "C8235R"
                mp = get_part(mild)
                if mp is not None:
                    code, part, ang = mild, mp, _curve_ang(mp)
            seq.append(code)
            pose_next = _advance(pose, part)
            object.__setattr__(pose, "x", pose_next.x) if False else None
            return_pose(pose_next)
            used += ang

    def return_pose(np):
        nonlocal pose
        pose = np

    n = len(pts) - 1
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        edge_h = _heading(a, b)
        turn_here = abs(normalize_heading(edge_h - pose.heading_degrees))
        used = 0.0
        for _ in range(8):
            err = normalize_heading(edge_h - pose.heading_degrees)
            if abs(err) < 16 or used >= max(turn_here, 90):
                break
            code, part = curve_for(err)
            if part is None:
                break
            pose = _advance(pose, part)
            seq.append(code)
            used += _curve_ang(part)
        for _ in range(28):
            remain = math.hypot(b[0] - pose.x, b[1] - pose.y)
            if remain < 80:
                break
            placed = False
            for code, L in straights:
                if remain < L * 0.78:
                    continue
                part = get_part(code)
                if part is None:
                    continue
                pose = _advance(pose, part)
                seq.append(code)
                placed = True
                break
            if not placed:
                break
    return seq
