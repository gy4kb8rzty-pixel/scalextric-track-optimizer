"""Manual A: one piece at a time on that track's coarse silhouette."""
from __future__ import annotations

import base64
import math
from collections import Counter
from typing import Any

from monza_optimizer.catalog import load_parts, get_part_by_id, base_id
from monza_optimizer.export.plan_view import render_png
from monza_optimizer.export.threemf_builder import PART_COLORS
from monza_optimizer.geometry.path import compute_track_path
from monza_optimizer.geometry.pose import Pose, normalize_heading
from monza_optimizer.optimize.accuracy_levels import get_profile, target_length_for
from monza_optimizer.optimize.shop_helpers import shopping_list
from monza_optimizer.optimize.silhouette import simplify_for_level_a
from monza_optimizer.reference import list_tracks, load_track_centreline, scale_centreline

MANUAL_A_ENABLED = True
MANUAL_A_GROUPS = (
    ("Straights", ("C8205", "C8207", "C8200", "C8236")),
    ("Radius 1", ("C8201L", "C8201R", "C8202L", "C8202R")),
    ("Radius 2", ("C8206L", "C8206R", "C8234L", "C8234R")),
    ("Radius 3", ("C8204L", "C8204R")),
    ("Radius 4", ("C8235L", "C8235R")),
    ("Chicanes", ("C8010L", "C8010R")),
    ("Crossovers", ("C8203L", "C8203R")),
)
MANUAL_A_SKUS = tuple(sku for _, skus in MANUAL_A_GROUPS for sku in skus)


def _sku_color(code: str) -> str:
    return "#" + PART_COLORS.get(base_id(code), "7F8C8D")


def _sku_cards() -> list[dict[str, str]]:
    cards = []
    for group, skus in MANUAL_A_GROUPS:
        for s in skus:
            cards.append({"sku": s, "color": _sku_color(s), "group": group})
    return cards


def _tid(track_id: str) -> str:
    tid = str(track_id or "").strip().lower()
    if not tid:
        raise ValueError("track_id is required")
    return tid


def _outline(track_id: str):
    loaded = load_track_centreline(track_id)
    profile = get_profile("a")
    target = target_length_for(profile, getattr(loaded, "official_length_m", None), track_id=track_id)
    scaled = scale_centreline(loaded.points_m, target, close=True)
    return simplify_for_level_a(scaled)


def _start_pose(outline):
    if len(outline) < 2:
        return Pose(0.0, 0.0, 90.0)
    x0, y0 = outline[0]
    x1, y1 = outline[1]
    return Pose(x0, y0, math.degrees(math.atan2(y1 - y0, x1 - x0)))


def _end_pose(sequence, get_part, start):
    parts = [get_part(c) for c in sequence if get_part(c)]
    if not parts:
        return start
    return compute_track_path(parts, start=start)[-1]


def _dist_to_outline(x, y, outline):
    best = 1e18
    for i in range(len(outline) - 1):
        ax, ay = outline[i]
        bx, by = outline[i + 1]
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        if den < 1e-9:
            d = math.hypot(x - ax, y - ay)
        else:
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / den))
            d = math.hypot(x - (ax + t * dx), y - (ay + t * dy))
        if d < best:
            best = d
    return best


def _png(sequence, get_part, outline):
    raw = render_png(sequence, get_part, outline_points=outline)
    return base64.b64encode(raw).decode("ascii")


def _state(track_id, sequence, parts_json="parts.json", inventory=None):
    parts = load_parts(parts_json)

    def get_part(c):
        return get_part_by_id(parts, c)

    outline = _outline(track_id)
    start = _start_pose(outline)
    pose = _end_pose(sequence, get_part, start)
    gap = math.hypot(pose.x - start.x, pose.y - start.y)
    head = abs(normalize_heading(pose.heading_degrees - start.heading_degrees))
    on_line = _dist_to_outline(pose.x, pose.y, outline)
    return {
        "hidden": False,
        "enabled": MANUAL_A_ENABLED,
        "mode": "manual_a",
        "track_id": track_id,
        "sequence": list(sequence),
        "n_pieces": len(sequence),
        "gap_mm": round(gap, 1),
        "heading_err_deg": round(head, 1),
        "off_line_mm": round(on_line, 1),
        "on_line": on_line < 420,
        "closed": bool(sequence) and gap < 120 and head < 22,
        "png_base64": _png(sequence, get_part, outline),
        "skus": list(MANUAL_A_SKUS),
        "sku_cards": _sku_cards(),
        "sku_groups": [{"label": label, "skus": list(skus)} for label, skus in MANUAL_A_GROUPS],
        "laid": [{"index": i, "sku": c, "color": _sku_color(c)} for i, c in enumerate(sequence)],
        "hint": "Tap a laid piece to swap it; the rest stays in order from that pose.",
        "shopping": shopping_list(
            dict(Counter(base_id(c) for c in sequence)),
            inventory or {},
            get_profile("a"),
        ).as_dict(),
    }


def manual_meta():
    return {
        "id": "manual_a",
        "label": "Manual A",
        "hidden": False,
        "enabled": MANUAL_A_ENABLED,
        "visible_in_menu": True,
        "tracks": [t["id"] for t in list_tracks()],
        "skus": list(MANUAL_A_SKUS),
        "sku_cards": _sku_cards(),
        "sku_groups": [{"label": label, "skus": list(skus)} for label, skus in MANUAL_A_GROUPS],
        "pitch": "Manual only. One official piece at a time on that track's simple outline.",
    }


def manual_start(track_id, parts_json="parts.json", inventory=None):
    return _state(_tid(track_id), [], parts_json, inventory)


def manual_place(track_id, sequence, sku, parts_json="parts.json", inventory=None):
    code = str(sku or "").strip()
    if code not in MANUAL_A_SKUS and base_id(code) not in {base_id(s) for s in MANUAL_A_SKUS}:
        raise ValueError(f"sku {code} is not on the Manual A list")
    return _state(_tid(track_id), list(sequence or []) + [code], parts_json, inventory)


def manual_undo(track_id, sequence, parts_json="parts.json", inventory=None):
    seq = list(sequence or [])
    if seq:
        seq = seq[:-1]
    return _state(_tid(track_id), seq, parts_json, inventory)


def _valid_sku(code: str) -> str:
    code = str(code or "").strip()
    if code in MANUAL_A_SKUS:
        return code
    raise ValueError(f"sku {code} is not on the Manual A list")


def manual_replace(track_id, sequence, index, sku, parts_json="parts.json", inventory=None):
    tid = _tid(track_id)
    seq = list(sequence or [])
    if not seq:
        raise ValueError("sequence is empty")
    i = int(index)
    if i < 0 or i >= len(seq):
        raise ValueError(f"index {i} out of range 0..{len(seq)-1}")
    seq[i] = _valid_sku(sku)
    return _state(tid, seq, parts_json, inventory)


def manual_finish(track_id, sequence, inventory=None, parts_json="parts.json"):
    state = _state(_tid(track_id), list(sequence or []), parts_json, inventory)
    state["finished"] = True
    return state
