# Track geometry sources

Replaced on `monza-optimizer-v1` from MIT-licensed [bacinger/f1-circuits](https://github.com/bacinger/f1-circuits).

| File | Circuit | Source | Notes |
|------|---------|--------|-------|
| `monaco_centerline_mm.json` | Circuit de Monaco (3.337 km) | `circuits/mc-1929.geojson` | Lon/lat projected to local mm. Polyline length ~3.33 km. |
| `nurburgring_gp_centerline_mm.json` | Nürburgring GP loop (5.148 km) | `circuits/de-1927.geojson` | This is the **Grand Prix** circuit, not the Nordschleife. |
| `nordschleife_outline_mm.json` | Nordschleife | *not replaced* | No MIT GeoJSON of the 20.8 km Nordschleife is in f1-circuits. OSM Overpass was unreachable from this environment. Keep using the GP file or drop an official/OSM extract here. |
| `charlotte_roval_centerline_mm.json` | Charlotte Roval | *not replaced* | Not an F1 circuit; no bacinger file. Wikimedia SVG was rate-limited (HTTP 429). |

Units: millimetres in a local ENU frame centred on the mean lon/lat of the source polyline.
License of imported polylines: MIT © Tomislav Bacinger 2019–2025.
