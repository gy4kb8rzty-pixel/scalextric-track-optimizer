# GitHub status (monza-optimizer-v1)

Do not merge to `main` until verified.

## Already on this branch
- Construction algorithms: corner-first, sequential (tight-curve on sharp turns), coverage fill
- Pareto hypervolume + elasticity model
- Lean 3MF exporter + colour key
- `monza_optimizer.api` for Lovable (user inventory + track_id + strategy)
- Track geometry stubs in `data/tracks/`
- F1 2026 + NASCAR Cup 2026 venue catalog in `data/TRACK_CATALOG.json`

## Meshes
Verified part geometry lives in repo-root `parts.json` plus existing BMP / 3MF / zip assets on `main`.
Do not re-upload multi-MB BMP dumps. Point the 3MF loader at those existing assets.

## Still placeholders
Replace these with official/OSM centrelines:
- `data/tracks/monaco_centerline_mm.json`
- `data/tracks/nordschleife_outline_mm.json`
- `data/tracks/charlotte_roval_centerline_mm.json`

Best source for F1 polylines: https://github.com/bacinger/f1-circuits
