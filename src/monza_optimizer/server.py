"""HTTP surface for Lovable / wrappers. No second optimizer."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from monza_optimizer.api import (
    OptimizeRequest,
    accuracy_levels_for_ui,
    optimize_layout,
    tracks_for_ui,
)

app = FastAPI(
    title="Scalextric Track Designer API",
    version="1.0.0",
    description="Inventory + circuit + ambition → official BOM and shop list.",
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
    accuracy_level: str = "B"
    target_length_mm: float | None = None
    strategy: str | None = None
    unlimited: bool | None = None
    parts_json: str = "parts.json"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tracks")
def tracks() -> list[dict[str, Any]]:
    return tracks_for_ui()


@app.get("/levels")
def levels() -> list[dict[str, Any]]:
    return accuracy_levels_for_ui()


@app.post("/optimize")
def optimize(body: OptimizeBody) -> dict[str, Any]:
    try:
        result = optimize_layout(
            OptimizeRequest(
                track_id=body.track_id,
                inventory=dict(body.inventory or {}),
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
