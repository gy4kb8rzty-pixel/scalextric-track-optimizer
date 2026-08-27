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
    return [_parse_part(raw_part, index) for index, raw_part in enumerate(raw_parts)]


def get_part_by_id(parts: list[TrackPart], part_id: str) -> TrackPart | None:
    for part in parts:
        if part.id == part_id or part_id in part.aliases:
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
