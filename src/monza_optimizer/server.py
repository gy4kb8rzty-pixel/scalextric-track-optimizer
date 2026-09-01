"""HTTP surface for Lovable / wrappers. No second optimizer."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
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
from monza_optimizer.optimize.inventory_book import apply_purchase, inventory_status
from monza_optimizer.optimize.inventory_picker import picker_payload, ticks_to_inventory
from monza_optimizer.optimize.part_art import bmp_to_png, resolve_art_path
from monza_optimizer.reference.race_calendar import upcoming_events

PUBLIC_API_BASE = os.environ.get(
    "PUBLIC_API_BASE", "https://scalextric-track-optimizer.onrender.com"
).rstrip("/")

app = FastAPI(
    title="Scalextric Track Designer API",
    version="1.3.4",
    description="Inventory + circuit + ambition → official BOM, lay-list, and files.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    from_scratch: bool = False


class TicksBody(BaseModel):
    ticks: list[dict[str, Any]] = Field(default_factory=list)


class BookBody(BaseModel):
    owned: dict[str, int] = Field(default_factory=dict)
    purchased: dict[str, int] = Field(default_factory=dict)
    used: dict[str, int] | None = None
    missing: dict[str, int] | None = None
    leftover: dict[str, int] | None = None
    track_id: str | None = None
    accuracy_level: str | None = None


class ExportBody(BaseModel):
    sequence: list[str]
    track_id: str = "layout"
    outputs: list[str] = Field(default_factory=lambda: ["lay", "svg"])
    parts_json: str = "parts.json"
    as_file: str | None = None


def _absolutize_art(payload: dict[str, Any]) -> dict[str, Any]:
    base = PUBLIC_API_BASE
    for group in payload.get("groups") or []:
        for part in group.get("parts") or []:
            for key in ("thumb_png", "thumb_url"):
                val = part.get(key)
                if isinstance(val, str) and val.startswith("/"):
                    part[key] = base + val
    payload["art_base"] = base + "/part-art"
    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tracks")
def tracks() -> list[dict[str, Any]]:
    return tracks_for_ui()


@app.get("/levels")
def levels() -> list[dict[str, Any]]:
    return accuracy_levels_for_ui()


@app.get("/calendar")
def calendar(days: int = Query(28, ge=1, le=120)) -> dict[str, Any]:
    return upcoming_events(days=days)


@app.get("/outputs")
def outputs() -> dict[str, Any]:
    return {
        "title": "Choose how you want the layout delivered",
        "default": ["shopping", "lay"],
        "formats": outputs_for_ui(),
    }


@app.get("/inventory-picker")
def inventory_picker() -> dict[str, Any]:
    return _absolutize_art(picker_payload())


@app.get("/part-art/{filename}")
def part_art(filename: str):
    path = resolve_art_path(filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="graphic file missing")
    want_png = filename.lower().endswith(".png")
    if want_png:
        try:
            png = bmp_to_png(path.read_bytes())
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        return Response(png, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    return FileResponse(path, media_type="image/bmp", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/inventory-from-ticks")
def inventory_from_ticks(body: TicksBody) -> dict[str, Any]:
    inv = ticks_to_inventory(body.ticks)
    return {"inventory": inv, "owned_piece_count": sum(inv.values()), "skus": sorted(inv)}


@app.post("/inventory/status")
def inventory_status_ep(body: BookBody) -> dict[str, Any]:
    return inventory_status(
        body.owned,
        used=body.used,
        missing=body.missing,
        leftover=body.leftover,
        track_id=body.track_id,
        accuracy_level=body.accuracy_level,
    )


@app.post("/inventory/apply-purchase")
def inventory_apply_purchase(body: BookBody) -> dict[str, Any]:
    owned = apply_purchase(body.owned, body.purchased)
    status = inventory_status(
        owned,
        used=body.used,
        missing={},
        leftover=body.leftover,
        track_id=body.track_id,
        accuracy_level=body.accuracy_level,
    )
    return {"owned": owned, "added": {k: int(v) for k, v in dict(body.purchased or {}).items() if int(v) > 0}, "status": status}


@app.post("/optimize")
def optimize(body: OptimizeBody) -> dict[str, Any]:
    inventory = dict(body.inventory or {})
    if body.ticks:
        inventory.update(ticks_to_inventory(body.ticks))
    if body.from_scratch:
        inventory = {}
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
                from_scratch=body.from_scratch,
            )
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    payload = result.as_dict()
    shop = payload.get("shopping") or {}
    payload["inventory_status"] = inventory_status(
        inventory,
        used=shop.get("owned_used") or shop.get("used"),
        missing=shop.get("missing"),
        leftover=shop.get("leftover"),
        track_id=payload.get("track_id"),
        accuracy_level=payload.get("accuracy_level"),
    )
    return payload


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
