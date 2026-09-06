# Sales-pitch workflow (data contract)

The wrapper does four steps. Every payload lives under `data/` on
`monza-optimizer-v1`. Do not merge to `main` until a layout is physically verified.

```
Inventory  →  Circuit  →  Ambition A–D  →  Basket (Shop SKUs)
```

| Step | User action | Data | API |
|------|-------------|------|-----|
| 1 Inventory | Parts on the table | `data/USER_INVENTORY.schema.json` | request.inventory |
| 2 Circuit | Named Grand Prix / Cup venue | `data/tracks/CIRCUITS_INDEX.json` | `tracks_for_ui()` |
| 3 Ambition | Lean Budget · Budget · Detailed · Full Accuracy | `data/ACCURACY_LEVELS.json` | `accuracy_levels_for_ui()` |
| 4 Basket | Missing official SKUs | `shopping.missing` | `optimize_layout()` |

Featured circuits for the first Shop screen: **Monza, Silverstone, Monaco, Charlotte Roval, Daytona**.

```python
from monza_optimizer.api import (
    OptimizeRequest, optimize_layout,
    tracks_for_ui, accuracy_levels_for_ui,
)

req = OptimizeRequest(
    track_id="monaco",
    inventory={"C8205": 39, "C8235": 5},
    accuracy_level="B",
)
result = optimize_layout(req)
cart = result.shopping["missing"]
```

Rules the wrapper must not break:

- Official catalogue only.
- Connectors / lanes / closure beat the score.
- A never adds SKUs. B ≤ 8 pieces / 3 SKUs. C ≤ 40 / 12. D is labelled unlimited.
- `within_shop_budget` is the flag for “this pack is sellable at this rung.”
