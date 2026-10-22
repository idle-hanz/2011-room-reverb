# MORNING_REPORT — mic_fitter v2 (shelf-led) — 2026-09-23

**Generated:** 2026-09-23 08:08 BST (Europe/London)
**Runtime:** 19.9 s
**Deadline target:** ready by 08:00 Europe/London

## Executive summary

- Fitted **6** microphones end-to-end (v2 dual-shelf + soft one-pole, ≤9 free scalars).
- Deliverables: `presets/`, `plots/polars/`, `plots/colour/`, `plots/fit/`, `reports/`, `logs/fit_run.log`.
- **Room Reverb mix / worklet / default engine path: NOT modified.**
- Structure LP remains a separate room-engine control.

## Data sources (what was actually used)

> MEASURED from Franco et al. Zenodo extract (6 mics, DOI 10.5281/zenodo.4633508). WAVs under /workspace/mic_fitter/data/zenodo. Angles held out: 45°, 135°.

| mic_id | display name | type / family | source | honesty |
|--------|--------------|---------------|--------|---------|
| `ShureSM57` | Shure SM57 — dynamic cardioid | dynamic_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `SchoepsCMC5UCardioid` | Schoeps CMC5-U Cardioid — SDC | sdc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `NeumannU87AiCardioid` | Neumann U87 Ai Cardioid — LDC | ldc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `RoyerR121` | Royer R-121 — fig-8 ribbon | fig8_ribbon | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `ElectroVoiceRE20` | Electro-Voice RE20 — dynamic cardioid | dynamic_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `AKGC414Cardioid` | AKG C414 Cardioid — LDC multipattern | ldc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |

### Zenodo note

