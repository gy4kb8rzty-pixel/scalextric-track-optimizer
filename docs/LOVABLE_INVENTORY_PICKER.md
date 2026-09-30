# Lovable inventory tick-box

The wrapper first screen is **owned stock**, not a blank JSON map.

## Endpoints

| Method | Path | Role |
|--------|------|------|
| GET | `/inventory-picker` | Groups of tickable SKUs with name, underside letter, hint, SVG, BMP url |
| GET | `/part-art/{filename}` | Top-view BMP already in the repo (`c8205.bmp`, `c8206r.bmp`, …) |
| POST | `/inventory-from-ticks` | `{ticks:[{sku,qty}]}` → `{inventory:{SKU:n}}` |
| POST | `/optimize` | accepts either `inventory` or `ticks` |

## Card fields Lovable should render

- `thumb_svg` — always present, works on iPhone without a second request
- `thumb_url` — `/part-art/c8205.bmp` when a silhouette exists in the repo
- `letter_under_track` — moulded Sport letter (B = standard straight)
- `hand` — `L` / `R` / null
- `qty_min` / `qty_max` / `default_qty`
- `in_flying_start` + preset `flying_start` (official C1446M mapped pack)

## Suggested UI

1. Preset chips: Empty box | Flying Start
2. One group per family (Straights, R2, R3, …)
3. Card = picture + SKU + stepper
4. POST `/optimize` with the resulting `inventory` and the chosen circuit / level

Count **pieces**, not shop packs. A C8205 box in the Hornby shop is two straights.
