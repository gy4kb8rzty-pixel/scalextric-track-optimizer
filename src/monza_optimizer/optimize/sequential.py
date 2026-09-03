"""Sequential centreline follower. See docs/LEARNINGS.md."""
from __future__ import annotations
import math
from collections import Counter
from dataclasses import dataclass, field
from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path, path_length
from monza_optimizer.optimize.accuracy_levels import may_place

DEFAULT_CANDIDATES = [
    "C8201L", "C8201R", "C8234L", "C8234R", "C8235L", "C8235R",
    "C8010L", "C8010R", "C8204L", "C8204R", "C8206L", "C8206R",
    "C187L", "C187R", "C8236", "C8200", "C8207", "C8205",
]
HAIRPINS = {"C8201", "C156"}


def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]


def _root(code: str) -> str:
    return base_id(code)


def _signed_angle(code, part) -> float:
    if not isinstance(part.geometry, CurveGeometry):
        return 0.0
    ang = abs(part.geometry.angle_degrees)
    return -ang if code.endswith("R") else ang


def _recent_spiral(seq, get_part) -> float:
    total = 0.0
    n = 0
    for code in reversed(seq):
        part = get_part(code)
        if part is None or not isinstance(part.geometry, CurveGeometry):
            if n:
                break
            continue
        total += _signed_angle(code, part)
        n += 1
        if n >= 6:
            break
    return total


def _turn_over(cl, s_idx, span_mm) -> float:
    j = s_idx
    while j < len(cl.s) - 1 and cl.s[j] < cl.s[s_idx] + span_mm:
        j += 1
    return normalize_heading(cl.heading(min(j, len(cl.points) - 2)) - cl.heading(min(s_idx, len(cl.points) - 2)))


@dataclass
class SequentialResult:
    sequence: list
    metrics: dict = field(default_factory=dict)


def sequential_follow(
    cl,
    get_part,
    avail=None,
    *,
    candidates=None,
    max_pieces=700,
    look_ahead_mm=220.0,
    sharp_turn_deg=28.0,
    max_radius_on_sharp=400.0,
    dist_tol_mm=150.0,
    shop=None,
    loose=False,
    **_kwargs,
):
    codes = list(candidates or DEFAULT_CANDIDATES)
    used = Counter()
    avail = avail or {base_id(c): 999 for c in codes}
    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    pose, seq, s_idx = start, [], 0
    while s_idx < len(cl.points) - 8 and len(seq) < max_pieces:
        turn_needed = _turn_over(cl, s_idx, look_ahead_mm)
        apex = _turn_over(cl, s_idx, 90.0)
        spiral = _recent_spiral(seq, get_part)
        recent = [_root(c) for c in seq[-4:]]
        hairpin_run = 0
        for r in reversed(recent):
            if r in HAIRPINS:
                hairpin_run += 1
            else:
                break
        best, best_sc = None, 1e18
        for code in codes:
            if shop is not None:
                if not may_place(code, used, avail, shop):
                    continue
            elif used[base_id(code)] >= avail.get(base_id(code), 0):
                continue
            part = get_part(code)
            if part is None or part.geometry is None:
                continue
            is_hp = _root(code) in HAIRPINS
            signed = _signed_angle(code, part)
            if isinstance(part.geometry, StraightGeometry):
                if abs(turn_needed) > 22 and part.geometry.length >= 300:
                    continue
            if isinstance(part.geometry, CurveGeometry):
                if abs(turn_needed) > 10 and signed * turn_needed < 0 and abs(signed) > 18:
                    continue
                if (not loose) and abs(turn_needed) > sharp_turn_deg and part.geometry.radius > max_radius_on_sharp:
                    continue
                if abs(spiral) >= 240 and signed * spiral > 0 and abs(signed) >= 20:
                    continue
                if is_hp:
                    if abs(apex) < 50 and abs(turn_needed) < 55:
                        continue
                    if hairpin_run >= 2:
                        continue
            np = _advance(pose, part)
            nidx, ndist = cl.closest(np.x, np.y, start=max(0, s_idx - 2), window=240)
            if ndist > dist_tol_mm:
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 1:
                continue
            head_err = abs(normalize_heading(np.heading_degrees - cl.heading(min(nidx, len(cl.points) - 2))))
            sc = ndist * 5.0 + head_err * 3.0 - prog * 0.5
            if is_hp:
                if abs(apex) >= 70:
                    sc -= 40.0
                else:
                    sc += 18.0
                sc += 14.0 * hairpin_run
            if sc < best_sc:
                best_sc, best = sc, (code, np, nidx)
        if best is None:
            break
        code, np, nidx = best
        seq.append(code)
        used[base_id(code)] += 1
        pose = np
        s_idx = max(s_idx + 1, nidx)
    pos = math.hypot(pose.x - start.x, pose.y - start.y)
    head = abs(normalize_heading(pose.heading_degrees - start.heading_degrees))
    metrics = {
        "n_pieces": len(seq),
        "pos_mm": pos,
        "head_deg": head,
        "length_mm": path_length([get_part(c) for c in seq]) if seq else 0.0,
    }
    return SequentialResult(seq, metrics)
