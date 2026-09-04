"""Shopping list and shop-gate helpers (split out of accuracy_levels)."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field

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
        return cls(owned, profile.max_shop_pieces, profile.max_shop_skus, profile.unlimited, profile.inventory_only, 0.0, 1.0)
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
