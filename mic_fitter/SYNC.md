# SYNC — mic_fitter v3 → Desktop

**Dest:** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter\`  
**machineId:** `9595fbf3-7e9f-488a-b70d-ab0e29294c12`  
**Box package:** `/workspace/mic_fitter_desktop_v3.tar.gz` (~30 MB compressed; ~281 MB uncompressed incl. 170 WAVs)  
**Excludes:** `.venv/`, `data/zenodo/*.zip` (~1.4 GB)  
**Includes:** extracted 17-mic Raw_IR WAVs under `data/zenodo/extracted/` (~240 MB uncompressed) so Desktop is self-runnable without re-extract.

## Parent agent / operator

1. `CopyFromBox` `/workspace/mic_fitter_desktop_v3.tar.gz` →  
   `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter_desktop_v3.tar.gz`
2. On Desktop machine Shell:

```powershell
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb"
if (Test-Path mic_fitter) { Rename-Item mic_fitter "mic_fitter_v2_backup_$(Get-Date -Format yyyyMMdd_HHmm)" }
tar -xzf mic_fitter_desktop_v3.tar.gz
# tarball top-level is mic_fitter/
if (-not (Test-Path .\mic_fitter\run_fit.py)) {
  Write-Error "extract layout unexpected — check tar contents"
}
```

Or recursive `CopyFromBox` of each file under `/workspace/mic_fitter/` (skip `.venv` and the big zip).

## Do not touch

`software\` mix / worklet / default engine — **untouched**. Room Reverb path not modified; only this separate `mic_fitter/` pack.

## v3 highlights

- `shelf_slope` bounds **0.6–12.0** (was 1.5–12; freer gentle end; tried 0.6–4.0 first but omnis pinned at 4.0)
- 17 MEASURED mics; schema `mic_fitter.preset.v3` + optional HPF switches
- Plots / polar3d from **20 Hz**; SE2200A pending (not in Zenodo)

## v3.1 — Røde NT2-A add-on (2026-09-24)

**Dest:** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter\`  
**Box package:** `/workspace/mic_fitter_nt2a_addon.tar.gz` (presets/plots/reports/docs/code + NT2-A WAVs only)

```powershell
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb"
tar -xzf mic_fitter_nt2a_addon.tar.gz
# extracts into existing mic_fitter/ (overlay)
```

- Three new MEASURED presets: `RodeNT2ACardioid`, `RodeNT2AOmni`, `RodeNT2ABidirect`
- NT5 still pending (`presets/pending_rode_nt5.md`); SE2200A pending retained
- Room `software\` untouched; giant Zenodo zip not copied

## v3.2 — NT2-A polar3d + report fixes (2026-09-27)

- New: `plots/polar3d/RodeNT2A{Cardioid,Omni,Bidirect}_polar3d.png` + `_polar3d_rings.png` (same generator/style as the other 17).
- Updated: `reports/gallery.html` (NT2-A cards), `MORNING_REPORT.md` + `reports/MORNING_REPORT.md` (20 MEASURED mics),
  `README.md`, `data/SOURCES.md`, `presets/pending_rode_nt5.md`, `presets/pending_se2200a.md`, `plots/polar3d/README.md`, `SYNC.md`.
- NT5 / SE2200A: **no measured data available; not planned**. Fits/presets unchanged. Room software untouched.
