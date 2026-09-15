"""Hypervolume indicator for Pareto fronts (minimization objectives).

The hypervolume of a set of points is the Lebesgue measure of the region
dominated by the set and bounded by a reference point. All objectives are
treated as **minimization**. Points that do not strictly dominate the
reference point contribute nothing.

Exact algorithms:
  - 1-D: trivial gap to reference
  - 2-D: sort + sweep O(n log n)
  - 3-D: sorted slabs × 2-D HV O(n²)
  - d > 3: recursive dimension reduction (exact; fine for small fronts)

Physical constraints must already be enforced; this module only scores
objective vectors for Pareto archive quality.
"""

from __future__ import annotations

from typing import Sequence


Vector = Sequence[float]
Front = Sequence[Vector]


def dominates(a: Vector, b: Vector) -> bool:
    """True if *a* Pareto-dominates *b* (min objectives, strict on ≥1 axis)."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same dimension")
    strictly_better = False
    for ai, bi in zip(a, b):
        if ai > bi:
            return False
        if ai < bi:
            strictly_better = True
    return strictly_better


def filter_non_dominated(points: Front) -> list[tuple[float, ...]]:
    """Non-dominated subset under minimization (first occurrence kept)."""
    pts = [tuple(float(x) for x in p) for p in points]
    if not pts:
        return []
    dim = len(pts[0])
    if any(len(p) != dim for p in pts):
        raise ValueError("all points must share the same dimension")
    kept: list[tuple[float, ...]] = []
    for i, p in enumerate(pts):
        if any(dominates(q, p) for j, q in enumerate(pts) if j != i):
            continue
        if p not in kept:
            kept.append(p)
    return kept


def _dominates_ref(point: Vector, ref: Vector) -> bool:
    """Every coordinate of *point* is strictly better (smaller) than *ref*."""
    return all(p < r for p, r in zip(point, ref))


def hypervolume_2d(points: Front, reference: Vector) -> float:
    """Exact 2-D hypervolume (minimization).

    Sort non-dominated points by ascending f₁ (envelope has decreasing f₂).
    Sweep left-to-right::

        HV = Σ_i (ref₁ − f₁_i) * (f₂_{i-1} − f₂_i)   with f₂_0 = ref₂
    """
    if len(reference) != 2:
        raise ValueError("reference must be 2-D")
    ref = (float(reference[0]), float(reference[1]))
    pts = [tuple(map(float, p)) for p in points if len(p) == 2 and _dominates_ref(p, ref)]
    if not pts:
        return 0.0
    pts = filter_non_dominated(pts)
    # Non-dominated + sort by f1 ascending ⇒ f2 strictly decreasing
    pts.sort(key=lambda p: (p[0], p[1]))

    hv = 0.0
    prev_f2 = ref[1]
    for f1, f2 in pts:
        if f2 < prev_f2 and f1 < ref[0]:
            hv += (ref[0] - f1) * (prev_f2 - f2)
            prev_f2 = f2
    return max(0.0, hv)


def hypervolume_3d(points: Front, reference: Vector) -> float:
    """Exact 3-D hypervolume via slabs in f₃ × 2-D HV (minimization)."""
    if len(reference) != 3:
        raise ValueError("reference must be 3-D")
    ref = tuple(float(x) for x in reference)
    pts = [tuple(map(float, p)) for p in points if len(p) == 3 and _dominates_ref(p, ref)]
    pts = filter_non_dominated(pts)
    if not pts:
        return 0.0

    pts.sort(key=lambda p: p[2])
    z_bounds = sorted({p[2] for p in pts}) + [ref[2]]
    hv = 0.0
    for i in range(len(z_bounds) - 1):
        z0, z1 = z_bounds[i], z_bounds[i + 1]
        height = z1 - z0
        if height <= 0:
            continue
        # Points with f3 <= z0 participate in this slab's 2-D front
        slice_2d = [(p[0], p[1]) for p in pts if p[2] <= z0 + 1e-15]
        if not slice_2d:
            continue
        hv += hypervolume_2d(slice_2d, (ref[0], ref[1])) * height
    return max(0.0, hv)


def _hypervolume_recursive(
    points: list[tuple[float, ...]],
    reference: tuple[float, ...],
) -> float:
    """Exact recursive HV for arbitrary dimension (exponential in d)."""
    pts = filter_non_dominated([p for p in points if _dominates_ref(p, reference)])
    if not pts:
        return 0.0
    d = len(reference)
    if d == 1:
        return max(0.0, reference[0] - min(p[0] for p in pts))
    if d == 2:
        return hypervolume_2d(pts, reference)
    if d == 3:
        return hypervolume_3d(pts, reference)

    pts = sorted(pts, key=lambda p: p[-1])
    hv = 0.0
    for i, p in enumerate(pts):
        next_z = pts[i + 1][-1] if i + 1 < len(pts) else reference[-1]
        height = next_z - p[-1]
        if height <= 0:
            continue
        subset = [q[:-1] for q in pts[: i + 1]]
        hv += _hypervolume_recursive(subset, reference[:-1]) * height
    return max(0.0, hv)


def hypervolume(
    points: Front,
    reference: Vector,
    *,
    filter: bool = True,
) -> float:
    """Hypervolume of ``points`` with respect to ``reference`` (all min).

    Parameters
    ----------
    points:
        Objective vectors (same dimension as ``reference``).
    reference:
        Point **worse** than the front on every objective (larger for min).
    filter:
        If True, reduce to the non-dominated subset first.
    """
    ref = tuple(float(x) for x in reference)
    pts = [tuple(float(x) for x in p) for p in points]
    if not pts:
        return 0.0
    dim = len(ref)
    if any(len(p) != dim for p in pts):
        raise ValueError("point dimension mismatch with reference")
    if filter:
        pts = filter_non_dominated(pts)
    pts = [p for p in pts if _dominates_ref(p, ref)]
    if not pts:
        return 0.0
    if dim == 1:
        return max(0.0, ref[0] - min(p[0] for p in pts))
    if dim == 2:
        return hypervolume_2d(pts, ref)
    if dim == 3:
        return hypervolume_3d(pts, ref)
    return _hypervolume_recursive(pts, ref)
