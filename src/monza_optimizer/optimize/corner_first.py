"""Corner-first construction for complex tracks (e.g. Monaco hairpins).

Three stages:
1. Corner detection + anchor placement (fit tricky curves first)
2. Gap-filling between anchors with vector mending
3. Local window re-optimisation on worst deviation segments
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Sequence

from monza_optimizer.catalog.geometry_types import CurveGeometry, StraightGeometry
from monza_optimizer.catalog.parts import base_id
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.geometry.path import compute_track_path, path_length


# ---------------------------------------------------------------------------
# Reference centreline helpers
# ---------------------------------------------------------------------------

@dataclass
class Centreline:
    """Densified reference path in millimetres."""
    points: list[tuple[float, float]]
    s: list[float]  # cumulative arc length

    @property
    def total_length(self) -> float:
        return self.s[-1] if self.s else 0.0

    def heading(self, i: int) -> float:
        i = max(0, min(len(self.points) - 2, i))
        x0, y0 = self.points[i]
        x1, y1 = self.points[i + 1]
        return math.degrees(math.atan2(y1 - y0, x1 - x0))

    def closest(self, x: float, y: float, start: int = 0, window: int = 200) -> tuple[int, float]:
        best, bd = start, 1e18
        lo = max(0, start - 10)
        hi = min(len(self.points), start + window)
        for i in range(lo, hi):
            d = (self.points[i][0] - x) ** 2 + (self.points[i][1] - y) ** 2
            if d < bd:
                bd, best = d, i
        return best, math.sqrt(bd)


def densify_polyline(pts: Sequence[tuple[float, float]], step: float = 12.0) -> Centreline:
    out: list[tuple[float, float]] = [pts[0]]
    for i in range(1, len(pts)):
        x0, y0 = out[-1]
        x1, y1 = pts[i]
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(math.ceil(d / step)))
        for k in range(1, n + 1):
            t = k / n
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
    s = [0.0]
    for i in range(1, len(out)):
        s.append(s[-1] + math.hypot(out[i][0] - out[i - 1][0], out[i][1] - out[i - 1][1]))
    return Centreline(out, s)


# ---------------------------------------------------------------------------
# 1. Corner detection
# ---------------------------------------------------------------------------

@dataclass
class CornerCluster:
    """High-curvature region on the reference centreline."""
    start_i: int
    end_i: int
    signed_turn: float  # total degrees (+ left)
    arc_length: float
    peak_curvature: float

    @property
    def mid_i(self) -> int:
        return (self.start_i + self.end_i) // 2


def detect_corners(
    cl: Centreline,
    window_mm: float = 400.0,
    min_turn_deg: float = 45.0,
    min_separation_mm: float = 500.0,
) -> list[CornerCluster]:
    """Find hairpin / chicane clusters by integrated heading change."""
    n = len(cl.points)
    if n < 10:
        return []

    # Curvature proxy: heading change per arc length
    curv = [0.0] * n
    for i in range(1, n - 1):
        dh = normalize_heading(cl.heading(i) - cl.heading(i - 1))
        ds = max(cl.s[i] - cl.s[i - 1], 1e-3)
        curv[i] = abs(dh) / ds

    # Sliding integrated turn
    clusters: list[CornerCluster] = []
    i = 1
    while i < n - 2:
        # grow while curvature is elevated
        if curv[i] < 0.02:  # ~1.1 deg per 100 mm
            i += 1
            continue
        j = i
        signed = 0.0
        peak = curv[i]
        while j < n - 2 and (curv[j] >= 0.012 or (cl.s[j] - cl.s[i]) < window_mm * 0.4):
            dh = normalize_heading(cl.heading(j) - cl.heading(j - 1))
            signed += dh
            peak = max(peak, curv[j])
            j += 1
            if cl.s[j] - cl.s[i] > window_mm * 2.5:
                break
        arc = cl.s[min(j, n - 1)] - cl.s[i]
        if abs(signed) >= min_turn_deg and arc >= 80.0:
            clusters.append(CornerCluster(i, j, signed, arc, peak))
        i = max(j, i + 1)

    # Merge / suppress nearby weaker clusters
    clusters.sort(key=lambda c: -abs(c.signed_turn))
    kept: list[CornerCluster] = []
    for c in clusters:
        mid_s = (cl.s[c.start_i] + cl.s[c.end_i]) / 2
        if any(abs(mid_s - (cl.s[k.start_i] + cl.s[k.end_i]) / 2) < min_separation_mm for k in kept):
            continue
        kept.append(c)
    kept.sort(key=lambda c: c.start_i)
    return kept


# ---------------------------------------------------------------------------
# Piece advance + inventory helpers
# ---------------------------------------------------------------------------

def advance(pose: Pose, part) -> Pose:
    path = compute_track_path([part], start=pose)
    return path[-1]


def gap_vector(from_pose: Pose, to_pose: Pose) -> tuple[float, float, float]:
    """Return (pos_err, long, lat) in the frame of from_pose heading."""
    dx = to_pose.x - from_pose.x
    dy = to_pose.y - from_pose.y
    pos = math.hypot(dx, dy)
    hr = math.radians(from_pose.heading_degrees)
    long_ = dx * math.cos(hr) + dy * math.sin(hr)
    lat_ = -dx * math.sin(hr) + dy * math.cos(hr)
    return pos, long_, lat_


# ---------------------------------------------------------------------------
# 1b. Anchor placement — fit curve sequences to each corner
# ---------------------------------------------------------------------------

@dataclass
class Anchor:
    corner: CornerCluster
    sequence: list[str]
    entry_pose: Pose  # world pose at start of anchor
    exit_pose: Pose
    score: float


def _curve_candidates(get_part, avail: dict[str, int], used: Counter) -> list[str]:
    codes = []
    for c in (
        "C8204L", "C8204R", "C8206L", "C8206R",
        "C8235L", "C8235R", "C187L", "C187R", "C8234L", "C8234R",
        "C8236", "C8200", "C8207",  # short straights for micro-adjust in corner
    ):
        p = get_part(c)
        if p is None or p.geometry is None:
            continue
        if used[base_id(c)] >= avail.get(base_id(c), 0):
            continue
        codes.append(c)
    return codes


def place_anchor(
    cl: Centreline,
    corner: CornerCluster,
    get_part: Callable,
    avail: dict[str, int],
    used: Counter,
    max_pieces: int = 10,
    beam_width: int = 24,
) -> Anchor | None:
    """Beam-search a curve-heavy sequence matching the corner's turn and path."""
    entry_i = corner.start_i
    entry = Pose(cl.points[entry_i][0], cl.points[entry_i][1], cl.heading(entry_i))
    target_turn = corner.signed_turn
    target_len = corner.arc_length
    end_i = corner.end_i

    def score_state(seq: list[str], pose: Pose, us: Counter) -> float:
        idx, dist = cl.closest(pose.x, pose.y, start=entry_i, window=max(100, end_i - entry_i + 60))
        prog = cl.s[idx] - cl.s[entry_i]
        turn = normalize_heading(pose.heading_degrees - entry.heading_degrees)
        # Must stay on the red line — chord cuts are expensive
        sc = -dist * 8.0
        sc -= abs(turn - target_turn) * 1.8
        # Reward progress along the FULL corner arc (not Euclidean shortcut)
        frac = prog / max(target_len, 1.0)
        sc += min(frac, 1.05) * 120.0
        if frac < 0.55 and len(seq) >= 4:
            sc -= 60.0  # lagging on centreline = taking a shortcut
        if prog > target_len * 1.3:
            sc -= (prog - target_len) * 2.5
        # No full-circle collapse
        loop_dist = math.hypot(pose.x - entry.x, pose.y - entry.y)
        if abs(turn) > 200 and loop_dist < 250:
            sc -= 500.0
        if abs(turn) > abs(target_turn) + 60:
            sc -= (abs(turn) - abs(target_turn)) * 2.5
        c156 = sum(1 for c in seq if c.startswith("C156"))
        if c156 >= 3:
            sc -= 100.0 * (c156 - 2)
        # Finished corner: on centreline near end_i
        if idx >= end_i - 8 and dist < 80:
            sc += 150.0
            sc -= abs(normalize_heading(pose.heading_degrees - cl.heading(min(idx, len(cl.points) - 2)))) * 2.0
        return sc

    # beam: (score, seq, pose, used)
    beam: list[tuple[float, list[str], Pose, Counter]] = [(0.0, [], entry, used.copy())]
    best: tuple[float, list[str], Pose, Counter] | None = None

    for depth in range(max_pieces):
        nxt: list[tuple[float, list[str], Pose, Counter]] = []
        seen: set[tuple] = set()
        for sc0, seq, pose, us in beam:
            for code in _curve_candidates(get_part, avail, us):
                # Prefer curves matching turn direction early
                p = get_part(code)
                if isinstance(p.geometry, CurveGeometry):
                    ang = abs(p.geometry.angle_degrees)
                    signed = -ang if code.endswith("R") else ang
                    if abs(target_turn) > 30 and signed * target_turn < 0 and depth < 3:
                        continue  # wrong direction at start of hairpin
                np = advance(pose, p)
                nus = us.copy()
                nus[base_id(code)] += 1
                key = (round(np.x / 20), round(np.y / 20),
                       round(normalize_heading(np.heading_degrees) / 11.25))
                if key in seen:
                    continue
                seen.add(key)
                nseq = seq + [code]
                sc = score_state(nseq, np, nus)
                nxt.append((sc, nseq, np, nus))
        if not nxt:
            break
        nxt.sort(key=lambda t: -t[0])
        beam = nxt[:beam_width]
        # Track best that has roughly matched the corner
        for sc, seq, pose, us in beam:
            idx, dist = cl.closest(pose.x, pose.y, start=entry_i, window=end_i - entry_i + 60)
            turn = normalize_heading(pose.heading_degrees - entry.heading_degrees)
            if dist < 120 and abs(turn - target_turn) < 35 and idx >= (entry_i + end_i) // 2:
                if best is None or sc > best[0]:
                    best = (sc, seq, pose, us)

    if best is None and beam:
        sc, seq, pose, us = beam[0]
        best = (sc, seq, pose, us)
    if best is None or not best[1]:
        return None
    sc, seq, exit_pose, _ = best
    return Anchor(corner, seq, entry, exit_pose, sc)


