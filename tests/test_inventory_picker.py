"""Lovable tick-box inventory catalogue."""

from fastapi.testclient import TestClient

from monza_optimizer.optimize.inventory_picker import ticks_to_inventory
from monza_optimizer.optimize.flying_start import flying_start_inventory
from monza_optimizer.server import app

client = TestClient(app)


def test_picker_lists_official_skus_with_graphics():
    r = client.get("/inventory-picker")
    assert r.status_code == 200, r.text
    body = r.json()
    skus = [p["sku"] for g in body["groups"] for p in g["parts"]]
    assert "C8205" in skus
    assert "C8206L" in skus and "C8206R" in skus
    flying = next(p for p in body["presets"] if p["id"] == "flying_start")
    assert flying["inventory"] == flying_start_inventory()
    card = next(p for g in body["groups"] for p in g["parts"] if p["sku"] == "C8205")
    assert card["tickable"] is True
    assert "<svg" in card["thumb_svg"]
    assert card["letter_under_track"] == "B"


def test_ticks_to_inventory_and_optimize_accepts_ticks():
    assert ticks_to_inventory([{"sku": "C8205", "qty": 4}, {"sku": "C8206L", "qty": 0}]) == {"C8205": 4}
    r = client.post(
        "/inventory-from-ticks",
        json={"ticks": [{"sku": "C8205", "qty": 2}, {"sku": "C8206R", "qty": 8}]},
    )
    assert r.status_code == 200
    assert r.json()["inventory"] == {"C8205": 2, "C8206R": 8}
