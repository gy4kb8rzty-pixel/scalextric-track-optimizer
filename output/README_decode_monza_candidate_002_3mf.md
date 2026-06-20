# Decode Monza Candidate 002 3MF

This directory provides a text-safe Base64 representation of the Phase 4A Microsoft 3D Builder package:

- `monza_candidate_002_3mf.base64.txt` — Base64 text encoding of `monza_candidate_002.3mf`.
- `README_decode_monza_candidate_002_3mf.md` — instructions for recreating the `.3mf` file from the Base64 text.

## Recreate `monza_candidate_002.3mf` on Windows PowerShell

Run this command from the directory containing `monza_candidate_002_3mf.base64.txt`:

```powershell
[IO.File]::WriteAllBytes('monza_candidate_002.3mf', [Convert]::FromBase64String((Get-Content -Raw 'monza_candidate_002_3mf.base64.txt')))
```

## Notes

- The output filename must be exactly `monza_candidate_002.3mf`.
- This is a text-safe packaging change only.
- The Phase 4A 3MF model was not regenerated or modified.
- No ZIP archive is created by this packaging step.