def place_all_anchors(
    cl: Centreline,
    corners: list[CornerCluster],
    get_part: Callable,
    avail: dict[str, int],
) -> tuple[list[Anchor], Counter]:
    used: Counter = Counter()
    anchors: list[Anchor] = []
    for corner in corners:
        a = place_anchor(cl, corner, get_part, avail, used)
        if a is None:
            continue
        for c in a.sequence:
            used[base_id(c)] += 1
        anchors.append(a)
    return anchors, used


# ---------------------------------------------------------------------------
# 2. Gap-filling with vector mending
# ---------------------------------------------------------------------------

def _straight_candidates(get_part, avail, used) -> list[str]:
    out = []
    for c in ("C8205", "C8207", "C8200", "C8236", "C8204L", "C8204R", "C8206L", "C8206R"):
        p = get_part(c)
        if p is None or p.geometry is None:
            continue
        if used[base_id(c)] >= avail.get(base_id(c), 0):
            continue
        out.append(c)
    return out


def fill_gap(
    start_pose: Pose,
    end_pose: Pose,
    cl: Centreline,
    get_part: Callable,
    avail: dict[str, int],
    used: Counter,
    max_pieces: int = 22,
    beam_width: int = 28,
) -> list[str]:
    """Connect two poses along the centreline with sweeping curves, not pure straights.

    When the reference bends between anchors, prefer mild curves (C8234/C8204/C8010)
    that match local centreline heading; block long straights across bends.
    """
    si, _ = cl.closest(start_pose.x, start_pose.y, start=0, window=len(cl.points))
    ei, _ = cl.closest(end_pose.x, end_pose.y, start=max(0, si - 5), window=len(cl.points))
    if ei <= si:
        ei = min(si + 40, len(cl.points) - 1)

    def ref_heading_ahead(pose: Pose, look_mm: float = 220.0) -> tuple[float, int]:
        idx, _ = cl.closest(pose.x, pose.y, start=0, window=len(cl.points))
        target_s = cl.s[idx] + look_mm
        j = idx
        while j < len(cl.s) - 1 and cl.s[j] < target_s:
            j += 1
        return cl.heading(min(j, len(cl.points) - 2)), idx

    def cost(pose: Pose) -> float:
        pos = math.hypot(pose.x - end_pose.x, pose.y - end_pose.y)
        head = abs(normalize_heading(pose.heading_degrees - end_pose.heading_degrees))
        idx, dist = cl.closest(pose.x, pose.y, start=0, window=len(cl.points))
        prog = cl.s[min(idx, len(cl.s) - 1)] - cl.s[si]
        target_prog = max(cl.s[ei] - cl.s[si], 1.0)
        return dist * 7.5 + pos * 0.5 + head * 4.0 - min(prog, target_prog) * 0.25

    candidates: list[str] = []
    for c in (
        "C8234L", "C8234R", "C8204L", "C8204R", "C8010L", "C8010R",
        "C8206L", "C8206R", "C187L", "C187R", "C8235L", "C8235R",
        "C156L", "C156R", "C8236", "C8200", "C8207", "C8205",
    ):
        p = get_part(c)
        if p is None or p.geometry is None:
            continue
        candidates.append(c)

    beam: list[tuple[float, list[str], Pose, Counter]] = [
        (cost(start_pose), [], start_pose, used.copy())
    ]
    best = beam[0]

    for _depth in range(max_pieces):
        if best[0] < 45:
            break
        nxt: list[tuple[float, list[str], Pose, Counter]] = []
        seen: set[tuple] = set()
        for _sc0, seq, pose, us in beam:
            ref_h, idx = ref_heading_ahead(pose, 220.0)
            turn_needed = normalize_heading(ref_h - pose.heading_degrees)
            for code in candidates:
                if us[base_id(code)] >= avail.get(base_id(code), 0):
                    continue
                p = get_part(code)
                if isinstance(p.geometry, StraightGeometry):
                    # No long straights across a bend
                    if abs(turn_needed) > 16 and p.geometry.length >= 300:
                        continue
                    if abs(turn_needed) > 28 and p.geometry.length >= 150:
                        continue
                if isinstance(p.geometry, CurveGeometry):
                    ang = abs(p.geometry.angle_degrees)
                    signed = -ang if code.endswith("R") else ang
                    if abs(turn_needed) > 12 and signed * turn_needed < 0 and abs(signed) > 20:
                        continue
                np = advance(pose, p)
                nidx, ndist = cl.closest(np.x, np.y, start=max(0, idx - 5), window=150)
                if ndist > 180:
                    continue
                rem = math.hypot(pose.x - end_pose.x, pose.y - end_pose.y)
                if math.hypot(np.x - end_pose.x, np.y - end_pose.y) > rem + 420 and nidx > ei + 15:
                    continue
                nus = us.copy()
                nus[base_id(code)] += 1
                key = (
                    round(np.x / 25),
                    round(np.y / 25),
                    round(normalize_heading(np.heading_degrees) / 12),
                )
                if key in seen:
                    continue
                seen.add(key)
                sc = cost(np)
                if isinstance(p.geometry, CurveGeometry) and abs(turn_needed) > 8:
                    sc -= 8.0  # reward following the sweep
                nxt.append((sc, seq + [code], np, nus))
        if not nxt:
            break
        nxt.sort(key=lambda t: t[0])
        beam = nxt[:beam_width]
        if beam[0][0] < best[0]:
            best = beam[0]

    return best[1]


