# GitHub status — monza-optimizer-v1

Working branch for the sales-pitch Track Designer. `main` stays untouched
until a layout is physically verified.

## Wrapper data (this drop)

- `data/WORKFLOW.json` — four-step pitch flow
- `data/ACCURACY_LEVELS.json` — A–D picker
- `data/tracks/CIRCUITS_INDEX.json` — F1 + NASCAR Cup + Nordschleife
- `data/OPTIMIZE_REQUEST.schema.json` / `data/OPTIMIZE_RESULT.schema.json`
- `data/USER_INVENTORY.schema.json` + example
- `docs/SALES_WORKFLOW.md`

## Already on the branch

- F1 and NASCAR centreline JSONs under `data/tracks/`
- `src/monza_optimizer/api.py` — `accuracy_level` + shopping cart
- ShopGate / enforce_shop_cap so B can land inside 8 pieces

## Do not

- Invent unofficial SKUs
- Bypass connector / lane / collision checks
- Merge this branch to `main` as a convenience shortcut
