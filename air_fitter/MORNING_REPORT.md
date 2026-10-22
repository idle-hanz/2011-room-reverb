# air_fitter — MORNING_REPORT / FIT_REPORT

**Generated:** 2026-09-23 17:02 BST (Europe/London)
**Elapsed:** 9.1 s
**Honesty:** FITTED_TO_ISO_9613_1 (not measured IRs)

## Locks (do not violate)

> **Later decision (Idle, 2026-09-23):** the Structure one-pole **is** retired, in Phase 6 of `docs/GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` (v2.5), together with swapping this shelf in. Not during mic phases. The lines below are the fit-time locks; the brief wins on the one-pole.

- Geometric **1/r²** stays; this only replaces the ASSUMED high-shelf colour path.
- Structure **1-pole Wet/Dis** — superseded by the decision above. Do not keep it “because this report said so.”
- Placement: **once** on early + FDN inject; **not** Direct; **not** feedback return.
- Do **not** import into live `software/` engine in this task.

## Physics

ISO 9613-1:1993 α(f) in dB/m (python-acoustics equations):
saturation vapour pressure → molar h → frO / frN → attenuation_coefficient.
Path attenuation: `A_db(f) = −α(f)·d` (model outputs ≤ 0 dB).
Fit grid: log-spaced 20-16000 Hz x distances [5.0, 10.0, 20.0, 40.0] m.
HF weight ×1.5 on 4–16 kHz. Candidates A (high shelf) → B (+ soft 1-pole) → C (dual shelf).

### ISO sanity (studio 20 °C / 50 % RH)

| f | α (dB/m) |
|---|----------|
| 125Hz | 0.002739 |
| 250Hz | 0.003181 |
| 500Hz | 0.003343 |
| 1000Hz | 0.003498 |
| 2000Hz | 0.003986 |
| 4000Hz | 0.005906 |
| 8000Hz | 0.013578 |
| 16000Hz | 0.044264 |

Check: α(~1 kHz) = **0.00350 dB/m** (expected rough order **0.003–0.005** at 20 °C / 50 % RH); rises toward 8–16 kHz.

## Winning models

| Climate | Candidate | Model | Joint RMSE (dB) | Flat naive RMSE | vs ASSUMED hum=0.5 |
|---------|-----------|-------|-----------------|-----------------|--------------------|
| `studio_20C_50RH` | **C** | `dual_high_shelf` | 0.01121 | 0.22236 | 0.32681 |
| `dry_20C_20RH` | **C** | `dual_high_shelf` | 0.00966 | 0.21764 | 0.33953 |
| `humid_20C_80RH` | **C** | `dual_high_shelf` | 0.01418 | 0.23126 | 0.31203 |
| `warm_22C_40RH` | **C** | `dual_high_shelf` | 0.01104 | 0.22233 | 0.32733 |

### Primary studio params

- **Winner:** candidate **C** — `dual_high_shelf`
- **Joint RMSE:** 0.011207 dB (weighted)
- **Flat naive RMSE:** 0.222358 dB
- **ASSUMED shelf RMSE:** hum=0.5 → 0.32681 dB; hum=1.0 → 0.90416 dB
- **All candidates (joint RMSE):** A=0.06058, B=0.02374, C=0.01121
- **Params:**
```json
{
  "f0": 500.00000000012307,
  "depth_db_per_m": -0.00655233332616923,
  "shelf_slope": 1.1217329192186143,
  "f0_hi": 15999.999999999645,
  "depth_hi_db_per_m": -0.07448108131080945,
  "shelf_slope_hi": 7.053415484505896
}
```

### Per-distance RMSE (studio)

| Distance | RMSE (dB) |
|----------|-----------|
| 5m | 0.002241 |
| 10m | 0.004482 |
| 20m | 0.008964 |
| 40m | 0.017928 |

## ASSUMED engine shelf (compare only)

