# 2011 Room Reverb: validation against a measured room (BRAS CR2)

Written 27 Sep 2026 (BST). Tags: **VERIFIED** means checked in code, data or a source page. **ASSUMED** means my inference. **ESTIMATED** means fitted by me.

Plots and adapted numbers derive from BRAS, which is **CC BY-SA 4.0**. See §8 before publishing.

## 1. What was compared

| item | value |
|---|---|
| Measured data | BRAS v3 (Benchmark for Room Acoustical Simulation, TU Berlin / RWTH Aachen), doi:10.14279/depositonce-6726.3. Scene **CR2 small room (seminar room)**, 2 dodecahedron sources × 5 B&K 4134 omni mics = 10 RIRs at 44.1 kHz. V = 145 m³, 19.5 °C, 41.7 % RH (BRAS documentation). **VERIFIED** |
| Why CR2 | It is the nearest to a shoebox in BRAS: a rectangular seminar room with an omni source, omni mics and five fitted materials (ceiling, concrete, floor, plaster, windows). RS1–RS6 are single- and double-reflection scenes with directional Genelec sources and an absorber whose height is unknown, so they are left for later (§7). The BRAS abstract warns that CR1–CR4 "can not be used as a direct reference" because of measurement uncertainty. That makes this a **plausibility check, not a strict reference**. **VERIFIED** (abstract text) |
| Geometry | The .skp could not be parsed reliably. I fitted the walls from reflection arrival times (`fit_geometry.py`, `geometry_fit.json`): x ∈ [−2.985, 2.890] and y ∈ [−4.030, 4.640], floor at 0. The ceiling was set to 2.847 m so that V = 145 m³ (the arrival fit gives 2.73–3.27 depending on band; the default run gives 2.78). Result: box **5.875 × 8.67 × 2.847 m**. **ESTIMATED** |
| Materials | BRAS fitted α per material (`mat_CR2_*.csv`). The layout is **ASSUMED**: side wall A = plaster; window wall C = 50/50 windows/plaster; end walls B and D = 50/50 concrete/plaster; floor; ceiling. The 1/1-octave Eyring estimate is 1.70, 1.50, 2.28, 2.17, 1.86, 1.71 and 0.96 s (125 Hz–8 kHz). |
| Model settings | Render path (`render_pipeline.render`, unit impulse, clip_guard undone) through `engine/tools/render_ir.py`. Centre capsule only, omni, colour **BYPASS**, space 0, early_wet 0, fdn_wet 1, direct_wet 1, dry 0, hadamard_n 32, humidity 0.35, air_lp 0.25, surfaces set per the layout above. **Coordinate mapping**: LIVE_32 has no −Z images (**VERIFIED**), so the model z axis is flipped per source so that the source sits "ahead" of the mic. The model's z=0 wall is therefore the one with no first-order image. |
| Variants | `snap_default` (snapshot, decay dial 1.8 s = UI default); `snap_eyring` (dial 2.22 s = Eyring mean of 500 Hz and 1 kHz); `snap_oracle` (dial 1.93 s = measured T20 at 1 kHz); `fix_eyring` and `fix_oracle` (the same dials on `engine/work/sw_fix`, F1–F3 fixes). |
| Physical baseline | `ism_baseline.py`: an energy-domain Allen–Berkley specular image-source model of the same box, with BRAS α, 1/r² energy, ISO 9613-1 air absorption, c = 343.1 m/s, up to 1.6 s. It shows what a *purely specular* shoebox gives. |
| Analysis | `analysis.py`: ISO 3382-1 style Butterworth octave bands, Schroeder EDC with simplified Lundeby truncation and noise compensation (measured data only), EDT, T20, T30, C50, C80 and D50. Onset is −20 dB of the peak. JND values follow ISO 3382-1 Annex A: 5 % for EDT and T, 1 dB for C. My measured values agree with the BRAS-supplied ITA-Toolbox values (the dots in the plots): T20 at 1 kHz is 1.94 s (mine) vs 1.92–1.93 s (BRAS). **VERIFIED** |

Run order: `fetch_bras.sh` → `render_all.py` (50 renders at about 25 s each) → `compare.py`. Results are in `results/` and plots in `plots/`.

