# Package 6: SOS colour per sample rate (decision 7, locked 28 Sep 2026)

**Decision:**
- Separate SOS tables for 44.1 kHz and 48 kHz. This fixes the U87 / NT2A omni at 44.1k.
- Any other rate turns colour **off with a visible UI notice**, never silently.
- Render speed-up (scipy `sosfilt` or a vectorised numpy path) and the 64-entry two-source limit are **Build's call**. The recommendations are below.

**Implemented in** `4_engine_fix_patches/patches/08_colour_per_rate.diff`. The tested tree is `work/p5/software`.

## What changed (VERIFIED on p5)

| File | Change |
|---|---|
| `mic_colour/sos_tables/44100/<mic>.json` (20 new files) | Fitted at 44.1 kHz with the same fitter and w-grid. They were written with Build's own `sos_table.write_v1_from_v0(src, dest)`, schema v1, `fit_fs` 44100, same `preset_hash`. The 48 kHz tables at `sos_tables/<mic>.json` are unchanged. |
| `mic_colour/sos_table.py` | `SUPPORTED_RATES = (44100, 48000)`, `rate_supported()`, `unsupported_rate_notice()`. `tables_dir(sr)` points to the 44100 subdir for 44.1k and the top level for 48k. `_load_one(mic, sr=48000)` caches per (mic, rate) and rejects a table whose `fit_fs` ≠ rate. `pack_for` loads the table for its rate. The signature is backward compatible. |
| `mic_colour/colour.py` | `MicColour.notice`. With SOS impl at an unsupported rate, `measured = False` and the notice explains why. The FIR impl (`colour_impl: "fir"`) is unchanged: it designs at any rate. |
| `mic_colour/live_bank.py` | The colour payload carries `notice` when set (`on: false`). |
| `render_pipeline.py` | Render `info["colour_notice"]` on all three render paths and in `live_fdn_params`. |
| `app_server.py` | The `/api/render` status text gets the notice line. |
| `static/js/live_fdn.js` | `colourNotice()` runs on every `takeColour()`. It shows the server notice, or a local "bank is for X Hz but the device runs at Y Hz" message, through the existing `status()` line. It shows each distinct message once. |
| Build's `tests/test_mic_colour_relative.py` | Two unit tests ran at 8 kHz and 16 kHz, where colour is now off by design. They were moved to 48 kHz (documented in the diff). |

## Accuracy (VERIFIED; fitter model vs SOS, 20 mics × 7 angles, f < 0.45·fs)

| Rate | Before (48k parameters reused) | After (per-rate tables) |
|---|---|---|
| 48 kHz | worst 0.461 dB (U87 Omni @180°) | **unchanged** (same tables): 0.461 dB, AT-C1 ≤ 0.5 PASS |
| 44.1 kHz | worst **0.692 dB** (U87 Omni @180°); NT2A Omni 0.62 → AT-C4 FAIL | worst **0.408 dB** (U87 Omni @180°); NT2A Omni 0.188 dB → **AT-C4 ≤ 0.6 PASS** |
| 32 / 88.2 / 96 kHz | 48k parameters reused, up to 2.1 dB off | **colour off + notice** (tests pass: `test_colour_unsupported_rate_disabled_with_notice[32000/88200/96000]`) |

- **Reproducibility:** re-running the same tool at 48 kHz (`results/wtable_params_48000_refit.json`) reproduces Build's shipped 48k tables exactly: max parameter difference 0 over all 20 mics (VERIFIED). So the 44.1k tables come from the identical procedure.
- **Fit logs:** `results/fit_44100.log` gives the max fit error per mic at 44.1k: 0.098–0.472 dB, and at most 0.104 dB rms (U87 Omni).
- **HPF-on low end at 44.1k:** within 0.5 dB of model+HPF below 100 Hz (`test_colour_hpf_on_low_end[44100]` PASS). Stable poles at 44.1k/48k.

## Render speed (recommendation: Build's call)

Build's Render uses a per-sample Python loop (`mic_colour/sos_fit.py:123-142`).

Benchmark (VERIFIED, `tools/bench_apply_sos.py`, 5 s of noise at 48 kHz, one colour filter; `results/bench_apply_sos.log`):

| Filter | Build loop | numpy (closed-form IR + FFT) | scipy `sosfilt` |
|---|---|---|---|
| SM57 @90°, 3 sections | 0.277 s | 0.020 s (**14×**), max abs err 4.5e-13 | 0.0024 s (**115×**), bit-identical |
| U87 Omni @180°, 3 sections | 0.273 s | 0.015 s (18×), err 1.5e-14 | 0.0018 s (150×), identical |
| C414 Cardioid @120° + HPF, 4 sections | 0.361 s | 0.016 s (22×), err 6.2e-14 | 0.0020 s (180×), identical |

- **Option A: scipy `sosfilt`.**
  - Build's own tests currently **assert scipy is absent** (`tests/test_mic_colour_relative.py:34-36`, `469`, `587`), and scipy is not in requirements (package 3 `test_p0_5_scipy_in_requirements`).
  - Adopting it means adding scipy to requirements and changing those 3 asserts. The packaged app (PyInstaller) grows by roughly the scipy wheel (ASSUMED, not measured).
  - Remap the coefficients: `sosfilt(np.c_[sos[:, :3], ones, sos[:, 3:]], x)`.
- **Option B: numpy only** (`tools/apply_sos_fast.py`, drop-in `apply_sos_numpy(buf, sos)`).
  - Each biquad's IR is `h[0] = b0, h[n] = A·p1ⁿ + B·p2ⁿ`, from its poles and residues.
  - The cascade IR is truncated at −200 dB of the slowest pole (`tol_db`), then applied by one FFT convolution.
  - Repeated or near-repeated poles (|p1 − p2| < 1e-7) fall back to the exact recurrence for that section's IR only.
  - Matches the loop to ≤ 1e-9 (package 3 `test_colour_numpy_sos_matches_loop`).
  - Costs one FFT per call; memory is O(len(x)).
  - No new dependency. The existing scipy-absent asserts keep passing.
- **Recommendation (ASSUMED):** B if the no-scipy rule is deliberate; otherwise A.

## Two sources, 64-entry Play bank (Build's call; unchanged)

- `test_colour_play_bank_fits_two_sources_apart` still FAILs on p5: 90 entries > `MAX_IRS` 64 (`live_stereo.c:55`). Play colour switches off with two sources placed apart.
- The new notice path does **not** cover this case: the worklet refuses the bank.
- Options:
  - (a) raise `MAX_IRS` to 128. Memory is `MAX_IRS × MAX_SOS × 5` floats plus the FIR slab, which is small for SOS (ASSUMED).
  - (b) quantise angles more coarsely.
  - (c) share entries between A and B.
- Whichever is chosen, add a `status()` notice when the worklet rejects a bank.

## Files

- `tools/wtable_study.py`, `tools/sos_fit.py`: the prototype fitter from build_support (`RR_SW`, `OUT_DIR`, `OUT_SUFFIX` env).
- `tools/apply_sos_fast.py`: the numpy alternative.
- `tools/bench_apply_sos.py`: the benchmark.
- `results/`: fit logs and JSON (44.1k tables + 48k refit) and the benchmark log.