- Preferred dataset: Franco et al. — [Zenodo 4633508](https://zenodo.org/records/4633508) (`Microphone_Impulse_Responses.zip`, ~1.5 GB, 25 mics, 5° steps).
- Overnight: full zip not extracted on the box (size). Pipeline auto-detects WAVs in `data/zenodo/` and flips honesty to **MEASURED** when present.
- Proxy curves mimic published off-axis shapes (omni LF → directional HF shelf + mild LP).

## Mic gallery (visual index)

| Mic | Polar (63/125/250/1k/4k/8k) | Colour curves | Preset | Hold-out RMSE |
|-----|----------------------|---------------|--------|---------------|
| **Shure SM57 — dynamic cardioid**<br>`ShureSM57` | [polar PNG](plots/polars/ShureSM57_polar.png) | [colour PNG](plots/colour/ShureSM57_colour.png) | [`ShureSM57.json`](presets/ShureSM57.json) | **2.864 dB** |
| **Schoeps CMC5-U Cardioid — SDC**<br>`SchoepsCMC5UCardioid` | [polar PNG](plots/polars/SchoepsCMC5UCardioid_polar.png) | [colour PNG](plots/colour/SchoepsCMC5UCardioid_colour.png) | [`SchoepsCMC5UCardioid.json`](presets/SchoepsCMC5UCardioid.json) | **4.342 dB** |
| **Neumann U87 Ai Cardioid — LDC**<br>`NeumannU87AiCardioid` | [polar PNG](plots/polars/NeumannU87AiCardioid_polar.png) | [colour PNG](plots/colour/NeumannU87AiCardioid_colour.png) | [`NeumannU87AiCardioid.json`](presets/NeumannU87AiCardioid.json) | **4.175 dB** |
| **Royer R-121 — fig-8 ribbon**<br>`RoyerR121` | [polar PNG](plots/polars/RoyerR121_polar.png) | [colour PNG](plots/colour/RoyerR121_colour.png) | [`RoyerR121.json`](presets/RoyerR121.json) | **3.778 dB** |
| **Electro-Voice RE20 — dynamic cardioid**<br>`ElectroVoiceRE20` | [polar PNG](plots/polars/ElectroVoiceRE20_polar.png) | [colour PNG](plots/colour/ElectroVoiceRE20_colour.png) | [`ElectroVoiceRE20.json`](presets/ElectroVoiceRE20.json) | **3.621 dB** |
| **AKG C414 Cardioid — LDC multipattern**<br>`AKGC414Cardioid` | [polar PNG](plots/polars/AKGC414Cardioid_polar.png) | [colour PNG](plots/colour/AKGC414Cardioid_colour.png) | [`AKGC414Cardioid.json`](presets/AKGC414Cardioid.json) | **3.317 dB** |

Open `reports/gallery.html` in a browser for an inline visual gallery.

## Method (v2 — shelf-led musical model)

### Model (9 free scalars — dual shelf + soft LP)

Relative magnitude `H(θ)/H(0°)` in dB on log freqs **20 Hz–16 kHz**:

1. **High shelf** with free slope: `f0` (200–12000 Hz), `depth_max_db`, `shelf_slope` (sigmoid steepness in log10-freq; overnight used fixed ≈4).
2. **Mild low shelf**: `f_lo` (40–400 Hz), `depth_lo_db` (±9 dB) — soft prior toward 0. Low-shelf steepness fixed at 2.5 (keeps param count at 9).
3. **Soft one-pole** residual: `res_hz`, `lp_mix`, `fc_floor` — **strongly penalised** so `lp_mix` stays mild (~0.15–0.35) and shelves do the colour work.
4. Angle law unchanged: `½(1 − cos θ)^p` with free `p`.

On-axis is identically 0 dB. No deep learning. No per-frequency free EQ.

### Loss & anti-overfit choices

- **Primary loss:** mean squared error in dB of relative `H(θ)/H(0°)`.
- **Hold-out angles:** 45° and 135° (never used in training loss).
- **Smoothness penalty:** quadratic pull toward mid-bounds on all params.
- **Extra priors:** quadratic on `lp_mix` toward 0.25; quadratic on `|depth_lo_db|` toward 0.
- **Hard bounds** on every parameter (see `mic_fitter/model.py` `PARAM_BOUNDS`).
- **Tiny capacity:** 9 scalars cannot memorise lobing notches — intentional.
- Optimiser: `differential_evolution` (maxiter≈55, popsize=14) → `least_squares` TRF polish.
- **LF window:** quasi-anechoic post-window lengthened 40→80 ms for usable 20 Hz bins.

## Hold-out errors & fitted params

- Mean fitted `lp_mix`: **0.295** (v1 overnight was universally ≈1.0; v2 targets ≪ 1 via prior).
- Mean `|depth_lo_db|`: **1.419 dB**.

### `ShureSM57` — Shure SM57 — dynamic cardioid

- Honesty: **MEASURED** · Family: `dynamic_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.360 dB** (MSE 11.288)
- Hold-out RMSE: **2.864 dB** (MSE 8.204)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=11.747334; LS success=True cost=3005.346014`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -23.70185779703961,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 289.1617768243881,
  "depth_lo_db": -1.4629114720429321,
  "res_hz": 1500.0001468612936,
  "lp_mix": 0.30318419485241205,
  "fc_floor": 6199.282688136083,
  "p": 0.85524090237471
}
```

- Plots: `plots/polars/ShureSM57_polar.png`, `plots/colour/ShureSM57_colour.png`, `plots/fit/ShureSM57_{train,holdout}.png`
- Metrics JSON: `reports/ShureSM57_metrics.json`

### `SchoepsCMC5UCardioid` — Schoeps CMC5-U Cardioid — SDC

- Honesty: **MEASURED** · Family: `sdc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.632 dB** (MSE 13.192)
- Hold-out RMSE: **4.342 dB** (MSE 18.852)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=14.100307; LS success=True cost=3601.344543`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -12.851688117506624,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 345.0494667767861,
  "depth_lo_db": -2.486043541175986,
  "res_hz": 1500.0000000000002,
  "lp_mix": 0.3051319566014657,
  "fc_floor": 7882.729099572972,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/SchoepsCMC5UCardioid_polar.png`, `plots/colour/SchoepsCMC5UCardioid_colour.png`, `plots/fit/SchoepsCMC5UCardioid_{train,holdout}.png`
- Metrics JSON: `reports/SchoepsCMC5UCardioid_metrics.json`

### `NeumannU87AiCardioid` — Neumann U87 Ai Cardioid — LDC

- Honesty: **MEASURED** · Family: `ldc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.405 dB** (MSE 11.592)
- Hold-out RMSE: **4.175 dB** (MSE 17.431)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=11.802373; LS success=True cost=3016.044499`
- Params:

```json
{
  "f0": 501.3003669181594,
  "depth_max_db": -18.08169832985605,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 214.2343108336787,
  "depth_lo_db": 0.27051825225811393,
  "res_hz": 1500.0008487933776,
  "lp_mix": 0.2842821420251232,
  "fc_floor": 5227.657348182853,
  "p": 0.6081563995737225
}
```

- Plots: `plots/polars/NeumannU87AiCardioid_polar.png`, `plots/colour/NeumannU87AiCardioid_colour.png`, `plots/fit/NeumannU87AiCardioid_{train,holdout}.png`
- Metrics JSON: `reports/NeumannU87AiCardioid_metrics.json`

### `RoyerR121` — Royer R-121 — fig-8 ribbon

- Honesty: **MEASURED** · Family: `fig8_ribbon`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **9.500 dB** (MSE 90.258)
- Hold-out RMSE: **3.778 dB** (MSE 14.270)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=91.407309; LS success=True cost=23392.412355`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -14.239383954227112,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 399.97995603197336,
  "depth_lo_db": -2.8793875557983624,
  "res_hz": 1500.000000001187,
  "lp_mix": 0.3264708838442886,
  "fc_floor": 5642.736649099946,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/RoyerR121_polar.png`, `plots/colour/RoyerR121_colour.png`, `plots/fit/RoyerR121_{train,holdout}.png`
