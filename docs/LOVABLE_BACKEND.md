# Lovable backend

Repo: `gy4kb8rzty-pixel/scalextric-track-optimizer`  
Branch: `monza-optimizer-v1` (do not merge to `main` until a layout is physically verified)

## Run locally

```bash
pip install -e ".[api,dev]"
uvicorn monza_optimizer.server:app --reload --port 8000
```

## Endpoints

| Method | Path | Body / query |
|--------|------|----------------|
| GET | `/health` | — |
| GET | `/tracks` | featured + available flags |
| GET | `/levels` | `0 A B C D` — no E |
| POST | `/optimize` | JSON `OptimizeBody` |

### POST /optimize

```json
{
  "track_id": "monaco",
  "inventory": {"C8205": 10},
  "accuracy_level": "0"
}
```

Empty `inventory` is an empty box. The catalogue is not injected.

Response includes `sequence`, `bom`, `metrics` (`closed`, `collapsed`, `cover_frac`, `pos_mm`, `target_length_mm`), `shopping.missing`, and on Bare Bones `shopping.join_dialogue` (`click` | `pinch_or_short` | `open`).

## Pitch flow

Inventory → Circuit → Ambition → Basket → Bare Bones join talk → Shop.

Rules: official SKUs only. Closure beats score. Pinch is not a click. E (1:32 true scale) is not a shopper level.

## curl

```bash
curl -s localhost:8000/levels | head
curl -s localhost:8000/optimize \
  -H 'content-type: application/json' \
  -d '{"track_id":"monza","inventory":{},"accuracy_level":"B"}'
```