def assemble_corner_first(
    cl: Centreline,
    anchors: list[Anchor],
    get_part: Callable,
    avail: dict[str, int],
    used: Counter,
) -> list[str]:
    """Order anchors by centreline s, fill gaps from S/F through anchors back to S/F."""
    if not anchors:
        return []

    # Sort by position on centreline
    def anchor_s(a: Anchor) -> float:
        return cl.s[a.corner.start_i]

    anchors = sorted(anchors, key=anchor_s)
    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    sequence: list[str] = []
    pose = start
    local_used = used.copy()

    for a in anchors:
        # gap from current pose to anchor entry
        gap_seq = fill_gap(pose, a.entry_pose, cl, get_part, avail, local_used)
        sequence.extend(gap_seq)
        for c in gap_seq:
            local_used[base_id(c)] += 1
            pose = advance(pose, get_part(c))
        # snap: use designed anchor sequence from its entry
        # Re-place anchor from *actual* pose if drifted
        if math.hypot(pose.x - a.entry_pose.x, pose.y - a.entry_pose.y) > 80:
            # small mend only
            mend = fill_gap(pose, a.entry_pose, cl, get_part, avail, local_used, max_pieces=8)
            sequence.extend(mend)
            for c in mend:
                local_used[base_id(c)] += 1
                pose = advance(pose, get_part(c))
        for c in a.sequence:
            if local_used[base_id(c)] >= avail.get(base_id(c), 0):
                # skip missing; try continue
                continue
            sequence.append(c)
            local_used[base_id(c)] += 1
            pose = advance(pose, get_part(c))

    # close back to start
    close = fill_gap(pose, start, cl, get_part, avail, local_used, max_pieces=30)
    sequence.extend(close)
    return sequence


