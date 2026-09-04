"""High-level API for web / Lovable / wrapper integration.

User inventory + named circuit + accuracy level → layout + shop cart.
Physical correctness (connectors, lanes, closure) always outranks scores.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from monza_optimizer.catalog import load_parts, get_part_by_id, base_id
from monza_optimizer.optimize import (
    densify_polyline,
    corner_first_build,
)
from monza_optimizer.optimize.sequential import sequential_follow
from monza_optimizer.optimize.coverage_fill import coverage_fill
from monza_optimizer.optimize.close_loop import close_loop
from monza_optimizer.optimize.kit_loop import closed_kit_loop
from monza_optimizer.geometry.pose import Pose
from monza_optimizer.optimize.accuracy_levels import (
    get_profile,
    candidates_for,
    levels_for_ui,
    shopping_list,
    resolve_availability,
    ShopGate,
    LevelProfile,
    enforce_shop_cap,
    join_dialogue_for,
    target_length_for,
)
from monza_optimizer.reference import list_tracks, load_track_centreline, scale_centreline
from monza_optimizer.export import build_track_3mf, build_output_pack, lay_payload, OUTPUT_MENU


@dataclass
class OptimizeRequest:
    track_id: str = "monza"
    inventory: dict[str, int] = field(default_factory=dict)
    target_length_mm: float | None = None
    strategy: str | None = None
    unlimited: bool | None = None
    accuracy_level: str = "detailed"
    parts_json: str = "parts.json"
    outputs: list[str] | None = None
    from_scratch: bool = False


@dataclass
class OptimizeResult:
    sequence: list[str]
    bom: dict[str, int]
    metrics: dict[str, Any]
    track_id: str
    strategy: str
    accuracy_level: str = "detailed"
    shopping: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    lay: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "accuracy_level": self.accuracy_level,
            "strategy": self.strategy,
            "sequence": list(self.sequence),
            "bom": dict(self.bom),
            "metrics": dict(self.metrics),
            "shopping": dict(self.shopping),
            "profile": dict(self.profile),
            "lay": dict(self.lay),
            "outputs": dict(self.outputs),
        }


def default_inventory_from_catalog(parts_json: str = "parts.json") -> dict[str, int]:
    parts = load_parts(parts_json)
    inv: dict[str, int] = {}
    for p in parts:
        inv[base_id(p.id)] = inv.get(base_id(p.id), 0) + getattr(p, "quantity", 1)
    return inv


def _look_ahead(profile) -> float:
    if profile.letter == "A":
        return 130.0
    if profile.letter == "B":
        return 160.0
    return 220.0


def _run_pipeline(cl, get_part, avail, profile, cand, shop=None):
    strategy = profile.strategy
    seq: list[str] = []
    metrics: dict[str, Any] = {}

    def _seq_kwargs():
        return dict(
            candidates=cand,
            max_pieces=profile.max_pieces,
            sharp_turn_deg=profile.sharp_turn_deg,
            max_radius_on_sharp=profile.max_radius_on_sharp,
            dist_tol_mm=profile.dist_tol_mm,
            look_ahead_mm=_look_ahead(profile),
        )

    if strategy == "sequential":
        try:
            result = sequential_follow(
                cl, get_part, avail, shop=shop, loose=True, **_seq_kwargs()
            )
        except TypeError:
            result = sequential_follow(cl, get_part, avail, **_seq_kwargs())
        seq = list(result.sequence)
        metrics = dict(result.metrics)
    elif strategy == "corner_first":
        try:
            result = corner_first_build(cl, get_part, avail, min_turn_deg=profile.min_turn_deg, shop=shop)
        except TypeError:
            result = corner_first_build(cl, get_part, avail, min_turn_deg=profile.min_turn_deg)
        seq = list(result.sequence)
        metrics = dict(result.metrics)
    else:
        try:
            result = corner_first_build(cl, get_part, avail, min_turn_deg=profile.min_turn_deg, shop=shop)
        except TypeError:
            result = corner_first_build(cl, get_part, avail, min_turn_deg=profile.min_turn_deg)
        seq = list(result.sequence)
        metrics = dict(result.metrics)
        if profile.run_coverage_fill:
            try:
                seq = coverage_fill(seq, cl, get_part, avail, prefer_sharp_first=True, shop=shop)
            except TypeError:
                seq = coverage_fill(seq, cl, get_part, avail, prefer_sharp_first=True)
            metrics["n_pieces"] = len(seq)
        if len(seq) < 8:
            try:
                alt = sequential_follow(cl, get_part, avail, shop=shop, loose=True, **_seq_kwargs())
                if len(alt.sequence) > len(seq):
                    seq = list(alt.sequence)
                    metrics = dict(alt.metrics)
                    strategy = "sequential"
            except TypeError:
                alt = sequential_follow(cl, get_part, avail, **_seq_kwargs())
                if len(alt.sequence) > len(seq):
                    seq = list(alt.sequence)
                    metrics = dict(alt.metrics)
                    strategy = "sequential"

    metrics["accuracy_level"] = profile.level.value
    metrics["accuracy_letter"] = profile.letter
    metrics["max_pieces_cap"] = profile.max_pieces
    return seq, metrics, strategy


def optimize_layout(req: OptimizeRequest) -> OptimizeResult:
    profile = get_profile(req.accuracy_level)
    parts = load_parts(req.parts_json)

    def get_part(c: str):
        return get_part_by_id(parts, c)

    catalog_ids = [p.id for p in parts] or candidates_for(profile)
    user_inv = dict(req.inventory or {})
    shopping_inv = dict(user_inv)
    from_scratch = bool(req.from_scratch)
    if from_scratch:
        user_inv = {}
        shopping_inv = {}
    if profile.ignore_inventory:
        shopping_inv = {}
        user_inv = {}

    unlimited = profile.unlimited if req.unlimited is None else bool(req.unlimited)
    if unlimited:
        profile = LevelProfile(**{**profile.__dict__, "unlimited": True, "inventory_only": False})

    if profile.ignore_inventory:
        avail = {base_id(i): 999 for i in catalog_ids}
        for code in candidates_for(profile):
            avail[base_id(code)] = max(avail.get(base_id(code), 0), 999)
        shop = ShopGate(owned={}, max_shop_pieces=999, max_shop_skus=99, unlimited=True)
    else:
        avail = resolve_availability(profile, user_inv, catalog_ids)
        shop = ShopGate.from_profile(profile, user_inv)

    loaded = load_track_centreline(req.track_id)
    target_mm = target_length_for(
        profile,
        getattr(loaded, "official_length_m", None),
        override_mm=float(req.target_length_mm) if req.target_length_mm else None,
        track_id=req.track_id,
    )
    scaled = scale_centreline(loaded.points_m, target_mm, close=True)
    cl = densify_polyline(scaled, step=profile.densify_step_mm)

    if req.strategy:
        from monza_optimizer.optimize.accuracy_levels import LevelProfile as LP
        profile = LP(**{**profile.__dict__, "strategy": req.strategy})

    cand = candidates_for(profile)
    seq, metrics, strategy = _run_pipeline(cl, get_part, avail, profile, cand, shop=shop)
    if not profile.ignore_inventory:
        seq = enforce_shop_cap(seq, user_inv, profile, get_part=get_part)
    start_pose = Pose(cl.points[0][0], cl.points[0][1], cl.heading(0))
    close_cands = [
        "C8236", "C8200", "C8207",
        "C8206L", "C8206R", "C8010L", "C8010R",
        "C8204L", "C8204R", "C8234L", "C8234R",
    ]
    if profile.letter not in {"A", "B"}:
        close_cands = ["C8205"] + close_cands + ["C8201L", "C8201R"]
    close_shop = ShopGate(owned={}, max_shop_pieces=999, max_shop_skus=99, unlimited=True)
    seq, close_stats = close_loop(
        seq, start_pose, get_part, avail, close_shop,
        max_pieces=24,
        candidates=close_cands,
        beam_width=48,
        lateral=True,
    )
    metrics.update({
        "pos_mm": close_stats.get("pos_mm", metrics.get("pos_mm")),
        "head_deg": close_stats.get("head_deg", metrics.get("head_deg")),
        "closed": close_stats.get("closed"),
        "pos_before_close_mm": close_stats.get("pos_before_mm"),
        "close_added": close_stats.get("added"),
        "from_scratch": from_scratch,
    })

    from monza_optimizer.geometry.path import path_length as _plen
    built = _plen([get_part(c) for c in seq if get_part(c)]) if seq else 0.0
    metrics["length_mm"] = built
    metrics["target_length_mm"] = target_mm
    metrics["n_pieces"] = len(seq)
    metrics["cover_frac"] = built / max(target_mm, 1.0)
    tiny = (not seq) or len(seq) < 8 or built < 1500.0
    metrics["collapsed"] = tiny
    if tiny:
        kit = closed_kit_loop(user_inv or shopping_inv, get_part)
        if kit:
            seq = kit
            built = _plen([get_part(c) for c in seq if get_part(c)])
            metrics["kit_loop"] = True
            metrics["closed"] = True
            metrics["n_pieces"] = len(seq)
            metrics["length_mm"] = built
            metrics["cover_frac"] = built / max(target_mm, 1.0)
            metrics["kit_note"] = (
                "Follow produced almost no pieces. Graphics show the closed kit oval. "
                "Shopping list is still the gap to the named circuit."
            )

    bom = dict(Counter(base_id(c) for c in seq))
    shop_list = shopping_list(bom, shopping_inv, profile)
    basket = shop_list.as_dict()
    dialogue = join_dialogue_for(profile, metrics)
    if dialogue is not None:
        basket["join_dialogue"] = dialogue
    if metrics.get("kit_note"):
        basket["kit_note"] = metrics["kit_note"]
    if from_scratch:
        basket["from_scratch"] = True
        basket["notes"] = list(basket.get("notes") or []) + [
            "Started from an empty box. Every piece on this list is to buy."
        ]

    title = f"{req.track_id} {profile.letter}"
    lay = lay_payload(seq, get_part, title=f"Lay-list - {title}")
    pack = build_output_pack(
        seq,
        get_part,
        title=title,
        wanted=req.outputs,
        shopping=basket,
        include_binary=bool(req.outputs),
        outline_points=scaled,
    )

    return OptimizeResult(
        sequence=seq,
        bom=bom,
        metrics=metrics,
        track_id=req.track_id,
        strategy=strategy,
        accuracy_level=profile.level.value,
        shopping=basket,
        lay=lay,
        outputs=pack,
        profile={
            "id": profile.level.value,
            "letter": profile.letter,
            "label": profile.label,
            "pitch": profile.pitch,
            "unlimited": profile.unlimited,
            "inventory_only": profile.inventory_only,
            "ignore_inventory": profile.ignore_inventory,
            "from_scratch": from_scratch,
            "target_length_mm": profile.target_length_mm,
        },
    )


def export_result_3mf(
    result: OptimizeResult,
    out_path: str | Path,
    parts_json: str = "parts.json",
    outline_from_track: bool = True,
    target_length_mm: float | None = None,
) -> Path:
    parts = load_parts(parts_json)

    def get_part(c: str):
        return get_part_by_id(parts, c)

    outline = None
    length = target_length_mm or result.metrics.get("target_length_mm") or 25000.0
    if outline_from_track:
        try:
            loaded = load_track_centreline(result.track_id)
            outline = scale_centreline(loaded.points_m, float(length), close=True)
        except Exception:
            outline = None
    title = f"{result.track_id} ({result.accuracy_level}/{result.strategy})"
    return build_track_3mf(
        result.sequence,
        get_part,
        out_path,
        outline_points=outline,
        title=title,
    )


def tracks_for_ui() -> list[dict]:
    return list_tracks()


def accuracy_levels_for_ui() -> list[dict]:
    return levels_for_ui()


def outputs_for_ui() -> list[dict]:
    return list(OUTPUT_MENU)
