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


def rdp(points: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
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
        left = rdp(points[: idx + 1], eps)
        right = rdp(points[idx:], eps)
        return left[:-1] + right
    return [points[0], points[-1]]


def simplify_for_level_a(
    points_mm: list[tuple[float, float]],
    *,
    min_keep: int = 10,
    max_keep: int = 18,
) -> list[tuple[float, float]]:
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


def _heading(a, b) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _straight_len(part) -> float:
    g = getattr(part, "geometry", None)
    if isinstance(g, StraightGeometry):
        return float(g.length)
    return 0.0


def _curve_ang(part) -> float:
    g = getattr(part, "geometry", None)
    if isinstance(g, CurveGeometry):
        return abs(float(g.angle_degrees))
    return 0.0


def build_on_silhouette(points_mm, get_part) -> list[str]:
    """Longs on each silhouette edge, R3/R4 at each vertex. No oval fallback."""
    pts = list(points_mm or [])
    if len(pts) < 4:
        return []
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1.0:
        pts = pts + [pts[0]]
    pose = Pose(pts[0][0], pts[0][1], _heading(pts[0], pts[1]))
    seq: list[str] = []
    straights = []
    for code in ("C8205", "C8207", "C8200", "C8236"):
        p = get_part(code)
        if p is not None and _straight_len(p) > 0:
            straights.append((code, _straight_len(p)))
    straights.sort(key=lambda t: -t[1])

    def _curve_code(err: float) -> str | None:
        side = "L" if err > 0 else "R"
        for sku in ("C8235" + side, "C8010" + side, "C8206" + side, "C8204" + side):
            p = get_part(sku)
            if p is not None and _curve_ang(p) > 0:
                return sku
        return None

    for i in range(len(pts) - 1):
        nxt = pts[i + 1]
        for _ in range(24):
            remain = math.hypot(nxt[0] - pose.x, nxt[1] - pose.y)
            if remain < 70:
                break
            want = _heading(pose.x, pose.y) if False else _heading((pose.x, pose.y), nxt)
            head_err = abs(normalize_heading(want - pose.heading_degrees))
            if head_err > 18:
                break
            placed = False
            for code, L in straights:
                if remain < L * 0.82:
                    continue
                part = get_part(code)
                pose = _advance(pose, part)
                seq.append(code)
                placed = True
                break
            if not placed:
                break
        if i + 2 < len(pts):
            desired = _heading(nxt, pts[i + 2])
            for _ in range(10):
                err = normalize_heading(desired - pose.heading_degrees)
                if abs(err) < 14:
                    break
                code = _curve_code(err)
                if code is None:
                    break
                part = get_part(code)
                ang = _curve_ang(part)
                if ang > abs(err) + 8 and ang > 30:
                    milder = "C8235L" if err > 0 else "C8235R"
                    if get_part(milder) is not None:
                        code, part = milder, get_part(milder)
                pose = _advance(pose, part)
                seq.append(code)
    return seq
