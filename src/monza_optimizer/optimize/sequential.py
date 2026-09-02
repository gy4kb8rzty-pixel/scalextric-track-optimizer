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


def _peak_turn(cl, s_idx, span_mm: float) -> float:
    """Largest |heading change| from s_idx along the next span_mm of centreline."""
    i0 = min(s_idx, len(cl.points) - 2)
    h0 = cl.heading(i0)
    peak = 0.0
    j = i0
    limit = cl.s[i0] + span_mm
    while j < len(cl.s) - 1 and cl.s[j] <= limit:
        t = abs(normalize_heading(cl.heading(j) - h0))
        if t > peak:
            peak = t
        j += 1
    return peak


def _turn_at(cl, s_idx, ahead_mm: float) -> float:
    j = s_idx
    while j < len(cl.s) - 1 and cl.s[j] < cl.s[s_idx] + ahead_mm:
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
    look_ahead_mm=180.0,
    sharp_turn_deg=28.0,
    max_radius_on_sharp=400.0,
    dist_tol_mm=160.0,
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
        turn_needed = normalize_heading(
            cl.heading(min(s_idx + 8, len(cl.points) - 2)) - pose.heading_degrees
        )
        turn_needed = _turn_at(cl, s_idx, look_ahead_mm) if abs(_turn_at(cl, s_idx, look_ahead_mm)) > abs(turn_needed) else turn_needed
        # signed turn from current pose to near centreline heading
        near_h_idx = s_idx
        while near_h_idx < len(cl.s) - 1 and cl.s[near_h_idx] < cl.s[s_idx] + 70:
            near_h_idx += 1
        turn_needed = normalize_heading(cl.heading(min(near_h_idx, len(cl.points) - 2)) - pose.heading_degrees)
        peak = _peak_turn(cl, s_idx, 220.0)
        sharp_apex = peak >= 70.0
        recent = [_root(c) for c in seq[-4:]]
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
                if (sharp_apex or abs(turn_needed) > 20) and part.geometry.length >= 175:
                    continue
            if isinstance(part.geometry, CurveGeometry):
                ang = abs(part.geometry.angle_degrees)
                signed = -ang if code.endswith("R") else ang
                if abs(turn_needed) > 8 and signed * turn_needed < 0 and abs(signed) > 18 and not sharp_apex:
                    continue
                if sharp_apex and signed * turn_needed < 0 and abs(signed) >= 80:
                    continue
                if (not loose) and peak > sharp_turn_deg and part.geometry.radius > max_radius_on_sharp and not sharp_apex:
                    continue
                is_hp = _root(code) in HAIRPINS
                if is_hp:
                    if not sharp_apex:
                        continue
                    if hairpin_run >= 3:
                        continue
                elif sharp_apex and part.geometry.radius > 280:
                    continue
            np = _advance(pose, part)
            nidx, ndist = cl.closest(np.x, np.y, start=max(0, s_idx - 1), window=280)
            tol = dist_tol_mm + (80.0 if sharp_apex else 0.0)
            if ndist > tol:
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 1:
                continue
            head_err = abs(normalize_heading(np.heading_degrees - cl.heading(min(nidx, len(cl.points) - 2))))
            sc = ndist * 4.0 + head_err * 2.5 - prog * 0.4
            if _root(code) in HAIRPINS and sharp_apex:
                sc -= 80.0
            if sharp_apex and isinstance(part.geometry, CurveGeometry) and part.geometry.radius <= 280:
                sc -= 20.0
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
