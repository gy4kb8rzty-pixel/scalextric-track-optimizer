from monza_optimizer.optimize.accuracy_levels import (
    AccuracyLevel, get_profile, candidates_for, levels_for_ui,
    shopping_list, resolve_availability,
)


def test_parse_aliases():
    assert AccuracyLevel.parse("0") is AccuracyLevel.BARE_BONES
    assert AccuracyLevel.parse("A") is AccuracyLevel.LEAN_BUDGET
    assert AccuracyLevel.parse("B") is AccuracyLevel.BUDGET
    assert AccuracyLevel.parse("C") is AccuracyLevel.DETAILED
    assert AccuracyLevel.parse("full") is AccuracyLevel.FULL_ACCURACY
    assert AccuracyLevel.parse(None) is AccuracyLevel.DETAILED


def test_five_levels_present():
    ui = levels_for_ui()
    assert [row["letter"] for row in ui] == ["0", "A", "B", "C", "D"]
    assert ui[0]["ignore_inventory"] is True
    assert ui[4]["unlimited"] is True


def test_candidate_sets_grow():
    a = candidates_for(get_profile("A"))
    b = candidates_for(get_profile("B"))
    d = candidates_for(get_profile("D"))
    assert set(a).issubset(set(b))
    assert set(b).issubset(set(d))
    assert "C156L" not in a
    assert "C156L" in b


def test_shopping_list_budget_cap():
    profile = get_profile("B")
    shop = shopping_list({"C8205": 10, "C8235": 2}, {"C8205": 10}, profile)
    assert shop.missing == {"C8235": 2}
    assert shop.within_shop_budget is True


def test_full_accuracy_unlimited_avail():
    profile = get_profile("D")
    avail = resolve_availability(profile, {"C8205": 1}, ["C8205", "C8235L"])
    assert avail["C8205"] == 999
    assert avail["C8235"] == 999
