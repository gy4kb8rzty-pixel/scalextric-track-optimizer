# Four accuracy levels

Sales-pitch ladder. The wrapper calls one level; the optimizer never invents unofficial parts.

| Letter | id | Inventory | Shop cart | Builder | Table scale |
|--------|----|-----------|-----------|---------|-------------|
| A | `lean_budget` | stock only | empty | sequential, compact pieces, few joints | 14 m |
| B | `budget` | stock first | ≤ 8 pieces / 3 SKUs | hybrid, standard set | 18 m |
| C | `detailed` | stock + shop | ≤ 40 pieces / 12 SKUs | hybrid, hairpins first, coverage fill, local re-opt | 25 m |
| D | `full_accuracy` | ignored (labelled unlimited) | full SKU map | hybrid, tight tolerances | 32 m |

## Wrapper contract

```
POST optimize
  track_id: str
  inventory: { sku: qty }
  accuracy_level: "A" | "B" | "C" | "D" | lean_budget | budget | detailed | full_accuracy

→ sequence, bom, metrics, shopping { used, owned_used, leftover, missing, within_shop_budget }, profile
```

Python:

```python
from monza_optimizer.api import OptimizeRequest, optimize_layout, accuracy_levels_for_ui

req = OptimizeRequest(track_id="monaco", inventory={"C8205": 20}, accuracy_level="B")
result = optimize_layout(req)
result.shopping["missing"]   # cart lines
```

`accuracy_levels_for_ui()` feeds the A–D picker.

## Hard rules

- Physical correctness beats the score at every level.
- A never adds SKUs. If the lap cannot close, `within_shop_budget` is false.
- B/C may open a short official-catalogue cart; over-cap is flagged, not silently dropped.
- D is the ceiling and is labelled unlimited.
- `strategy` and `target_length_mm` on the request still override the level defaults when the wrapper wants a one-off.
