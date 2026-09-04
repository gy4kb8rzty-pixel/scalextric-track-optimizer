"""Level A: coarse F1 silhouette + multi-start s-follow + home."""
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


def _close(pts):
    if not pts:
        return pts
    if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > 1.0:
        return list(pts) + [pts[0]]
    return list(pts)


def smooth_polyline(points, passes=2):
    pts = _close(list(points or []))
    if len(pts) < 4:
        return pts
    for _ in range(passes):
        body = pts[:-1]
        n = len(body)
        nxt = []
        for i in range(n):
            a = body[i]
            b = body[(i + 1) % n]
            nxt.append((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]))
            nxt.append((0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))
        pts = _close(nxt)
    return pts


def simplify_for_level_a(points_mm, *, min_keep=10, max_keep=14):
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
    eps = max(200.0, min(span * 0.085, length * 0.038))
    simple = rdp(pts, eps)
    guard = 0
    while len(simple) > max_keep and guard < 10:
        eps *= 1.28
        simple = rdp(pts, eps)
        guard += 1
    if len(simple) < 6:
        simple = rdp(pts, eps * 0.7)
    return _close(simple)


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _signed_curve(code, part):
    if not isinstance(part.geometry, CurveGeometry):
        return 0.0
    ang = abs(float(part.geometry.angle_degrees))
    return -ang if str(code).endswith("R") else ang


def _follow(cl, get_part, codes):
    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    pose = start
    seq = []
    s_idx = 0
    consec_c = 0
    n = len(cl.points)
    total = max(cl.s[-1], 1.0)
    while s_idx < n - 5 and len(seq) < 110:
        frac = cl.s[min(s_idx, n - 1)] / total
        look = s_idx
        ahead = 280 if frac < 0.82 else 160
        while look < n - 1 and cl.s[look] < cl.s[s_idx] + ahead:
            look += 1
        need = normalize_heading(cl.heading(min(look, n - 2)) - pose.heading_degrees)
        cap = 10 if len(seq) < 8 else (6 if frac < 0.8 else 4)
        tol = 1400 if len(seq) < 8 else (560 if frac < 0.8 else 440)
        best = None
        for code in codes:
            part = get_part(code)
            if part is None or part.geometry is None:
                continue
            is_c = isinstance(part.geometry, CurveGeometry)
            if is_c and consec_c >= cap:
                continue
            if is_c:
                signed = _signed_curve(code, part)
                if abs(need) < 8 and abs(signed) >= 20 and frac < 0.8:
                    continue
                if abs(need) >= 8 and signed * need < 0:
                    continue
            if isinstance(part.geometry, StraightGeometry) and abs(need) > 38 and part.geometry.length >= 250:
                continue
            nxt = _advance(pose, part)
            nidx, ndist = cl.closest(nxt.x, nxt.y, start=s_idx, window=45)
            if nidx <= s_idx and frac < 0.88:
                continue
            if nidx > s_idx + 55:
                continue
            prog = cl.s[min(nidx, n - 1)] - cl.s[s_idx]
            if prog < 18 and frac < 0.88:
                continue
            if ndist > tol:
                continue
            head = abs(normalize_heading(nxt.heading_degrees - cl.heading(min(nidx, n - 2))))
            sc = ndist * 1.1 + head * 1.0 - max(prog, 0) * 0.55
            if is_c:
                sc += 4.0 if consec_c == 0 else 14.0
            if frac >= 0.82:
                gap = math.hypot(nxt.x - start.x, nxt.y - start.y)
                sc += gap * 0.08
                sc += abs(normalize_heading(nxt.heading_degrees - start.heading_degrees)) * 0.4
            if best is None or sc < best[0]:
                best = (sc, code, nxt, max(nidx, s_idx + 1), is_c)
        if best is None:
            break
        seq.append(best[1])
        pose = best[2]
        s_idx = min(best[3], n - 2)
        consec_c = consec_c + 1 if best[4] else 0
        if frac >= 0.9 and math.hypot(pose.x - start.x, pose.y - start.y) < 180:
            break
    cover = cl.s[min(s_idx, len(cl.s) - 1)] / total
    gap = math.hypot(pose.x - start.x, pose.y - start.y)
    return seq, cover, gap


def _replay(seq, cl, get_part):
    pose = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    start = pose
    for c in seq:
        part = get_part(c)
        if part is not None:
            pose = _advance(pose, part)
    return start, pose


def _home(seq, start, pose, get_part, codes, max_add=14):
    out = list(seq)
    for _ in range(max_add):
        gap = math.hypot(pose.x - start.x, pose.y - start.y)
        head = abs(normalize_heading(pose.heading_degrees - start.heading_degrees))
        if gap < 140 and head < 28:
            break
        best = None
        for code in codes:
            part = get_part(code)
            if part is None:
                continue
            nxt = _advance(pose, part)
            ng = math.hypot(nxt.x - start.x, nxt.y - start.y)
            if ng >= gap - 8:
                continue
            nh = abs(normalize_heading(nxt.heading_degrees - start.heading_degrees))
            sc = ng + nh * 1.2
            if best is None or sc < best[0]:
                best = (sc, code, nxt)
        if best is None:
            break
        out.append(best[1])
        pose = best[2]
    return out


def _rotate_pts(pts, k):
    body = pts[:-1] if pts and math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < 2 else list(pts)
    k = k % max(len(body), 1)
    return _close(body[k:] + body[:k])


def build_on_silhouette(points_mm, get_part):
    pts = list(points_mm or [])
    if len(pts) > 40:
        pts = simplify_for_level_a(pts)
    if len(pts) < 4:
        return []
    codes = [c for c in (
        "C8205", "C8207", "C8200", "C8236",
        "C8235L", "C8235R", "C8010L", "C8010R", "C8206L", "C8206R",
    ) if get_part(c) is not None]
    body = pts[:-1] if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) < 2 else pts
    best_seq, best_sc = [], -1e18
    step = max(1, len(body) // 6)
    for k in range(0, len(body), step):
        rot = _rotate_pts(pts, k)
        cl = densify_polyline(rot, step=32.0)
        seq, cover, gap = _follow(cl, get_part, codes)
        if not seq:
            continue
        start, pose = _replay(seq, cl, get_part)
        seq = _home(seq, start, pose, get_part, codes)
        start, pose = _replay(seq, cl, get_part)
        gap = math.hypot(pose.x - start.x, pose.y - start.y)
        sc = cover * 1000.0 - min(gap, 2500) * 0.18
        if sc > best_sc:
            best_sc, best_seq = sc, seq
    return best_seq