# ---------------------------------------------------------------------------
# 3. Local window re-optimisation
# ---------------------------------------------------------------------------

def mean_centreline_distance(sequence: list[str], get_part: Callable, cl: Centreline, start: Pose) -> list[float]:
    """Per-piece mean distance of exit pose to centreline."""
    dists = []
    pose = start
    for c in sequence:
        pose = advance(pose, get_part(c))
        _, d = cl.closest(pose.x, pose.y, start=0, window=len(cl.points))
        dists.append(d)
    return dists


def local_window_reopt(
    sequence: list[str],
    cl: Centreline,
    get_part: Callable,
    avail: dict[str, int],
    window: int = 6,
    passes: int = 2,
) -> list[str]:
    """Re-solve the worst centreline-deviation windows in place."""
    if len(sequence) < window + 2:
        return sequence

    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    seq = list(sequence)

    for _ in range(passes):
        dists = mean_centreline_distance(seq, get_part, cl, start)
        if not dists:
            break
        # worst window start
        worst_i, worst_sum = 0, -1.0
        for i in range(0, len(dists) - window + 1):
            sm = sum(dists[i : i + window])
            if sm > worst_sum:
                worst_sum, worst_i = sm, i

        # poses at window boundaries
        pose = start
        for c in seq[:worst_i]:
            pose = advance(pose, get_part(c))
        entry = pose
        for c in seq[worst_i : worst_i + window]:
            pose = advance(pose, get_part(c))
        exit_pose = pose

        # inventory excluding pieces outside window
        used_out = Counter(base_id(c) for c in seq[:worst_i] + seq[worst_i + window :])
        # re-fill window
        new_mid = fill_gap(entry, exit_pose, cl, get_part, avail, used_out, max_pieces=window + 6, beam_width=40)
        if not new_mid:
            continue

        # accept if better mean distance
        trial = seq[:worst_i] + new_mid + seq[worst_i + window :]
        old_mean = sum(dists[worst_i : worst_i + window]) / window
        new_dists = mean_centreline_distance(trial, get_part, cl, start)
        new_window = new_dists[worst_i : worst_i + len(new_mid)]
        new_mean = sum(new_window) / max(len(new_window), 1) if new_window else 1e9
        # also check closure didn't explode
        end = start
        for c in trial:
            end = advance(end, get_part(c))
        old_end = start
        for c in seq:
            old_end = advance(old_end, get_part(c))
        old_close = math.hypot(old_end.x - start.x, old_end.y - start.y)
        new_close = math.hypot(end.x - start.x, end.y - start.y)
        if new_mean < old_mean * 0.92 and new_close <= old_close * 1.15 + 50:
            seq = trial

    return seq


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------

