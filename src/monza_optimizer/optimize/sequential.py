"""Sequential centreline follower."""
from __future__ import annotations
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable
from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path, path_length
from monza_optimizer.optimize.corner_first import Centreline
from monza_optimizer.optimize.accuracy_levels import may_place

DEFAULT_CANDIDATES = ["C156L", "C156R", "C8234L", "C8234R", "C8235L", "C8235R", "C8010L", "C8010R", "C8204L", "C8204R", "C8206L", "C8206R", "C187L", "C187R", "C8236", "C8200", "C8207", "C8205"]

def _advance(pose, part):
    return compute_track_path([part], start=pose)[-1]

@dataclass
class SequentialResult:
    sequence: list
    metrics: dict = field(default_factory=dict)

def sequential_follow(cl, get_part, avail=None, *, candidates=None, max_pieces=700, look_ahead_mm=160.0, sharp_turn_deg=28.0, max_radius_on_sharp=400.0, dist_tol_mm=150.0, shop=None, loose=False, **_kwargs):
    codes = list(candidates or DEFAULT_CANDIDATES)
    used = Counter()
    avail = avail or {base_id(c): 999 for c in codes}
    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    pose, seq, s_idx = start, [], 0
    while s_idx < len(cl.points) - 8 and len(seq) < max_pieces:
        j = s_idx
        while j < len(cl.s) - 1 and cl.s[j] < cl.s[s_idx] + look_ahead_mm:
            j += 1
        turn_needed = normalize_heading(cl.heading(min(j, len(cl.points) - 2)) - pose.heading_degrees)
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
                if abs(turn_needed) > 20 and part.geometry.length >= 300:
                    continue
            if isinstance(part.geometry, CurveGeometry):
                ang = abs(part.geometry.angle_degrees)
                signed = -ang if code.endswith("R") else ang
                if abs(turn_needed) > 10 and signed * turn_needed < 0 and abs(signed) > 18:
                    continue
                if (not loose) and abs(turn_needed) > sharp_turn_deg and part.geometry.radius > max_radius_on_sharp:
                    continue
            np = _advance(pose, part)
            nidx, ndist = cl.closest(np.x, np.y, start=max(0, s_idx - 2), window=200)
            if ndist > dist_tol_mm:
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 1:
                continue
            head_err = abs(normalize_heading(np.heading_degrees - cl.heading(min(nidx, len(cl.points) - 2))))
            sc = ndist * 5.0 + head_err * 3.0 - prog * 0.5
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
    metrics = {"n_pieces": len(seq), "pos_mm": pos, "head_deg": head, "length_mm": path_length([get_part(c) for c in seq]) if seq else 0.0}
    return SequentialResult(seq, metrics)
