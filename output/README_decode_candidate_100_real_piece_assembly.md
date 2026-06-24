# Decode Candidate 100 Real-Piece Assembly 3MF

This handoff stores the Candidate 100 real-piece assembly as Base64 text so it can be committed safely without adding a raw `.3mf` binary.

## Decode

```bash
base64 -d output/candidate_100_real_piece_assembly_3mf.base64.txt > candidate_100_real_piece_assembly.3mf
```

## Validate ZIP contents

```bash
unzip -l candidate_100_real_piece_assembly.3mf
```

Expected required member:

- `3D/3dmodel.model`

## Source limitation

`examples/phase_7a/C187_real_geometry.3mf` was not present; the available fallback `examplesphase_7aC187_real_geometry.3mf` was used for C187 geometry.
