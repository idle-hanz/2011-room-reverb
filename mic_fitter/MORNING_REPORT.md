# MORNING_REPORT — mic_fitter v3 (freer shelf + more MEASURED) — 2026-09-23

**Generated:** 2026-09-23 08:51 BST (Europe/London)
**Runtime:** 57.4 s
**Deadline target:** ready by 08:00 Europe/London

## Executive summary

- **20 MEASURED microphones** (v3 dual-shelf + soft one-pole, ≤9 free scalars): the original **17** fitted in the 2026-09-23 run plus the **three Røde NT2-A patterns** (`RodeNT2ACardioid`, `RodeNT2AOmni`, `RodeNT2ABidirect`) added 2026-09-24 — see the NT2-A add-on section at the end.
- Røde NT5 and sE Electronics SE2200A: **no measured data available; not planned** (no presets fabricated).
- Deliverables: `presets/`, `plots/polars/`, `plots/colour/`, `plots/fit/`, `plots/polar3d/` (all 20 MEASURED incl. NT2-A), `reports/`, `logs/fit_run.log`.
- **Room Reverb mix / worklet / default engine path: NOT modified.**
- Structure LP remains a separate room-engine control.


## v2 → v3 hold-out RMSE (original 6)

| mic_id | v2 hold-out | v3 hold-out | Δ | v3 shelf_slope | v3 lp_mix |
|--------|------------:|------------:|--:|---------------:|----------:|
| `ShureSM57` | 2.864 | **2.848** | -0.016 | 1.113 | 0.268 |
| `SchoepsCMC5UCardioid` | 4.342 | **4.316** | -0.026 | 0.600 | 0.295 |
| `NeumannU87AiCardioid` | 4.175 | **4.150** | -0.025 | 1.297 | 0.290 |
| `RoyerR121` | 3.778 | **3.911** | +0.134 | 0.600 | 0.317 |
| `ElectroVoiceRE20` | 3.621 | **3.532** | -0.089 | 0.641 | 0.275 |
| `AKGC414Cardioid` | 3.317 | **3.318** | +0.001 | 1.463 | 0.274 |

## New MEASURED mics (v3)

| mic_id | family | hold-out RMSE | shelf_slope | lp_mix |
|--------|--------|--------------:|------------:|-------:|
| `AKGC414Bidirect` | fig8 | **2.746** | 0.600 | 0.328 |
| `AKGC414Hyper` | hypercardioid | **2.630** | 1.479 | 0.306 |
| `AKGC414Omni` | omni | **2.638** | 3.100 | 0.283 |
| `Coles4038` | fig8_ribbon | **3.057** | 0.600 | 0.311 |
| `DPA4006` | omni | **0.931** | 8.190 | 0.252 |
| `NeumannU87AiBidirect` | fig8 | **2.626** | 0.600 | 0.306 |
| `NeumannU87AiOmni` | omni | **2.319** | 11.415 | 0.269 |
| `SchoepsCMC5UBidirect` | fig8 | **2.084** | 0.600 | 0.277 |
| `SchoepsCMC5UOmni` | omni | **1.350** | 4.758 | 0.252 |
| `SennheiserMD441` | hypercardioid | **5.664** | 0.651 | 0.271 |
| `ShureSM58` | dynamic_cardioid | **4.801** | 0.600 | 0.269 |

### Slope / prior summary (original 17 MEASURED from the 2026-09-23 run; NT2-A ×3 not included in these stats)

- Mean `lp_mix`: **0.285**
- Mean `|depth_lo_db|`: **0.475 dB**
- `shelf_slope` bounds now **0.6–12.0** (was 1.5–12; v2 often pinned at 1.5).
- Still pins at lower 0.6: **7/17** mics; at upper 12: **0/17**.
- Several cardioids moved into the gentle band (e.g. SM57 ≈1.11, U87 cardioid ≈1.30) that v2 could not reach.

### 20 Hz plots

- Colour / fit panels use fit band **20 Hz–16 kHz**.
- 2D polar gallery: **20 / 63 / 125 / 250 / 1k / 4k / 8k**.
- polar3d: `DEFAULT_F_LO=20`, rings include 20 Hz, z-ticks include 20.

### Optional HPF (not fitted)

| mic family / id | documented default `hpf_hz` | notes |
|-----------------|----------------------------:|-------|
| Neumann U87 Ai (all patterns) | 140 | LF roll-off switch |
| AKG C414 (all patterns) | 160 | bass-cut options ~40/80/160 |
| Shure SM57 / SM58 | none | no switch |
| EV RE20, MD 441, ribbons, DPA 4006, Schoeps CMC | none / external | see `MANUFACTURER_HPF_DEFAULTS` |

