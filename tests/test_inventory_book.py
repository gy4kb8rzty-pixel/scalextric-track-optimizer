from monza_optimizer.optimize.inventory_book import apply_purchase, inventory_status


def test_apply_purchase_adds_to_box():
    owned = apply_purchase({"C8205": 4}, {"C8205": 2, "C8235L": 4})
    assert owned["C8205"] == 6
    assert owned["C8235L"] == 4


def test_status_ready_when_nothing_missing():
    st = inventory_status(
        {"C8205": 4, "C8206L": 8},
        used={"C8205": 4, "C8206L": 8},
        missing={},
    )
    assert st["piece_count"] == 12
    assert st["box_ready_for_same_lap"] is True
    assert st["still_to_buy_pieces"] == 0
