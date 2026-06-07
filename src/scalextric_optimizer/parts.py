"""Loading and validation for track part inventory data."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal


REQUIRED_PART_FIELDS = {"id", "name", "type", "count", "verified_geometry", "geometry"}


class PartValidationError(ValueError):
    """Raised when part inventory data is missing required information."""


@dataclass(frozen=True)
class StraightGeometry:
    """Geometry for a straight track section."""

    length: float


@dataclass(frozen=True)
class CurveGeometry:
    """Geometry for a constant-radius curved track section."""

    radius: float
    angle_degrees: float


Geometry = StraightGeometry | CurveGeometry


@dataclass(frozen=True)
class TrackPart:
    """A single track inventory entry."""

    id: str
    name: str
    type: Literal["straight", "curve"] | str
    count: int | None
    verified_geometry: bool
    geometry: Geometry | None
    notes: str | None = None
    alternative_markings: tuple[str, ...] = ()
    category: str | None = None


def load_parts(path: str | Path) -> list[TrackPart]:
    """Load and validate track parts from a JSON inventory file."""

    inventory_path = Path(path)
    with inventory_path.open(encoding="utf-8") as handle:
        raw_inventory = json.load(handle)

    if not isinstance(raw_inventory, dict):
        raise PartValidationError("parts inventory must be a JSON object")

    raw_parts = raw_inventory.get("parts")
    if not isinstance(raw_parts, list):
        raise PartValidationError("parts inventory must contain a 'parts' list")

    return [_parse_part(raw_part, index) for index, raw_part in enumerate(raw_parts)]


def _parse_part(raw_part: Any, index: int) -> TrackPart:
    if not isinstance(raw_part, dict):
        raise PartValidationError(f"part at index {index} must be an object")

    missing_fields = sorted(REQUIRED_PART_FIELDS - raw_part.keys())
    if missing_fields:
        raise PartValidationError(
            f"part at index {index} is missing required field(s): {', '.join(missing_fields)}"
        )

    part_id = _require_string(raw_part, "id", index)
    name = _require_string(raw_part, "name", index)
    part_type = _require_string(raw_part, "type", index)
    count = _parse_count(raw_part["count"], part_id, part_type)
    verified_geometry = raw_part["verified_geometry"]
    if not isinstance(verified_geometry, bool):
        raise PartValidationError(
            f"part '{part_id}' field 'verified_geometry' must be a boolean"
        )

    geometry = _parse_geometry(raw_part["geometry"], part_type, part_id)
    if verified_geometry and geometry is None:
        raise PartValidationError(
            f"part '{part_id}' cannot have verified_geometry true when geometry is null"
        )

    return TrackPart(
        id=part_id,
        name=name,
        type=part_type,
        count=count,
        verified_geometry=verified_geometry,
        geometry=geometry,
        notes=_parse_optional_string(raw_part, "notes", part_id),
        alternative_markings=_parse_optional_string_tuple(
            raw_part, "alternative_markings", part_id
        ),
        category=_parse_optional_string(raw_part, "category", part_id),
    )


def _require_string(raw_part: dict[str, Any], field: str, index: int) -> str:
    value = raw_part[field]
    if not isinstance(value, str) or not value:
        raise PartValidationError(
            f"part at index {index} field '{field}' must be a non-empty string"
        )
    return value


def _parse_count(raw_count: Any, part_id: str, part_type: str) -> int | None:
    if raw_count is None:
        if part_id == "SMALL_JOINERS" and part_type == "accessory":
            return None
        raise PartValidationError(
            f"part '{part_id}' field 'count' may only be null for unknown accessory counts"
        )
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise PartValidationError(f"part '{part_id}' field 'count' must be a non-negative integer")
    if raw_count < 0:
        raise PartValidationError(f"part '{part_id}' field 'count' must be a non-negative integer")
    return raw_count


def _parse_optional_string(
    raw_part: dict[str, Any], field: str, part_id: str
) -> str | None:
    value = raw_part.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise PartValidationError(f"part '{part_id}' field '{field}' must be a non-empty string")
    return value


def _parse_optional_string_tuple(
    raw_part: dict[str, Any], field: str, part_id: str
) -> tuple[str, ...]:
    value = raw_part.get(field, [])
    if not isinstance(value, list):
        raise PartValidationError(f"part '{part_id}' field '{field}' must be a list of strings")
    for item in value:
        if not isinstance(item, str) or not item:
            raise PartValidationError(
                f"part '{part_id}' field '{field}' must be a list of non-empty strings"
            )
    return tuple(value)


def _parse_geometry(raw_geometry: Any, part_type: str, part_id: str) -> Geometry | None:
    if raw_geometry is None:
        return None
    if not isinstance(raw_geometry, dict):
        raise PartValidationError(f"part '{part_id}' field 'geometry' must be an object or null")

    kind = raw_geometry.get("kind", part_type)
    if kind == "straight":
        return StraightGeometry(length=_require_number(raw_geometry, "length", part_id))
    if kind == "curve":
        return CurveGeometry(
            radius=_require_positive_number(raw_geometry, "radius", part_id),
            angle_degrees=_require_number(raw_geometry, "angle_degrees", part_id),
        )

    raise PartValidationError(f"part '{part_id}' has unsupported geometry kind '{kind}'")


def _require_number(raw_geometry: dict[str, Any], field: str, part_id: str) -> float:
    value = raw_geometry.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PartValidationError(f"part '{part_id}' geometry field '{field}' must be a number")
    return float(value)


def _require_positive_number(raw_geometry: dict[str, Any], field: str, part_id: str) -> float:
    value = _require_number(raw_geometry, field, part_id)
    if value <= 0:
        raise PartValidationError(f"part '{part_id}' geometry field '{field}' must be positive")
    return value
