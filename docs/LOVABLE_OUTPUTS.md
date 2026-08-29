# Choosable outputs

Default after `/optimize` is still the **shopping list**. The user can add:

| id | What |
|----|------|
| `shopping` | Missing official SKUs (default) |
| `lay` | Assembly list: step, part number, L/R |
| `svg` | Colour plan view |
| `png` | Colour plan view bitmap |
| `pdf` | Plan view + lay-list on one page |
| `3mf` | Microsoft 3D Builder mesh |

## Menu

`GET /outputs` — checkboxes for the result screen.

## On optimize

```json
{
  "track_id": "monza",
  "inventory": {"C8205": 4, "C8206L": 8, "C8206R": 8},
  "accuracy_level": "B",
  "outputs": ["shopping", "lay", "png"]
}
```

`lay` is always filled on the result (`result.lay.rows[]` with `sku` + `hand`).
Binaries are only built when `outputs` asks for them, so the default JSON stays small.

## After optimize

`POST /export` with the returned `sequence` if the user ticks PNG/PDF/3MF later.

```json
{
  "sequence": ["C8205", "C8206L"],
  "track_id": "monza",
  "outputs": ["png", "pdf", "3mf"]
}
```

Files come back as `files.png.base64` (and so on). `as_file: "png"` returns the raw bytes instead.

Lay-list columns: `step`, `sku`, `base`, `hand` (`L`/`R`/null), `hand_label`, `name`, `letter_under_track`.