`switches.hpf_engaged` defaults **false**; `apply_hpf()` for future UI.

### SE2200A / Røde NT5

**No measured data available; not planned.** Absent from Zenodo 4633508 and Idle has confirmed he has no data for either — notes at [`presets/pending_se2200a.md`](presets/pending_se2200a.md) and [`presets/pending_rode_nt5.md`](presets/pending_rode_nt5.md). No fake MEASURED fit.

## Data sources (what was actually used)

> MEASURED from Franco et al. Zenodo extract (20 MEASURED mics: the 17 below from the v3 run + Røde NT2-A Cardioid/Omni/Bidirect in the add-on section; DOI 10.5281/zenodo.4633508). WAVs under /workspace/mic_fitter/data/zenodo. Angles held out: 45°, 135°.

| mic_id | display name | type / family | source | honesty |
|--------|--------------|---------------|--------|---------|
| `ShureSM57` | Shure SM57 — dynamic cardioid | dynamic_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `SchoepsCMC5UCardioid` | Schoeps CMC5-U Cardioid — SDC | sdc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `NeumannU87AiCardioid` | Neumann U87 Ai Cardioid — LDC | ldc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `RoyerR121` | Royer R-121 — fig-8 ribbon | fig8_ribbon | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `ElectroVoiceRE20` | Electro-Voice RE20 — dynamic cardioid | dynamic_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `AKGC414Cardioid` | AKG C414 Cardioid — LDC multipattern | ldc_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `ShureSM58` | Shure SM58 — dynamic cardioid | dynamic_cardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `SennheiserMD441` | Sennheiser MD 441 — dynamic hypercardioid | hypercardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `NeumannU87AiOmni` | Neumann U87 Ai Omni — LDC | omni | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `NeumannU87AiBidirect` | Neumann U87 Ai Bidirect — LDC fig-8 | fig8 | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `AKGC414Omni` | AKG C414 Omni — LDC multipattern | omni | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `AKGC414Hyper` | AKG C414 Hyper — LDC multipattern | hypercardioid | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `AKGC414Bidirect` | AKG C414 Bidirect — LDC fig-8 | fig8 | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `SchoepsCMC5UOmni` | Schoeps CMC5-U Omni — SDC | omni | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `SchoepsCMC5UBidirect` | Schoeps CMC5-U Bidirect — SDC fig-8 | fig8 | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `Coles4038` | Coles 4038 — fig-8 ribbon | fig8_ribbon | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |
| `DPA4006` | DPA 4006 — measurement omni | omni | Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles) | **MEASURED** |

### Zenodo note

