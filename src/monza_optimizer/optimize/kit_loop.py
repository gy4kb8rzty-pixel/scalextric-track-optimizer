"""Closed oval from a small official box when the named-circuit follow collapses."""

from __future__ import annotations

from typing import Callable

from monza_optimizer.geometry.path import compute_track_path, is_closed
from monza_optimizer.geometry.pose import Pose


def closed_kit_loop(inventory: dict[str, int], get_part: Callable) -> list[str]:
    """Official START oval: two straights, 180, two straights, 180.

    Both 180s must be the SAME hand. 4x L then 4x R does not close.
    Flying Start has 8 L and 8 R; we use 8 of one hand and leave the rest.
    """
    inv = {str(k): int(v) for k, v in (inventory or {}).items() if int(v) > 0}
    n_s = inv.get("C8205", 0)
    if n_s < 2:
        return []
    side = min(2, n_s // 2)
    n_l = inv.get("C8206L", 0)
    n_r = inv.get("C8206R", 0)
    if n_l >= 8:
        end = ["C8206L"] * 4
    elif n_r >= 8:
        end = ["C8206R"] * 4
    else:
        return []
    seq = ["C8205"] * side + end + ["C8205"] * side + end
    parts = [get_part(c) for c in seq]
    if any(p is None for p in parts):
        return []
    path = compute_track_path(parts, start=Pose(0.0, 0.0, 0.0))
    if not is_closed(path, pos_tol_mm=80.0, head_tol_deg=12.0):
        return []
    return seq