Current listened path (`software/engine/early_field.py`):
`gain_db = -0.15 * distance * humidity`, RBJ high-shelf corner ≈ `0.35 * Nyquist`
(≈ 7718 Hz at 44.1 kHz). Humidity UI 0.5 and 1.0 plotted vs ISO — **not fitted**.
ISO α(f) is strongly frequency-dependent; the flat-above-shelf ASSUMED curve is a coarse colour only.

## hall_long_path note

No extra fit. Studio coeffs reused at 40 / 60 / 80 m — see `plots/fit/hall_long_path_studio.png`.
Useful for hall / outdoor-path distance colouring without a new climate preset.

## Absolute paths (box)

- Pack root: `/workspace/air_fitter`
- Presets: `/workspace/air_fitter/presets`
- Plots fit: `/workspace/air_fitter/plots/fit`
- Plots shape: `/workspace/air_fitter/plots/shape`
- Reports: `/workspace/air_fitter/reports`

## Desktop sync target

`C:\Users\IdleHanz\Desktop\2011 Room Reverb\air_fitter\`

## Usage reminder

`A_db(f,d) = d * H1(f)`; magnitude `10^(A_db/20)` once per path (early) or inject distance (FDN).
Do not put on feedback return. Do not replace geometric 1/r².

### `studio_20C_50RH` detail

- Label: Studio 20 °C / 50 % RH (PRIMARY)
- Conditions: {'temperature_c': 20.0, 'relative_humidity_pct': 50.0, 'pressure_kpa': 101.325}
- Candidate C / `dual_high_shelf`
- Params: `{"f0": 500.00000000012307, "depth_db_per_m": -0.00655233332616923, "shelf_slope": 1.1217329192186143, "f0_hi": 15999.999999999645, "depth_hi_db_per_m": -0.07448108131080945, "shelf_slope_hi": 7.053415484505896}`
- Message: winner=C (dual_high_shelf); DE success=False nit=80 fun=0.000130375; LS success=True cost=0.0241128

### `dry_20C_20RH` detail

- Label: Dry 20 °C / 20 % RH
- Conditions: {'temperature_c': 20.0, 'relative_humidity_pct': 20.0, 'pressure_kpa': 101.325}
- Candidate C / `dual_high_shelf`
- Params: `{"f0": 7999.999999655233, "depth_db_per_m": -0.00731179164937025, "shelf_slope": 0.7255599034851314, "f0_hi": 15999.999999999998, "depth_hi_db_per_m": -0.07453046939096905, "shelf_slope_hi": 6.943995090816494}`
- Message: winner=C (dual_high_shelf); DE success=False nit=80 fun=9.35775e-05; LS success=True cost=0.0179044

### `humid_20C_80RH` detail

- Label: Humid 20 °C / 80 % RH
- Conditions: {'temperature_c': 20.0, 'relative_humidity_pct': 80.0, 'pressure_kpa': 101.325}
- Candidate C / `dual_high_shelf`
- Params: `{"f0": 500.0000000000019, "depth_db_per_m": -0.00912276299802007, "shelf_slope": 1.3699487604857439, "f0_hi": 15999.999999999998, "depth_hi_db_per_m": -0.07343110569022904, "shelf_slope_hi": 7.34625271358996}`
- Message: winner=C (dual_high_shelf); DE success=False nit=80 fun=0.000206475; LS success=True cost=0.0386279

### `warm_22C_40RH` detail

- Label: Warm 22 °C / 40 % RH
- Conditions: {'temperature_c': 22.0, 'relative_humidity_pct': 40.0, 'pressure_kpa': 101.325}
- Candidate C / `dual_high_shelf`
- Params: `{"f0": 500.0000000045118, "depth_db_per_m": -0.006380612520158538, "shelf_slope": 1.0774956971836434, "f0_hi": 15999.999999999998, "depth_hi_db_per_m": -0.0748390862778581, "shelf_slope_hi": 7.023806524995857}`
- Message: winner=C (dual_high_shelf); DE success=False nit=80 fun=0.00012558; LS success=True cost=0.0233854
