"""HTTP surface for Lovable / wrappers. No second optimizer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from monza_optimizer.api import (
    OptimizeRequest,
    accuracy_levels_for_ui,
    optimize_layout,
    tracks_for_ui,
)
from monza_optimizer.optimize.inventory_picker import picker_payload, ticks_to_inventory

app = FastAPI(
    title="Scalextric Track Designer API",
    version="1.1.0",
    description="Inventory + circuit + ambition → official BOM and shop list.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Only the part-identification BMPs already in the repo root.
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


class TicksBody(BaseModel):
    ticks: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tracks")
def tracks() -> list[dict[str, Any]]:
    return tracks_for_ui()


@app.get("/levels")
def levels() -> list[dict[str, Any]]:
    return accuracy_levels_for_ui()


@app.get("/inventory-picker")
def inventory_picker() -> dict[str, Any]:
    """Tick-box catalogue with part graphics for the Lovable inventory step."""
    return picker_payload()


@app.get("/part-art/{filename}")
def part_art(filename: str):
    key = filename.strip().lower()
    if key not in _ALLOWED_ART:
        raise HTTPException(status_code=404, detail="unknown part graphic")
    # Preserve original casing on disk (c8205.bmp vs 512x512_C8206.bmp).
    for candidate in (REPO_ROOT / filename, REPO_ROOT / filename.replace("C", "C")):
        pass
    path = REPO_ROOT / filename
    if not path.is_file():
        # Case-insensitive match among allowed names on disk.
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
            )
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result.as_dict()
