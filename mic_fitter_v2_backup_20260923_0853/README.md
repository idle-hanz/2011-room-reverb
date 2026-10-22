# mic_fitter (v0.2.0 — shelf-led)

**Standalone overnight tool** for Idle Hanz — fits a *tiny* off-axis microphone colour model  
so the 2011 Room Reverb app can load presets later.

> **Does not modify** the listened Room Reverb mix, AudioWorklet, or default engine path.  
> This folder is separate from `software/`.

## Honesty tags

| Tag | Meaning |
|-----|---------|
| **ASSUMED** | Synthetic / manufacturer-style proxy curves. Useful for plumbing + demos. **Not** lab truth. |
| **MEASURED** | Fitted from Franco et al. Zenodo IR WAVs when present under `data/zenodo/`. |
| **Structure LP** | Room-engine structure low-pass is **separate** — these presets are off-axis magnitude colour only. |

Zenodo dataset (preferred when available): https://zenodo.org/records/4633508  
(Franco, Brookes, De Sena — multi-angle mic IRs, ~1.5 GB zip.)

## Model v2 (`dual_shelf_plus_soft_one_pole`, schema `mic_fitter.preset.v2`)

Relative response `H(θ) / H(0°)` in dB on log frequencies **20 Hz – 16 kHz**:

1. **High shelf** — `f0` (200–12000 Hz), `depth_max_db`, **`shelf_slope`**  
   Steepness of the log-frequency sigmoid (overnight v1 used fixed ≈4 as `exp(-4·x)`).  
   Larger `shelf_slope` → sharper transition around `f0`.
2. **Mild low shelf** — `f_lo` (40–400 Hz), `depth_lo_db` (±9 dB)  
   Soft prior toward `depth_lo_db ≈ 0`. Low-shelf slope fixed at 2.5 (keeps free count at 9).
3. **Soft one-pole** — `res_hz`, `lp_mix`, `fc_floor`  
   Strong prior on `lp_mix` toward ~0.25 so shelves carry the musical colour (v1 slammed `lp_mix→1`).
4. **Angle law** — `½(1 − cos θ)^p` with free exponent `p` (unchanged).

**Param choice:** all **9** free scalars kept  
(`f0`, `depth_max_db`, `shelf_slope`, `f_lo`, `depth_lo_db`, `res_hz`, `lp_mix`, `fc_floor`, `p`).  
DE `maxiter` default **70**, `popsize=14`, with smoothness + `lp_mix` + `|depth_lo|` priors.

Loss: dB MSE on relative response; hold out 45° & 135°; no deep learning.  
Optimiser: `scipy.optimize.differential_evolution` (+ `least_squares` polish).

### LF analysis window

Quasi-anechoic IR window: **2 ms pre + 80 ms post** around the direct peak (was 40 ms).  
Needed so 20 Hz bins have usable SNR for the mild low shelf; trade-off is slightly more
early-reflection leakage. Default `n_fft` floor raised to 16384.

## One-command run

```bat
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter"
REM Prefer existing room venv if present:
REM   ..\software\.venv\Scripts\activate
REM else:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_fit.py
```

On the agent box:

```bash
cd /workspace/mic_fitter
source .venv/bin/activate
python run_fit.py
```

Force ASSUMED proxies only: `python run_fit.py --no-zenodo`

Outputs:

- `presets/*.json` — MEASURED presets (`mic_fitter.preset.v2`)
- `presets/index.json` — catalog
- `presets/assumed/` — ASSUMED proxy presets
- `plots/polars/` — polar at **63 / 125 / 250 / 1k / 4k / 8k** Hz
- `plots/colour/`, `plots/fit/`
- `MORNING_REPORT.md` — overnight summary + hold-out errors
- `data/manifest.json` — ASSUMED vs MEASURED note

## Pointing at Zenodo files

1. Download the zip from https://zenodo.org/records/4633508 (or extract only a few mics).
2. Place WAVs under `data/zenodo/` (any depth; names containing angle tokens like `30Deg` are detected).
3. Re-run `python run_fit.py` — honesty flips to **MEASURED** for discovered mics.

## Room Reverb pointer

Room software lives at `../software/` (Desktop) / `/workspace/2011-Room-Reverb/software/` (box).  
**Untouched** by this tool. Future integration: read `mic_fitter/presets/*.json` as optional colour tables.

## Package layout

```
mic_fitter/
  README.md
  MORNING_REPORT.md
  SYNC.md
  requirements.txt
  run_fit.py
  mic_fitter/          # Python package (v0.2.0)
    model.py           # dual shelf + soft one-pole
    synthetic.py       # ASSUMED proxy curves
    data.py            # Zenodo loader + fallback
    fit.py             # DE + priors
    plot.py / polar.py / export.py
  presets/
  plots/
  data/
```

## Fitted MEASURED mics (Franco et al. Zenodo)

| mic_id | type |
|--------|------|
| ShureSM57 | dynamic cardioid |
| SchoepsCMC5UCardioid | SDC cardioid |
| NeumannU87AiCardioid | LDC cardioid |
| RoyerR121 | fig-8 ribbon |
| ElectroVoiceRE20 | dynamic cardioid |
| AKGC414Cardioid | LDC cardioid |


See `MORNING_REPORT.md` for hold-out RMSE and fitted params.
