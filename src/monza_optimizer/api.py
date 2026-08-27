"""High-level API for web / Lovable integration.

User-specific inventory + track selection → optimized layout + exports.
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
from monza_optimizer.reference import list_tracks, load_track_centreline, scale_centreline
from monza_optimizer.export import build_track_3mf


@dataclass
class OptimizeRequest:
    """Input for one optimization run (serialisable for Lovable)."""
    track_id: str = "monza"
    inventory: dict[str, int] = field(default_factory=dict)  # base_id -> qty
    target_length_mm: float = 25000.0
    strategy: str = "corner_first"  # corner_first | sequential | hybrid
    unlimited: bool = False
    parts_json: str = "parts.json"


@dataclass
class OptimizeResult:
    sequence: list[str]
    bom: dict[str, int]
    metrics: dict[str, Any]
    track_id: str
    strategy: str


def default_inventory_from_catalog(parts_json: str = "parts.json") -> dict[str, int]:
    parts = load_parts(parts_json)
    inv: dict[str, int] = {}
    for p in parts:
        inv[base_id(p.id)] = inv.get(base_id(p.id), 0) + getattr(p, "quantity", 1)
    return inv


def optimize_layout(req: OptimizeRequest) -> OptimizeResult:
    """Run construction pipeline for a track + inventory."""
    parts = load_parts(req.parts_json)
    def get_part(c: str):
        return get_part_by_id(parts, c)

    if req.unlimited:
        avail = {base_id(p.id): 999 for p in parts}
    else:
        avail = dict(req.inventory) if req.inventory else default_inventory_from_catalog(req.parts_json)

    profile = load_track_centreline(req.track_id)
    scaled = scale_centreline(profile.points_m, req.target_length_mm, close=True)
    cl = densify_polyline(scaled, step=14.0)

    strategy = req.strategy
    if strategy == "corner_first":
        result = corner_first_build(cl, get_part, avail, min_turn_deg=28.0)
        seq = list(result.sequence)
        metrics = dict(result.metrics)
    elif strategy == "sequential":
        result = sequential_follow(cl, get_part, avail)
        seq = list(result.sequence)
        metrics = dict(result.metrics)
    else:  # hybrid: corner-first then sequential coverage
        result = corner_first_build(cl, get_part, avail, min_turn_deg=28.0)
        seq = list(result.sequence)
        seq = coverage_fill(seq, cl, get_part, avail, prefer_sharp_first=True)
        metrics = dict(result.metrics)
        metrics["n_pieces"] = len(seq)

    bom = dict(Counter(base_id(c) for c in seq))
    return OptimizeResult(
        sequence=seq,
        bom=bom,
        metrics=metrics,
        track_id=req.track_id,
        strategy=strategy,
    )


def export_result_3mf(
    result: OptimizeResult,
    out_path: str | Path,
    parts_json: str = "parts.json",
    outline_from_track: bool = True,
    target_length_mm: float = 25000.0,
) -> Path:
    parts = load_parts(parts_json)
    def get_part(c: str):
        return get_part_by_id(parts, c)

    outline = None
    if outline_from_track:
        try:
            profile = load_track_centreline(result.track_id)
            outline = scale_centreline(profile.points_m, target_length_mm, close=True)
        except Exception:
            outline = None
    return build_track_3mf(
        result.sequence,
        get_part,
        out_path,
        outline_points=outline,
        title=f"{result.track_id} ({result.strategy})",
    )


def tracks_for_ui() -> list[dict]:
    """JSON-friendly track list for Lovable site."""
    return list_tracks()
