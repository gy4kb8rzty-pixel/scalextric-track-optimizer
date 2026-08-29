# Track geometry sources

Centrelines on `monza-optimizer-v1` are projected from MIT-licensed [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits) GeoJSON (lon/lat to local millimetres about each circuit centroid).

## Bundle

- `data/tracks/f1_centrelines_mm.json` — all 2025/2026 F1 circuits (and 2025-only Bahrain, Jeddah, Imola)
- `data/tracks/F1_CIRCUITS_INDEX.json` — ids, official lengths, point counts, calendar years
- Per-circuit files: `data/tracks/<id>_centerline_mm.json`

## 2026 calendar mapping

Albert Park, Shanghai, Suzuka, Miami, Montreal, Monaco, Barcelona, Red Bull Ring, Silverstone, Spa, Hungaroring, Zandvoort, Monza, Madring (es-2026), Baku, Sepang (2026 Bahrain GP venue), Marina Bay, COTA, Mexico, Interlagos, Las Vegas, Lusail, Yas Marina.

2025-only in the bundle: Bahrain International, Jeddah, Imola.

## Still not in this import

- Nordschleife 20.8 km (not an F1 2025/2026 race; no bacinger file)
- Charlotte Roval (NASCAR)

License of imported polylines: MIT © Tomislav Bacinger 2019–2025.
