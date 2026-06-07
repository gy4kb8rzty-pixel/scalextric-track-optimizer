# scalextric-track-optimizer

## Phase 1 scope

This repository contains a minimal foundation for a generic Scalextric track
optimizer. It includes:

- A `parts.json` inventory with required fields for track parts.
- Python dataclasses for track parts and simple straight/curve geometry.
- Loading and validation for the part inventory.
- A deterministic path calculation for sequences whose parts have geometry.
- Unit tests using `pytest`.

The full optimizer is **not implemented yet**. This project still does not
include solving, optimization, SVG or PNG export, named circuit generation,
layout generation, or packaging for other tools.

Real Scalextric geometry should only be added when verified. Unknown dimensions
are represented with `geometry: null` and `verified_geometry: false`.

## Phase 2 inventory status

Phase 2 replaces the small demo inventory with the real Scalextric / slot-car
track inventory identified so far. Geometry is still deliberately unverified, so
all real inventory entries currently use `geometry: null` and
`verified_geometry: false`.

The current numeric inventory total is **104** track pieces. This excludes
unknown-count accessories such as `SMALL_JOINERS`, which remain in the inventory
with `count: null` until their exact count is confirmed.

Optimization and layout solving are still **not implemented**.

## Running tests

Install the package with test dependencies, then run `pytest`:

```bash
python -m pip install -e '.[dev]'
pytest
```
