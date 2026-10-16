# Scalextric Track Optimizer (Monza Optimizer 1.0+)

Standalone toolkit that builds **closed Scalextric tracks** from verified part
geometry and optimizes them toward **real circuit outlines** (Monza, Silverstone,
Monaco, Nordschleife, Charlotte Roval, …).

Designed so a **Lovable** (or any) interactive site can call a thin API with
**user-specific inventory** and **user-selected track + detailing**.

## Requirements

- Python 3.11+ (3.12 / 3.13 supported)
- PySide6 (desktop GUI)
- Optional: PyInstaller for Windows packaging

## Install

```bash
python -m pip install -e ".[dev]"
```

## Run desktop app

```bash
monza-optimizer
# or
python -m monza_optimizer.app
```

## Core algorithms (this branch)

| Module | Role |
|--------|------|
| `optimize.corner_first` | **Sharp bends first**: detect corners, place curve anchors, gap-fill, local re-opt |
| `optimize.sequential` | Full centreline walk; **rejects large-R (C8204) on sharp turns** |
| `optimize.coverage_fill` | Find uncovered red-line stretches; splice-in fill (sharp gaps first) |
| `optimize.hypervolume` | Pareto hypervolume indicator |
| `geometry.elasticity` | Length-dependent joint tolerance for real-world closure |
| `export.threemf_builder` | Lean 3MF for Microsoft 3D Builder (colour key, red outline tube) |
| `reference.tracks` | Circuit centreline registry under `data/tracks/` |
| `api` | **Lovable-ready** `OptimizeRequest` / `optimize_layout` / `export_result_3mf` |

### Physical correctness always wins

Never bypass geometry, lane, connector, or collision validation. Pareto is not
replaced by weighted scores; profile weights may only guide search/ranking.

## Lovable / web API sketch

```python
from monza_optimizer.api import (
    OptimizeRequest,
    optimize_layout,
    export_result_3mf,
    tracks_for_ui,
    default_inventory_from_catalog,
)

# User inventory (base part id → quantity)
inv = default_inventory_from_catalog("parts.json")
# or inv = {"C8205": 40, "C8235": 12, "C8204": 8, ...}

req = OptimizeRequest(
    track_id="monaco",          # see tracks_for_ui()
    inventory=inv,
    target_length_mm=30000,     # scale real circuit to slot-car size
    strategy="hybrid",          # corner_first | sequential | hybrid
    unlimited=False,
)
result = optimize_layout(req)
print(result.metrics, result.bom)

export_result_3mf(result, "out.3mf", target_length_mm=req.target_length_mm)
```

`tracks_for_ui()` returns JSON-friendly metadata for track pickers.

## Track data

Place centreline files in `data/tracks/`:

| File | Units | Notes |
|------|-------|--------|
| `monza_centerline_m.csv` | m | Real GP centreline |
| `silverstone_centerline_mm.csv` | mm | Scaled reference |
| `monaco_centerline_mm.json` | mm | `{ "scaled": [[x,y], ...] }` |
| `nordschleife_outline_mm.json` | mm | Prefer official outline / GPS |
| `charlotte_roval_centerline_mm.json` | mm | |

Replace placeholders with verified GPS/OSM/official outlines as available.

## Parts catalog

`parts.json` — verified parametric geometry (straights, curves L/R) with quantities.
3MF mesh assets and BMP top-views live in the repo root / `examples/`.

## Test

```bash
pytest
```

## Package (Windows)

```bash
python -m pip install -e ".[dev]"
pyinstaller packaging/monza_optimizer.spec
```

## Branch policy

- `main` — stable releases only
- `monza-optimizer-v1` — active development (algorithms, tracks, export, API)

## Milestones

1. Foundation (app shell)
2. Geometry and catalog
3. Reference geometry
4. Construction-first / corner-first / sequential optimizers
5. GUI
6. Import / export (3MF, SVG, PNG, PDF, …)
7. Verification and release candidate
