# Candidate 100 Real-Piece Assembly Report

## Inputs

- `examples/phase_4f/best_monza_candidate.json`
- `examples/phase_4f/placement_table.json`
- `all_x_3mf_rotated_full_parser.zip`
- `examplesphase_7aC187_real_geometry.3mf` (fallback because `examples/phase_7a/C187_real_geometry.3mf` was not present)

## Candidate summary

- Name: 40-60 realistic closed Monza
- Piece count: 48
- Inventory usage: {'C8205': 36, 'C187': 4, 'C153': 8}
- Closure error: 0.0 mm
- Heading error: 0.0 degrees

## Validation metrics

- Objects: 48
- Vertices: 9716
- Triangles: 7912
- 3MF ZIP entries: `[Content_Types].xml`, `_rels/.rels`, `3D/3dmodel.model`
- Required model entry present: yes
- More than 1 object: yes
- More than 1000 vertices: yes
- More than 1000 triangles: yes
- Raw `.3mf` committed: no

## Geometry sources used

- `C187.3mf` from `examplesphase_7aC187_real_geometry.3mf`
- `c153l.3mf` from `all_x_3mf_rotated_full_parser.zip:c153l.3mf`
- `c8205.3mf` from `all_x_3mf_rotated_full_parser.zip:c8205.3mf`
