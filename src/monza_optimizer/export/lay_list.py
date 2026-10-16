"""Assembly lay-list: piece order with official SKU and L/R."""

from __future__ import annotations

from typing import Any, Callable

from monza_optimizer.catalog.parts import base_id
from monza_optimizer.optimize.inventory_picker import LETTER_UNDER


def hand_of(sku: str) -> str | None:
    if sku.endswith("L"):
        return "L"
    if sku.endswith("R"):
        return "R"
    return None


def hand_word(sku: str) -> str:
    h = hand_of(sku)
    if h == "L":
        return "left"
    if h == "R":
        return "right"
    return "-"


def lay_rows(sequence: list[str], get_part: Callable | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, sku in enumerate(sequence, start=1):
        part = get_part(sku) if get_part else None
        name = getattr(part, "name", None) or sku
        rows.append(
            {
                "step": i,
                "sku": sku,
                "base": base_id(sku),
                "hand": hand_of(sku),
                "hand_label": hand_word(sku),
                "name": name,
                "letter_under_track": LETTER_UNDER.get(sku) or LETTER_UNDER.get(base_id(sku)),
            }
        )
    return rows


def lay_text(rows: list[dict[str, Any]], title: str = "Lay list") -> str:
    lines = [title, "step  sku       L/R    name", "-" * 56]
    for r in rows:
        hand = r.get("hand") or "-"
        lines.append(f"{r['step']:4d}  {r['sku']:<8}  {hand:<4}  {r['name']}")
    return "\n".join(lines) + "\n"


def lay_payload(sequence: list[str], get_part: Callable | None = None, title: str = "Lay list") -> dict[str, Any]:
    rows = lay_rows(sequence, get_part)
    return {
        "title": title,
        "piece_count": len(rows),
        "rows": rows,
        "text": lay_text(rows, title),
    }
