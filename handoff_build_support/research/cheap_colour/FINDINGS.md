# Cheaper mic colour: findings

Written 27 Sep 2026 (BST). Box measurements: node + the real `fdn_worklet.js` + `live_stereo.wasm` built with `zig cc -O3 -msimd128`. Nothing in `software\` was changed. The patched trees live in `research/cheap_colour/work/`.

Tags: **VERIFIED** = measured here or read in code. **ASSUMED** = judgement or estimate.

## Recommendation

**Replace the Play colour FIR (partitioned FFT convolution) with a K = 3 biquad cascade (low shelf + 2 high shelves, RBJ, minimum phase) per colour entry.** Fit the coefficients from the mic preset via a per-mic **w-table**. Add the manufacturer HPF as exact Butterworth sections. Non-uniform partitioned convolution and hybrids are not needed.

| | FIR (today) | SOS K = 3 | SOS K = 4 |
|---|---|---|---|
| Play CPU, 1 source, snapshot tree | **1.158 ms** (43.4% of 2.667) | **0.577 ms** (21.6%) | 0.635 ms (23.8%) |
| Play CPU, 2 sources, snapshot tree | 1.385 ms (51.9%) | 0.863 ms (32.4%) | 0.909 ms (34.1%) |
| Play CPU, 1 source, F1–F3+F5 tree | 1.396 ms (52.3%) | 0.863 ms (32.4%) | 0.877 ms (32.9%) |
| Play CPU, 2 sources, F1–F3+F5 tree | 1.839 ms (69.0%) | 1.318 ms (49.4%) | 1.343 ms (50.4%) |
| Colour share of the block (1 src snapshot, colour off = 0.496 ms) | 0.662 ms (57%) | **0.081 ms (−88%)** | 0.139 ms |
| dB error vs current FIR, 20 mics × 5…180° (direct fit) | — | max 0.46, p95 0.25, median 0.09 dB | max 0.24, p95 0.18 dB |
| dB error vs current FIR, **w-table (production path)**, 20 mics × 1…180° at 1° | — | **max 0.46 dB, p95 0.24, median of per-mic max 0.17 dB** | — |
| Play render null (SOS − FIR), 3 scenes | — | **−47.7 … −48.5 dB** (colour effect itself −11.9 … −14.7 dB) | −55 … −58 dB |
| Octave-band energy difference, Play render | — | ≤ 0.03 dB | ≤ 0.02 dB |

All VERIFIED (box measurements). The CPU figures are the median of 3 runs each (3 s noise). The run-to-run spread is about ±5–10%.

## 1. How colour works today (VERIFIED, code read)

- **Render:** `_colour_apply` per image tap and ear (`render_pipeline.py`) uses the mic model `relative_db(model, f, θ)`. That is a dual shelf + soft pole whose angle dependence goes only through **w = ½(1 − cos θ)^p** (`mic_colour/model.py`, from `mic_fitter`). `mic_colour/design.py::design_ir` turns that dB curve into a **minimum-phase FIR** (cepstral method).
- **Play:** `mic_colour/live_bank.py` builds a bank of these FIRs per angle bucket, and `app_server.live_fdn_params` packs them into the blob. `live_stereo.c` runs **uniformly partitioned FFT convolution** per `Filt` (MAX_FILT 112, per capsule and early line/bus): `design_ir()` pre-FFTs partitions, and `run_fir()` does a 128-block FFT, a multiply-accumulate over partitions, and an IFFT.
- Colour is about 57% of a 1-source block in the snapshot tree (0.662 of 1.158 ms, VERIFIED here). This matches the brief's "~60%".

## 2. Options evaluated

| Option | Verdict | Why |
|---|---|---|
| **IIR biquad cascade per colour entry** (K = 2/3/4) | **Chosen, K = 3** | The model *is* a few shelves and a pole, so it is naturally low-order. K = 3 costs 15 mult/sample per filter against FFT work per block. |
| Truncated FIR (512 / 1024 taps) | Rejected | Max error 1.14 / 1.13 dB (median 0.24 / 0.22) is worse than K = 3, and it is still FFT-bound. |
| Non-uniform partitioned convolution | Not needed | It cuts latency-driven cost for long FIRs, but even an ideal NUPC still does FFTs per filter per block. The SOS path gets colour down to 0.08 ms, which leaves nothing worth optimising. (Not benchmarked: the analysis is by operation count, ASSUMED.) |
| Hybrid (SOS + short FIR residual) | Not needed | The residual is ≤ 0.46 dB. That is well below the preset's own fit error to the measured mics (the mic_fitter rmse is dB-scale). |
| **Per-image angle-dependent part** | Covered by the w-table | Each image/line has its own θ, so w maps to table parameters, then RBJ coefficients (a few flops at scene change). |

### Accuracy detail (direct per-angle fit vs the current 4096-tap FIR, 20–20 kHz, 600 log points; `results/accuracy.json`)

| | max of max | p95 of max | median of max | worst rms |
|---|---|---|---|---|
| FIR vs analytic model | 0.32 | 0.25 | 0.07 | 0.07 |
| SOS K = 2 | 1.04 | 0.80 | 0.25 | 0.35 |
| **SOS K = 3** | **0.46** | **0.25** | **0.09** | **0.10** |
| SOS K = 4 | 0.24 | 0.18 | 0.06 | 0.07 |
| FIR 1024 taps | 1.13 | 0.80 | 0.22 | 0.20 |
| FIR 512 taps | 1.14 | 0.78 | 0.24 | 0.36 |

Fit time: about 60 ms per angle (K = 3, scipy least squares). That is too slow to do per image at runtime, hence the w-table.

### W-table (production design; `tools/wtable_study.py`, `results/wtable_48000.json`, `results/wtable_params_48000.json`)

- One table per mic: parameters (log2 f, gain dB, log2 Q) for 3 sections, on a w-grid starting at 65 uniform nodes, warm-started. It adds a continuity repair and **adaptive bisection** where the midpoint misses the model by > 0.2 dB (the fitter can jump branches near a shelf-gain sign change). The grid ends up with 65–160 nodes per mic. Build time is 3–19 s per mic (mean 8.4 s), so **build offline** and ship the tables (288 KB JSON for 20 mics).
- Runtime: w → binary search → linear interpolation of the parameters → RBJ coefficients.
- Result over 20 mics × 180 angles: **max 0.46 dB** (NeumannU87AiOmni, ShureSM57), p95 0.24 dB. Before the bisection step, two mics had isolated 0.7–1.4 dB spikes (SM57 at 100°, Schoeps CMC5U Omni at 50°). After it, the spikes were gone (0.46 and 0.06 dB).
- **Sample rate:** the tables were built at 48 kHz. The parameters are sample-rate independent (Hz, dB, Q), so at 44.1 kHz the same table gives RBJ coefficients. Near-Nyquist cramping differences are **ASSUMED** small. See acceptance test AT-C4.

### HPF finding (a current-FIR accuracy bug)

With the manufacturer HPF engaged (7 mic families: AKG C414 ×4, U87Ai ×3, NT2-A ×3), the **current FIR misses its own analytic target by 14.5–23 dB below 100 Hz and by 5.9–7.5 dB above 100 Hz** (at 90°; `hpf_90deg` in `results/wtable_48000.json`). The cause is **ASSUMED** to be time-aliasing in the cepstral minimum-phase design (FFT length vs a deep LF notch). SOS K = 3 plus exact Butterworth HPF sections matches the analytic target within **0.03–0.17 dB**. So the SOS path fixes this rather than inheriting it. (Whether Play currently sends `hpf_engaged` is not checked here.)

## 3. Play patch (proof of concept, VERIFIED to build and run)

`diffs/live_stereo.sos_colour.diff` (it applies cleanly to both the snapshot tree and `engine/work/sw_fix_same`; also `tools/patch_sos.py`):
- A colour entry whose float payload starts with the magic **−2011** is read as `[−2011, K, (b0 b1 b2 a1 a2) × K]`. K ≤ `MAX_SOS` = 6, which leaves room for K = 3 + 2 HPF sections. `design_ir()` dispatches to `design_sos()`, and `run_fir()` dispatches to `run_sos()` (TDF-II, double state per Filt, zeroed in `zero_filts`). Old FIR blobs behave exactly as before.
- `tools/sosify_params.py` replaces the FIRs in a params JSON with direct-fit SOS records. This was used for the null and bench runs. Production should use the w-table packer (brief).

## 4. Sample-0 click check in Play (steering request)

room_validation found a t = 0 click in the FDN diffuser in Render (`fdn.py process_block_poly` `y = −gi·x + v`: the Schroeder allpass feed-forward term, zero delay). **Play has it too** (VERIFIED from the Play IRs rendered by this harness and by compare_ref). The first output sample is non-zero while the direct sound arrives at sample 459 (9.6 ms):

| Scene / tree | x[0] (L+R)/2 | re direct peak |
|---|---|---|
| default lock-18 scene, snapshot, FIR colour | −0.018 | −32.4 dB |
| same, SOS colour | −0.018 | −32.4 dB (colour-independent) |
| same, colour off | −0.029 | −29.7 dB |
| unlocked scene, colour off | −0.063 | −24.0 dB |
| compare_ref stand-in scene (GainF 1, DM −0.5, early off; TS4 sidecar), `play_current` | −0.368 | **−7.7 dB** |
| same, `play_F1-F3` | −0.368 | −8.7 dB |
| same, `play_F1-F3+F5` | −0.302 | −10.4 dB |
| same, `render_current` | −0.268 | −12.9 dB |

- The click lands **before** the direct sound (a pre-echo), and it scales with Dffs (the Diffusion Master and surface Diffusion). It is present in every tree, so F1–F3/F5 do not remove it. The form is the same in `live_stereo.c` (around line 956).
- The 2011 Diffuser Delay has the same allpass structure (**ASSUMED** from the Structure notes), so the original may have had this click too. `compare_ref.py` reports `zero_time_db_re_direct` for the reference captures, so Idle's captures will show whether 2011 had it. **Recommendation:** don't "fix" it until a capture shows 2011 did not have it. If it has to go, the cheapest fix is to feed the diffuser from after the minimum line/pre-delay, so the feed-forward term lands at or after the direct sound, not at t = 0.
- The cheap Play check is now built in. `rr_metrics.zero_time_db_re_direct` runs on every Play/Render IR in `compare_ref.py`. A standalone one-liner is in the brief (AT-C6).

## 5. CPU budget for the full roadmap (per 128-sample block, 2.667 ms at 48 kHz)

Deltas are from the roadmap's P4/P5/P6 figures (BRIEF/ASSUMED there). The colour saving is measured here.

| Configuration | FIR colour | SOS K = 3 colour |
|---|---|---|
| Measured today, snapshot, 2 src | 1.385 ms | 0.863 ms (−0.52) |
| Measured, F1–F3+F5 tree, 2 src | 1.839 ms | 1.318 ms (−0.52) |
| Roadmap "P4 + P5 scatter + P6 source radiation, 2 src" (roadmap: 2.4–2.5 ms, 90–94%, ASSUMED) | 2.4–2.5 | **≈ 1.9–2.0 ms (71–75%)** |
| Same, but adding the F1–F3+F5 overhead measured here (+0.45 ms at 2 src, +0.28 at 1 src, colour off 0.73 → 1.20 ms) if the roadmap baseline did not include it | ≈ 2.85–2.95 (over budget) | **≈ 2.35–2.45 ms (88–92%)** |

- **The colour switch alone takes the full roadmap back under the 80% comfort line only if the engine-fix overhead is also dealt with.** VERIFIED observation: the F1–F3+F5 tree costs +0.28 ms (1 src) and +0.46 ms (2 src) more than the snapshot even with colour **off**. Its cause (F5's same-sample solve, or F2 per-line loss) was not investigated here. Flag it to the engine worker. The shed order in the roadmap still applies.
- Remaining big levers after SOS colour (ASSUMED): scatter K (the brief's K = 8 vs 16) and the F5 overhead.

## 6. Files

- `FINDINGS.md` (this file) and `GROK_BUILD_BRIEF_Cheap_colour.md`.
- `diffs/live_stereo.sos_colour.diff`.
- `tools/`: `sos_fit.py` (RBJ fitter), `accuracy_study.py`, `wtable_study.py`, `sosify_params.py`, `null_test.py`, `bench_colour.py`, `patch_sos.py`.
- `results/`: `accuracy.json`, `wtable_48000.json`, `wtable_params_48000.json` (the prototype table, schema `colour_sos_wtable.v0`), `bench_wasm.json`, `null_tests.jsonl`.
- `work/`: patched trees (`sw_sos` = snapshot + patch, `sw_same_sos` = F1–F3+F5 + patch) with built wasm. Box only.