@dataclass
class CornerFirstResult:
    sequence: list[str]
    corners: list[CornerCluster]
    anchors: list[Anchor]
    metrics: dict = field(default_factory=dict)


def corner_first_build(
    cl: Centreline,
    get_part: Callable,
    avail: dict[str, int],
    min_turn_deg: float = 50.0,
) -> CornerFirstResult:
    """Full pipeline: detect corners → anchors → gap fill → local reopt."""
    corners = detect_corners(cl, min_turn_deg=min_turn_deg)
    anchors, used = place_all_anchors(cl, corners, get_part, avail)
    sequence = assemble_corner_first(cl, anchors, get_part, avail, used)
    if not sequence:
        # fallback empty
        return CornerFirstResult([], corners, anchors, {"error": "no sequence"})

    sequence = local_window_reopt(sequence, cl, get_part, avail)

    start = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    end = start
    for c in sequence:
        end = advance(end, get_part(c))
    pos = math.hypot(end.x - start.x, end.y - start.y)
    head = abs(normalize_heading(end.heading_degrees - start.heading_degrees))
    dists = mean_centreline_distance(sequence, get_part, cl, start)
    mean_d = sum(dists) / max(len(dists), 1)
    metrics = {
        "n_corners": len(corners),
        "n_anchors": len(anchors),
        "n_pieces": len(sequence),
        "pos_mm": pos,
        "head_deg": head,
        "mean_centreline_mm": mean_d,
        "length_mm": path_length([get_part(c) for c in sequence]),
    }
    return CornerFirstResult(sequence, corners, anchors, metrics)
