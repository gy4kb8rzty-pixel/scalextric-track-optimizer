"""Sales-pitch accuracy levels for the Lovable backend."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Sequence

class AccuracyLevel(str, Enum):
    BARE_BONES = "bare_bones"
    LEAN_BUDGET = "lean_budget"
    BUDGET = "budget"
    DETAILED = "detailed"
    FULL_ACCURACY = "full_accuracy"
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
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"{value!r} is not a valid AccuracyLevel") from exc

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

STARTER_CANDIDATES = ["C8205", "C8206L", "C8206R", "C8204L", "C8204R", "C8010L", "C8010R", "C8234L", "C8234R", "C8201L", "C8201R"]
COMPACT_CANDIDATES = ["C8205", "C8207", "C8200", "C8236", "C8204L", "C8204R", "C8206L", "C8206R", "C8010L", "C8010R"]
STANDARD_CANDIDATES = COMPACT_CANDIDATES + ["C8235L", "C8235R", "C8234L", "C8234R", "C8201L", "C8201R", "C187L", "C187R"]
FULL_CANDIDATES = list(STANDARD_CANDIDATES)
STREET_CIRCUITS = {"monaco", "monte_carlo", "marina_bay", "singapore", "las_vegas", "baku", "jeddah", "miami", "montreal", "san_diego"}

def _p(*a, **k):
    return LevelProfile(*a, **k)

LEVELS = {
    AccuracyLevel.BARE_BONES: _p(AccuracyLevel.BARE_BONES, "0", "Bare Bones", "Empty-box starter kit.", "sequential", False, False, 64, 6, 5000.0, 60.0, 80.0, 80.0, 2500.0, 1600.0, 1800.0, 64, True, False, False, "starter", ignore_inventory=True, scale_frac=0.18, min_target_mm=5500.0, max_target_mm=8000.0),
    AccuracyLevel.LEAN_BUDGET: _p(AccuracyLevel.LEAN_BUDGET, "A", "Lean Budget", "Silhouette + tiny closer pack.", "sequential", False, False, 4, 2, 11000.0, 32.0, 65.0, 65.0, 1600.0, 600.0, 700.0, 56, True, False, False, "compact", scale_frac=0.34, min_target_mm=8000.0, max_target_mm=14000.0),
    AccuracyLevel.BUDGET: _p(AccuracyLevel.BUDGET, "B", "Budget", "Inventory first, small cart.", "hybrid", False, False, 8, 3, 18000.0, 18.0, 40.0, 32.0, 450.0, 200.0, 280.0, 160, True, True, False, "standard", scale_frac=0.56, min_target_mm=14000.0, max_target_mm=20000.0),
    AccuracyLevel.DETAILED: _p(AccuracyLevel.DETAILED, "C", "Detailed", "Hairpins first.", "hybrid", False, False, 40, 12, 25000.0, 14.0, 28.0, 28.0, 400.0, 150.0, 220.0, 400, False, True, True, "full", scale_frac=0.78, min_target_mm=20000.0, max_target_mm=28000.0),
    AccuracyLevel.FULL_ACCURACY: _p(AccuracyLevel.FULL_ACCURACY, "D", "Full Accuracy", "Unlimited official catalogue.", "hybrid", True, False, 10000, 10000, 32000.0, 12.0, 22.0, 22.0, 360.0, 120.0, 180.0, 900, False, True, True, "full", scale_frac=1.0, min_target_mm=24000.0, max_target_mm=40000.0),
}

def target_length_for(profile, official_length_m=None, override_mm=None, track_id=None, kind=None):
    if override_mm:
        return float(override_mm)
    raw = 32000.0 if not official_length_m else max(14000.0, min(40000.0, 32000.0 * (float(official_length_m) / 5793.0)))
    raw *= float(profile.scale_frac)
    lo, hi = profile.min_target_mm, profile.max_target_mm
    if profile.letter == "0" and (track_id or "").lower() in STREET_CIRCUITS:
        lo, hi, raw = max(lo, 8000.0), max(hi, 12000.0), max(raw, 8000.0)
        if (track_id or "").lower() in {"monaco", "monte_carlo"}:
            lo, hi, raw = 12000.0, 14000.0, 12000.0
    return max(lo, min(hi, raw))

def get_profile(level):
    return LEVELS[AccuracyLevel.parse(level)]

def candidates_for(profile):
    return {"starter": list(STARTER_CANDIDATES), "compact": list(COMPACT_CANDIDATES), "standard": list(STANDARD_CANDIDATES), "full": list(FULL_CANDIDATES)}[profile.candidate_set]

def levels_for_ui():
    return [{"id": p.level.value, "letter": p.letter, "label": p.label, "pitch": p.pitch, "strategy": p.strategy, "unlimited": p.unlimited, "inventory_only": p.inventory_only, "max_shop_pieces": p.max_shop_pieces, "max_shop_skus": p.max_shop_skus, "target_length_mm": p.target_length_mm, "scale_frac": p.scale_frac, "min_target_mm": p.min_target_mm, "max_target_mm": p.max_target_mm, "candidate_set": p.candidate_set, "ignore_inventory": p.ignore_inventory} for p in LEVELS.values()]

@dataclass
class ShoppingList:
    used: dict
    owned_used: dict
    leftover: dict
    missing: dict
    missing_piece_count: int
    missing_sku_count: int
    within_shop_budget: bool
    notes: list = field(default_factory=list)
    def as_dict(self):
        return {"used": dict(self.used), "owned_used": dict(self.owned_used), "leftover": dict(self.leftover), "missing": dict(self.missing), "missing_piece_count": self.missing_piece_count, "missing_sku_count": self.missing_sku_count, "within_shop_budget": self.within_shop_budget, "notes": list(self.notes)}

def shopping_list(bom, inventory, profile, *, base_id_fn=None):
    from monza_optimizer.catalog.parts import base_id as _base
    bid = base_id_fn or _base
    used = Counter({bid(k): int(v) for k, v in dict(bom).items() if int(v) > 0})
    inv = Counter({bid(k): int(v) for k, v in dict(inventory or {}).items() if int(v) > 0})
    owned_used, leftover, missing = {}, {}, {}
    for sku, qty in used.items():
        have = inv.get(sku, 0)
        if min(have, qty):
            owned_used[sku] = min(have, qty)
        if qty > have:
            missing[sku] = qty - have
    for sku, have in inv.items():
        if have - used.get(sku, 0) > 0:
            leftover[sku] = have - used.get(sku, 0)
    miss_n, miss_skus = sum(missing.values()), len(missing)
    within = True if profile.unlimited else (miss_n == 0 if profile.inventory_only else miss_n <= profile.max_shop_pieces and miss_skus <= profile.max_shop_skus)
    return ShoppingList(dict(used), owned_used, leftover, missing, miss_n, miss_skus, within, [])

def join_dialogue_for(profile, metrics):
    if profile.letter != "0":
        return None
    pos = float(metrics.get("pos_mm") or 0.0)
    head = float(metrics.get("head_deg") or 0.0)
    closed = bool(metrics.get("closed"))
    if not closed:
        return {"kind": "open", "audience": "bare_bones", "gap_mm": round(pos, 1), "head_deg": round(head, 1), "headline": "This starter kit does not yet click.", "body": "Too far for Sport-track play.", "options": []}
    if pos <= 20:
        return {"kind": "click", "audience": "bare_bones", "gap_mm": round(pos, 1), "head_deg": round(head, 1), "headline": "The last pair meets.", "body": "Connectors should click.", "options": [{"id": "buy", "label": "Buy this starter kit", "extra_sku": None, "extra_qty": 0}]}
    return {"kind": "pinch_or_short", "audience": "bare_bones", "gap_mm": round(pos, 1), "head_deg": round(head, 1), "headline": "Closed on the computer — pinch or add one short.", "body": f"Gap {pos:.0f} mm.", "options": [{"id": "pinch", "label": "Pinch the join", "extra_sku": None, "extra_qty": 0}, {"id": "short_c8236", "label": "Add one C8236 short", "extra_sku": "C8236", "extra_qty": 1}, {"id": "short_c8200", "label": "Add one C8200 quarter", "extra_sku": "C8200", "extra_qty": 1}]}

def resolve_availability(profile, inventory, catalog_ids, *, base_id_fn=None):
    from monza_optimizer.catalog.parts import base_id as _base
    bid = base_id_fn or _base
    ids = [bid(c) for c in catalog_ids]
    if profile.unlimited:
        return {i: 999 for i in ids}
    avail = {i: 0 for i in ids}
    for k, v in dict(inventory or {}).items():
        avail[bid(k)] = avail.get(bid(k), 0) + max(0, int(v))
    return avail

@dataclass
class ShopGate:
    owned: dict
    max_shop_pieces: int
    max_shop_skus: int
    unlimited: bool = False
    inventory_only: bool = False
    defer_until_frac: float = 0.0
    progress_frac: float = 1.0
    @classmethod
    def from_profile(cls, profile, inventory, *, base_id_fn=None):
        from monza_optimizer.catalog.parts import base_id as _base
        bid = base_id_fn or _base
        owned = {bid(k): max(0, int(v)) for k, v in dict(inventory or {}).items() if int(v) > 0}
        return cls(owned, profile.max_shop_pieces, profile.max_shop_skus, profile.unlimited, profile.inventory_only, 0.82 if profile.letter == "A" else 0.0, 1.0)
    def owned_left(self, sku, used):
        return max(0, self.owned.get(sku, 0) - int(used.get(sku, 0)))
    def missing_from(self, used):
        return {sku: int(qty) - self.owned.get(sku, 0) for sku, qty in dict(used).items() if int(qty) - self.owned.get(sku, 0) > 0}
    def may_add(self, sku, used):
        if self.unlimited or self.owned_left(sku, used) > 0:
            return True
        if self.inventory_only or self.progress_frac < self.defer_until_frac:
            return False
        missing = self.missing_from(used)
        if sum(missing.values()) >= self.max_shop_pieces:
            return False
        if sku not in missing and len(missing) >= self.max_shop_skus:
            return False
        return True
    def shop_penalty(self, sku, used):
        return 0.0 if self.unlimited else (-6.0 if self.owned_left(sku, used) > 0 else 40.0)

def may_place(code, used, avail, gate, *, base_id_fn=None):
    from monza_optimizer.catalog.parts import base_id as _base
    bid = (base_id_fn or _base)(code)
    if gate is not None:
        return gate.may_add(bid, used)
    return int(used.get(bid, 0)) < int((avail or {}).get(bid, 0))

def enforce_shop_cap(sequence, inventory, profile, *, get_part=None):
    if profile.unlimited:
        return list(sequence)
    from monza_optimizer.catalog.parts import base_id as _base
    gate = ShopGate.from_profile(profile, inventory)
    used, out = Counter(), []
    for code in sequence:
        sku = _base(code)
        if gate.may_add(sku, used):
            out.append(code); used[sku] += 1
    return out