- Preferred dataset: Franco et al. — [Zenodo 4633508](https://zenodo.org/records/4633508) (`Microphone_Impulse_Responses.zip`, ~1.5 GB, 25 mics, 5° steps).
- Overnight: full zip not extracted on the box (size). Pipeline auto-detects WAVs in `data/zenodo/` and flips honesty to **MEASURED** when present.
- Proxy curves mimic published off-axis shapes (omni LF → directional HF shelf + mild LP).

## Mic gallery (visual index)

| Mic | Polar (20/63/125/250/1k/4k/8k) | Colour curves | Preset | Hold-out RMSE |
|-----|----------------------|---------------|--------|---------------|
| **Shure SM57 — dynamic cardioid**<br>`ShureSM57` | [polar PNG](plots/polars/ShureSM57_polar.png) | [colour PNG](plots/colour/ShureSM57_colour.png) | [`ShureSM57.json`](presets/ShureSM57.json) | **2.848 dB** |
| **Schoeps CMC5-U Cardioid — SDC**<br>`SchoepsCMC5UCardioid` | [polar PNG](plots/polars/SchoepsCMC5UCardioid_polar.png) | [colour PNG](plots/colour/SchoepsCMC5UCardioid_colour.png) | [`SchoepsCMC5UCardioid.json`](presets/SchoepsCMC5UCardioid.json) | **4.316 dB** |
| **Neumann U87 Ai Cardioid — LDC**<br>`NeumannU87AiCardioid` | [polar PNG](plots/polars/NeumannU87AiCardioid_polar.png) | [colour PNG](plots/colour/NeumannU87AiCardioid_colour.png) | [`NeumannU87AiCardioid.json`](presets/NeumannU87AiCardioid.json) | **4.150 dB** |
| **Royer R-121 — fig-8 ribbon**<br>`RoyerR121` | [polar PNG](plots/polars/RoyerR121_polar.png) | [colour PNG](plots/colour/RoyerR121_colour.png) | [`RoyerR121.json`](presets/RoyerR121.json) | **3.911 dB** |
| **Electro-Voice RE20 — dynamic cardioid**<br>`ElectroVoiceRE20` | [polar PNG](plots/polars/ElectroVoiceRE20_polar.png) | [colour PNG](plots/colour/ElectroVoiceRE20_colour.png) | [`ElectroVoiceRE20.json`](presets/ElectroVoiceRE20.json) | **3.532 dB** |
| **AKG C414 Cardioid — LDC multipattern**<br>`AKGC414Cardioid` | [polar PNG](plots/polars/AKGC414Cardioid_polar.png) | [colour PNG](plots/colour/AKGC414Cardioid_colour.png) | [`AKGC414Cardioid.json`](presets/AKGC414Cardioid.json) | **3.318 dB** |
| **Shure SM58 — dynamic cardioid**<br>`ShureSM58` | [polar PNG](plots/polars/ShureSM58_polar.png) | [colour PNG](plots/colour/ShureSM58_colour.png) | [`ShureSM58.json`](presets/ShureSM58.json) | **4.801 dB** |
| **Sennheiser MD 441 — dynamic hypercardioid**<br>`SennheiserMD441` | [polar PNG](plots/polars/SennheiserMD441_polar.png) | [colour PNG](plots/colour/SennheiserMD441_colour.png) | [`SennheiserMD441.json`](presets/SennheiserMD441.json) | **5.664 dB** |
| **Neumann U87 Ai Omni — LDC**<br>`NeumannU87AiOmni` | [polar PNG](plots/polars/NeumannU87AiOmni_polar.png) | [colour PNG](plots/colour/NeumannU87AiOmni_colour.png) | [`NeumannU87AiOmni.json`](presets/NeumannU87AiOmni.json) | **2.319 dB** |
| **Neumann U87 Ai Bidirect — LDC fig-8**<br>`NeumannU87AiBidirect` | [polar PNG](plots/polars/NeumannU87AiBidirect_polar.png) | [colour PNG](plots/colour/NeumannU87AiBidirect_colour.png) | [`NeumannU87AiBidirect.json`](presets/NeumannU87AiBidirect.json) | **2.626 dB** |
| **AKG C414 Omni — LDC multipattern**<br>`AKGC414Omni` | [polar PNG](plots/polars/AKGC414Omni_polar.png) | [colour PNG](plots/colour/AKGC414Omni_colour.png) | [`AKGC414Omni.json`](presets/AKGC414Omni.json) | **2.638 dB** |
| **AKG C414 Hyper — LDC multipattern**<br>`AKGC414Hyper` | [polar PNG](plots/polars/AKGC414Hyper_polar.png) | [colour PNG](plots/colour/AKGC414Hyper_colour.png) | [`AKGC414Hyper.json`](presets/AKGC414Hyper.json) | **2.630 dB** |
| **AKG C414 Bidirect — LDC fig-8**<br>`AKGC414Bidirect` | [polar PNG](plots/polars/AKGC414Bidirect_polar.png) | [colour PNG](plots/colour/AKGC414Bidirect_colour.png) | [`AKGC414Bidirect.json`](presets/AKGC414Bidirect.json) | **2.746 dB** |
| **Schoeps CMC5-U Omni — SDC**<br>`SchoepsCMC5UOmni` | [polar PNG](plots/polars/SchoepsCMC5UOmni_polar.png) | [colour PNG](plots/colour/SchoepsCMC5UOmni_colour.png) | [`SchoepsCMC5UOmni.json`](presets/SchoepsCMC5UOmni.json) | **1.350 dB** |
| **Schoeps CMC5-U Bidirect — SDC fig-8**<br>`SchoepsCMC5UBidirect` | [polar PNG](plots/polars/SchoepsCMC5UBidirect_polar.png) | [colour PNG](plots/colour/SchoepsCMC5UBidirect_colour.png) | [`SchoepsCMC5UBidirect.json`](presets/SchoepsCMC5UBidirect.json) | **2.084 dB** |
| **Coles 4038 — fig-8 ribbon**<br>`Coles4038` | [polar PNG](plots/polars/Coles4038_polar.png) | [colour PNG](plots/colour/Coles4038_colour.png) | [`Coles4038.json`](presets/Coles4038.json) | **3.057 dB** |
| **DPA 4006 — measurement omni**<br>`DPA4006` | [polar PNG](plots/polars/DPA4006_polar.png) | [colour PNG](plots/colour/DPA4006_colour.png) | [`DPA4006.json`](presets/DPA4006.json) | **0.931 dB** |

Open `reports/gallery.html` in a browser for an inline visual gallery.

## Method (v3 — freer high-shelf slope + optional HPF schema)

### Model (9 free scalars — dual shelf + soft LP)

Relative magnitude `H(θ)/H(0°)` in dB on log freqs **20 Hz–16 kHz**:

1. **High shelf** with free slope: `f0` (200–12000 Hz), `depth_max_db`, `shelf_slope` (sigmoid steepness in log10-freq; v2 bound 1.5–12 pinned at 1.5; v3 **0.6–12.0**).
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

- Mean fitted `lp_mix`: **0.285** (v1 overnight was universally ≈1.0; v2 targets ≪ 1 via prior).
- Mean `|depth_lo_db|`: **0.475 dB**.

### `ShureSM57` — Shure SM57 — dynamic cardioid

- Honesty: **MEASURED** · Family: `dynamic_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.341 dB** (MSE 11.160)
- Hold-out RMSE: **2.848 dB** (MSE 8.111)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=11.444415; LS success=True cost=2927.565709`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -23.999999999999996,
  "shelf_slope": 1.1132513766017254,
  "f_lo": 289.79044546409676,
  "depth_lo_db": -0.9262662545479734,
  "res_hz": 1500.0004099442817,
  "lp_mix": 0.26829942508104715,
  "fc_floor": 4672.535805865078,
  "p": 0.8132753068527583
}
```

- Plots: `plots/polars/ShureSM57_polar.png`, `plots/colour/ShureSM57_colour.png`, `plots/fit/ShureSM57_{train,holdout}.png`
- Metrics JSON: `reports/ShureSM57_metrics.json`

### `SchoepsCMC5UCardioid` — Schoeps CMC5-U Cardioid — SDC

- Honesty: **MEASURED** · Family: `sdc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.547 dB** (MSE 12.579)
- Hold-out RMSE: **4.316 dB** (MSE 18.629)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=12.908413; LS success=True cost=3298.226463`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -16.086176399293713,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 247.69816792900176,
  "depth_lo_db": -0.920662157473726,
  "res_hz": 1500.0000000000002,
  "lp_mix": 0.2946662043675183,
  "fc_floor": 7595.688064680623,
  "p": 0.6214766830438848
}
```

