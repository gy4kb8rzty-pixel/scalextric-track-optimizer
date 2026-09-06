# NASCAR Cup track geometry sources

Centrelines on `monza-optimizer-v1` for the 2025/2026 NASCAR Cup Series
calendar, projected from OpenStreetMap (`highway=raceway`, `type=circuit`
relations, SAFER/fence rings) into local millimetres about each venue
centroid. OSM data © OpenStreetMap contributors, ODbL 1.0.

## Files

- `data/tracks/NASCAR_CIRCUITS_INDEX.json` — ids, official lengths, point counts, calendar years
- Per-venue: `data/tracks/<id>_centerline_mm.json`

## 2025 + 2026 Cup venues covered

Daytona, EchoPark/Atlanta, Phoenix, Las Vegas Motor Speedway, Darlington,
Martinsville, Bristol, Kansas, Talladega, Texas, Watkins Glen, Charlotte
oval, Charlotte Roval, Nashville, Michigan, Pocono, Sonoma, Chicagoland,
North Wilkesboro, Indianapolis oval, Iowa, Richmond, New Hampshire,
Gateway, Homestead-Miami, Bowman Gray (Clash), Dover (2026 All-Star).

Reuse F1 files for COTA and Mexico City (2025 Cup).

## Known limitations

- **Texas Motor Speedway oval** is a schematic 1.5-mile quad-oval at the OSM
  facility centroid — OSM does not contain a usable racing-line way.
- **Watkins Glen** is the OSM GP long course (~5.46 km). The NASCAR Cup cut
  is ~3.94 km.
- **Sonoma** is the OSM SRO/full layout (~4.13 km). The NASCAR Cup cut is
  ~3.20 km.
- **Charlotte Roval** OSM mapping is incomplete; current ring is a facility
  proxy, not the 2.28-mile competition layout.
- **Naval Base Coronado / San Diego** (2026 street race) has no stable OSM
  centreline yet.
- Several ovals use SAFER-wall / fence / stadium rings as the racing-line
  proxy when the racing surface itself is split across unjoined ways.

Official lengths are the published Cup configurations (miles × 1609.344).
