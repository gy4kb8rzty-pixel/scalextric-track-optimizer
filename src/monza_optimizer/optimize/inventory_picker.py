"""Tick-box owned inventory for the Lovable wrapper."""

from __future__ import annotations

from typing import Any

from monza_optimizer.optimize.flying_start import (
    FLYING_START_NOTE,
    FLYING_START_SET_ID,
    flying_start_inventory,
)
from monza_optimizer.optimize.inventory_extra import EXTRA_CARDS, LETTER_EXTRA
from monza_optimizer.optimize.part_art import urls_for_sku

LETTER_UNDER = {
    "C8200": "F",
    "C8204": "N",
    "C8204L": "N",
    "C8204R": "N",
    "C8205": "B",
    "C8206": "C",
    "C8206L": "C",
    "C8206R": "C",
    "C8207": "D",
    "C8234": "U",
    "C8234L": "U",
    "C8234R": "U",
    "C8235": "S",
    "C8235L": "S",
    "C8235R": "S",
    "C8236": "T",
}
LETTER_UNDER.update(LETTER_EXTRA)

OFFICIAL_SHOP = {
    "C8205": "https://uk.scalextric.com/products/standard-straight-350mm-x-2-c8205",
    "C8206": "https://uk.scalextric.com/products/radius-2-curve-45-x-2-c8206",
    "C8210": "https://uk.scalextric.com/products/straight-crossover-c8210",
}

CARDS: list[dict[str, Any]] = [
    {"sku": "C8205", "name": "Standard straight 350 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Long black straight. Letter B underneath."},
    {"sku": "C8207", "name": "Half straight 175 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Half the standard straight. Letter D underneath."},
    {"sku": "C8200", "name": "Quarter straight 87 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Short filler. Letter F underneath."},
    {"sku": "C8236", "name": "Short straight 78 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Tiny closer. Letter T underneath."},
    {"sku": "C8206L", "name": "R2 curve 45 left", "family": "r2", "group": "Radius 2", "hand": "L", "hint": "Standard starter bend, turns left. Letter C underneath."},
    {"sku": "C8206R", "name": "R2 curve 45 right", "family": "r2", "group": "Radius 2", "hand": "R", "hint": "Standard starter bend, turns right. Letter C underneath."},
    {"sku": "C8234L", "name": "R2 curve 22.5 left", "family": "r2", "group": "Radius 2", "hand": "L", "hint": "Shallower R2. Letter U underneath."},
    {"sku": "C8234R", "name": "R2 curve 22.5 right", "family": "r2", "group": "Radius 2", "hand": "R", "hint": "Shallower R2. Letter U underneath."},
    {"sku": "C8204L", "name": "R3 curve 22.5 left", "family": "r3", "group": "Radius 3", "hand": "L", "hint": "Wider sweep. Letter N underneath."},
    {"sku": "C8204R", "name": "R3 curve 22.5 right", "family": "r3", "group": "Radius 3", "hand": "R", "hint": "Wider sweep. Letter N underneath."},
    {"sku": "C8235L", "name": "R4 curve 22.5 left", "family": "r4", "group": "Radius 4", "hand": "L", "hint": "Outer sweep. Letter S underneath."},
    {"sku": "C8235R", "name": "R4 curve 22.5 right", "family": "r4", "group": "Radius 4", "hand": "R", "hint": "Outer sweep. Letter S underneath."},
    {"sku": "C156L", "name": "R1 Classic 90 left C156", "family": "r1", "group": "Radius 1", "hand": "L", "hint": "Classic R1 90. Sport hairpin is C8201."},
    {"sku": "C156R", "name": "R1 Classic 90 right C156", "family": "r1", "group": "Radius 1", "hand": "R", "hint": "Classic R1 90. Sport hairpin is C8201."},
    {"sku": "C187L", "name": "Banked curve 45 left", "family": "banked", "group": "Specials", "hand": "L", "hint": "Raised outer edge."},
    {"sku": "C187R", "name": "Banked curve 45 right", "family": "banked", "group": "Specials", "hand": "R", "hint": "Raised outer edge."},
    {"sku": "C8010L", "name": "Chicane curve 22.5 left", "family": "chicane", "group": "Chicanes", "hand": "L", "hint": "Offset lane chicane bend."},
    {"sku": "C8010R", "name": "Chicane curve 22.5 right", "family": "chicane", "group": "Chicanes", "hand": "R", "hint": "Offset lane chicane bend."},
]


def _card(raw: dict[str, Any]) -> dict[str, Any]:
    sku = raw["sku"]
    art = urls_for_sku(sku)
    card = {
        "sku": sku,
        "name": raw["name"],
        "family": raw["family"],
        "group": raw["group"],
        "hand": raw["hand"],
        "letter_under_track": LETTER_UNDER.get(sku),
        "hint": raw["hint"],
        "tickable": True,
        "qty_min": 0,
        "qty_max": 80,
        "qty_step": 1,
        "default_qty": 0,
        "thumb_bmp": art["thumb_bmp"],
        "thumb_url": art["thumb_url"],
        "thumb_png": art["thumb_png"],
        "shop_url": OFFICIAL_SHOP.get(sku),
        "in_flying_start": sku in flying_start_inventory(),
        "flying_start_qty": flying_start_inventory().get(sku, 0),
    }
    return card


def picker_cards() -> list[dict[str, Any]]:
    return [_card(c) for c in CARDS + EXTRA_CARDS]


def ticks_to_inventory(ticks: list[dict[str, Any]] | dict[str, int] | None) -> dict[str, int]:
    if ticks is None:
        return {}
    if isinstance(ticks, dict):
        return {str(k): max(0, int(v)) for k, v in ticks.items() if int(v) > 0}
    out: dict[str, int] = {}
    for row in ticks:
        sku = str(row.get("sku") or row.get("id") or "").upper()
        qty = int(row.get("qty") or row.get("quantity") or 0)
        if sku and qty > 0:
            out[sku] = out.get(sku, 0) + qty
    return out


def picker_payload() -> dict[str, Any]:
    cards = picker_cards()
    groups: list[dict[str, Any]] = []
    seen: dict[str, list] = {}
    for card in cards:
        seen.setdefault(card["group"], []).append(card)
    for name, items in seen.items():
        groups.append({"id": name.lower().replace(" ", "_"), "label": name, "parts": items})
    zeros = {card["sku"]: 0 for card in cards}
    return {
        "title": "Tick the pieces you already own",
        "blurb": "Match the top-view photo to the piece in your box.",
        "how_to_count": "Count single pieces, not shop packs.",
        "presets": [
            {
                "id": "empty_box",
                "label": "Empty box — reset",
                "inventory": zeros,
                "replace": True,
                "note": "Sets every SKU to 0.",
            },
            {
                "id": "flying_start",
                "label": "Flying Start — official C1446M START Grand Prix",
                "set_id": FLYING_START_SET_ID,
                "inventory": flying_start_inventory(),
                "replace": True,
                "note": FLYING_START_NOTE,
            },
        ],
        "groups": groups,
        "optimize_hint": {
            "path": "/optimize",
            "inventory_field": "inventory",
            "example": {"track_id": "monza", "accuracy_level": "B", "inventory": {"C8205": 12}},
        },
    }
