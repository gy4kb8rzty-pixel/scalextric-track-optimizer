# Apply the Phase 4F Rebuild Patch

This folder contains a text-safe handoff patch for the Phase 4F rebuild changes.

## Files

- `output/phase_4f_rebuild.patch` — unified git patch for the Phase 4E/4F rebuild changes.
- `output/phase_4f_rebuild_file_manifest.json` — manifest of every file included in the patch, with type, size, and text-safety metadata.
- `output/phase_4f_best_preview_3mf.base64.txt` — text-safe Base64 encoded preview 3MF included by the patch.
- `output/README_decode_phase_4f_best_preview_3mf.md` — instructions for decoding the Base64 preview locally.

## Windows PowerShell instructions

From a fresh local clone of the GitHub repository, run the following in PowerShell:

```powershell
# 1. Go to your local repository clone
cd C:\path\to\scalextric-track-optimizer

# 2. Ensure you are on main and up to date
git checkout main
git pull origin main

# 3. Create a working branch for the Phase 4F rebuild
git checkout -b phase-4f-rebuild

# 4. Copy phase_4f_rebuild.patch into the repository's output folder
#    Example, if the patch is in Downloads:
New-Item -ItemType Directory -Force -Path .\output
Copy-Item "$env:USERPROFILE\Downloads\phase_4f_rebuild.patch" .\output\phase_4f_rebuild.patch

# 5. Check that the patch applies cleanly without changing files yet
git apply --check .\output\phase_4f_rebuild.patch

# 6. Apply the patch
git apply .\output\phase_4f_rebuild.patch

# 7. Review the changes
git status
git diff --stat

# 8. Commit the applied Phase 4F rebuild changes
git add examples/phase_4e examples/phase_4f scripts/generate_phase_4e.py scripts/generate_phase_4f.py output/phase_4f_best_preview_3mf.base64.txt output/README_decode_phase_4f_best_preview_3mf.md
git commit -m "Add Phase 4E/4F rebuild outputs"

# 9. Push and open a pull request
git push -u origin phase-4f-rebuild
```

After pushing, open GitHub and create a pull request from `phase-4f-rebuild` into `main`.

## Safety checks

The patch is intended to be text-only. It should not contain or create any of these binary extensions:

- `.3mf`
- `.stl`
- `.obj`
- `.zip`

You can verify this locally with PowerShell:

```powershell
$binaryFileHeaders = Select-String -Path .\output\phase_4f_rebuild.patch -Pattern '^(diff --git|\+\+\+ b/|--- a/).*(\.3mf|\.stl|\.obj|\.zip)$'
$binaryFileHeaders
```

No matches should be returned. The patch may contain text references such as `source_3mf` metadata, but it must not add binary files.
