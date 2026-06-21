# Phase 4D Monza Optimization

- Inputs: merged Phase 4B full 3MF geometry and Phase 4C closure-first output.
- Placement uses connector-to-connector lengths from the 3MF connector records where present.
- C187 is reconstructed as an 87 mm by 78 mm short-straight prism when used because no C187 3MF is present.
- Binary 3MF output is intentionally not written; the preview package is Base64 text at `output/phase_4d_best_preview_3mf.base64.txt`.

## Ranked candidates

| Rank | Name | Closed | Pieces | Inventory % | Closure mm | Heading deg | Monza score | C187 rebuilt |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | closed_reference_4c | True | 52 | 48.15 | 0.0 | 0.0 | 57 | False |
| 2 | monza_max_inventory | False | 61 | 56.48 | 3078.617 | 90.0 | 100 | True |
| 3 | monza_balanced | False | 55 | 50.93 | 3653.52 | 90.0 | 88 | True |
