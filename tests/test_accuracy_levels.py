from monza_optimizer.optimize.accuracy_levels import (
    AccuracyLevel, get_profile, candidates_for, levels_for_ui,
    shopping_list, resolve_availability, target_length_for,
)


def test_parse_aliases():
    assert AccuracyLevel.parse("0") is AccuracyLevel.BARE_BONES
    assert AccuracyLevel.parse("A") is AccuracyLevel.LEAN_BUDGET
    assert AccuracyLevel.parse("B") is AccuracyLevel.BUDGET
    assert AccuracyLevel.parse("C") is AccuracyLevel.DETAILED
    assert AccuracyLevel.parse("full") is AccuracyLevel.FULL_ACCURACY
    assert AccuracyLevel.parse("E") is AccuracyLevel.EVENT_132
    assert AccuracyLevel.parse("1:32") is AccuracyLevel.EVENT_132
    assert AccuracyLevel.parse(None) is AccuracyLevel.DETAILED


def test_five_levels_present():
    ui = levels_for_ui()
    letters = [row["letter"] for row in ui]
    assert letters[:5] == ["0", "A", "B", "C", "D"]
    assert "E" in letters
    e = next(r for r in ui if r["letter"] == "E")
    assert e["severe"] is True
    assert e["warning"]


def test_event_length_is_one_thirty_two():
    p = get_profile("E")
    mm = target_length_for(p, official_length_m=5793.0)
    assert abs(mm - 5793.0 * 1000.0 / 32.0) < 1.0


def test_candidate_sets_grow():
    a = candidates_for(get_profile("A"))
    b = candidates_for(get_profile("B"))
    d = candidates_for(get_profile("D"))
    assert "C8205" in a and "C8206L" in a
    assert "C8201L" in b
    assert "C156L" not in a and "C156L" not in b and "C156L" not in d


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