## 2. Headline numbers (mean of 10 RIRs, octave bands)

| | EDT 1k | T20 500 / 1k / 2k / 4k / 8k | T30 1k | C50 1k | C80 1k | D50 1k |
|---|---|---|---|---|---|---|
| **Measured** | 1.91 s | 2.00 / 1.94 / 1.74 / 1.54 / 1.11 s | 1.94 s | −3.4 dB | −0.8 dB | 0.31 |
| ISM (specular, physical) | 2.52 | 3.19 / 2.90 / 2.31 / 2.01 / 0.99 | 2.81 | −4.2 | −1.9 | 0.27 |
| snap_default (1.8 s) | **0.27** | 2.02 / 1.97 / 2.02 / 1.99 / 1.95 | **2.94** | **+12.3** | **+14.7** | 0.94 |
| snap_oracle (1.93 s) | 0.29 | 2.01 / 1.95 / 2.01 / 1.98 / 1.94 | 2.92 | +11.9 | +14.4 | 0.94 |
| fix_eyring (2.22 s) | 2.23 | 2.19 / 2.16 / 2.22 / 2.20 / 2.20 | 2.18 | −1.9 | 0.0 | — |
| **fix_oracle (1.93 s)** | 1.96 | 1.89 / 1.90 / 1.93 / 1.92 / 1.91 | 1.89 | −1.5 | +0.5 | 0.42 |

The full tables are `results/cr2_octave_table.md` and `results/cr2_error_jnd.md` (errors in JND per band). Mean absolute error over the 7 octaves, in JNDs:

| | EDT | T20 | T30 | C50 | C80 |
|---|---|---|---|---|---|
| ISM | 5.7 | 9.4 | 9.2 | 0.7 | 0.9 |
| snap_oracle | 16.1 | 5.2 | 16.3 | 13.8 | 13.5 |
| fix_eyring | 8.6 | 7.4 | 7.2 | 1.1 | 1.3 |
| fix_oracle | 5.5 | 4.3 | 4.0 | 1.3 | 1.3 |

Plots:
- `plots/cr2_params_octave.png`: parameters vs frequency
- `plots/cr2_edc_LS1_MP1.png`: EDC at 250 Hz, 1 kHz and 4 kHz
- `plots/cr2_early_LS1_MP1.png` and `plots/cr2_early_LS2_MP4.png`: 0–60 ms envelopes with the first-order image times
- `plots/cr2_first_order_levels.png`
- `plots/geometry_fit_scans.png`

## 3. Findings

### 3.1 The snapshot (as on the PC today) is not realistic in its energy balance. **VERIFIED** (measured here)
- **The direct sound dominates.** C80 is +14.4 dB vs −0.8 dB measured, C50 is +11.9 vs −3.4, and D50 is 0.94 vs 0.31. Late energy is about 24 dB lower relative to direct than in the room: late (>50 ms) over direct is −10.6 dB vs +13.3 dB at 1 kHz.
- **EDT is 0.29 s vs 1.91 s.** The EDC drops about 12–15 dB almost immediately (the direct plus sparse images), then decays at the dialled rate.
- **Two-slope tail.** T20 is right (≈1.95 s with the oracle dial) but T30 is 2.92 s. This is the known snapshot tail defect that F1–F3 address: the late slope is shallower than the dial.
- The decay dial is honoured for T20 at 500 Hz–1 kHz within about 1 JND.

### 3.2 The F2-fixed engine is close to the measured room in broadband energy terms. **VERIFIED** (measured here)
- With the dial at the measured T20 (`fix_oracle`), the mid-band results are:
  - EDT, T20 and T30 within ±1 JND at 500 Hz–1 kHz
  - C50 and C80 within +1.4 to +2.2 dB (dB = JND)
  - D50 of 0.42 vs 0.31
- This result depends on the F2 change. The F2 per-line decay gains put far more energy into the tail. Late over direct rises from −10.6 dB to +3.3 dB at 1 kHz.
- With the dial from Eyring (`fix_eyring`, 2.22 s vs a measured 1.94 s), T is 11–15 % long mid-band, i.e. about +2 to +3 JND. That error comes from the Eyring estimate and my material layout, not the engine.

