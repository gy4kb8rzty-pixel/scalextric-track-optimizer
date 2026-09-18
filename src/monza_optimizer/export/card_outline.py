"""Card silhouettes from the official centreline (never the A-level simplify)."""
from __future__ import annotations

from monza_optimizer.optimize.accuracy_levels import get_profile, target_length_for
from monza_optimizer.reference import load_track_centreline, scale_centreline


def outline_points(track_id: str, level: str = "D") -> list[list[float]] | None:
    tid = str(track_id or "").strip().lower()
    if not tid or tid in {"ad_lib", "create_your_own", "layout", "track"}:
        return None
    letter = (level or "D").upper()
    if letter in {"A", "0"}:
        letter = "D"
    try:
        loaded = load_track_centreline(tid)
        profile = get_profile(letter)
        target = target_length_for(profile, getattr(loaded, "official_length_m", None), track_id=tid)
        pts = scale_centreline(loaded.points_m, target, close=True)
    except Exception:
        return None
    if len(pts) < 8:
        return None
    return [[round(float(x), 2), round(float(y), 2)] for x, y in pts]


def outline_svg(points: list[list[float]], vw: float = 400.0, vh: float = 140.0) -> str | None:
    if not points or len(points) < 8:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = max(maxx - minx, 1e-6)
    h = max(maxy - miny, 1e-6)
    pad = 10.0
    scale = min((vw - 2 * pad) / w, (vh - 2 * pad) / h)
    ox = (vw - w * scale) / 2.0
    oy = (vh - h * scale) / 2.0
    parts = []
    for i, (x, y) in enumerate(points):
        px = ox + (x - minx) * scale
        py = oy + (maxy - y) * scale
        parts.append(("M" if i == 0 else "L") + f"{px:.1f} {py:.1f}")
    d = " ".join(parts) + " Z"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<path d="{d}" fill="none" stroke="#c0392b" stroke-width="2.2" '
        f'stroke-linejoin="round" stroke-linecap="round"/></svg>'
    )


def attach_outline(row: dict) -> dict:
    tid = row.get("id")
    pts = outline_points(tid, "D")
    if pts:
        row["outline_points"] = pts
        svg = outline_svg(pts)
        if svg:
            row["outline_svg"] = svg
    try:
        from monza_optimizer.optimize.nascar_levels import NASCAR_R4_NOTE, nascar_hides_cde
        if nascar_hides_cde(tid):
            row["nascar_r4_only"] = True
            row["max_letter"] = "B"
            row["allowed_levels"] = ["A", "B"]
            row["level_notice"] = NASCAR_R4_NOTE
    except Exception:
        pass
    return row
