# Decode Candidate Monza 002

This directory provides a text-safe Base64 representation of the preserved `candidate_monza_002.lay` export.

## Files

- `candidate_monza_002_lay.base64.txt` — Base64 text encoding of `candidate_monza_002.lay`.
- `README_decode_candidate_monza_002.md` — instructions for recreating the `.lay` file from the Base64 text.

## Recreate `candidate_monza_002.lay` on Windows PowerShell

Run this command from the directory containing `candidate_monza_002_lay.base64.txt`:

```powershell
[IO.File]::WriteAllBytes('candidate_monza_002.lay', [Convert]::FromBase64String((Get-Content -Raw 'candidate_monza_002_lay.base64.txt')))
```

## Notes

- The output filename must be exactly `candidate_monza_002.lay`.
- This is a text-safe packaging change only.
- The candidate layout was not optimized, regenerated, or modified.
- No ZIP, SVG, or 3MF file is included.