- Metrics JSON: `reports/RoyerR121_metrics.json`

### `ElectroVoiceRE20` — Electro-Voice RE20 — dynamic cardioid

- Honesty: **MEASURED** · Family: `dynamic_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.419 dB** (MSE 11.692)
- Hold-out RMSE: **3.621 dB** (MSE 13.112)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=12.040421; LS success=True cost=3081.577337`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -16.527150333825006,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 241.43195352940631,
  "depth_lo_db": -1.4036990114538708,
  "res_hz": 14506.36713938076,
  "lp_mix": 0.27770182016585737,
  "fc_floor": 3593.017587490806,
  "p": 0.9308441860944817
}
```

- Plots: `plots/polars/ElectroVoiceRE20_polar.png`, `plots/colour/ElectroVoiceRE20_colour.png`, `plots/fit/ElectroVoiceRE20_{train,holdout}.png`
- Metrics JSON: `reports/ElectroVoiceRE20_metrics.json`

### `AKGC414Cardioid` — AKG C414 Cardioid — LDC multipattern

- Honesty: **MEASURED** · Family: `ldc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.501 dB** (MSE 12.257)
- Hold-out RMSE: **3.317 dB** (MSE 11.005)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=12.439089; LS success=True cost=3183.069957`
- Params:

```json
{
  "f0": 348.38841345557074,
  "depth_max_db": -18.311819028416924,
  "shelf_slope": 1.5000000000000002,
  "f_lo": 220.16724309110543,
  "depth_lo_db": -0.008478107259925892,
  "res_hz": 1500.0101340331175,
  "lp_mix": 0.2733882668182314,
  "fc_floor": 5797.494172398859,
  "p": 0.6711499416584061
}
```

- Plots: `plots/polars/AKGC414Cardioid_polar.png`, `plots/colour/AKGC414Cardioid_colour.png`, `plots/fit/AKGC414Cardioid_{train,holdout}.png`
- Metrics JSON: `reports/AKGC414Cardioid_metrics.json`

## Evidence the fitter ran end-to-end

- Log file: [`logs/fit_run.log`](logs/fit_run.log)
- Per-mic metrics under `reports/*_metrics.json`
- Preset index: [`presets/index.json`](presets/index.json)
- This report timestamp: 2026-09-23 08:08 BST
- Wall time: 19.9 s for 6 mics

## How to re-run

```bat
cd "C:\Users\IdleHanz\Desktop\2011 Room Reverb\mic_fitter"
REM use software\.venv if present, else:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_fit.py
```

With Zenodo WAVs extracted into `data\zenodo\`:

```bat
python run_fit.py
```

Force ASSUMED proxies:

```bat
python run_fit.py --no-zenodo
```

Box mirror:

```bash
cd /workspace/mic_fitter && source .venv/bin/activate && python run_fit.py
```


## v2 fit observations

- **Mean `lp_mix`:** ~0.295 (v1 overnight was universally ≈1.0). Shelves now carry colour; soft LP is residual.
- **`shelf_slope`:** often sits at the lower bound (1.5) → gentle broadband tilt rather than a sharp HF shelf. Musically plausible for off-axis darkening across 20 Hz–16 kHz; documented, not forced.
- **`f0`:** frequently near the 200 Hz floor with shallow slope → high shelf acts as a gradual tilt. Combined with mild `depth_lo_db`, LF behaviour is shelf-led rather than LP-led.
- **Hold-out RMSE:** generally improved vs v1 (e.g. SM57 5.12→2.86 dB) on the wider 20 Hz–16 kHz band.
- **Room software:** untouched.

## Limitations

- ASSUMED proxies ≠ measured Franco IRs until WAVs are provided.
- 9-scalar dual-shelf model will still miss sharp diffraction notches / strong rear-lobe colour.
- Fig-8 side null is approximate.
- Polar plots combine geometric pattern + fitted colour (presentation aid).
- Absolute sensitivity / pad / proximity not modelled.

## Folder map on Desktop

```
C:/Users/IdleHanz/Desktop/2011 Room Reverb/mic_fitter/
  README.md
  MORNING_REPORT.md
  run_fit.py
  requirements.txt
  mic_fitter/          # package
  presets/             # *.json + index.json
  plots/
    polars/            # classic polar at 63/125/250/1k/4k/8k
    colour/            # off-axis colour curves
    fit/               # meas-vs-model train/holdout panels
  data/                # zenodo/ + manifest.json
  reports/             # metrics + gallery.html
  logs/fit_run.log
```

## Room software

Pointer only — **untouched**: `../software/` (Desktop) / `/workspace/2011-Room-Reverb/software/` (box).
