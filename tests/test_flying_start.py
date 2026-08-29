"""Official Flying Start pack is the C1446M START Grand Prix map."""

from monza_optimizer.optimize.flying_start import (
    FLYING_START_INVENTORY,
    FLYING_START_SET_ID,
    flying_start_inventory,
)


def test_flying_start_is_official_start_grand_prix():
    inv = flying_start_inventory()
    assert FLYING_START_SET_ID == "C1446M"
    assert inv == {"C8205": 4, "C8206L": 8, "C8206R": 8}
    assert inv is not FLYING_START_INVENTORY
    assert sum(inv.values()) == 20
