"""Verified catalog loading and inventory helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from monza_optimizer.catalog.geometry_types import StraightGeometry, CurveGeometry, Geometry

REQUIRED_PART_FIELDS = {"id", "name", "type", "verified_geometry", "geometry"}


class PartValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TrackPart:
    id: str
    name: str
    type: Literal["straight", "curve"] | str
    verified_geometry: bool
    geometry: Geometry | None
    quantity: int = 1
    aliases: tuple[str, ...] = ()
    track_width_mm: float = 156.0
    notes: str = ""

    @property
    def base_code(self) -> str:
        return base_id(self.id)


def base_id(part_id: str) -> str:
    if part_id.endswith("L") or part_id.endswith("R"):
        return part_id[:-1]
    return part_id


def load_parts(path: str | Path) -> list[TrackPart]:
    inventory_path = Path(path)
    with inventory_path.open(encoding="utf-8") as handle:
        raw_inventory = json.load(handle)
    if not isinstance(raw_inventory, dict):
        raise PartValidationError("parts inventory must be a JSON object")
    raw_parts = raw_inventory.get("parts")
    if not isinstance(raw_parts, list):
        raise PartValidationError("parts inventory must contain a 'parts' list")
    parsed = [_parse_part(raw_part, index) for index, raw_part in enumerate(raw_parts)]
    if not any(p.geometry is not None for p in parsed):
        return builtin_sport_catalog()
    return parsed


def get_part_by_id(parts: list[TrackPart], part_id: str) -> TrackPart | None:
    for part in parts:
        if part.id == part_id or part_id in part.aliases:
            return part
    handed = part_id.endswith("L") or part_id.endswith("R")
    if not handed:
        for part in parts:
            if base_id(part.id) == part_id:
                return part
    return None


def inventory_counts(parts: list[TrackPart]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in parts:
        b = base_id(part.id)
        if b not in counts or part.quantity > counts[b]:
            counts[b] = part.quantity
    return counts


def _parse_part(raw_part: Any, index: int) -> TrackPart:
    if not isinstance(raw_part, dict):
        raise PartValidationError(f"part at index {index} must be an object")
    missing = REQUIRED_PART_FIELDS - set(raw_part)
    if missing:
        raise PartValidationError(f"part at index {index} missing fields: {sorted(missing)}")
    geometry = _parse_geometry(raw_part.get("geometry"), index)
    aliases = raw_part.get("aliases") or []
    if not isinstance(aliases, list):
        raise PartValidationError(f"part at index {index}: aliases must be a list")
    return TrackPart(
        id=str(raw_part["id"]),
        name=str(raw_part["name"]),
        type=str(raw_part["type"]),
        verified_geometry=bool(raw_part["verified_geometry"]),
        geometry=geometry,
        quantity=int(raw_part.get("quantity", 1)),
        aliases=tuple(str(a) for a in aliases),
        track_width_mm=float(raw_part.get("track_width_mm", 156.0)),
        notes=str(raw_part.get("notes", "")),
    )


def _parse_geometry(raw: Any, index: int) -> Geometry | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise PartValidationError(f"part at index {index}: geometry must be object or null")
    if "length" in raw:
        return StraightGeometry(length=float(raw["length"]))
    if "radius" in raw and "angle_degrees" in raw:
        return CurveGeometry(radius=float(raw["radius"]), angle_degrees=float(raw["angle_degrees"]))
    raise PartValidationError(f"part at index {index}: unrecognized geometry")


def builtin_sport_catalog() -> list[TrackPart]:
    """Official Sport pieces used when parts.json has no geometry."""
    raw = [
        {"id": "C8205", "name": "Standard Straight", "type": "straight", "verified_geometry": True, "geometry": {"length": 350.0}},
        {"id": "C8207", "name": "Half Straight", "type": "straight", "verified_geometry": True, "geometry": {"length": 175.0}},
        {"id": "C8200", "name": "Quarter Straight", "type": "straight", "verified_geometry": True, "geometry": {"length": 87.0}},
        {"id": "C8236", "name": "Short Straight", "type": "straight", "verified_geometry": True, "geometry": {"length": 78.0}},
        {"id": "C8206L", "name": "R2 45 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": 45.0}},
        {"id": "C8206R", "name": "R2 45 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": -45.0}},
        {"id": "C8204L", "name": "R3 22.5 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 449.0, "angle_degrees": 22.5}},
        {"id": "C8204R", "name": "R3 22.5 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 449.0, "angle_degrees": -22.5}},
        {"id": "C8235L", "name": "R4 22.5 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 608.0, "angle_degrees": 22.5}},
        {"id": "C8235R", "name": "R4 22.5 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 608.0, "angle_degrees": -22.5}},
        {"id": "C156L", "name": "R1 90 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": 90.0}},
        {"id": "C156R", "name": "R1 90 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 137.0, "angle_degrees": -90.0}},
        {"id": "C8234L", "name": "R2 11.25 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": 11.25}},
        {"id": "C8234R", "name": "R2 11.25 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": -11.25}},
        {"id": "C187L", "name": "Banked 45 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 280.0, "angle_degrees": 45.0}},
        {"id": "C187R", "name": "Banked 45 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 280.0, "angle_degrees": -45.0}},
        {"id": "C8010L", "name": "Chicane 22.5 L", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": 22.5}},
        {"id": "C8010R", "name": "Chicane 22.5 R", "type": "curve", "verified_geometry": True, "geometry": {"radius": 294.0, "angle_degrees": -22.5}},
    ]
    return [_parse_part(row, i) for i, row in enumerate(raw)]
