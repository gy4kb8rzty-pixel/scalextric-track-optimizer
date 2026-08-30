"""Editable owned-inventory book. Server is stateless; the client stores the book.

After a Shop purchase the wrapper POSTs the lines bought. The book returns the
new owned map so the next /optimize uses the updated box.
"""

from __future__ import annotations

from typing import Any

from monza_optimizer.catalog.parts import base_id


def _clean(raw: dict[str, Any] | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for key, val in dict(raw or {}).items():
        sku = str(key).strip().upper()
        if sku.endswith("P"):
            sku = sku[:-1]
        qty = int(val or 0)
        if sku and qty > 0:
            out[sku] = out.get(sku, 0) + qty
    return out


def apply_purchase(owned: dict[str, int] | None, purchased: dict[str, int] | None) -> dict[str, int]:
    """Add bought official pieces to the box. Purchases are single pieces."""
    box = _clean(owned)
    for sku, qty in _clean(purchased).items():
        box[sku] = box.get(sku, 0) + qty
    return {k: box[k] for k in sorted(box)}


def inventory_status(
    owned: dict[str, int] | None,
    *,
    used: dict[str, int] | None = None,
    missing: dict[str, int] | None = None,
    leftover: dict[str, int] | None = None,
    track_id: str | None = None,
    accuracy_level: str | None = None,
) -> dict[str, Any]:
    box = _clean(owned)
    used_n = _clean(used)
    miss_n = _clean(missing)
    left_n = _clean(leftover)
    if not left_n and used_n:
        for sku, have in box.items():
            take = used_n.get(base_id(sku), used_n.get(sku, 0))
            if have > take:
                left_n[sku] = have - take
    piece_count = sum(box.values())
    sku_count = len(box)
    still_missing = sum(miss_n.values())
    return {
        "owned": box,
        "piece_count": piece_count,
        "sku_count": sku_count,
        "used_on_last_lap": used_n,
        "leftover_after_last_lap": left_n,
        "still_to_buy": miss_n,
        "still_to_buy_pieces": still_missing,
        "box_ready_for_same_lap": still_missing == 0 and bool(used_n),
        "track_id": track_id,
        "accuracy_level": accuracy_level,
        "note": (
            "This book lives on the phone until the wrapper saves it. "
            "After a Shop order, POST /inventory/apply-purchase with the lines bought."
        ),
    }
