# SYNC — polar3d add-on → Desktop

**Dest:** `C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter\`  
**machineId:** `9595fbf3-7e9f-488a-b70d-ab0e29294c12`  
**Box package:** `/workspace/mic_fitter_polar3d.tar.gz`

## Parent / operator

1. `CopyFromBox` `/workspace/mic_fitter_polar3d.tar.gz` → Desktop folder above (or parent of `mic_fitter`).
2. Extract **into** existing `mic_fitter/` (merge):

```powershell
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb"
tar -xzf mic_fitter_polar3d.tar.gz -C mic_fitter
# or if tar has paths relative to mic_fitter contents already:
# tar -xzf mic_fitter_polar3d.tar.gz -C ".\mic_fitter"
```

Package contains:
- `mic_fitter/polar3d.py`
- `scripts/make_polar3d.py`
- `plots/polar3d/*` (solids + rings for 6 MEASURED mics)
- `reports/gallery.html` (updated with 3D thumbs)

Highlight PNGs also in box `/workspace/uploads/` for chat:
`ShureSM57_polar3d.png`, `NeumannU87AiCardioid_polar3d.png`, `RoyerR121_polar3d.png` (+ rings).

## Regen on box

```bash
cd /workspace/mic_fitter && .venv/bin/python scripts/make_polar3d.py
```

Do **not** touch room reverb `software\` mix / worklet.
