# SYNC — mic_fitter v2 → Desktop

**Dest:** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter\`  
**machineId:** `9595fbf3-7e9f-488a-b70d-ab0e29294c12`  
**Box package:** `/workspace/mic_fitter_desktop_v2.tar.gz` (~7.8 MB)  
**Excludes:** `.venv/`, `data/zenodo/*.zip` (~1.4 GB)  
**Includes:** extracted 6-mic Raw_IR WAVs under `data/zenodo/extracted/` (~83 MB uncompressed) so Desktop is self-runnable without re-extract.

## Parent agent / operator

1. `CopyFromBox` `/workspace/mic_fitter_desktop_v2.tar.gz` →  
   `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter_desktop_v2.tar.gz`
2. On Desktop machine Shell:

```powershell
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb"
if (Test-Path mic_fitter) { Rename-Item mic_fitter "mic_fitter_v1_backup_$(Get-Date -Format yyyyMMdd_HHmm)" }
tar -xzf mic_fitter_desktop_v2.tar.gz
# tarball top-level is mic_fitter/
if (-not (Test-Path .\mic_fitter\run_fit.py)) {
  Write-Error "extract layout unexpected — check tar contents"
}
```

Or recursive `CopyFromBox` of each file under `/workspace/mic_fitter/` (skip `.venv` and the big zip).

## Hold-out RMSE (v2 MEASURED, 20 Hz–16 kHz)

| mic_id | hold-out RMSE (dB) | train RMSE | lp_mix |
|--------|-------------------|------------|--------|
| ShureSM57 | **2.864** | 3.360 | 0.303 |
| SchoepsCMC5UCardioid | **4.342** | 3.632 | 0.305 |
| NeumannU87AiCardioid | **4.175** | 3.405 | 0.284 |
| RoyerR121 | **3.778** | 9.500 | 0.326 |
| ElectroVoiceRE20 | **3.621** | 3.419 | 0.278 |
| AKGC414Cardioid | **3.317** | 3.501 | 0.273 |

**Mean `lp_mix`:** **0.295** (v1 overnight was universally ≈1.0).

## Do not touch

`software\` mix / worklet / default engine — **untouched**. Room Reverb path not modified; only this separate `mic_fitter/` pack.
