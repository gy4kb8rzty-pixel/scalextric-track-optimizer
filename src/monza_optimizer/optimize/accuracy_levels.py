"""Sales-pitch accuracy levels for the Lovable backend."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from monza_optimizer.optimize.shop_helpers import (
    ShoppingList,
    shopping_list,
    join_dialogue_for,
    resolve_availability,
    ShopGate,
    may_place,
    enforce_shop_cap,
)

class AccuracyLevel(str, Enum):
    BARE_BONES = "bare_bones"
    LEAN_BUDGET = "lean_budget"
    BUDGET = "budget"
    DETAILED = "detailed"
    FULL_ACCURACY = "full_accuracy"
    EVENT_132 = "event_132"
    @classmethod
    def parse(cls, value):
        if value is None:
            return cls.DETAILED
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "0": cls.BARE_BONES, "starter": cls.BARE_BONES, "bare": cls.BARE_BONES,
            "barebones": cls.BARE_BONES, "bare_bones": cls.BARE_BONES,
            "a": cls.LEAN_BUDGET, "lean": cls.LEAN_BUDGET, "leanbudget": cls.LEAN_BUDGET,
            "lean_budget": cls.LEAN_BUDGET,
            "b": cls.BUDGET, "budget": cls.BUDGET,
            "c": cls.DETAILED, "detailed": cls.DETAILED,
            "d": cls.FULL_ACCURACY, "full": cls.FULL_ACCURACY,
            "fullaccuracy": cls.FULL_ACCURACY, "full_accuracy": cls.FULL_ACCURACY,
            "unlimited": cls.FULL_ACCURACY,
            "e": cls.EVENT_132, "event": cls.EVENT_132, "event_132": cls.EVENT_132,
            "1:32": cls.EVENT_132, "132": cls.EVENT_132, "scale_132": cls.EVENT_132,
            "super": cls.EVENT_132,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"{value!r} is not a valid AccuracyLevel") from exc

E_WARNING = (
    "Level E is a 1:32 scale layout of the real circuit. Expect several hundred "
    "to a few thousand Sport pieces, a hall or outdoor site rather than a living room, "
    "many minutes of compute (the request may time out on a free server), and a full "
    "club build weekend. Only use this for a serious fan community or a sponsored event."
)

@dataclass(frozen=True)
class LevelProfile:
    level: AccuracyLevel
    letter: str
    label: str
    pitch: str
    strategy: str
    unlimited: bool
    inventory_only: bool
    max_shop_pieces: int
    max_shop_skus: int
    target_length_mm: float
    densify_step_mm: float
    min_turn_deg: float
    sharp_turn_deg: float
    max_radius_on_sharp: float
    dist_tol_mm: float
    coverage_threshold_mm: float
    max_pieces: int
    prefer_long_straights: bool
    run_coverage_fill: bool
    run_local_reopt: bool
    candidate_set: str
    ignore_inventory: bool = False
    scale_frac: float = 1.0
    min_target_mm: float = 4000.0
    max_target_mm: float = 40000.0
    warning: str | None = None
    scale_note: str | None = None

STARTER_CANDIDATES = ["C8205", "C8206L", "C8206R", "C8204L", "C8204R", "C8010L", "C8010R", "C8234L", "C8234R", "C8201L", "C8201R"]
COMPACT_CANDIDATES = ["C8205", "C8207", "C8200", "C8236", "C8204L", "C8204R", "C8206L", "C8206R", "C8010L", "C8010R"]
STANDARD_CANDIDATES = COMPACT_CANDIDATES + ["C8235L", "C8235R", "C8234L", "C8234R", "C8201L", "C8201R", "C187L", "C187R"]
BUDGET_CANDIDATES = ["C8205", "C8207", "C8200", "C8236", "C8206L", "C8206R", "C8010L", "C8010R", "C8204L", "C8204R", "C8235L", "C8235R"]
LEAN_CANDIDATES = ["C8205", "C8207", "C8200", "C8236", "C8206L", "C8206R", "C8010L", "C8010R", "C8235L", "C8235R"]
FULL_CANDIDATES = list(STANDARD_CANDIDATES)
STREET_CIRCUITS = {"monaco", "monte_carlo", "marina_bay", "singapore", "las_vegas", "baku", "jeddah", "miami", "montreal", "san_diego"}

def _p(*a, **k):
    return LevelProfile(*a, **k)

LEVELS = {
    AccuracyLevel.BARE_BONES: _p(AccuracyLevel.BARE_BONES, "0", "Bare Bones", "Empty-box starter kit.", "sequential", False, False, 64, 6, 5000.0, 60.0, 80.0, 80.0, 2500.0, 1600.0, 1800.0, 64, True, False, False, "starter", ignore_inventory=True, scale_frac=0.18, min_target_mm=5500.0, max_target_mm=8000.0),
    AccuracyLevel.LEAN_BUDGET: _p(AccuracyLevel.LEAN_BUDGET, "A", "Lean Budget", "Manual only. Build on a very simple red outline, one official piece at a time.", "manual", False, False, 56, 8, 9000.0, 36.0, 32.0, 28.0, 900.0, 280.0, 400.0, 140, True, False, False, "lean", scale_frac=0.30, min_target_mm=7500.0, max_target_mm=11000.0),
    AccuracyLevel.BUDGET: _p(AccuracyLevel.BUDGET, "B", "Budget", "Simplified red guide. Follow the main straight and big corners — no oval shortcut.", "sequential", False, False, 56, 10, 14000.0, 36.0, 36.0, 32.0, 420.0, 240.0, 280.0, 200, False, False, False, "budget", scale_frac=0.42, min_target_mm=9000.0, max_target_mm=16000.0),
    AccuracyLevel.DETAILED: _p(AccuracyLevel.DETAILED, "C", "Detailed", "Near Full, with a shop cap high enough to close a named circuit.", "sequential", False, False, 100, 18, 36000.0, 13.0, 26.0, 24.0, 380.0, 240.0, 200.0, 550, False, False, True, "full", scale_frac=1.15, min_target_mm=34000.0, max_target_mm=48000.0),
    AccuracyLevel.FULL_ACCURACY: _p(AccuracyLevel.FULL_ACCURACY, "D", "Full Accuracy", "Unlimited official catalogue. Follows the red centreline.", "sequential", True, False, 10000, 10000, 50000.0, 12.0, 22.0, 22.0, 360.0, 280.0, 180.0, 900, False, False, True, "full", scale_frac=1.5, min_target_mm=48000.0, max_target_mm=64000.0),
    AccuracyLevel.EVENT_132: _p(
        AccuracyLevel.EVENT_132, "E", "1:32 Event",
        "True 1:32 length of the real circuit. Club or sponsor build only.",
        "sequential", True, False, 100000, 100000, 180000.0, 18.0, 20.0, 20.0, 360.0, 280.0, 200.0, 2800,
        False, False, True, "full", scale_frac=1.0, min_target_mm=80000.0, max_target_mm=250000.0,
        warning=E_WARNING, scale_note="1:32 of official circuit length",
    ),
}

def target_length_for(profile, official_length_m=None, override_mm=None, track_id=None, kind=None):
    if override_mm:
        return float(override_mm)
    if profile.letter == "E" and official_length_m:
        mm = float(official_length_m) * 1000.0 / 32.0
        return max(profile.min_target_mm, min(profile.max_target_mm, mm))
    raw = 32000.0 if not official_length_m else max(14000.0, min(64000.0, 32000.0 * (float(official_length_m) / 5793.0)))
    raw *= float(profile.scale_frac)
    lo, hi = profile.min_target_mm, profile.max_target_mm
    tid = (track_id or "").lower()
    if profile.letter == "0" and tid in STREET_CIRCUITS:
        lo, hi, raw = max(lo, 8000.0), max(hi, 12000.0), max(raw, 8000.0)
        if tid in {"monaco", "monte_carlo"}:
            lo, hi, raw = 12000.0, 14000.0, 12000.0
    if profile.letter in {"C", "D"} and tid in {"monaco", "monte_carlo"}:
        floor = 50000.0 if profile.letter == "D" else 36000.0
        lo, raw = max(lo, floor), max(raw, floor)
    return max(lo, min(hi, raw))

def get_profile(level):
    return LEVELS[AccuracyLevel.parse(level)]

def candidates_for(profile):
    return {
        "starter": list(STARTER_CANDIDATES),
        "lean": list(LEAN_CANDIDATES),
        "compact": list(COMPACT_CANDIDATES),
        "budget": list(BUDGET_CANDIDATES),
        "standard": list(STANDARD_CANDIDATES),
        "full": list(FULL_CANDIDATES),
    }[profile.candidate_set]

def levels_for_ui(track_id: str | None = None):
    from monza_optimizer.reference.tracks import level_a_allowed
    rows = []
    for p in LEVELS.values():
        a_ok = True if p.letter != "A" else (level_a_allowed(track_id) if track_id else True)
        rows.append({
            "id": p.level.value,
            "letter": p.letter,
            "label": p.label,
            "pitch": p.pitch,
            "strategy": p.strategy,
            "unlimited": p.unlimited,
            "inventory_only": p.inventory_only,
            "max_shop_pieces": p.max_shop_pieces,
            "max_shop_skus": p.max_shop_skus,
            "target_length_mm": p.target_length_mm,
            "scale_frac": p.scale_frac,
            "min_target_mm": p.min_target_mm,
            "max_target_mm": p.max_target_mm,
            "candidate_set": p.candidate_set,
            "ignore_inventory": p.ignore_inventory,
            "warning": p.warning,
            "scale_note": p.scale_note,
            "severe": p.letter == "E",
            "visible_in_menu": p.letter != "0" and a_ok,
            "restricted_to_tracks": None,
            "manual": p.letter == "A",
            "manual_endpoint": "/manual/a" if p.letter == "A" else None,
        })
    return rows
