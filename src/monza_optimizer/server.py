"""HTTP surface for Lovable / wrappers. No second optimizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from monza_optimizer.api import (
    OptimizeRequest,
    accuracy_levels_for_ui,
    optimize_layout,
    outputs_for_ui,
    tracks_for_ui,
)
from monza_optimizer.catalog import load_parts, get_part_by_id
from monza_optimizer.export import build_output_pack
from monza_optimizer.optimize.inventory_picker import picker_payload, ticks_to_inventory

app = FastAPI(
    title="Scalextric Track Designer API",
    version="1.2.0",
    description="Inventory + circuit + ambition → official BOM, lay-list, and files.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_ART = {
    "c8205.bmp",
    "c8206r.bmp",
    "512x512_c8206.bmp",
    "c8207p.bmp",
    "c8200p.bmp",
    "c8236p.bmp",
    "c8204lp.bmp",
    "c8204rp.bmp",
    "c8235lp.bmp",
    "c8235rp.bmp",
    "c8234lp.bmp",
    "c8234rp.bmp",
    "c156lp.bmp",
    "c156rp.bmp",
    "c8010lp.bmp",
    "c8010r.bmp",
}


class OptimizeBody(BaseModel):
    track_id: str = "monza"
    inventory: dict[str, int] = Field(default_factory=dict)
    ticks: list[dict[str, Any]] | None = None
    accuracy_level: str = "B"
    target_length_mm: float | None = None
    strategy: str | None = None
    unlimited: bool | None = None
    parts_json: str = "parts.json"
    outputs: list[str] | None = None


class TicksBody(BaseModel):
    ticks: list[dict[str, Any]] = Field(default_factory=list)


class ExportBody(BaseModel):
    sequence: list[str]
    track_id: str = "layout"
    outputs: list[str] = Field(default_factory=lambda: ["lay", "svg"])
    parts_json: str = "parts.json"
    as_file: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tracks")
def tracks() -> list[dict[str, Any]]:
    return tracks_for_ui()


@app.get("/levels")
def levels() -> list[dict[str, Any]]:
    return accuracy_levels_for_ui()


@app.get("/outputs")
def outputs() -> dict[str, Any]:
    return {
        "title": "Choose how you want the layout delivered",
        "default": ["shopping", "lay"],
        "formats": outputs_for_ui(),
    }


@app.get("/inventory-picker")
def inventory_picker() -> dict[str, Any]:
    return picker_payload()


@app.get("/part-art/{filename}")
def part_art(filename: str):
    key = filename.strip().lower()
    if key not in _ALLOWED_ART:
        raise HTTPException(status_code=404, detail="unknown part graphic")
    path = REPO_ROOT / filename
    if not path.is_file():
        for child in REPO_ROOT.iterdir():
            if child.name.lower() == key and child.is_file():
                path = child
                break
    if not path.is_file():
        raise HTTPException(status_code=404, detail="graphic file missing")
    return FileResponse(path, media_type="image/bmp")


@app.post("/inventory-from-ticks")
def inventory_from_ticks(body: TicksBody) -> dict[str, Any]:
    inv = ticks_to_inventory(body.ticks)
    return {"inventory": inv, "owned_piece_count": sum(inv.values()), "skus": sorted(inv)}


@app.post("/optimize")
def optimize(body: OptimizeBody) -> dict[str, Any]:
    inventory = dict(body.inventory or {})
    if body.ticks:
        inventory.update(ticks_to_inventory(body.ticks))
    try:
        result = optimize_layout(
            OptimizeRequest(
                track_id=body.track_id,
                inventory=inventory,
                accuracy_level=body.accuracy_level,
                target_length_mm=body.target_length_mm,
                strategy=body.strategy,
                unlimited=body.unlimited,
                parts_json=body.parts_json,
                outputs=body.outputs,
            )
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result.as_dict()


@app.post("/export")
def export(body: ExportBody):
    parts = load_parts(body.parts_json)

    def get_part(c: str):
        return get_part_by_id(parts, c)

    if not body.sequence:
        raise HTTPException(status_code=400, detail="sequence is empty")
    pack = build_output_pack(
        body.sequence,
        get_part,
        title=body.track_id,
        wanted=body.outputs,
        include_binary=True,
    )
    if body.as_file:
        key = body.as_file.lower()
        files = pack.get("files") or {}
        if key == "svg" and "svg" in files:
            return Response(files["svg"]["text"], media_type="image/svg+xml")
        import base64

        if key in files and "base64" in files[key]:
            raw = base64.b64decode(files[key]["base64"])
            return Response(raw, media_type=files[key]["media_type"])
        raise HTTPException(status_code=404, detail=f"no binary for {key}")
    return pack
