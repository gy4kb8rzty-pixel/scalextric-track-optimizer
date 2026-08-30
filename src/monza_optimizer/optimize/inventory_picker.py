"""Tick-box owned inventory for the Lovable wrapper."""

from __future__ import annotations

from typing import Any

from monza_optimizer.optimize.flying_start import (
    FLYING_START_NOTE,
    FLYING_START_SET_ID,
    flying_start_inventory,
)
from monza_optimizer.optimize.inventory_extra import EXTRA_CARDS, LETTER_EXTRA

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

THUMB_BMP = {
    "C8205": "c8205.bmp",
    "C8207": "c8207p.bmp",
    "C8200": "c8200p.bmp",
    "C8236": "c8236p.bmp",
    "C8206": "512x512_C8206.bmp",
    "C8206L": "512x512_C8206.bmp",
    "C8206R": "c8206r.bmp",
    "C8204L": "c8204lp.bmp",
    "C8204R": "c8204rp.bmp",
    "C8235L": "c8235lp.bmp",
    "C8235R": "c8235rp.bmp",
    "C8234L": "c8234lp.bmp",
    "C8234R": "c8234rp.bmp",
    "C156L": "c156lp.bmp",
    "C156R": "c156rp.bmp",
    "C8010L": "c8010lp.bmp",
    "C8010R": "c8010r.bmp",
}

OFFICIAL_SHOP = {
    "C8205": "https://uk.scalextric.com/products/standard-straight-350mm-x-2-c8205",
    "C8206": "https://uk.scalextric.com/products/radius-2-curve-45-x-2-c8206",
    "C8206L": "https://uk.scalextric.com/products/radius-2-curve-45-x-2-c8206",
    "C8206R": "https://uk.scalextric.com/products/radius-2-curve-45-x-2-c8206",
    "C8207": "https://uk.scalextric.com/products/half-straight-175mm-x-2-c8207",
    "C8235": "https://uk.scalextric.com/products/radius-4-curve-22-5-x-2-c8235",
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

_FAMILY_FILL = {
    "straight": "#2b2b2b",
    "r1": "#c45c26",
    "r2": "#1f6feb",
    "r3": "#2f9e44",
    "r4": "#9b51e0",
    "banked": "#b42318",
    "chicane": "#c11574",
    "special": "#44546A",
    "digital": "#0563C1",
}


def _svg_icon(family: str, hand: str | None) -> str:
    fill = _FAMILY_FILL.get(family, "#444")
    if family in ("straight", "special", "digital"):
        body = '<rect x="18" y="44" width="92" height="40" rx="4" fill="%s"/>' % fill
        slots = '<line x1="18" y1="54" x2="110" y2="54" stroke="#f4d35e" stroke-width="3"/>'
        slots += '<line x1="18" y1="74" x2="110" y2="74" stroke="#f4d35e" stroke-width="3"/>'
    else:
        sweep = "1" if hand != "R" else "0"
        body = (
            f'<path d="M 28 96 A 48 48 0 0 {sweep} 100 36 L 88 28 A 36 36 0 0 {1 if sweep == "0" else 0} 36 88 Z" '
            f'fill="{fill}"/>'
        )
        slots = ""
    label = (hand or "")[:1]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">'
        '<rect width="128" height="128" rx="16" fill="#f3f1ea"/>'
        f"{body}{slots}"
        f'<text x="10" y="22" font-size="14" font-family="sans-serif" fill="#222">{label}</text>'
        "</svg>"
    )


def _card(raw: dict[str, Any]) -> dict[str, Any]:
    sku = raw["sku"]
    bmp = THUMB_BMP.get(sku)
    return {
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
        "thumb_bmp": bmp,
        "thumb_url": f"/part-art/{bmp}" if bmp else None,
        "thumb_svg": _svg_icon(raw["family"], raw["hand"]),
        "shop_url": OFFICIAL_SHOP.get(sku),
        "in_flying_start": sku in flying_start_inventory(),
        "flying_start_qty": flying_start_inventory().get(sku, 0),
    }


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
        "blurb": (
            "Match the top-view picture to the piece in your box. "
            "The letter moulded under Sport track is the fastest check. "
            "Leave a box at 0 if you do not have that SKU. "
            "Empty box clears every counter so you can type your own collection."
        ),
        "how_to_count": (
            "Count single pieces, not shop packs. A C8205 pack is two straights. "
            "Curves: hold the connectors toward you; the slot bend is L or R."
        ),
        "presets": [
            {
                "id": "empty_box",
                "label": "Empty box — reset",
                "inventory": zeros,
                "replace": True,
                "note": "Sets every SKU to 0. Then type the pieces on your table.",
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
            "example": {"track_id": "monza", "accuracy_level": "B", "inventory": {"C8205": 12, "C8206L": 4}},
        },
    }
