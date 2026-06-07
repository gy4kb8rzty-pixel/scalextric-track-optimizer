import json

import pytest

from scalextric_optimizer.parts import PartValidationError, StraightGeometry, load_parts


def test_loads_repository_parts_json():
    parts = load_parts("parts.json")

    assert parts
    assert parts[0].id == "C8205"
    assert parts[0].verified_geometry is False
    assert parts[0].geometry is None


def test_missing_required_fields_produce_clear_validation_error(tmp_path):
    inventory = tmp_path / "parts.json"
    inventory.write_text(json.dumps({"parts": [{"id": "demo"}]}), encoding="utf-8")

    with pytest.raises(PartValidationError, match="missing required field") as error:
        load_parts(inventory)

    message = str(error.value)
    assert "geometry" in message
    assert "name" in message
    assert "type" in message
    assert "verified_geometry" in message


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
