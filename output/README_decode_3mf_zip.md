# Decode the candidate 3MF ZIP

This directory includes a text-safe Base64 copy of `candidate_3mf_download.zip` because binary ZIP files cannot be committed through Codex.

The Base64 file is:

```text
candidate_3mf_download.zip.base64.txt
```

On Windows PowerShell, recreate the ZIP with:

```powershell
[IO.File]::WriteAllBytes(
  "candidate_3mf_download.zip",
  [Convert]::FromBase64String((Get-Content "candidate_3mf_download.zip.base64.txt" -Raw))
)
```

The recreated ZIP contains exactly one file:

```text
candidate.3mf
```
