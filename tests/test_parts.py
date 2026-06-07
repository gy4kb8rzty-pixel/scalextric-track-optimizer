import json

import pytest

from scalextric_optimizer.parts import PartValidationError, StraightGeometry, load_parts


def parts_by_id():
    return {part.id: part for part in load_parts("parts.json")}


def numeric_inventory_total(parts):
    return sum(part.count for part in parts if part.count is not None)


def test_loads_repository_parts_json():
    parts = load_parts("parts.json")
    indexed_parts = {part.id: part for part in parts}

    assert parts
    assert indexed_parts["C160"].count == 39
    assert indexed_parts["C160"].verified_geometry is False
    assert indexed_parts["C160"].geometry is None


def test_known_numeric_inventory_total_excludes_unknown_accessories():
    parts = load_parts("parts.json")
    indexed_parts = {part.id: part for part in parts}

    assert numeric_inventory_total(parts) == 104
    assert indexed_parts["SMALL_JOINERS"].count is None


def test_known_inventory_counts_are_recorded():
    indexed_parts = parts_by_id()

    assert indexed_parts["C160"].count == 39
    assert indexed_parts["C151"].count == 8
    assert indexed_parts["C187"].count == 7


def test_real_inventory_geometry_remains_unverified():
    parts = load_parts("parts.json")

    assert all(part.verified_geometry is False for part in parts)
    assert all(part.geometry is None for part in parts)


def test_no_part_can_have_verified_geometry_true_with_null_geometry(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(
        json.dumps(
            {
                "parts": [
                    {
                        "id": "bad-geometry",
                        "name": "Bad geometry",
                        "type": "straight",
                        "count": 1,
                        "verified_geometry": True,
                        "geometry": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PartValidationError, match="verified_geometry true"):
        load_parts(inventory)


def test_missing_required_fields_produce_clear_validation_error(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(json.dumps({"parts": [{"id": "demo"}]}), encoding="utf-8")

    with pytest.raises(PartValidationError, match="missing required field") as error:
        load_parts(inventory)

    message = str(error.value)
    assert "count" in message
    assert "geometry" in message
    assert "name" in message
    assert "type" in message
    assert "verified_geometry" in message


def test_numeric_counts_must_be_non_negative_integers(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(
        json.dumps(
            {
                "parts": [
                    {
                        "id": "negative-count",
                        "name": "Negative count",
                        "type": "straight",
                        "count": -1,
                        "verified_geometry": False,
                        "geometry": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PartValidationError, match="non-negative integer"):
        load_parts(inventory)


def test_null_count_is_only_allowed_for_unknown_accessory_counts(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(
        json.dumps(
            {
                "parts": [
                    {
                        "id": "unknown-track-count",
                        "name": "Unknown track count",
                        "type": "straight",
                        "count": None,
                        "verified_geometry": False,
                        "geometry": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PartValidationError, match="may only be null"):
        load_parts(inventory)


def test_loads_synthetic_geometry_for_tests(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(
        json.dumps(
            {
                "parts": [
                    {
                        "id": "test-straight",
                        "name": "Synthetic straight",
                        "type": "straight",
                        "count": 1,
                        "verified_geometry": True,
                        "geometry": {"kind": "straight", "length": 10},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    parts = load_parts(inventory)

    assert parts[0].geometry == StraightGeometry(length=10.0)
