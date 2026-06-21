# Decode Phase 4F Best Preview 3MF

This repository stores the Phase 4F preview as Base64 text so no binary `.3mf` file is committed.

## Windows PowerShell

```powershell
[Convert]::FromBase64String((Get-Content .\output\phase_4f_best_preview_3mf.base64.txt -Raw)) | Set-Content -Encoding Byte .\phase_4f_best_preview.3mf
```

## macOS/Linux

```bash
base64 -d output/phase_4f_best_preview_3mf.base64.txt > phase_4f_best_preview.3mf
```

The decoded `.3mf` file is a local preview artifact and should not be committed.