- Plots: `plots/polars/SchoepsCMC5UCardioid_polar.png`, `plots/colour/SchoepsCMC5UCardioid_colour.png`, `plots/fit/SchoepsCMC5UCardioid_{train,holdout}.png`
- Metrics JSON: `reports/SchoepsCMC5UCardioid_metrics.json`

### `NeumannU87AiCardioid` — Neumann U87 Ai Cardioid — LDC

- Honesty: **MEASURED** · Family: `ldc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.401 dB** (MSE 11.564)
- Hold-out RMSE: **4.150 dB** (MSE 17.226)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=11.767683; LS success=True cost=3012.056366`
- Params:

```json
{
  "f0": 765.0274902653846,
  "depth_max_db": -20.093301924875494,
  "shelf_slope": 1.2972559132475152,
  "f_lo": 209.53261099747354,
  "depth_lo_db": 0.37675863755905176,
  "res_hz": 1500.0000261755463,
  "lp_mix": 0.2902997704353872,
  "fc_floor": 5650.425132934155,
  "p": 0.6022950754493743
}
```

- Plots: `plots/polars/NeumannU87AiCardioid_polar.png`, `plots/colour/NeumannU87AiCardioid_colour.png`, `plots/fit/NeumannU87AiCardioid_{train,holdout}.png`
- Metrics JSON: `reports/NeumannU87AiCardioid_metrics.json`

### `RoyerR121` — Royer R-121 — fig-8 ribbon

