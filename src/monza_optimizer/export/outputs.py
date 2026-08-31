"""Choosable deliverables after optimize: shopping (default) plus lay/3mf/pdf/png."""

from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable, Sequence

from monza_optimizer.export.lay_list import lay_payload
from monza_optimizer.export.plan_view import render_pdf, render_png, render_svg
from monza_optimizer.export.threemf_builder import build_track_3mf

OUTPUT_MENU = [
    {
        "id": "shopping",
        "label": "Shopping list",
        "default": True,
        "kind": "json",
        "note": "Always returned on /optimize as shopping.",
    },
    {
        "id": "lay",
        "label": "Lay-list (SKU + left/right)",
        "default": True,
        "kind": "json+text",
        "note": "Build order: step, official part number, L/R.",
    },
    {
        "id": "svg",
        "label": "Plan view SVG",
        "default": False,
        "kind": "image/svg+xml",
    },
    {
        "id": "png",
        "label": "Plan view PNG",
        "default": False,
        "kind": "image/png",
    },
    {
        "id": "pdf",
        "label": "Plan PDF",
        "default": False,
        "kind": "application/pdf",
    },
    {
        "id": "3mf",
        "label": "3D Builder 3MF",
        "default": False,
        "kind": "model/3mf",
        "note": "Colour-coded pieces for Microsoft 3D Builder.",
    },
]

CHOOSABLE = {row["id"] for row in OUTPUT_MENU}


def normalize_wanted(wanted: Iterable[str] | None) -> list[str]:
    if not wanted:
        return ["shopping", "lay"]
    out: list[str] = []
    for raw in wanted:
        key = str(raw).strip().lower()
        if key in ("threemf", "3d", "3d-builder"):
            key = "3mf"
        if key in ("lay-list", "laylist", "list"):
            key = "lay"
        if key in CHOOSABLE and key not in out:
            out.append(key)
    if "shopping" not in out:
        out.insert(0, "shopping")
    return out


def build_output_pack(
    sequence: Sequence[str],
    get_part: Callable,
    *,
    title: str,
    wanted: Iterable[str] | None = None,
    shopping: dict[str, Any] | None = None,
    include_binary: bool = True,
    outline_points: Sequence[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    want = normalize_wanted(wanted)
    pack: dict[str, Any] = {"wanted": want, "available": [r["id"] for r in OUTPUT_MENU]}
    if "shopping" in want and shopping is not None:
        pack["shopping"] = shopping
    if "lay" in want or "pdf" in want:
        pack["lay"] = lay_payload(list(sequence), get_part, title=f"Lay-list - {title}")
    files: dict[str, Any] = {}
    if include_binary:
        if "svg" in want:
            svg = render_svg(sequence, get_part, title=title, outline_points=outline_points)
            files["svg"] = {
                "filename": _fname(title, "svg"),
                "media_type": "image/svg+xml",
                "text": svg,
            }
        if "png" in want:
            png = render_png(sequence, get_part, outline_points=outline_points)
            files["png"] = {
                "filename": _fname(title, "png"),
                "media_type": "image/png",
                "base64": base64.b64encode(png).decode("ascii"),
            }
        if "pdf" in want:
            text = pack.get("lay", {}).get("text") or ""
            pdf = render_pdf(sequence, get_part, title, text, outline_points=outline_points)
            files["pdf"] = {
                "filename": _fname(title, "pdf"),
                "media_type": "application/pdf",
                "base64": base64.b64encode(pdf).decode("ascii"),
            }
        if "3mf" in want:
            with TemporaryDirectory() as tmp:
                path = Path(tmp) / _fname(title, "3mf")
                build_track_3mf(list(sequence), get_part, path, title=title)
                blob = path.read_bytes()
            files["3mf"] = {
                "filename": _fname(title, "3mf"),
                "media_type": "model/3mf",
                "base64": base64.b64encode(blob).decode("ascii"),
            }
    pack["files"] = files
    return pack


def _fname(title: str, ext: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower()).strip("-") or "layout"
    return f"{slug[:40]}.{ext}"
