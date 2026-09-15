"""Coverage-gap detection and splice-in fill along the reference centreline.

After corner-first or sequential construction, detect stretches of the red
guide that have no nearby piece and insert connecting sequences.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable

from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.optimize.corner_first import Centreline, fill_gap
from monza_optimizer.optimize.sequential import sequential_follow


def _advance(pose: Pose, part) -> Pose:
    return compute_track_path([part], start=pose)[-1]


def _path_poses(seq: list[str], start: Pose, get_part: Callable) -> list[Pose]:
    poses = [start]
    p = start
    for c in seq:
        p = _advance(p, get_part(c))
        poses.append(p)
    return poses


def coverage_distances(
    seq: list[str],
    cl: Centreline,
    get_part: Callable,
    start: Pose | None = None,
) -> list[float]:
    """Per-CL-point distance to nearest piece pose."""
    if start is None:
        start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    poses = _path_poses(seq, start, get_part)
    return [
        min(math.hypot(x - p.x, y - p.y) for p in poses)
        for x, y in cl.points
    ]


def find_uncovered_segments(
    cov: list[float],
    cl: Centreline,
    *,
    threshold_mm: float = 220.0,
    min_gap_mm: float = 400.0,
) -> list[tuple[int, int]]:
    """Return (start_idx, end_idx) clusters where coverage exceeds threshold."""
    uncovered = [i for i, d in enumerate(cov) if d > threshold_mm]
    if not uncovered:
        return []
    segments: list[tuple[int, int]] = []
    a = prev = uncovered[0]
    for i in uncovered[1:]:
        if i <= prev + 5:
            prev = i
        else:
            segments.append((a, prev))
            a = prev = i
    segments.append((a, prev))
    return [
        (a, b)
        for a, b in segments
        if cl.s[b] - cl.s[a] >= min_gap_mm
    ]


def coverage_fill(
    seq: list[str],
    cl: Centreline,
    get_part: Callable,
    avail: dict[str, int],
    *,
    threshold_mm: float = 220.0,
    min_gap_mm: float = 400.0,
    prefer_sharp_first: bool = True,
) -> list[str]:
    """Detect uncovered centreline stretches and splice in connecting pieces.

    If prefer_sharp_first, process high-curvature gaps before gentle ones
    (human strategy: fix hairpins first).
    """
    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    cov = coverage_distances(seq, cl, get_part, start)
    segments = find_uncovered_segments(cov, cl, threshold_mm=threshold_mm, min_gap_mm=min_gap_mm)
    if not segments:
        return seq

    def seg_curvature(a: int, b: int) -> float:
        tot = 0.0
        for i in range(a, min(b, len(cl.points) - 2)):
            tot += abs(normalize_heading(cl.heading(i + 1) - cl.heading(i)))
        return tot

    if prefer_sharp_first:
        segments = sorted(segments, key=lambda ab: -seg_curvature(ab[0], ab[1]))

    current = list(seq)
    for a, b in segments:
        poses = _path_poses(current, start, get_part)
        entry = Pose(cl.points[a][0], cl.points[a][1], cl.heading(a))
        exitp = Pose(cl.points[b][0], cl.points[b][1], cl.heading(min(b, len(cl.points) - 2)))

        def nearest(target_s: float) -> int:
            best_i, best_ds = 0, 1e18
            for i, p in enumerate(poses):
                idx, _ = cl.closest(p.x, p.y, start=0, window=len(cl.points))
                ds = abs(cl.s[idx] - target_s)
                if ds < best_ds:
                    best_ds, best_i = ds, i
            return best_i

        i0 = nearest(cl.s[a])
        i1 = nearest(cl.s[b])
        if i1 <= i0:
            i1 = min(i0 + 1, len(current))

        used = Counter(base_id(c) for c in current[:i0] + current[i1:])
        mid = fill_gap(
            entry, exitp, cl, get_part, avail, used,
            max_pieces=60, beam_width=40,
        )
        if not mid:
            # fall back to sequential on the local CL slice
            local_pts = cl.points[a : b + 1]
            if len(local_pts) < 3:
                continue
            from monza_optimizer.optimize.corner_first import densify_polyline
            local_cl = densify_polyline(local_pts, step=12.0)
            local_avail = {
                k: max(0, avail.get(k, 0) - used[k]) for k in avail
            }
            sub = sequential_follow(local_cl, get_part, local_avail, max_pieces=80)
            mid = sub.sequence
        if not mid:
            continue

        pre = fill_gap(
            poses[i0], entry, cl, get_part, avail, used,
            max_pieces=10, beam_width=25,
        )
        used2 = Counter(base_id(c) for c in current[:i0] + pre + mid)
        end_mid = poses[i0]
        for c in pre + mid:
            end_mid = _advance(end_mid, get_part(c))
        post = fill_gap(
            end_mid, poses[min(i1, len(poses) - 1)], cl, get_part, avail, used2,
            max_pieces=10, beam_width=25,
        )
        trial = current[:i0] + pre + mid + post + current[i1:]
        new_cov = coverage_distances(trial, cl, get_part, start)
        old_max = max(cov[a : b + 1])
        new_max = max(new_cov[a : b + 1])
        if new_max < old_max * 0.9 or new_max < 250:
            current = trial
            cov = new_cov

    return current
