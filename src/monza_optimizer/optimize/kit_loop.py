"""Closed oval from a small official box when the named-circuit follow collapses."""

from __future__ import annotations

from typing import Callable

from monza_optimizer.geometry.path import compute_track_path, is_closed
from monza_optimizer.geometry.pose import Pose


def _have(inv: dict[str, int], sku: str) -> int:
    n = int(inv.get(sku, 0))
    n += int(inv.get(sku + "L", 0))
    n += int(inv.get(sku + "R", 0))
    return n


def closed_kit_loop(inventory: dict[str, int], get_part: Callable) -> list[str]:
    inv = {str(k): int(v) for k, v in (inventory or {}).items() if int(v) > 0}
    n_s = _have(inv, "C8205")
    if n_s < 2:
        return []
    side = min(2, n_s // 2)
    if _have(inv, "C8206") < 8:
        return []
    end = ["C8206L"] * 4
    seq = ["C8205"] * side + end + ["C8205"] * side + end
    parts = [get_part(c) for c in seq]
    if any(p is None for p in parts):
        return []
    path = compute_track_path(parts, start=Pose(0.0, 0.0, 0.0))
    if not is_closed(path, pos_tol_mm=80.0, head_tol_deg=12.0):
        return []
    return seq
