"""Sequential centreline follower with tight-curve preference on sharp turns.

Used for long circuits (e.g. Nordschleife) where corner-first anchors alone
cannot cover the full path. Rejects large-radius pieces (e.g. C8204) when
heading error exceeds a threshold so hairpins stay on the reference line.
"""

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


DEFAULT_CANDIDATES = [
    "C156L", "C156R", "C8234L", "C8234R", "C8235L", "C8235R",
    "C8010L", "C8010R", "C8204L", "C8204R", "C8206L", "C8206R",
    "C187L", "C187R", "C8236", "C8200", "C8207", "C8205",
]

TIGHT_FIRST = [
    "C156L", "C156R", "C8234L", "C8234R", "C8235L", "C8235R",
    "C8010L", "C8010R",
]


def _advance(pose: Pose, part) -> Pose:
    return compute_track_path([part], start=pose)[-1]


@dataclass
class SequentialResult:
    sequence: list[str]
    metrics: dict = field(default_factory=dict)


def sequential_follow(
    cl: Centreline,
    get_part: Callable,
    avail: dict[str, int] | None = None,
    *,
    candidates: list[str] | None = None,
    max_pieces: int = 700,
    look_ahead_mm: float = 160.0,
    sharp_turn_deg: float = 28.0,
    max_radius_on_sharp: float = 400.0,
    dist_tol_mm: float = 150.0,
) -> SequentialResult:
    """Walk the centreline placing pieces one-by-one.

    On sharp heading changes, large-radius curves are rejected so the path
    stays close to the red guide (fixes C8204 hairpin bulges).
    """
    codes = list(candidates or DEFAULT_CANDIDATES)
    used: Counter = Counter()
    avail = avail or {base_id(c): 999 for c in codes}

    start = Pose(
        cl.points[0][0],
        cl.points[0][1],
        cl.heading(0),
    )
    pose = start
    seq: list[str] = []
    s_idx = 0

    while s_idx < len(cl.points) - 8 and len(seq) < max_pieces:
        look = look_ahead_mm
        j = s_idx
        while j < len(cl.s) - 1 and cl.s[j] < cl.s[s_idx] + look:
            j += 1
        ref_h = cl.heading(min(j, len(cl.points) - 2))
        turn_needed = normalize_heading(ref_h - pose.heading_degrees)

        best = None
        best_sc = 1e18
        for code in codes:
            if used[base_id(code)] >= avail.get(base_id(code), 0):
                continue
            part = get_part(code)
            if part is None or part.geometry is None:
                continue
            if isinstance(part.geometry, StraightGeometry):
                if abs(turn_needed) > 20 and part.geometry.length >= 300:
                    continue
                if abs(turn_needed) > 30 and part.geometry.length >= 150:
                    continue
            if isinstance(part.geometry, CurveGeometry):
                ang = abs(part.geometry.angle_degrees)
                signed = -ang if code.endswith("R") else ang
                if abs(turn_needed) > 10 and signed * turn_needed < 0 and abs(signed) > 18:
                    continue
                # KEY: reject large-R on sharp turns (C8204 bulge fix)
                if abs(turn_needed) > sharp_turn_deg and part.geometry.radius > max_radius_on_sharp:
                    continue
            np = _advance(pose, part)
            nidx, ndist = cl.closest(np.x, np.y, start=max(0, s_idx - 2), window=200)
            if ndist > dist_tol_mm:
                continue
            prog = cl.s[nidx] - cl.s[s_idx]
            if prog < 1:
                continue
            head_err = abs(
                normalize_heading(
                    np.heading_degrees - cl.heading(min(nidx, len(cl.points) - 2))
                )
            )
            sc = ndist * 5.0 + head_err * 3.0 - prog * 0.5
            if isinstance(part.geometry, CurveGeometry) and abs(turn_needed) > 18:
                sc += part.geometry.radius / 90.0  # prefer tighter
            if isinstance(part.geometry, CurveGeometry) and abs(turn_needed) > 8:
                sc -= 10
            if sc < best_sc:
                best_sc = sc
                best = (code, np, nidx)

        if best is None:
            for code in ["C8236", "C8200", "C8234L", "C8234R", "C156L", "C156R", "C8205"]:
                if used[base_id(code)] >= avail.get(base_id(code), 0):
                    continue
                part = get_part(code)
                if part is None:
                    continue
                np = _advance(pose, part)
                nidx, ndist = cl.closest(np.x, np.y, start=s_idx, window=250)
                if ndist > 300:
                    continue
                best = (code, np, nidx)
                break
        if best is None:
            break

        code, np, nidx = best
        seq.append(code)
        used[base_id(code)] += 1
        pose = np
        s_idx = max(s_idx + 1, nidx)

    end = pose
    pos = math.hypot(end.x - start.x, end.y - start.y)
    head = abs(normalize_heading(end.heading_degrees - start.heading_degrees))
    # mean distance of piece midpoints to CL
    poses = [start]
    p = start
    for c in seq:
        p = _advance(p, get_part(c))
        poses.append(p)
    dists = []
    for i in range(len(seq)):
        mx = (poses[i].x + poses[i + 1].x) / 2
        my = (poses[i].y + poses[i + 1].y) / 2
        _, d = cl.closest(mx, my, start=0, window=len(cl.points))
        dists.append(d)
    mean_d = sum(dists) / max(len(dists), 1)
    metrics = {
        "n_pieces": len(seq),
        "pos_mm": pos,
        "head_deg": head,
        "mean_centreline_mm": mean_d,
        "length_mm": path_length([get_part(c) for c in seq]) if seq else 0.0,
        "s_covered_mm": cl.s[min(s_idx, len(cl.s) - 1)],
    }
    return SequentialResult(seq, metrics)
