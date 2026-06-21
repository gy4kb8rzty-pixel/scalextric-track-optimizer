# Phase 4B Full 3MF-Based Monza Optimization

- Models extracted and indexed: 230.
- Catalog rows read from workbook: 457.
- Best score: 8.226.
- Closure error: 10309.795 mm.
- Heading error: 90.0 degrees.
- Overlap error: 46409.19 mm².
- Missing 3MF codes in Monza sequence: ['C187'].
- C8205 classification: standard_straight (not crossover).

## Top 10

1. score=8.226 closure=10309.795mm overlap=46409.19mm² scale=0.96 mirror=1 missing_3mf=['C187']
2. score=8.226 closure=10309.795mm overlap=46409.19mm² scale=0.96 mirror=-1 missing_3mf=['C187']
3. score=8.082 closure=10524.583mm overlap=47105.425mm² scale=0.98 mirror=1 missing_3mf=['C187']
4. score=8.082 closure=10524.583mm overlap=47105.425mm² scale=0.98 mirror=-1 missing_3mf=['C187']
5. score=3.386 closure=29531.4mm overlap=0.0mm² scale=1.0 mirror=1 missing_3mf=['C187']
6. score=3.386 closure=29531.4mm overlap=0.0mm² scale=1.0 mirror=-1 missing_3mf=['C187']
7. score=3.32 closure=30122.028mm overlap=0.0mm² scale=1.02 mirror=1 missing_3mf=['C187']
8. score=3.32 closure=30122.028mm overlap=0.0mm² scale=1.02 mirror=-1 missing_3mf=['C187']
9. score=3.256 closure=30712.656mm overlap=0.0mm² scale=1.04 mirror=1 missing_3mf=['C187']
10. score=3.256 closure=30712.656mm overlap=0.0mm² scale=1.04 mirror=-1 missing_3mf=['C187']

## Inventory usage

- C151: 11
- C153: 26
- C154: 2
- C156: 7
- C187: 7
- C8005: 2
- C8006: 2
- C8010: 1
- C8031: 3
- C8200: 1
- C8205: 39
- C8207: 1
- C8235: 5
- C8236: 1

## 3MF availability corrections

- C187: missing from `all_x_3mf_rotated_full_parser.zip`; placement uses fallback dimensions and the preview 3MF excludes real C187 mesh geometry.
- C8205: standard straight track geometry from `c8205.3mf`; not classified as crossover.
