"""Level A: simplified silhouette + s-parameter follow. Max two curves in a row."""
from __future__ import annotations
import math
from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.optimize.corner_first import densify_polyline


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


def simplify_for_level_a(points_mm, *, min_keep=12, max_keep=18):
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
    eps = max(200.0, min(span * 0.08, length * 0.035))
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


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _signed_curve(code, part):
    if not isinstance(part.geometry, CurveGeometry):
        return 0.0
    ang = abs(float(part.geometry.angle_degrees))
    return -ang if str(code).endswith("R") else ang


def build_on_silhouette(points_mm, get_part):
    """Follow densified silhouette. Prefer longs. Never more than two curves in a row."""
    pts = simplify_for_level_a(points_mm) if points_mm else []
    if len(pts) < 4:
        return []
    cl = densify_polyline(pts, step=40.0)
    pose = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    codes = []
    for c in (
        "C8205", "C8207", "C8200", "C8236",
        "C8235L", "C8235R", "C8010L", "C8010R",
    ):
        if get_part(c) is not None:
            codes.append(c)
    seq = []
    s_idx = 0
    consec_c = 0
    n = len(cl.points)
    while s_idx < n - 4 and len(seq) < 80:
        look = s_idx
        while look < n - 1 and cl.s[look] < cl.s[s_idx] + 280:
            look += 1
        need = normalize_heading(cl.heading(min(look, n - 2)) - pose.heading_degrees)
        best = None
        for code in codes:
            part = get_part(code)
            if part is None or part.geometry is None:
                continue
            is_c = isinstance(part.geometry, CurveGeometry)
            if is_c and consec_c >= 2:
                continue
            if is_c:
                signed = _signed_curve(code, part)
                if abs(need) < 12 and abs(signed) >= 20:
                    continue
                if abs(need) >= 12 and signed * need < 0:
                    continue
            if isinstance(part.geometry, StraightGeometry) and abs(need) > 28 and part.geometry.length >= 250:
                continue
            nxt = _advance(pose, part)
            nidx, ndist = cl.closest(nxt.x, nxt.y, start=s_idx, window=50)
            if nidx <= s_idx or ndist > 280:
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 35:
                continue
            head = abs(normalize_heading(nxt.heading_degrees - cl.heading(min(nidx, n - 2))))
            sc = ndist + head * 1.5 - prog * 0.35
            if is_c:
                sc += 8.0
            if best is None or sc < best[0]:
                best = (sc, code, nxt, nidx, is_c)
        if best is None:
            break
        seq.append(best[1])
        pose = best[2]
        s_idx = best[3]
        consec_c = consec_c + 1 if best[4] else 0
    return seq
