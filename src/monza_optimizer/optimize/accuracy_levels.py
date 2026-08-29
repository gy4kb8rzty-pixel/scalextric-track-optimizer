"""Four sales-pitch accuracy levels the wrapper can select.

A  Lean Budget   — fewest pieces, silhouette, small table
B  Budget        — inventory first, smallest cart that closes the lap
C  Detailed      — hairpins first, closer outline, full BOM + shop list
D  Full Accuracy — unlimited official catalogue, ceiling layout + SKU map

Physical correctness (connectors, lanes, closure) always outranks the score.
Budget modes never invent unofficial parts. D is labelled unlimited.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Sequence


class AccuracyLevel(str, Enum):
    LEAN_BUDGET = "lean_budget"
    BUDGET = "budget"
    DETAILED = "detailed"
    FULL_ACCURACY = "full_accuracy"

    @classmethod
    def parse(cls, value: str | "AccuracyLevel" | None) -> "AccuracyLevel":
        if value is None:
            return cls.DETAILED
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "a": cls.LEAN_BUDGET,
            "lean": cls.LEAN_BUDGET,
            "leanbudget": cls.LEAN_BUDGET,
            "silhouette": cls.LEAN_BUDGET,
            "b": cls.BUDGET,
            "budget": cls.BUDGET,
            "c": cls.DETAILED,
            "detailed": cls.DETAILED,
            "detail": cls.DETAILED,
            "d": cls.FULL_ACCURACY,
            "full": cls.FULL_ACCURACY,
            "fullaccuracy": cls.FULL_ACCURACY,
            "unlimited": cls.FULL_ACCURACY,
            "ceiling": cls.FULL_ACCURACY,
        }
        if key in aliases:
            return aliases[key]
        return cls(key)


@dataclass(frozen=True)
class LevelProfile:
    """Knobs the construction pipeline reads for one accuracy level."""

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
    candidate_set: str  # "compact" | "standard" | "full"


COMPACT_CANDIDATES = [
    "C8205", "C8207", "C8200", "C8236",
    "C8204L", "C8204R", "C8206L", "C8206R",
    "C8010L", "C8010R",
]

STANDARD_CANDIDATES = COMPACT_CANDIDATES + [
    "C8235L", "C8235R", "C8234L", "C8234R",
    "C156L", "C156R", "C187L", "C187R",
]

FULL_CANDIDATES = [
    "C156L", "C156R", "C8234L", "C8234R", "C8235L", "C8235R",
    "C8010L", "C8010R", "C8204L", "C8204R", "C8206L", "C8206R",
    "C187L", "C187R", "C8236", "C8200", "C8207", "C8205",
]


LEVELS: dict[AccuracyLevel, LevelProfile] = {
    AccuracyLevel.LEAN_BUDGET: LevelProfile(
        level=AccuracyLevel.LEAN_BUDGET,
        letter="A",
        label="Lean Budget",
        pitch="Fewest pieces. The silhouette of the circuit. The small living room.",
        strategy="sequential",
        unlimited=False,
        inventory_only=True,
        max_shop_pieces=0,
        max_shop_skus=0,
        target_length_mm=14000.0,
        densify_step_mm=22.0,
        min_turn_deg=55.0,
        sharp_turn_deg=40.0,
        max_radius_on_sharp=520.0,
        dist_tol_mm=280.0,
        coverage_threshold_mm=360.0,
        max_pieces=80,
        prefer_long_straights=True,
        run_coverage_fill=False,
        run_local_reopt=False,
        candidate_set="compact",
    ),
    AccuracyLevel.BUDGET: LevelProfile(
        level=AccuracyLevel.BUDGET,
        letter="B",
        label="Budget",
        pitch="Only their inventory. A short missing-parts list — the smallest cart that finishes the lap.",
        strategy="hybrid",
        unlimited=False,
        inventory_only=False,
        max_shop_pieces=8,
        max_shop_skus=3,
        target_length_mm=18000.0,
        densify_step_mm=18.0,
        min_turn_deg=40.0,
        sharp_turn_deg=32.0,
        max_radius_on_sharp=450.0,
        dist_tol_mm=200.0,
        coverage_threshold_mm=280.0,
        max_pieces=160,
        prefer_long_straights=True,
        run_coverage_fill=True,
        run_local_reopt=False,
        candidate_set="standard",
    ),
    AccuracyLevel.DETAILED: LevelProfile(
        level=AccuracyLevel.DETAILED,
        letter="C",
        label="Detailed",
        pitch="Hairpins first. Closer to the real outline. Full bill of materials plus a shopping list.",
        strategy="hybrid",
        unlimited=False,
        inventory_only=False,
        max_shop_pieces=40,
        max_shop_skus=12,
        target_length_mm=25000.0,
        densify_step_mm=14.0,
        min_turn_deg=28.0,
        sharp_turn_deg=28.0,
        max_radius_on_sharp=400.0,
        dist_tol_mm=150.0,
        coverage_threshold_mm=220.0,
        max_pieces=400,
        prefer_long_straights=False,
        run_coverage_fill=True,
        run_local_reopt=True,
        candidate_set="full",
    ),
    AccuracyLevel.FULL_ACCURACY: LevelProfile(
        level=AccuracyLevel.FULL_ACCURACY,
        letter="D",
        label="Full Accuracy",
        pitch="Unlimited official catalogue. The ceiling — and a complete SKU map for the collector.",
        strategy="hybrid",
        unlimited=True,
        inventory_only=False,
        max_shop_pieces=10_000,
        max_shop_skus=10_000,
        target_length_mm=32000.0,
        densify_step_mm=12.0,
        min_turn_deg=22.0,
        sharp_turn_deg=22.0,
        max_radius_on_sharp=360.0,
        dist_tol_mm=120.0,
        coverage_threshold_mm=180.0,
        max_pieces=900,
        prefer_long_straights=False,
        run_coverage_fill=True,
        run_local_reopt=True,
        candidate_set="full",
    ),
}


def get_profile(level: str | AccuracyLevel | None) -> LevelProfile:
    return LEVELS[AccuracyLevel.parse(level)]


def candidates_for(profile: LevelProfile) -> list[str]:
    return {
        "compact": list(COMPACT_CANDIDATES),
        "standard": list(STANDARD_CANDIDATES),
        "full": list(FULL_CANDIDATES),
    }[profile.candidate_set]


def levels_for_ui() -> list[dict[str, Any]]:
    return [
        {
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
            "candidate_set": p.candidate_set,
        }
        for p in LEVELS.values()
    ]


@dataclass
class ShoppingList:
    used: dict[str, int]
    owned_used: dict[str, int]
    leftover: dict[str, int]
    missing: dict[str, int]
    missing_piece_count: int
    missing_sku_count: int
    within_shop_budget: bool
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "used": dict(self.used),
            "owned_used": dict(self.owned_used),
            "leftover": dict(self.leftover),
            "missing": dict(self.missing),
            "missing_piece_count": self.missing_piece_count,
            "missing_sku_count": self.missing_sku_count,
            "within_shop_budget": self.within_shop_budget,
            "notes": list(self.notes),
        }


def shopping_list(
    bom: dict[str, int] | Counter,
    inventory: dict[str, int] | None,
    profile: LevelProfile,
    *,
    base_id_fn: Callable[[str], str] | None = None,
) -> ShoppingList:
    from monza_optimizer.catalog.parts import base_id as _base

    bid = base_id_fn or _base
    used = Counter({bid(k): int(v) for k, v in dict(bom).items() if int(v) > 0})
    inv = Counter({bid(k): int(v) for k, v in dict(inventory or {}).items() if int(v) > 0})

    owned_used: dict[str, int] = {}
    leftover: dict[str, int] = {}
    missing: dict[str, int] = {}
    for sku, qty in used.items():
        have = inv.get(sku, 0)
        take = min(have, qty)
        if take:
            owned_used[sku] = take
        if qty > have:
            missing[sku] = qty - have
    for sku, have in inv.items():
        remain = have - used.get(sku, 0)
        if remain > 0:
            leftover[sku] = remain

    miss_n = sum(missing.values())
    miss_skus = len(missing)
    notes: list[str] = []
    if profile.unlimited:
        notes.append("Full Accuracy: official catalogue treated as unlimited; missing is the complete SKU map.")
    elif profile.inventory_only and miss_n:
        notes.append("Lean Budget is inventory-only; missing pieces were not purchased — layout should stay inside stock.")
    elif miss_n > profile.max_shop_pieces or miss_skus > profile.max_shop_skus:
        notes.append(
            f"Shop list exceeds {profile.label} cap "
            f"({profile.max_shop_pieces} pieces / {profile.max_shop_skus} SKUs)."
        )

    within = True
    if profile.inventory_only:
        within = miss_n == 0
    elif not profile.unlimited:
        within = miss_n <= profile.max_shop_pieces and miss_skus <= profile.max_shop_skus

    return ShoppingList(
        used=dict(used),
        owned_used=owned_used,
        leftover=leftover,
        missing=missing,
        missing_piece_count=miss_n,
        missing_sku_count=miss_skus,
        within_shop_budget=within,
        notes=notes,
    )


def resolve_availability(
    profile: LevelProfile,
    inventory: dict[str, int] | None,
    catalog_ids: Sequence[str],
    *,
    base_id_fn: Callable[[str], str] | None = None,
) -> dict[str, int]:
    from monza_optimizer.catalog.parts import base_id as _base

    bid = base_id_fn or _base
    ids = [bid(c) for c in catalog_ids]
    if profile.unlimited:
        return {i: 999 for i in ids}

    avail = {i: 0 for i in ids}
    for k, v in dict(inventory or {}).items():
        avail[bid(k)] = avail.get(bid(k), 0) + max(0, int(v))

    if not profile.inventory_only and profile.max_shop_pieces > 0:
        slack = max(1, profile.max_shop_pieces)
        for i in ids:
            avail[i] = avail.get(i, 0) + slack
    return avail
