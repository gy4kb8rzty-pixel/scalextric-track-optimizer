"""Level B centreline: simpler than C, more corners than A."""
from __future__ import annotations

import math

from monza_optimizer.optimize.silhouette import _close, rdp, smooth_polyline


def simplify_for_level_b(points_mm, *, min_keep=14, max_keep=22):
    pts = _close(list(points_mm or []))
    if len(pts) < 4:
        return pts
    pts = smooth_polyline(pts, passes=3)
    length = sum(
        math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        for i in range(len(pts) - 1)
    )
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    eps = max(140.0, min(span * 0.06, length * 0.028))
    simple = rdp(pts, eps)
    guard = 0
    while len(simple) > max_keep and guard < 12:
        eps *= 1.18
        simple = rdp(pts, eps)
        guard += 1
    if len(simple) < min_keep:
        simple = rdp(pts, max(eps * 0.55, 90.0))
    return _close(simple)
