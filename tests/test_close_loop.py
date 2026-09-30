from monza_optimizer.optimize.close_loop import CLOSE_POS_MM, CLOSE_HEAD_DEG
from monza_optimizer.optimize.accuracy_levels import get_profile, join_dialogue_for


def test_closure_thresholds():
    assert CLOSE_POS_MM <= 80
    assert CLOSE_HEAD_DEG <= 12


def test_bare_bones_join_dialogue_pinch():
    d = join_dialogue_for(get_profile("0"), {"pos_mm": 69.0, "head_deg": 0.0, "closed": True})
    assert d["kind"] == "pinch_or_short"
    assert {o["id"] for o in d["options"]} == {"pinch", "short_c8236", "short_c8200"}


def test_other_levels_have_no_join_talk():
    assert join_dialogue_for(get_profile("B"), {"pos_mm": 4.0, "head_deg": 0.0, "closed": True}) is None