- Honesty: **MEASURED** · Family: `fig8_ribbon`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **9.462 dB** (MSE 89.522)
- Hold-out RMSE: **3.911 dB** (MSE 15.300)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=89.967159; LS success=True cost=23010.196758`
- Params:

```json
{
  "f0": 200.0000002362417,
  "depth_max_db": -17.831521473487285,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 286.8110225914407,
  "depth_lo_db": -1.1046230777093495,
  "res_hz": 1500.0002041190194,
  "lp_mix": 0.317183673001222,
  "fc_floor": 5375.651747401621,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/RoyerR121_polar.png`, `plots/colour/RoyerR121_colour.png`, `plots/fit/RoyerR121_{train,holdout}.png`
- Metrics JSON: `reports/RoyerR121_metrics.json`

### `ElectroVoiceRE20` — Electro-Voice RE20 — dynamic cardioid

- Honesty: **MEASURED** · Family: `dynamic_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.328 dB** (MSE 11.079)
- Hold-out RMSE: **3.532 dB** (MSE 12.473)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=11.251062; LS success=True cost=2880.197554`
- Params:

```json
{
  "f0": 1106.409831071917,
  "depth_max_db": -23.999999999999996,
  "shelf_slope": 0.6409255834061125,
  "f_lo": 211.45618398367876,
  "depth_lo_db": -0.2888168353815412,
  "res_hz": 14128.495970523794,
  "lp_mix": 0.27529514725933607,
  "fc_floor": 3530.6539896163945,
  "p": 0.9365045539975528
}
```

- Plots: `plots/polars/ElectroVoiceRE20_polar.png`, `plots/colour/ElectroVoiceRE20_colour.png`, `plots/fit/ElectroVoiceRE20_{train,holdout}.png`
- Metrics JSON: `reports/ElectroVoiceRE20_metrics.json`

### `AKGC414Cardioid` — AKG C414 Cardioid — LDC multipattern

- Honesty: **MEASURED** · Family: `ldc_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.501 dB** (MSE 12.255)
- Hold-out RMSE: **3.318 dB** (MSE 11.011)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=12.424547; LS success=True cost=3180.168415`
- Params:

```json
{
  "f0": 363.3790361787889,
  "depth_max_db": -18.534848059937737,
  "shelf_slope": 1.463408226221397,
  "f_lo": 219.73914572617107,
  "depth_lo_db": 0.018758254659365065,
  "res_hz": 1500.009731315695,
  "lp_mix": 0.27418992584783775,
  "fc_floor": 5874.955571009443,
  "p": 0.6704385487789598
}
```

- Plots: `plots/polars/AKGC414Cardioid_polar.png`, `plots/colour/AKGC414Cardioid_colour.png`, `plots/fit/AKGC414Cardioid_{train,holdout}.png`
- Metrics JSON: `reports/AKGC414Cardioid_metrics.json`

### `ShureSM58` — Shure SM58 — dynamic cardioid

- Honesty: **MEASURED** · Family: `dynamic_cardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **4.190 dB** (MSE 17.559)
- Hold-out RMSE: **4.801 dB** (MSE 23.050)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=17.776411; LS success=True cost=4548.895569`
- Params:

```json
{
  "f0": 200.00000000000003,
  "depth_max_db": -23.999999999999996,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 194.39755638106806,
  "depth_lo_db": -0.38027718166945856,
  "res_hz": 1500.6379521370686,
  "lp_mix": 0.26929651396822984,
  "fc_floor": 5364.713301406919,
  "p": 0.7807139815483786
}
```

- Plots: `plots/polars/ShureSM58_polar.png`, `plots/colour/ShureSM58_colour.png`, `plots/fit/ShureSM58_{train,holdout}.png`
- Metrics JSON: `reports/ShureSM58_metrics.json`

### `SennheiserMD441` — Sennheiser MD 441 — dynamic hypercardioid

- Honesty: **MEASURED** · Family: `hypercardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.275 dB** (MSE 10.726)
- Hold-out RMSE: **5.664 dB** (MSE 32.080)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=10.921157; LS success=True cost=2793.996413`
- Params:

```json
{
  "f0": 200.00104884992794,
  "depth_max_db": -21.261527748576714,
  "shelf_slope": 0.651182849036821,
  "f_lo": 219.8475288973311,
  "depth_lo_db": 0.00989414074661616,
  "res_hz": 1500.002986319497,
  "lp_mix": 0.2712688479112171,
  "fc_floor": 5118.467525845489,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/SennheiserMD441_polar.png`, `plots/colour/SennheiserMD441_colour.png`, `plots/fit/SennheiserMD441_{train,holdout}.png`
- Metrics JSON: `reports/SennheiserMD441_metrics.json`

### `NeumannU87AiOmni` — Neumann U87 Ai Omni — LDC

- Honesty: **MEASURED** · Family: `omni`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **2.464 dB** (MSE 6.070)
- Hold-out RMSE: **2.319 dB** (MSE 5.380)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=6.242127; LS success=True cost=1597.948485`
- Params:

```json
{
  "f0": 10041.421197747917,
  "depth_max_db": -19.20312521033122,
  "shelf_slope": 11.41540546441811,
  "f_lo": 262.91546121188117,
  "depth_lo_db": -0.42275458527701676,
  "res_hz": 2481.7455851748564,
  "lp_mix": 0.26919653478007444,
  "fc_floor": 6429.432581077348,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/NeumannU87AiOmni_polar.png`, `plots/colour/NeumannU87AiOmni_colour.png`, `plots/fit/NeumannU87AiOmni_{train,holdout}.png`
- Metrics JSON: `reports/NeumannU87AiOmni_metrics.json`

### `NeumannU87AiBidirect` — Neumann U87 Ai Bidirect — LDC fig-8

- Honesty: **MEASURED** · Family: `fig8`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **5.738 dB** (MSE 32.929)
- Hold-out RMSE: **2.626 dB** (MSE 6.898)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=33.177439; LS success=True cost=8491.207391`
- Params:

```json
{
  "f0": 3359.9029190977594,
  "depth_max_db": -20.239629527365118,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 239.2412999302356,
  "depth_lo_db": -0.6873608850453116,
  "res_hz": 1500.0000000003135,
  "lp_mix": 0.3064159525692415,
  "fc_floor": 4230.827546878981,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/NeumannU87AiBidirect_polar.png`, `plots/colour/NeumannU87AiBidirect_colour.png`, `plots/fit/NeumannU87AiBidirect_{train,holdout}.png`
- Metrics JSON: `reports/NeumannU87AiBidirect_metrics.json`

### `AKGC414Omni` — AKG C414 Omni — LDC multipattern

- Honesty: **MEASURED** · Family: `omni`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **2.988 dB** (MSE 8.927)
- Hold-out RMSE: **2.638 dB** (MSE 6.959)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=9.110504; LS success=True cost=2331.929258`
- Params:

```json
{
  "f0": 9807.16291900873,
  "depth_max_db": -23.999999999999996,
  "shelf_slope": 3.100012114160725,
  "f_lo": 242.43564291432207,
  "depth_lo_db": -0.34208209736199385,
  "res_hz": 1500.0080162041681,
  "lp_mix": 0.2832137377677979,
  "fc_floor": 6002.42219953281,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/AKGC414Omni_polar.png`, `plots/colour/AKGC414Omni_colour.png`, `plots/fit/AKGC414Omni_{train,holdout}.png`
- Metrics JSON: `reports/AKGC414Omni_metrics.json`

### `AKGC414Hyper` — AKG C414 Hyper — LDC multipattern

- Honesty: **MEASURED** · Family: `hypercardioid`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **3.659 dB** (MSE 13.391)
- Hold-out RMSE: **2.630 dB** (MSE 6.916)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=13.653874; LS success=True cost=3480.009711`
- Params:

```json
{
  "f0": 200.00000000000315,
  "depth_max_db": -17.786634428706712,
  "shelf_slope": 1.4793735187528014,
  "f_lo": 223.29493413898527,
  "depth_lo_db": -0.02844526970196577,
  "res_hz": 1500.0001664193776,
  "lp_mix": 0.3055629569964796,
  "fc_floor": 5403.097363984535,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/AKGC414Hyper_polar.png`, `plots/colour/AKGC414Hyper_colour.png`, `plots/fit/AKGC414Hyper_{train,holdout}.png`
- Metrics JSON: `reports/AKGC414Hyper_metrics.json`

### `AKGC414Bidirect` — AKG C414 Bidirect — LDC fig-8

- Honesty: **MEASURED** · Family: `fig8`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **7.227 dB** (MSE 52.223)
- Hold-out RMSE: **2.746 dB** (MSE 7.541)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=52.619884; LS success=True cost=13455.776461`
- Params:

```json
{
  "f0": 200.0002859814414,
  "depth_max_db": -17.79721112742918,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 248.28390453272488,
  "depth_lo_db": -0.9152270771256192,
  "res_hz": 1500.0008216023655,
  "lp_mix": 0.3276882351494259,
  "fc_floor": 4693.456985436847,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/AKGC414Bidirect_polar.png`, `plots/colour/AKGC414Bidirect_colour.png`, `plots/fit/AKGC414Bidirect_{train,holdout}.png`
- Metrics JSON: `reports/AKGC414Bidirect_metrics.json`

### `SchoepsCMC5UOmni` — Schoeps CMC5-U Omni — SDC

- Honesty: **MEASURED** · Family: `omni`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **1.031 dB** (MSE 1.062)
- Hold-out RMSE: **1.350 dB** (MSE 1.821)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=1.172212; LS success=True cost=300.066534`
- Params:

```json
{
  "f0": 10529.557321107039,
  "depth_max_db": -22.312846297318863,
  "shelf_slope": 4.757575588170816,
  "f_lo": 224.1169462242109,
  "depth_lo_db": -0.1257197256379913,
  "res_hz": 5409.448041361462,
  "lp_mix": 0.2523749471644026,
  "fc_floor": 5244.871084191734,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/SchoepsCMC5UOmni_polar.png`, `plots/colour/SchoepsCMC5UOmni_colour.png`, `plots/fit/SchoepsCMC5UOmni_{train,holdout}.png`
- Metrics JSON: `reports/SchoepsCMC5UOmni_metrics.json`

### `SchoepsCMC5UBidirect` — Schoeps CMC5-U Bidirect — SDC fig-8

- Honesty: **MEASURED** · Family: `fig8`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **4.125 dB** (MSE 17.012)
- Hold-out RMSE: **2.084 dB** (MSE 4.345)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=17.225503; LS success=True cost=4408.443139`
- Params:

```json
{
  "f0": 7638.243173231971,
  "depth_max_db": -18.71106918016628,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 192.58174346939623,
  "depth_lo_db": -0.7575635781073159,
  "res_hz": 1500.0000020933953,
  "lp_mix": 0.27703300070917813,
  "fc_floor": 3157.898040673983,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/SchoepsCMC5UBidirect_polar.png`, `plots/colour/SchoepsCMC5UBidirect_colour.png`, `plots/fit/SchoepsCMC5UBidirect_{train,holdout}.png`
- Metrics JSON: `reports/SchoepsCMC5UBidirect_metrics.json`

### `Coles4038` — Coles 4038 — fig-8 ribbon

- Honesty: **MEASURED** · Family: `fig8_ribbon`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **6.194 dB** (MSE 38.371)
- Hold-out RMSE: **3.057 dB** (MSE 9.345)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=38.684272; LS success=True cost=9892.432004`
- Params:

```json
{
  "f0": 200.00003177605709,
  "depth_max_db": -11.875142550740794,
  "shelf_slope": 0.6000000000000001,
  "f_lo": 235.1594229118391,
  "depth_lo_db": -0.7602830802165925,
  "res_hz": 1500.0007270249603,
  "lp_mix": 0.3107442499725204,
  "fc_floor": 5241.531433738029,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/Coles4038_polar.png`, `plots/colour/Coles4038_colour.png`, `plots/fit/Coles4038_{train,holdout}.png`
- Metrics JSON: `reports/Coles4038_metrics.json`

### `DPA4006` — DPA 4006 — measurement omni

- Honesty: **MEASURED** · Family: `omni`
- Source: `Franco et al. Zenodo 10.5281/zenodo.4633508 (Raw_IRs, 5m, 24-bit, selected angles)`
- Train RMSE: **0.874 dB** (MSE 0.764)
- Hold-out RMSE: **0.931 dB** (MSE 0.867)
- Hold-out angles: [45.0, 135.0]
- Train angles: [0.0, 15.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
- Fit log: `DE success=False nit=70 fun=0.851471; LS success=True cost=217.919702`
- Params:

```json
{
  "f0": 11044.036356110752,
  "depth_max_db": -17.12874911813715,
  "shelf_slope": 8.190175905459276,
  "f_lo": 219.98400886436144,
  "depth_lo_db": 0.0035863408480218554,
  "res_hz": 6797.162778604721,
  "lp_mix": 0.25209998372183756,
  "fc_floor": 4830.7413662843255,
  "p": 0.6000000000000001
}
```

- Plots: `plots/polars/DPA4006_polar.png`, `plots/colour/DPA4006_colour.png`, `plots/fit/DPA4006_{train,holdout}.png`
- Metrics JSON: `reports/DPA4006_metrics.json`

## Evidence the fitter ran end-to-end

- Log file: [`logs/fit_run.log`](logs/fit_run.log)
- Per-mic metrics under `reports/*_metrics.json`
- Preset index: [`presets/index.json`](presets/index.json)
- This report timestamp: 2026-09-23 08:51 BST
- Wall time: 57.4 s for the original 17 mics (NT2-A ×3 fitted separately in 10.7 s on 2026-09-24; 20 MEASURED total)

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

## Optional HPF (schema only — not fitted)

- Preset field `switches: { hpf_hz, hpf_slope (6|12|18), hpf_engaged }` (default engaged=false).
- Manufacturer defaults documented in `mic_fitter.model.MANUFACTURER_HPF_DEFAULTS` (U87 ≈140 Hz, C414 bass-cut options, SM57/SM58 none, etc.).
- Helper `apply_hpf(db, freqs, ...)` for future UI; colour/polar/fit plots stay filter-out.
- Zenodo Raw_IRs are used without engaging HPF (filters out of the MEASURED fit).

## SE Electronics SE2200A / Røde NT5 — no measured data available; not planned

- **Requested but absent** from Franco et al. Zenodo 4633508, and Idle confirmed (2026-09-27) he has no data for either.
- Status: **no measured data available; not planned**. See `presets/pending_se2200a.md` / `presets/pending_rode_nt5.md`; no fake MEASURED fit.

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
    polars/            # classic polar at 20/63/125/250/1k/4k/8k
    colour/            # off-axis colour curves
    fit/               # meas-vs-model train/holdout panels
  data/                # zenodo/ + manifest.json
  reports/             # metrics + gallery.html
  logs/fit_run.log
```

## Room software

Pointer only — **untouched**: `../software/` (Desktop) / `/workspace/2011-Room-Reverb/software/` (box).

---

## Røde NT2-A MEASURED add-on — 2026-09-24 19:40 BST

- Filtered re-fit of **3** mic(s) in 10.7 s; other presets left intact.
- Source: Franco et al. Zenodo Raw_IRs 5 m 24-bit (cardioid / omni / bidirect).
- **NT5**: absent from Zenodo and no user data — **no measured data available; not planned** (see `presets/pending_rode_nt5.md`).
- NT2-A is a **1" LDC multipattern**, not an NT5 stand-in for matched-pair SDC use.
- Room Reverb mix / worklet / default engine: **untouched**.

| mic_id | display | family | train RMSE | hold-out RMSE |
|--------|---------|--------|------------:|--------------:|
| `RodeNT2ACardioid` | Røde NT2-A Cardioid | ldc_cardioid | **3.600** | **4.100** |
| `RodeNT2AOmni` | Røde NT2-A Omni | omni | **1.955** | **1.373** |
| `RodeNT2ABidirect` | Røde NT2-A Bidirect (fig-8) | fig8 | **4.461** | **2.260** |

### Fit details

#### `RodeNT2ACardioid` — Røde NT2-A Cardioid

- Honesty: **MEASURED** · Family: `ldc_cardioid`
- Train RMSE: **3.600 dB** · Hold-out RMSE: **4.100 dB**
- Fit: `DE success=False nit=70 fun=13.130401; LS success=True cost=3359.664325`
- Params: `{"f0": 312.04226563580175, "depth_max_db": -18.07525078667601, "shelf_slope": 1.4597338003514664, "f_lo": 218.3223106603378, "depth_lo_db": 0.12823876576253299, "res_hz": 1500.0025442486706, "lp_mix": 0.2769423278359476, "fc_floor": 5257.740786945445, "p": 0.6783597959965227}`
- Plots: `plots/polars/RodeNT2ACardioid_polar.png`, `plots/colour/RodeNT2ACardioid_colour.png`, `plots/fit/RodeNT2ACardioid_{train,holdout}.png`

#### `RodeNT2AOmni` — Røde NT2-A Omni

- Honesty: **MEASURED** · Family: `omni`
- Train RMSE: **1.955 dB** · Hold-out RMSE: **1.373 dB**
- Fit: `DE success=False nit=70 fun=3.964194; LS success=True cost=1014.801283`
- Params: `{"f0": 11411.227959401911, "depth_max_db": -18.33874344258462, "shelf_slope": 9.212254031972837, "f_lo": 244.17001391356277, "depth_lo_db": -0.2881913273098104, "res_hz": 2741.880898086813, "lp_mix": 0.2630349087599272, "fc_floor": 6223.154164249277, "p": 0.6000000000000001}`
- Plots: `plots/polars/RodeNT2AOmni_polar.png`, `plots/colour/RodeNT2AOmni_colour.png`, `plots/fit/RodeNT2AOmni_{train,holdout}.png`

#### `RodeNT2ABidirect` — Røde NT2-A Bidirect (fig-8)

- Honesty: **MEASURED** · Family: `fig8`
- Train RMSE: **4.461 dB** · Hold-out RMSE: **2.260 dB**
- Fit: `DE success=False nit=70 fun=20.143980; LS success=True cost=5150.002529`
- Params: `{"f0": 4667.743547563702, "depth_max_db": -15.875810506692973, "shelf_slope": 0.6000000000000001, "f_lo": 207.18670604294732, "depth_lo_db": -0.819885946067054, "res_hz": 1500.0000000000002, "lp_mix": 0.2892804701424431, "fc_floor": 3987.049413373144, "p": 0.6000000000000001}`
- Plots: `plots/polars/RodeNT2ABidirect_polar.png`, `plots/colour/RodeNT2ABidirect_colour.png`, `plots/fit/RodeNT2ABidirect_{train,holdout}.png`

### polar3d (added 2026-09-27)

- Generated with the same `mic_fitter.polar3d` functions/style as the other 17 (from the MEASURED NT2-A presets; fits unchanged):
  `plots/polar3d/RodeNT2A{Cardioid,Omni,Bidirect}_polar3d.png` and `..._polar3d_rings.png`.
- `reports/gallery.html` now lists all 20 MEASURED mics incl. NT2-A.
