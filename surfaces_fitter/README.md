# surfaces_fitter (v0.1.0)

**Standalone tool** for Idle Hanz — textbook octave absorption α → musical
per-bounce reflection magnitude model, parallel to `mic_fitter` / `air_fitter`.

> **Does not modify** the listened Room Reverb mix, AudioWorklet, or live `software/`.
> This folder is separate. Do **not** import presets into live engine here.

## Honesty

| Tag | Meaning |
|-----|---------|
| **ASSUMED_TEXTBOOK** | Sengpiel-style / typical published octave α (125–4 kHz + gentle 8 kHz extend). |
| **Not Structure VERIFIED** | These tables are not OCR from Reaktor Structure. |

## Physics

Energy absorb α(f) at octave centres; log-frequency interpolate between centres.

```
R_db(f) = 20 * log10(√(max(1 − α(f), 1e-6)))   # amplitude reflection
```

- **One bounce:** apply R(f).
- **Multi-bounce:** cascade product along the hit list.
- Depth is **absolute per bounce** (not per metre like air).

Export `absorb[7]` at centres `125, 250, 500, 1000, 2000, 4000, 8000` matching
Desktop Surfaces cards A–F.

## Filter candidates

| Candidate | Model | When |
|-----------|-------|------|
| **A** | `dual_high_shelf` | Rising-α carpets / tiles / hard finishes |
| **B** | `low_shelf_high_shelf` | LF absorb (plywood, glass, curtain, foam carpet) |

Loss: RMSE of model R_db vs target R_db on logspace **20 Hz – 16 kHz**.
Also report absorb-band L1 error.

## Materials (roles)

| id | Roles |
|----|-------|
| `plaster_smooth` | wall, ceiling |
| `gypsum_painted` | wall, ceiling |
| `brick_unglazed` | wall |
| `concrete_painted` | floor, wall, ceiling |
| `wood_parquet` | floor |
| `plywood_panel` | wall |
| `carpet_on_concrete` | floor ONLY |
| `carpet_on_foam` | floor ONLY |
| `glass_window` | wall ONLY |
| `acoustic_ceiling_tile` | ceiling |
| `absorber_panel_2in` | wall |
| `heavy_curtain` | wall ONLY |

See `PURGE_LIST.md` — Curtain/Carpet must not be unrestricted paint-all.

## One-command run

```bash
cd /workspace/surfaces_fitter   # or Desktop surfaces_fitter/
python -m venv .venv && . .venv/bin/activate   # optional
pip install -r requirements.txt
python run_fit.py
```

Windows Desktop:

```bat
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb\surfaces_fitter"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_fit.py
```

## Outputs

- `presets/*.json` — schema `surfaces_fitter.material.v1` + `index.json`
- `plots/*_alpha.png`, `*_r_db.png`, `gallery_index.png`, `role_matrix.png`
- `reports/summary.json`, `*_metrics.json`, `FIT_REPORT.md`
- `MORNING_REPORT.md` — RMSE table + role matrix
- `PURGE_LIST.md` — crazy-kit purge (Idle pick #11)

## Locks

- No edits under `software/` / engine / static that Build may be editing for mic/air.
- Do not change listened mix defaults in the live app.
- Do not delete Floor/Ceiling cards E/F — only illegal material kits on those faces.
