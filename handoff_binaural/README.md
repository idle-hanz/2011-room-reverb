# binaural: MEASURED dummy-head presets for the 2011 Room Reverb mic model

Adds a **Binaural (dummy head)** mic option: two ears at a fixed head spacing, per-ear HRTF colour fitted to the
project's IIR colour format (min-phase RBJ biquads, one record per grid node, separate 44.1 / 48 kHz tables), ITD as
delay (ear geometry + a measured correction), ILD in the magnitude. Standalone: nothing in `software\` is touched and the
20 existing mic presets are untouched (checked by `tests/test_binaural_presets.py::test_existing_20_presets_untouched`).

Tags: **MEASURED** = fitted from published measured HRIRs (derived, see below); **VERIFIED** = checked by a script or
test here; **ASSUMED** = judgement. No measured numbers are invented: every figure in this pack comes from
`reports/metrics_G60.json`, `reports/bench_sos_box.log` or the SOFA files.

## Read order

1. `DECISIONS_LOCKED_2026-09-30.md`: Idle's locked binaural decisions (diffuse IC tail, SADIE2_KU100 default, K=6 with
   one mirror table, 1/r² from the head centre, rear images).
2. `BINAURAL_MODE_BRIEF.md`: build spec for Grok Build.
3. `reports/SUMMARY.md`, `reports/rear_images.json`, `reports/tail_ic.json`: numbers.
4. `DATA_LICENCES.md`, `LICENSES/`, `RESEARCH_NOTES.md`.

## Presets (all MEASURED)

| preset_id | head | source | licence | ear spacing | distance | native rates |
|---|---|---|---|---|---|---|
| `SADIE2_KU100` (default, LOCKED) | Neumann KU100 | SADIE II v2-2 D1, doi:10.5281/zenodo.12092466 | Apache-2.0 | 0.180 m | 1.2 m | 44.1 / 48 kHz |
| `SADIE2_KEMAR` | KEMAR | SADIE II v2-2 D2 | Apache-2.0 | 0.180 m | 1.2 m | 44.1 / 48 kHz |
| `THK_KU100_FF` | Neumann KU100 | TH Köln far field, doi:10.5281/zenodo.3928297 | CC BY-SA 3.0 (conflict noted) | 0.175 m | 3.25 m | 48 kHz (44.1 table fitted from the 48k magnitude) |

Ear spacing = |ReceiverPosition L − R| in each SOFA file (VERIFIED). See `DATA_LICENCES.md`, `LICENSES/`, `RESEARCH_NOTES.md`.

## Method (short)

1. Load SOFA (netCDF4). Receiver 0 = left ear (VERIFIED by test: ILD > 0 at 4 kHz for a left source).
2. |H| via 8192-point FFT, diffuse-field EQ (area-weighted power average over the sphere, both ears, 1/3-oct smoothed;
   SADIE is already DF-EQ'd: its DF response is flat within 0.3 dB over 100 Hz–16 kHz, VERIFIED), 1/6-octave power smoothing.
3. Grid **G60** (60 head-relative nodes, rings at el 0/±30/±60/±90, 20° azimuth on the horizontal). Nearest measured
   direction per node (SADIE exact, THK ≤ 1.6°, VERIFIED). Mirror-average L(n) with R(mirror n) so one record serves both ears.
4. Fit K = 3…6 RBJ sections (LS + HS + (K−2) PK), greedy peak/notch seeding then joint least squares on dB, per node,
   per rate, at the table's own rate. Weights 1 in 100 Hz–16 kHz, 0.3 outside (40 Hz–20 kHz).
5. Metrics per node and ear (max / RMS dB, 100 Hz–16 kHz), hold-out = measured directions on a 5° azimuth grid at
   el 0, ±15…±60 that are > 2.5° from every node (fit of nearest node vs measurement), grid-only error,
   symmetrisation cost, stability (float32 too).
6. ITD: LF (< 1.5 kHz) cross-correlation per direction → median per 5° lateral bin → correction over free-field ear
   geometry (Woodworth fit kept as fallback).

## Headline results (VERIFIED; details `reports/SUMMARY.md`)

- **K = 6 (LOCKED)** (= `MAX_SOS` 6): node max error median 1.4–1.7 dB, p95 3.0–3.4 dB, worst 4.0–4.4 dB;
  node RMS median 0.4–0.5 dB (K = 3: p95 7.6–8.1 dB, worst up to 12.3 dB). All poles ≤ 0.9988, min-phase.
- Hold-out RMS (incl. grid) ≈ 1.7–1.8 dB median for K ≥ 5: the grid, not K, limits off-node accuracy.
- **Entries**: 60 records worst case (fixed bank) ≤ MAX_IRS 64. Front-only p5 image set: 17–22 in tested scenes at yaw 0.
  With the locked rear-image set: 19–28 at yaw 0, 24 with two sources, and up to 38 at yaw 90.
- **CPU (Play, box native C)**: binaural K = 6 front-only ≈ 3.0 % of one core @ 48 kHz, today's ORTF (K = 3, 87 filters) 4.0 %;
  locked mode (rear images + tail mixer) 4.6–5.8 %.
- **ITD**: geometry alone under-estimates by ~30 % (max 515–529 µs vs measured 721–797 µs); + table correction RMS
  13–36 µs.

## Locked-decision additions (30 Sep 2026, VERIFIED)

- **Diffuse tail:** the even/odd line split plus a 513-tap M/S FIR mixer to the head's measured diffuse-field IC
  (`presets/binaural/tail_ic/`). On the p5 FDN: max |ΔIC| 0.065–0.098, RMS 0.028–0.044 (1/3-octave bands, 125 Hz–8 kHz).
- **Rear images:** `presets/binaural/image_sets/binaural_rear32.json` (N = 32 kept, 5 rear images). Worst entry count
  seen is 38 records ≤ 64, and the fixed bank is 60. CPU is about 4.6–5.8 % of one box core at 48 kHz, tail mixer included.

## Layout

```
binaural/
  README.md  BINAURAL_MODE_BRIEF.md  RESEARCH_NOTES.md  DATA_LICENCES.md  LICENSES/
  binaural_fitter/   core.py (SOFA, spectra, DF-EQ)  sosfit.py  grid.py  itd.py  datasets.py  reference.py
                     rear_images.py (binaural_rear32)  tail_ic.py (diffuse IC mixer)
  run_binaural_fit.py      stage 1 fits (cached reports/fits_G60.json) + stage 2 metrics
  export_binaural.py       presets/binaural/*.json + sos_tables/{44100,48000}/
  scripts/  download_data.sh  engine_directions.py  make_plots.py  make_summary.py  rear_tail_study.py
  presets/binaural/        3 presets, index.json, sos_tables/44100|48000/<id>.json (K6) + <id>.K3.json,
                           tail_ic/<id>.json, image_sets/binaural_rear32.json, LICENSES/
  plots/binaural/          per preset: hrtf_vs_fit, ild_itd, polar_top, grid_error_map; k_tradeoff_and_grid; diffuse_field_coherence;
                           tail_ic_SADIE2_KU100; rear_images_top
  reports/                 SUMMARY.md, metrics_G60.json, bench_sos_box.log, engine_directions.json, ...
  tests/                   test_binaural_presets.py + test_binaural_locked.py (pass), test_binaural_mode_acceptance.py (xfail until built)
  bench/bench_sos.c  bench/bench_fir.c
```

## Run

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
bash scripts/download_data.sh          # SOFA files are not shipped (licence + size)
python scripts/engine_directions.py    # needs the p5 software tree (read-only import)
python run_binaural_fit.py             # stage 1 is cached in reports/fits_G60.json
python export_binaural.py
python scripts/make_plots.py && python scripts/make_summary.py
python scripts/rear_tail_study.py      # locked items 1 and 5 (needs the p5 tree, ~35 s)
pytest tests/ -rx                      # 61 passed, 22 xfailed
```

Windows: same steps with `.venv\Scripts\activate`; get the data with the URLs in `scripts/download_data.sh`.
