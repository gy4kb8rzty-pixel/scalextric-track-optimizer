"""Coarse silhouette of a centreline. Used only by ambition level A."""
from __future__ import annotations
import math


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
    max_keep: int = 22,
) -> list[tuple[float, float]]:
    """Fewer vertices so A can follow with longs and large radii."""
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
    eps = max(180.0, min(span * 0.08, length * 0.035))
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
