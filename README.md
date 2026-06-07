# scalextric-track-optimizer

## Phase 1 scope

This repository currently contains a minimal Phase 1 foundation for a generic
Scalextric track optimizer. It includes:

- A small `parts.json` inventory with required fields for track parts.
- Python dataclasses for track parts and simple straight/curve geometry.
- Loading and validation for the part inventory.
- A deterministic path calculation for sequences whose parts have geometry.
- Unit tests using `pytest`.

The full optimizer is **not implemented yet**. This phase does not include
solving, optimization, SVG or PNG export, named circuit generation, or packaging
for other tools.

Real Scalextric geometry should only be added when verified. Unknown dimensions
are represented with `geometry: null` and `verified_geometry: false`.

## Running tests

Install the package with test dependencies, then run `pytest`:

```bash
python -m pip install -e '.[dev]'
pytest
```
