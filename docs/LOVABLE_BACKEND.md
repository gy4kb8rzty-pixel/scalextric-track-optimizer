# Lovable backend

Repo: `gy4kb8rzty-pixel/scalextric-track-optimizer`  
Branch: `monza-optimizer-v1`

## Endpoints

| Method | Path | Role |
|--------|------|------|
| GET | `/health` | liveness |
| GET | `/tracks` | circuit picker |
| GET | `/levels` | 0 A B C D |
| GET | `/inventory-picker` | tick-box cards |
| GET | `/outputs` | shopping / lay / svg / png / pdf / 3mf |
| POST | `/optimize` | inventory + optional `outputs` |
| POST | `/export` | sequence → chosen files |

Default result is shopping list + lay-list. Graphics are opt-in.
See `docs/LOVABLE_INVENTORY_PICKER.md` and `docs/LOVABLE_OUTPUTS.md`.
