"""Closed oval from a small official box when the named-circuit follow collapses."""

from __future__ import annotations

from typing import Callable

from monza_optimizer.geometry.path import compute_track_path, is_closed
from monza_optimizer.geometry.pose import Pose


def closed_kit_loop(inventory: dict[str, int], get_part: Callable) -> list[str]:
    """Official-style oval: two straights, 180 end, two straights, 180 end.

    Flying Start (C1446M mapped to 4x C8205 + 8x C8206L + 8x C8206R) yields
    4x C8205 + 4x C8206L + 4x C8206R. Extra curves stay in the box.
    """
    inv = {str(k): int(v) for k, v in (inventory or {}).items() if int(v) > 0}
    n_s = inv.get("C8205", 0)
    if n_s < 2:
        return []
    side = min(2, n_s // 2)
    n_l = inv.get("C8206L", 0)
    n_r = inv.get("C8206R", 0)
    if n_l >= 4 and n_r >= 4:
        end_a, end_b = ["C8206L"] * 4, ["C8206R"] * 4
    elif n_l >= 8:
        end_a = end_b = ["C8206L"] * 4
    elif n_r >= 8:
        end_a = end_b = ["C8206R"] * 4
    else:
        return []
    seq = ["C8205"] * side + end_a + ["C8205"] * side + end_b
    parts = [get_part(c) for c in seq]
    if any(p is None for p in parts):
        return []
    path = compute_track_path(parts, start=Pose(0.0, 0.0, 0.0))
    if not is_closed(path, pos_tol_mm=80.0, head_tol_deg=12.0):
        return []
    return seq