### 3.3 The decay is frequency-flat; the room is not. **VERIFIED** (code + measurement)
- The model's T20 is 1.89–1.93 s from 125 Hz to 8 kHz.
- The measured T20 is 1.34 s at 125 Hz, 1.54 s at 4 kHz and 1.11 s at 8 kHz, so the model is +14 JND at 8 kHz and +5 JND at 125 Hz and 4 kHz.
- The cause is in the code: `decay_lock` + `decay_s` → `structure_gain_for_rt60` sets one broadband loop gain. Surface α only scales the inject by √(1−ᾱ) and the per-hit EQ acts on the first pass. Air absorption (humidity 0.35, air_lp) does not shorten the HF tail enough to matter here.
- **Spectral balance** of late (>50 ms) over direct, normalised at 1 kHz (125 / 250 / 500 / 1k / 2k / 4k / 8k):
  - measured: +15.7 / +8.9 / +2.9 / 0 / −1.3 / +0.6 / −3.3 dB
  - fix_oracle: +17.4 / +6.5 / +1.5 / 0 / +0.1 / −0.4 / −0.4 dB
  - So the tail is about 3 dB too bright at 8 kHz.
  - The large 125/250 Hz values in both are partly an artefact of the 3 ms direct window at low frequency, and partly the dodecahedron's weak LF direct radiation. Compare the columns side by side, not in absolute terms.

### 3.4 Early reflections: the timing is right, the levels are about 15–30 dB too low, and the field is too sparse. **VERIFIED** (measured here), causes partly **ASSUMED**
The first-order images were compared by wall. Levels are the band envelope (0.5–4 kHz) after a matched filter on the direct, in dB relative to the direct, averaged over the 10 pairs (`results/cr2_first_order_by_wall.md`):

| wall | model arrival − physical | measured | snap_oracle | fix_oracle | physical 1/r·√(1−α) | model law 1/r²·√(1−α) |
|---|---|---|---|---|---|---|
| A side wall (x=0) | +0.10 ms | −6.6 | −20.9 | −22.5 | −7.4 | −14.6 |
| C window wall | +0.08 | −7.0 | −25.5 | −26.6 | −6.5 | −12.8 |
| E floor | +0.01 | −5.0 | −16.1 | −18.7 | −1.9 | −3.5 |
| F ceiling | +0.05 | −8.9 | −27.8 | −36.6 | −4.5 | −8.7 |
| D back wall (model z=0, **no image in LIVE_32**) | +0.22 | −8.9 | −25.8* | −24.5* | −11.9 | −23.6 |
| B front wall | +0.08 | −6.2 | −30.4 | −24.7 | −6.4 | −12.5 |

\*The D wall has no image in the model, so these values are whatever other energy sits at that time. They represent the model's detection floor.

