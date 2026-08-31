"""Tick-box owned inventory. One stepper per moulding."""

from __future__ import annotations

from typing import Any

from monza_optimizer.catalog.parts import base_id
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
    "C8205": "B",
    "C8206": "C",
    "C8207": "D",
    "C8234": "U",
    "C8235": "S",
    "C8236": "T",
    "C8201": "J",
    "C187": None,
    "C8010": None,
}
LETTER_UNDER.update(LETTER_EXTRA)

REVERSIBLE = {
    "C8206", "C8204", "C8234", "C8235", "C8201", "C8202",
    "C187", "C8010",
}

OFFICIAL_SHOP = {
    "C8205": "https://uk.scalextric.com/products/standard-straight-350mm-x-2-c8205",
    "C8206": "https://uk.scalextric.com/products/radius-2-curve-45-x-2-c8206",
    "C8201": "https://uk.scalextric.com/products/radius-1-hairpin-curve-90-x-2-c8201",
    "C8210": "https://uk.scalextric.com/products/straight-crossover-c8210",
}

HERO_HEADLINE = (
    "Build Monza / Monaco / Silverstone with what you own. "
    "We will tell you the pieces that finish it. "
    "This is a demo of the optimiser: one inventory, four ambition levels, "
    "from a small shop list to a closer layout."
)

CARDS: list[dict[str, Any]] = [
    {"sku": "C8205", "name": "Standard straight 350 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Letter B. Pack is two pieces."},
    {"sku": "C8207", "name": "Half straight 175 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Letter D."},
    {"sku": "C8200", "name": "Quarter straight 87 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Letter F."},
    {"sku": "C8236", "name": "Short straight 78 mm", "family": "straight", "group": "Straights", "hand": None, "hint": "Letter T."},
    {"sku": "C8206", "name": "R2 curve 45 (C8206)", "family": "r2", "group": "Radius 2", "hand": None, "hint": "Letter C. One moulding."},
    {"sku": "C8234", "name": "R2 curve 22.5 (C8234)", "family": "r2", "group": "Radius 2", "hand": None, "hint": "Letter U. One moulding."},
    {"sku": "C8204", "name": "R3 curve 22.5 (C8204)", "family": "r3", "group": "Radius 3", "hand": None, "hint": "Letter N. One moulding."},
    {"sku": "C8235", "name": "R4 curve 22.5 (C8235)", "family": "r4", "group": "Radius 4", "hand": None, "hint": "Letter S. One moulding."},
    {"sku": "C187", "name": "Banked curve 45 (C187)", "family": "banked", "group": "Specials", "hand": None, "hint": "Raised outer edge."},
    {"sku": "C8010", "name": "Chicane curve 22.5 (C8010)", "family": "chicane", "group": "Chicanes", "hand": None, "hint": "Offset lane bend."},
]


def _card(raw: dict[str, Any]) -> dict[str, Any]:
    sku = raw["sku"]
    art = urls_for_sku(sku)
    if not art.get("thumb_png"):
        art = urls_for_sku(sku + "L") or art
    return {
        "sku": sku,
        "name": raw["name"],
        "family": raw["family"],
        "group": raw["group"],
        "hand": None,
        "reversible": sku in REVERSIBLE,
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


def picker_cards() -> list[dict[str, Any]]:
    seen = set()
    out = []
    for raw in CARDS + EXTRA_CARDS:
        if raw["sku"] in {"C156", "C156L", "C156R"}:
            continue
        if raw["sku"] in seen:
            continue
        seen.add(raw["sku"])
        out.append(_card(raw))
    return out


def ticks_to_inventory(ticks: list[dict[str, Any]] | dict[str, int] | None) -> dict[str, int]:
    if ticks is None:
        return {}
    raw: dict[str, int] = {}
    if isinstance(ticks, dict):
        for k, v in ticks.items():
            sku = str(k).strip().upper()
            qty = max(0, int(v))
            if sku and qty:
                raw[sku] = raw.get(sku, 0) + qty
    else:
        for row in ticks:
            sku = str(row.get("sku") or row.get("id") or "").upper()
            qty = int(row.get("qty") or row.get("quantity") or 0)
            if sku and qty > 0:
                raw[sku] = raw.get(sku, 0) + qty
    out: dict[str, int] = {}
    for sku, qty in raw.items():
        root = base_id(sku)
        if root in REVERSIBLE:
            out[root] = out.get(root, 0) + qty
        else:
            out[sku] = out.get(sku, 0) + qty
    return {k: v for k, v in out.items() if v > 0}


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
        "hero": HERO_HEADLINE,
        "title": "List the parts you already own by entering number of parts in the picker below",
        "blurb": "",
        "how_to_count": "",
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
            "example": {"track_id": "monza", "accuracy_level": "B", "inventory": {"C8205": 4, "C8206": 16, "C8201": 2}},
        },
    }
