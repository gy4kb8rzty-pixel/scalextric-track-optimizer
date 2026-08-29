# Lovable site integration

Goal: interactive web UI where each user supplies **their inventory**,
picks a **real circuit**, chooses an **accuracy level** (A–D), and receives
a valid Scalextric layout (preview + 3MF / BOM / shop cart).

## Backend surface

Use `monza_optimizer.api` (Python). Expose via FastAPI / serverless / Lovable
backend actions:

| Function | Purpose |
|----------|---------|
| `tracks_for_ui()` | Track picker metadata |
| `accuracy_levels_for_ui()` | A–D picker (letter, pitch, shop caps) |
| `default_inventory_from_catalog()` | Start from catalog quantities |
| `optimize_layout(OptimizeRequest)` | Build sequence + metrics + BOM + shopping |
| `export_result_3mf(...)` | Downloadable 3MF for 3D Builder |

### OptimizeRequest fields

- `track_id` — `monza` | `silverstone` | `monaco` | `daytona` | …
- `inventory` — `{ "C8205": 39, "C8235": 12, ... }` (base ids)
- `accuracy_level` — `A`/`B`/`C`/`D` or `lean_budget` | `budget` | `detailed` | `full_accuracy`
- `target_length_mm` — optional override of the level default
- `strategy` — optional override (`corner_first` | `sequential` | `hybrid`)
- `unlimited` — optional override (D is already unlimited)

### Accuracy levels (sales ladder)

See `docs/ACCURACY_LEVELS.md`.

1. **A Lean Budget** — inventory only, silhouette, fewest pieces
2. **B Budget** — inventory first, smallest official cart that closes the lap
3. **C Detailed** — hairpins first, closer outline, full BOM + shop list
4. **D Full Accuracy** — unlimited official catalogue, complete SKU map

### Strategies (used internally by a level)

1. **corner_first** — place hairpins/sharp bends first, then connect
2. **sequential** — walk full centreline; reject large-R on sharp turns
3. **hybrid** — corner_first + coverage_fill on remaining red-line gaps

## Recommended flow

1. User picks track → outline thumbnail
2. User edits inventory
3. User chooses accuracy level A–D
4. `optimize_layout` → BOM + shopping.missing (cart lines)
5. `export_result_3mf` → download
6. Optional Pareto set for multi-objective search

## Do not

- Bypass connector / lane / collision checks for a prettier score
- Replace Pareto with a single weighted score for primary ranking
- Invent unofficial SKUs at any level
