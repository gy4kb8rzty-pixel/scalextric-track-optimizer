# GitHub status — monza-optimizer-v1

Lovable HTTP backend lives on this branch. `main` stays untouched
until a layout is physically verified.

## Wrapper data

- `data/WORKFLOW.json` — inventory → circuit → ambition → basket → join talk
- `data/ACCURACY_LEVELS.json` — 0 / A–D
- `data/tracks/CIRCUITS_INDEX.json`
- `src/monza_optimizer/server.py` — FastAPI (`GET /health /tracks /levels`, `POST /optimize`)
- `docs/LOVABLE_BACKEND.md`

## Do not

- Invent unofficial SKUs
- Bypass connector / lane / collision checks
- Merge this branch to `main` as a convenience shortcut
- Expose E as a shopper level
