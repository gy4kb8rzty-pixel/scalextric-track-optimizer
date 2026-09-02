"""Sequential centreline follower."""
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


def _heading_in(cl, s_idx, ahead_mm):
    j = s_idx
    while j < len(cl.s) - 1 and cl.s[j] < cl.s[s_idx] + ahead_mm:
        j += 1
    return cl.heading(min(j, len(cl.points) - 2)), j


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
        far_h, j = _heading_in(cl, s_idx, look_ahead_mm)
        near_h, _ = _heading_in(cl, s_idx, 80.0)
        turn_needed = normalize_heading(far_h - pose.heading_degrees)
        turn_near = normalize_heading(near_h - pose.heading_degrees)
        sharp_apex = abs(turn_near) >= 58 or abs(turn_needed) >= 75
        recent = [_root(c) for c in seq[-3:]]
        hairpin_run = sum(1 for r in recent if r in HAIRPINS)
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
            if isinstance(part.geometry, StraightGeometry):
                if (abs(turn_needed) > 22 or sharp_apex) and part.geometry.length >= 175:
                    continue
            if isinstance(part.geometry, CurveGeometry):
                ang = abs(part.geometry.angle_degrees)
                signed = -ang if code.endswith("R") else ang
                local_turn = turn_near if sharp_apex else turn_needed
                if abs(local_turn) > 10 and signed * local_turn < 0 and abs(signed) > 18:
                    continue
                if (not loose) and abs(turn_needed) > sharp_turn_deg and part.geometry.radius > max_radius_on_sharp:
                    continue
                is_hp = _root(code) in HAIRPINS
                if is_hp:
                    if not sharp_apex and abs(turn_needed) < 58:
                        continue
                    if hairpin_run >= 3:
                        continue
                elif ang >= 80 and not sharp_apex and abs(turn_needed) < 70:
                    continue
            np = _advance(pose, part)
            nidx, ndist = cl.closest(np.x, np.y, start=max(0, s_idx - 2), window=260)
            if ndist > (dist_tol_mm + (40.0 if sharp_apex else 0.0)):
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 1:
                continue
            head_err = abs(normalize_heading(np.heading_degrees - cl.heading(min(nidx, len(cl.points) - 2))))
            sc = ndist * 5.0 + head_err * 3.0 - prog * 0.5
            if _root(code) in HAIRPINS:
                if sharp_apex:
                    sc -= 55.0
                else:
                    sc += 30.0 + 20.0 * hairpin_run
            if sharp_apex and isinstance(part.geometry, CurveGeometry) and part.geometry.radius > 300:
                sc += 40.0
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
