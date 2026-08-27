# Lovable site integration

Goal: interactive web UI where each user supplies **their inventory** and
**detailing preferences**, selects a real circuit, and receives a valid
Scalextric layout (preview + 3MF / BOM).

## Backend surface

Use `monza_optimizer.api` (Python). Expose via FastAPI / serverless / Lovable
backend actions:

| Function | Purpose |
|----------|---------|
| `tracks_for_ui()` | Track picker metadata |
| `default_inventory_from_catalog()` | Start from catalog quantities |
| `optimize_layout(OptimizeRequest)` | Build sequence + metrics + BOM |
| `export_result_3mf(...)` | Downloadable 3MF for 3D Builder |

### OptimizeRequest fields

- `track_id` — `monza` | `silverstone` | `monaco` | `nordschleife` | …
- `inventory` — `{ "C8205": 39, "C8235": 12, ... }` (base ids)
- `target_length_mm` — scale real circuit to table size
- `strategy` — `corner_first` | `sequential` | `hybrid`
- `unlimited` — ignore inventory caps (demo / accuracy stress-test)

### Strategies

1. **corner_first** — place hairpins/sharp bends first, then connect (Monaco-style)
2. **sequential** — walk full centreline; reject large-R on sharp turns
3. **hybrid** — corner_first + coverage_fill on remaining red-line gaps

## User-specific inventory

Store per-user JSON with base part ids → quantities. Map aliases via `base_id()`.

## User-specific detailing

Future hooks: colour themes, borders, elevation, export quality.
Physical validity stays independent of cosmetic detailing.

## Recommended flow

1. User picks track → outline thumbnail
2. User edits inventory
3. User chooses scale + strategy
4. `optimize_layout` → BOM + metrics
5. `export_result_3mf` → download
6. Optional Pareto set for multi-objective search

## Do not

- Bypass connector / lane / collision checks for a prettier score
- Replace Pareto with a single weighted score for primary ranking