- **Timing is fine.** c = 340 instead of 343 m/s gives only +0.01 to +0.22 ms relative error. The absolute direct arrival is also about 0.9 % late (e.g. 0.1 ms at 4 m). This is **VERIFIED** (`early_field.py` c = 340, and the direct at sample 576 exactly as predicted).
- **Levels are low.** Measured first-order reflections sit near the physical 1/r expectation (−5 to −9 dB; the D wall reads high because the peak search picks up neighbouring arrivals). The model's reflections are 15–30 dB lower, and 7–15 dB below even the model's own 1/r² law. **ASSUMED** causes, in order:
  1. The 1/r² amplitude law, which is faithful to Reaktor. It costs 3.5–12 dB against 1/r at these distances (the table's last two columns).
  2. Each image leaves through its FDN line, i.e. through the Schroeder diffuser allpass. The allpass spreads the image energy: part goes out at t=0 (§3.5) and part into the recirculation, rather than one spike.
  3. The per-hit surface EQ and air filters.
  4. The model's direct is the 0.55 spike **plus** the FDN n=(0,0,0) line, which makes the reference louder.
- **Density.** The measured 0–60 ms field is dense, at about −5 to −15 dB relative to the direct, from about 8 ms on (dodecahedron plus furniture scattering). The model shows a few discrete images at −15 to −25 dB. The 32-tap table (29 unique entries, no ±2W, no −Z) cannot supply that density. See the early plots.

### 3.5 A non-physical sample at t=0. **VERIFIED** (code + renders)
- Every model IR has a spike at sample 0, before the direct arrives:
  - `fix_oracle`: −7.5 to −21 dB relative to the IR peak (value −0.12 against a 0.29 peak for LS1 MP1)
  - snapshot: −20 to −33 dB
- `fdn_wet=0` removes it and `direct_wet=0` keeps it, so it comes from the FDN.
- In `engine/fdn.py` `process_block_poly`, the line output is the diffuser allpass output `y = -g_i*x + v`. Its feed-forward term `-g_i*x` passes the t=0 inject straight to the output.
- In a live plug-in this would be a pre-echo ahead of the direct sound, e.g. 13 ms early for a 4.5 m source. The analysis zeroes the first 32 samples of the model IRs (`compare.py PRE_ZERO`).
- The live C path has the same form: `engine/live_stereo.c` line 956 is `double y = -gi * s + st->delayed[i];`. This is **VERIFIED** as code text in the snapshot. Its effect on Play was **not measured** here (**ASSUMED** to be a zero-latency leak of the input into the wet output).
- Whether Reaktor did the same is unknown (**ASSUMED** the topology is faithful). Either way, the output tap should not see the undelayed inject.

### 3.6 The purely specular physical ISM is too long too. **VERIFIED** (measured here)
- The specular ISM with BRAS α gives T20 at 1 kHz of 2.90 s vs 1.94 s measured, i.e. +10 JND on average.
- Its C50 and C80 are close (within about 1 dB).
- So material α alone, with specular reflections in a box, over-predicts the decay here. The likely reasons are that the real room is not an empty box (furniture, scattering, non-uniform absorption) and that my geometry and layout are estimates. **ASSUMED**
- The implication for the rebuild: deriving the tail purely from surface α by image counting would make CR2-like rooms too long. Eyring/Sabine with a scattering-aware (diffuse) assumption lands nearer (Eyring 2.17 s at 1 kHz vs a measured 1.94 s).

## 4. Where the model is realistic and where it is not

| aspect | snapshot | F2-fixed |
|---|---|---|
| Reflection timing | realistic (c = 340 m/s is ≤0.2 ms off) | same |
| Decay rate at the dial frequency (T20) | realistic | realistic |
| Late slope (T30 vs T20) | **not**: +50 % long | realistic |
| Early decay (EDT), clarity (C50/C80), D50 | **not**: direct 12–15 dB too dominant | about 1–2 JND, plausible |
| Decay vs frequency | **not**: flat | **not**: flat, +14 JND at 8 kHz |
| First-order reflection levels | **not**: 15–30 dB low | **not**: 15–30 dB low |
| Early density 0–60 ms | **not**: sparse | **not**: sparse |
| Missing back-wall (−Z) reflection | missing | missing |
| t=0 pre-echo | present, −20 to −33 dB | present, −7.5 to −21 dB |

## 5. Ranked improvements (for Grok Build; each can be tested with `compare.py`)

1. **Ship the F2 tail fix.** This is the largest single gain: C80 goes from +15 dB error to about 1 dB, EDT from 0.29 s to 1.96 s, and T30 from +50 % to ≈0 %. The risk is low because it is already in `engine/work`.
2. **Remove the t=0 pre-echo.** Take the line output after the delay only, or delay the allpass feed-forward term to the line's tap time. This is one-line territory in `fdn.py` and `fdn_core.c`, and must be mirrored in C/WASM.
3. **Frequency-dependent decay.** Add a per-line in-loop shelf or low-order absorption filter per line (Jot-style) whose target T60(f) comes from surface α with Eyring (optionally Sabine or Arau-Puchades) plus air. Keep the dial as a global scale or override. On CR2 this removes the +5 to +14 JND errors at 125 Hz and 4–8 kHz. The tail needs about 3 dB less 8 kHz energy.
4. **Early-reflection level law and direct level.** Add a "physical" option with 1/r amplitude and a distance-scaled direct (1/r relative to a reference, replacing the fixed ×0.55), and exclude the FDN n=0 line from the direct when that mode is on. Keep "2011 (1/r²)" as the faithful default. Expected effect: first-order images move from −15…−30 dB to about −2…−12 dB relative to the direct, matching the measured −5…−9 dB.
5. **Full first-order set.** Include −Z (the back wall) and ±2W, or grow the table to cover all six first-order walls plus a second-order set. This fixes the missing D-wall reflection (measured −8.9 dB relative to direct, absent in the model).
6. **Early density and scattering.** Add a short scattered early component (e.g. per-image diffusion taps or a low-order velvet-noise cluster scaled by the surface `diffusion` field). The measured 8–60 ms field sits at −5 to −15 dB and is dense.
7. **c from temperature.** Use c = 331.3 + 0.606·T. The effect is small (≤0.2 ms here) but costs nothing.
8. **DRR/level calibration check.** After items 1–4, re-run `compare.py` and tune the default inject scaling so that late over direct at 1 kHz stays within ±2 dB of measured for this room (measured +13.3 dB; fix_oracle +3.3 dB with direct = spike + n=0 line).

## 6. Caveats
- CR2 is a real furnished room, not an empty box. BRAS flags CR rooms as uncertain. The geometry and material layout are **ESTIMATED/ASSUMED**, and the ceiling is set from the volume.
- The source is a dodecahedron, which is not omni above about 4 kHz and has a smeared direct. Per-IR direct-peak scatter is up to ±30 samples. Measured first-order levels are therefore ±3 dB at best, and the 125/250 Hz direct-window numbers are unreliable.
- Only the Render (Python) path was tested, not the Play (C/WASM) path, and only with the centre omni and colour bypassed.
- The oracle variants use the measured T20 as the dial, a best case. Real users will dial by ear or from a material estimate (the Eyring variants).
- The simplified Lundeby is only applied to the measured data; model IRs are noise-free.

## 7. Suggested next scenes (not done)
- **BRAS RS1–RS6** (single reflection on reflector/absorber, diffraction). They would isolate the per-hit surface filter against measured α(f). They need the Genelec directivity (in BRAS) and the absorber geometry.
- **Other open RIR sets with documented geometry:** not checked in this pass, so I make no claims about them or their licences.

## 8. Licence notes (BRAS)
- BRAS v3 and its GRAS predecessor are **CC BY-SA 4.0**. **VERIFIED** from the DepositOnce record `dc.rights.uri` and the SOFA `License` attribute.
- The plots and the per-band numbers in this report are derived from BRAS data (adapted material). If they are published (blog, repo, paper):
  - credit BRAS (Aspöck, Brinkmann, Ackermann, Weinzierl, Vorländer; doi:10.14279/depositonce-6726.3)
  - state that changes were made
  - release the plots and derived tables under **CC BY-SA 4.0** (share-alike)
- Our code (`*.py`) does not contain BRAS data and can keep its own licence. That is **ASSUMED**: CC BY-SA covers the data and its adaptations, not independent analysis code.
- Do **not** re-host the raw BRAS files. Point to the DOI and `fetch_bras.sh` instead (redistribution is allowed under BY-SA, but it is unnecessary and bloats the repo).
- Do not present the CR2 comparison as a strict validation, per the BRAS authors' own warning.

## 9. Files
- `bras_cr2.py`: BRAS constants and loaders
- `fetch_bras.sh`: download script
- `analysis.py`: ISO 3382-style parameters
- `fit_geometry.py` and `geometry_fit.json`: wall fit from arrivals
- `scene.py`: model mapping, material layout, Eyring
- `render_all.py`: 50 renders into `/workspace/rv_work`
- `ism_baseline.py`: physical specular ISM
- `compare.py`: all numbers and plots
- `results/`:
  - `cr2_octave_table.md` and `cr2_octave_summary.json`
  - `cr2_error_jnd.md` and `cr2_error_jnd.json`
  - `cr2_first_order_by_wall.md` and `cr2_first_order.json`
  - `compare_stdout.txt` and `fit_geometry_stdout.txt`
- `plots/*.png`
