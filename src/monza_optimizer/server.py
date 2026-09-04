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
    version="1.3.5",
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
def levels(track_id: str | None = Query(None)) -> list[dict[str, Any]]:
    return accuracy_levels_for_ui(track_id)


@app.get("/calendar")
def calendar(days: int = Query(28, ge=1, le=120)) -> dict[str, Any]:
    return upcoming_events(days=days)
