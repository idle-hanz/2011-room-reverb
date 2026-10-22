# Play (C/WASM) vs Render (Python) parity

## Method (VERIFIED)
- Scene P1: std room, decay lock 1.8 s, humidity 0.5, early/direct/FDN wet all 1, 48 kHz, colour off (BYPASS) and on (MEASURED_SHELF).
- Play IRs: the shipped wasm through the real worklet packer (`tools/wasm_run.js ir`).
- Render IRs: `render()` with a 1-sample impulse, `norm_scale` undone (`tools/render_ir.py`), 3 s.
- Metrics: `tools/parity.py`. Stored in `work/parity_P1_orig.json`, `parity_P1_fix_z1.json` (F1–F3) and `parity_P1_fix_same.json` (F1–F3 + F5).

## Results

| Metric | Current | After F1–F3 | After F1–F3 + F5 |
|---|---|---|---|
| Direct timing | 459 = 459 smp | same | same |
| Direct level | **−3.35 dB** (energy −2.5) | 0.00 dB | 0.00 dB |
| Early energy 0–80 ms | **+3.3 dB** | +4.5 dB | +4.5 dB |
| Early per-peak level (median \|Δ\|) | 5.1 dB | 5.9 dB | 5.9 dB |
| Early timing | mostly 0–0.33 ms, worst 1.75 ms, 4 sign flips | same | same |
| Tail T30 500 Hz–8 kHz | **Play 2.1–5.8 s vs Render 0.8–2.9 s** (Render truncated/long) | within ~10 % | equal |
| Tail octave balance | +2…+5 dB at 1–4 kHz, −8.5 dB at 16 kHz | ±4–5 dB (e.g. 125 Hz +5.2, 1 kHz +4.2) | equal |
| Tail level 80 ms–1 s | – | **−5.8 dB** | 0.0 dB |
| Stereo tail correlation | **0.66 vs 0.32** | 0.58 vs 0.35 | 0.35 vs 0.35 |
| FDN-only null (Play vs Render) | +0.8 dB (a different network) | +1.4 dB | **−47.5 / −48.3 dB** |

Every row is VERIFIED from the stored metrics or from test pack runs. Colour on gives the same conclusions.

## Divergence list

| # | Divergence | Cause (code) | Severity | Fix |
|---|---|---|---|---|
| D1 | Tail 1.5–6× too long, level and balance off | Dffs self-loops ignored by the decay lock (`structure_gain_for_rt60`); see bug_tail_length.md. Render is also affected. | **High** | F2 (both engines) |
| D2 | Play HF tail too short once D1 is fixed; direct −3.35 dB | Delays rounded at 44.1 kHz (`live_fdn_params`, `render_pipeline.py` 1347ff) and read fractionally at 48 kHz (`read_lane` 833) | **High** | F3 |
| D3 | Different network: z⁻¹ between Hadamard and allpass in Play; Render solves same-sample. `loop_mix` is shipped but unused by C | `diffuse()` `live_stereo.c` 948; `_attach_loop_mix` `render_pipeline.py` 1337/1552 | **Medium-high** (tail colour, stereo correlation, near-Nyquist mode, positive-Dffs instability) | F5 (consume M = `loop_mix`, or build it in C as in the diff) |
| D4 | Early field: level ±5–10 dB per reflection, +3–4.5 dB energy, sign flips, ≤1.75 ms shifts | Play early taps have no serial per-hit surface cascade and no Δd jitter/allpass diffusion (known gap) | **High** for sound; out of scope here | Track A (Surfaces materials) should bring the per-hit cascade into C. t13 reports this as XFAIL. |
| D5 | Play N fixed at 32 | `n_had = 32` (`render_pipeline.py` 1363); Render uses `hadamard_n` | Medium (only when N ≠ 32) | Pass `hadamard_n` through, C sized for N ≤ 128 or gate it. t17 is PENDING. |
| D6 | One "diffusion" surface key drives both diffusion layers | `tap_dff` reads `card["diffusion"]` (`render_pipeline.py` 494) and the Δd jitter reads the same key (`surface_colour.py` 344) | Medium, **violates a product lock** | Add a separate key (e.g. `dd_jitter`/`surface_scatter`) for Δd, keep `diffusion` → Dffs, and migrate presets. t16 is PENDING. |
| D7 | Filter corner frequencies ×1.088 in Play | Air/shelf/peaking coefficients designed at 44.1 kHz, run at 48 kHz | Low-medium | F4 |
| D8 | Render IR truncated at `ir_length_ms` (default 1500 ms) | `render_pipeline.py` 918–919, 1373 | Medium for long dials | Make length ≥ 1.5×T60 when the decay lock is on (recommendation, ASSUMED desirable) |
| D9 | Decay-lock delay set: Render uses "mean"-channel delays, Play the "c" channel | `render_pipeline.py` 1447–1451 vs 1014/1147 | Low (irrelevant once F2 is in, since lg is per line) | Unify when convenient |
| D10 | Tail +5.8 dB louder after F5 (matches Render) → hot input peaks 0.997 | Makeup computed for the old z⁻¹ network | Low-medium | Re-check makeup / headroom after F5 (t14) |
| D11 | Dffs sign not clamped server-side | `app_server.py` 342 `diffusion_master` unclamped | Low (UI can't reach it) | Clamp |

Locks respected by all the fixes: the unscaled ±1 Hadamard stays (F2 only moves the loss into per-line gains; the Hadamard runs at g = 1/√N); early images still excite the FDN; 1/r² unchanged; air placement unchanged (F2 is loss on lane reads, not "air on the FDN return"); the two diffusion layers are kept (D6 recommends splitting them further).
