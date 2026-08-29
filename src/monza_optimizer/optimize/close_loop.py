"""Force a layout to close: last pose must meet the start pose."""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable

from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.optimize.accuracy_levels import ShopGate, may_place

CLOSE_POS_MM = 80.0
CLOSE_HEAD_DEG = 12.0

CLOSE_CANDIDATES = [
    "C8236", "C8200", "C8207",
    "C8010L", "C8010R",
    "C8235L", "C8235R",
    "C8234L", "C8234R",
    "C156L", "C156R",
    "C8206L", "C8206R",
    "C8204L", "C8204R",
    "C187L", "C187R",
    "C8205",
]


def _advance(pose: Pose, part) -> Pose:
    return compute_track_path([part], start=pose)[-1]


def end_pose(seq: list[str], start: Pose, get_part: Callable) -> Pose:
    pose = start
    for c in seq:
        part = get_part(c)
        if part is None:
            continue
        pose = _advance(pose, part)
    return pose


def closure_metrics(seq: list[str], start: Pose, get_part: Callable) -> dict:
    end = end_pose(seq, start, get_part)
    pos = math.hypot(end.x - start.x, end.y - start.y)
    head = abs(normalize_heading(end.heading_degrees - start.heading_degrees))
    return {
        "pos_mm": pos,
        "head_deg": head,
        "closed": pos <= CLOSE_POS_MM and head <= CLOSE_HEAD_DEG,
    }


def close_loop(
    seq: list[str],
    start: Pose,
    get_part: Callable,
    avail: dict[str, int] | None = None,
    shop: ShopGate | None = None,
    *,
    max_pieces: int = 12,
    beam_width: int = 36,
    candidates: list[str] | None = None,
    lateral: bool = False,
) -> tuple[list[str], dict]:
    used = Counter(base_id(c) for c in seq)
    pose = end_pose(seq, start, get_part)
    pos = math.hypot(pose.x - start.x, pose.y - start.y)
    head = abs(normalize_heading(pose.heading_degrees - start.heading_degrees))
    stats = {"pos_before_mm": pos, "head_before_deg": head, "added": []}
    if pos <= CLOSE_POS_MM and head <= CLOSE_HEAD_DEG:
        stats.update({"pos_mm": pos, "head_deg": head, "closed": True})
        return list(seq), stats

    def score(p: Pose) -> float:
        g = math.hypot(p.x - start.x, p.y - start.y)
        h = abs(normalize_heading(p.heading_degrees - start.heading_degrees))
        if lateral and g > CLOSE_POS_MM:
            return g * 3.0 + h * 1.6
        return g * 2.4 + h * 16.0

    beam: list[tuple[float, list[str], Pose, Counter]] = [(score(pose), [], pose, used.copy())]
    best = beam[0]
    for _ in range(max_pieces):
        bp = best[2]
        if math.hypot(bp.x - start.x, bp.y - start.y) <= CLOSE_POS_MM and abs(
            normalize_heading(bp.heading_degrees - start.heading_degrees)
        ) <= CLOSE_HEAD_DEG:
            break
        nxt: list[tuple[float, list[str], Pose, Counter]] = []
        seen: set[tuple] = set()
        for _sc, extra, p, us in beam:
            rem = math.hypot(p.x - start.x, p.y - start.y)
            for code in (candidates or CLOSE_CANDIDATES):
                if not may_place(code, us, avail, shop):
                    continue
                part = get_part(code)
                if part is None or part.geometry is None:
                    continue
                np = _advance(p, part)
                nrem = math.hypot(np.x - start.x, np.y - start.y)
                if nrem > rem + 700:
                    continue
                key = (round(np.x / 20), round(np.y / 20), round(normalize_heading(np.heading_degrees) / 11.25))
                if key in seen:
                    continue
                seen.add(key)
                nus = us.copy()
                nus[base_id(code)] += 1
                nxt.append((score(np), extra + [code], np, nus))
        if not nxt:
            break
        nxt.sort(key=lambda t: t[0])
        beam = nxt[:beam_width]
        if beam[0][0] < best[0]:
            best = beam[0]
    extra = best[1]
    end = best[2]
    pos2 = math.hypot(end.x - start.x, end.y - start.y)
    head2 = abs(normalize_heading(end.heading_degrees - start.heading_degrees))
    stats.update({"added": extra, "pos_mm": pos2, "head_deg": head2,
                  "closed": pos2 <= CLOSE_POS_MM and head2 <= CLOSE_HEAD_DEG})
    return list(seq) + extra, stats
