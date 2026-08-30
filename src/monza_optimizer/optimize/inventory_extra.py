"""Extra official SKUs. Curve mouldings are unsigned in the picker."""

from __future__ import annotations

from typing import Any

LETTER_EXTRA = {
    "C8201": "J",
    "C8202": "K",
    "C8203": "E",
    "C8210": "P",
    "C8246": "G",
    "C8246A": "G",
    "C8246B": "H",
    "C8295": "W",
    "C7007": "X",
    "C7010": "X",
    "C8234": "U",
}

EXTRA_GEOMETRY: list[dict[str, Any]] = [
    {"id": "C8201L", "name": "R1 hairpin 90 L (C8201)", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": 90.0}},
    {"id": "C8201R", "name": "R1 hairpin 90 R (C8201)", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": -90.0}},
    {"id": "C8202L", "name": "R1 inner 45 L (C8202)", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": 45.0}},
    {"id": "C8202R", "name": "R1 inner 45 R (C8202)", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": -45.0}},
    {"id": "C8203", "name": "R2 racing curve crossover 90", "type": "curve", "verified_geometry": False, "geometry": {"radius": 294.0, "angle_degrees": 90.0}},
    {"id": "C8210", "name": "Straight crossover 90 409 mm", "type": "straight", "verified_geometry": True, "geometry": {"length": 409.0}},
    {"id": "C8006", "name": "Change-over / crossover (Classic)", "type": "straight", "verified_geometry": False, "geometry": {"length": 355.0}},
    {"id": "C8005", "name": "Skid chicane (Classic)", "type": "straight", "verified_geometry": False, "geometry": {"length": 350.0}},
    {"id": "C8009", "name": "Straight chicane extension", "type": "straight", "verified_geometry": False, "geometry": {"length": 350.0}},
    {"id": "C8031A", "name": "Chicane section A", "type": "straight", "verified_geometry": False, "geometry": {"length": 175.0}},
    {"id": "C8031B", "name": "Chicane section B", "type": "straight", "verified_geometry": False, "geometry": {"length": 175.0}},
    {"id": "C8246A", "name": "Side-swipe straight A (G)", "type": "straight", "verified_geometry": True, "geometry": {"length": 350.0}},
    {"id": "C8246B", "name": "Side-swipe straight B (H)", "type": "straight", "verified_geometry": True, "geometry": {"length": 350.0}},
    {"id": "C8295", "name": "Elevated crossover 233 mm", "type": "straight", "verified_geometry": True, "geometry": {"length": 233.0}},
    {"id": "C7004", "name": "Digital accessory C7004", "type": "straight", "verified_geometry": False, "geometry": {"length": 175.0}},
    {"id": "C7000", "name": "Digital / ARC special C7000", "type": "straight", "verified_geometry": False, "geometry": {"length": 175.0}},
    {"id": "C7007", "name": "Digital LC curve R2 90 C7007", "type": "curve", "verified_geometry": False, "geometry": {"radius": 294.0, "angle_degrees": 90.0}},
    {"id": "C7010", "name": "Digital LC curve R2 90 C7010", "type": "curve", "verified_geometry": False, "geometry": {"radius": 294.0, "angle_degrees": 90.0}},
]

EXTRA_CARDS: list[dict[str, Any]] = [
    {"sku": "C8201", "name": "R1 hairpin 90° (C8201)", "family": "r1", "group": "Radius 1", "hand": None, "hint": "Letter J. Same piece both ways. Use with C8246. Pack is two pieces."},
    {"sku": "C8202", "name": "R1 inner 45° (C8202)", "family": "r1", "group": "Radius 1", "hand": None, "hint": "Letter K. Rotate for left or right."},
    {"sku": "C8234", "name": "R2 22.5° (C8234)", "family": "r2", "group": "Radius 2", "hand": None, "hint": "Letter U. One moulding; L/R is placement only."},
    {"sku": "C8210", "name": "90° straight crossover (C8210)", "family": "special", "group": "Crossovers", "hand": None, "hint": "Letter P. 409 mm flat cross."},
    {"sku": "C8006", "name": "Change-over / crossover (C8006)", "family": "special", "group": "Crossovers", "hand": None, "hint": "Classic change-over."},
    {"sku": "C8295", "name": "Elevated crossover (C8295)", "family": "special", "group": "Crossovers", "hand": None, "hint": "Letter W."},
    {"sku": "C8203", "name": "R2 racing-curve crossover 90° (C8203)", "family": "special", "group": "Crossovers", "hand": None, "hint": "Letter E."},
    {"sku": "C8005", "name": "Skid chicane (C8005)", "family": "chicane", "group": "Chicanes", "hand": None, "hint": "Classic skid chicane."},
    {"sku": "C8009", "name": "Straight chicane extension (C8009)", "family": "chicane", "group": "Chicanes", "hand": None, "hint": "Pairs with C8031."},
    {"sku": "C8031A", "name": "Chicane A (C8031A)", "family": "chicane", "group": "Chicanes", "hand": None, "hint": "One half of the C8031 pair."},
    {"sku": "C8031B", "name": "Chicane B (C8031B)", "family": "chicane", "group": "Chicanes", "hand": None, "hint": "Other half of the C8031 pair."},
    {"sku": "C8246A", "name": "Side-swipe A / G (C8246A)", "family": "special", "group": "Side swipe", "hand": None, "hint": "Letter G. Not the same as B."},
    {"sku": "C8246B", "name": "Side-swipe B / H (C8246B)", "family": "special", "group": "Side swipe", "hand": None, "hint": "Letter H. Not the same as A."},
    {"sku": "C7000", "name": "Digital special C7000", "family": "digital", "group": "Digital", "hand": None, "hint": "Tick if that code is on the piece."},
    {"sku": "C7004", "name": "Digital special C7004", "family": "digital", "group": "Digital", "hand": None, "hint": "Tick if that code is on the piece."},
    {"sku": "C7007", "name": "Digital LC curve C7007", "family": "digital", "group": "Digital", "hand": None, "hint": "With C7010."},
    {"sku": "C7010", "name": "Digital LC curve C7010", "family": "digital", "group": "Digital", "hand": None, "hint": "With C7007."},
]
