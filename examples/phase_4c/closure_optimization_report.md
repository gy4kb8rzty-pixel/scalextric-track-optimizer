# Phase 4C Connector-Closure-First Monza Optimization

- Best closure error: 0.0 mm.
- Best heading error: 0.0 degrees.
- Piece count: 52.
- Inventory usage: {'C8205': 36, 'C153': 16}.
- Monza score: 100.0.
- Buildable: True.
- Excluded default-search parts: ['C187'].

## Tier ranking

| Rank | Tier | Pieces | Closure mm | Heading deg | Overlap mm² | Monza score | Buildable | Reason |
|---:|---|---:|---:|---:|---:|---:|---|---|
| 1 | 45-60 | 52 | 0.0 | 0.0 | 0.0 | 100.0 | True |  |
| 2 | 30-45 | 32 | 0.0 | 0.0 | 0.0 | 90.0 | True |  |
| 3 | 20-30 | 24 | 0.0 | 0.0 | 0.0 | 86.0 | True |  |
| 4 | 60-80 | 60 | 0.0 | 0.0 | 0.0 | 96.0 | False | inventory violations: {'C8006': 2} |

## Parts preventing larger closed layouts

- C187 is excluded because no 3MF exists in the Phase 4B library.
