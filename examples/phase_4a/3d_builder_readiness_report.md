# 3D Builder Readiness Report

- 3MF generated: yes (`monza_candidate_002.3mf`).
- Source of truth: decoded in-memory sequence from `output/candidate_monza_002_lay.base64.txt`.
- Piece count: 108.
- All part identities preserved: yes.
- All orientations preserved in placement table: yes.
- New Track Designer `.lay` generated: no.
- New optimization run: no.
- All parts used real mesh data: False.
- Parametric fallback parts: ['C187'].
- Microsoft 3D Builder expectation: should open as a valid 3MF package containing documented envelope solids.
- Known limitation: true connector geometry and flattened DirectX mesh transforms are not fully recovered in this implementation; fallbacks are documented instead of silent.
- Next recommended phase: implement binary DirectX `.x` transform/mesh importer and replace envelope solids with recovered part meshes.
