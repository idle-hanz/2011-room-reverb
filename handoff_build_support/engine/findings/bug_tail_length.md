# Bug 2: tail runs far longer than dialled, plus a slow 9/11 kHz residue

Snapshot: `/workspace/build_support/snapshot_2026-09-27/software`. The line numbers below refer to that snapshot. Harnesses are in `tools/` (native build and wasm-in-node Play; `render_ir.py` for Render). Analysis: Schroeder EDC, T30 per octave (`analyze.py`, `tail_report.py`), and "late T60" = slope of the band EDC well after onset (`edc_profile.py`).

## Symptom (VERIFIED)

Play, FDN only, std room, decay lock at 1.8 s:

| Band | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 11k | broadband |
|---|---|---|---|---|---|---|---|---|---|
| T30 current (s) | 1.22 | 2.22 | 3.65 | 5.3 | 7.59 | 9.47 | 17.7 | 21.4 | 11.6 |
| T30 after F2+F3 (s) | 1.6* | 1.94 | ~1.8 | ~1.8 | ~1.8 | ~1.8 | ~1.8 | ~1.8 | ~1.8 |

- Current late T60: 22.4 s at 9 kHz and 25.4 s at 11 kHz. That is the "slow 9/11 kHz residue".
- After F2+F3 these are 1.8 and 1.81 s.
- *The 125 Hz figure comes from the in-loop peaking cut. It is intended room colour (ASSUMED).

Sweep, 3 rooms × 3 dials (`findings/t60_sweep_raw.txt`, Play, `fix` = F1+F2+F3):

| Room / dial (s) | current T30 1k / 4k / broadband / late 10k (s) | fixed T30 1k / 4k / broadband / late 10k (s) |
|---|---|---|
| std 0.8 | 5.10 / 6.83 / 5.28 / 4.34 | 0.73 / 0.75 / 0.75 / 0.80 |
| std 1.8 | 5.11 / 8.84 / 6.91 / 9.08 | 1.78 / 1.76 / 1.78 / 1.78 |
| std 4.0 | 7.40 / 12.45 / 10.50 / 23.40 | 3.99 / 3.93 / 3.96 / 4.01 |
| small 0.8 | 2.74 / 5.40 / 3.98 / 7.02 | 0.76 / 0.78 / 0.84 / 0.81 |
| small 1.8 | 3.42 / 7.52 / 5.30 / 8.64 | 1.79 / 1.85 / 1.89 / 1.80 |
| small 4.0 | 5.92 / 11.06 / 7.57 / 12.04 | 4.11 / 4.03 / 4.30 / 4.01 |
| hall 0.8 | 2.55 / 2.32 / 1.97 / 2.07 | 0.76 / 0.73 / 0.75 / 0.79 |
| hall 1.8 | 3.33 / 3.28 / 2.98 / 3.67 | 1.83 / 1.74 / 1.74 / 1.80 |
| hall 4.0 | 5.06 / 4.87 / 4.74 / 5.69 | 3.88 / 4.01 / 4.03 / 4.01 |

- Current code: 1.5–6× over the dial.
- Fixed code: within about ±8 %. The one outlier is 250 Hz in the small room at 4 s, which measured 3.31 s.
- The hall is least affected because its |Dffs| ≤ 0.83. Std has 20 of 32 lines at |Dffs| ≥ 0.9 and small has 25 of 32.

## Root causes

### 1. The in-loop Dffs allpass recirculates on its own and is ignored by the decay lock (main cause, VERIFIED)
- Each line is a Schroeder allpass around its delay. See `diffuse()` at `live_stereo.c` 948–964 and the non-mix path in `bus_sample()` at 966ff.
  - Write: `s + gi*y`, with `y = -gi*s + delayed`.
  - So a sample re-enters its own line with gain `gi`, and back-to-back trips through the same line see gain `gi`, not `g·√N`.
- With `gi = −0.98`, the allpass group delay peaks at (1+|g|)/(1−|g|)·d ≈ 99·d. Energy parks in those self-loops, which gives a two-slope decay with a late T60 of about 6–25 s.
- The decay lock ignores all of this:
  - `structure_gain_for_rt60()` (`engine/fdn.py` 508ff) picks one loop gain `g` so that (g√N)^(t/t_mean) = −60 dB at T60, using the mean delay.
  - It is used in `render_pipeline.py` 1447–1451 (Play), 1014 / 1147 / 1243 (Render), and clamped to 0.99/√N.
- Proof (VERIFIED):
  - Dffs forced to 0 → T30 1.5–2.3 s.
  - Peaking off → no change.
  - Integer delays alone → still long.

### 2. Play line delays are fractional (VERIFIED)
- `live_fdn_params` (`render_pipeline.py` 1347ff) rounds delays in samples at `sr = SAMPLE_RATE_HZ` = 44100 (`engine/early_field.py` 15/51, marked ASSUMED there) and sends them as ms. Play runs at the AudioContext rate of 48 kHz, so every line is fractional.
- `read_lane()` (`live_stereo.c` 833) uses linear interpolation. Inside the loop that acts as a per-trip low-pass. With the tail otherwise fixed, 8 kHz T30 was 0.89 s and 11 kHz 0.68 s against a 1.8 s dial.
- The same interpolated read lowers the direct peak by **3.35 dB** (energy −2.5 dB) compared with Render.

### 3. The 9/11 kHz residue is Play-only (VERIFIED)
- It comes from the z⁻¹ `diffuse()` restructure: the Hadamard output feeds the allpass input one sample later. Combined with the Dffs self-loops, this leaves a near-Nyquist, very slowly decaying mode.
- Render has no specific HF residue. After F2+F3, a small peak near 23.5 kHz is still visible in Play (harmless, above hearing). F5 (same-sample solve) removes it.

### 4. Render has the same long tail but no HF residue (VERIFIED)
- Render, std, lock 1.8: T30 over 500 Hz–11 kHz is 1.75–4.56 s, late T60 about 6.5 s broadband.
- With the Python counterpart of F2: T30 1.57–1.81 s, late 1.8 s.
- Render also truncates its IR at `ir_length_ms` (default 1500 ms, `render_pipeline.py` 836/918–919 and 1373), so a long dial is cut off in Render. Keep that in mind when comparing.

### 5. Positive Dffs is unstable in the current z⁻¹ loop (VERIFIED natively; not reachable from the UI)
- With g√N = 0.99:
  - Dffs +0.98 on all lines grows to 0 dBFS about 40 s after the input stops.
  - Dffs +0.5 grows from −48 to −15.6 dB.
  - Negative Dffs decays.
- The current formula only gives Dffs ≤ 0 while `diffusion_master` = −0.5. But `diffusion_master` is not clamped server-side (`app_server.py` 342, `_f(...)`), so a crafted request could reach positive Dffs.
- Both fixed trees decay at the maximum decay of 8 s. At a T60 of 60 s both show bounded fluctuations (lattice "hidden energy", up to about 14 dB).
- Recommendation: clamp Dffs to [−0.98, 0] server-side and/or adopt F5.

### 6. Other rate mismatch (VERIFIED in code, not patched = F4)
- Air 1-pole, shelf and peaking coefficients are designed at 44.1 kHz and run at 48 kHz, so every corner frequency is shifted ×1.088 in Play.

## Fixes (diffs in `briefs/`)

**F2: per-line absorption (Jot)**
- When the decay lock is on: `lg_i = 10^(−3·d_i/(sr·T60))` on each FDN lane read, and the Hadamard runs lossless at g = 1/√N.
- Every path (Hadamard or allpass self-loop) then loses exactly 60 dB per T60 in proportion to its delay.
- Makeup and `decay_out` keep the old g (`g_decay`), so levels elsewhere don't move.
- Changes by file:
  - C: `Line.lg/lgB`, a new trailing blob float `line_t60` (BLOB_LEN 1981 → 1982; an older 1981-float blob still loads because `rf` reads 0 → off; ASSUMED from reader behaviour), and multiply in `read_peaked`.
  - JS: `fdn_worklet.js` pushes `num(data.line_t60, 0)`. `live_fdn.js` sends it, `WORKLET_VER` 29.
  - Server: `live_fdn_params` returns `g = g_loop`, `g_decay` and `line_t60`.
  - Python Render: `FDN(line_t60=...)`, `reads *= lg`, limit 1/√N when active, C fast path skipped when active. Threaded through `render_fdn_ir`, `combined_ir(line_t60, loop_g)` and the 3 decay-lock branches of `render()`.
- **g must be exactly 1/√N**. Using the old 0.99 clamp together with lg gives T30 of only 1.15–1.3 s at a 1.8 s dial (VERIFIED).

**F3: round Play delays at the Play rate**
- `live_fdn_params` computes delays at `dsr` = the AudioContext rate (`colour_sr_i`, falling back to `sr`), for both buses and bus B.
- This makes delays integer, gives full HF T30, and the direct peak comes back to 0.00 dB vs Render.

**F5 (recommended): same-sample loop solve in Play**
- M = (I + g·diag(dffs)·H)⁻¹, built once per room load. This is what the shipped but unused `loop_mix` is for.
- It is Render's structure. It removes the near-Nyquist peak and makes Play null against Render (−47.5 dB).
- Cost (WASM, node):
  - 1 source + colour: 1.34 → 1.50 ms
  - 2 sources + colour: 1.84 → 2.11 ms (79 % of budget)
  - colour off: 0.58 → 0.81 ms
- A SIMD f32x4 matvec, or skipping the solve when `anyDffs` = 0, should bring the cost back (ASSUMED).

**Dffs clamp:** clamp Dffs to [−0.98, 0] (or clamp `diffusion_master` to [−1, 0]) in `params_from_body`.

**F4 (optional):** design the air, shelf and peaking coefficients at the Play rate.

## Acceptance
- t10 Play T30 within ±15 % of the dial for 3 scenes: snapshot FAIL → sw_fix PASS.
- t11 late 9/11 kHz T60 ≤ 1.25× dial: FAIL (21.7 / 25.0 s) → PASS (1.81 / 1.80).
- t12 Render T30 ±15 %: FAIL → PASS (1.75–1.81).
- t08 stability: FAIL → PASS on both fixed trees.
- **t14 caution:** with F5, Play's tail level rises by 5.8 dB to match Render. Under hot ±0.3 uniform noise the peak reaches 0.997 (soft limiter at 0.95), so t14 FAILs on `sw_fix_same`. Render has the same level, so the fix may need a small makeup or headroom trim (e.g. −3 dB fdn makeup) or a less hot test signal. Build and Idle should decide; the test was deliberately not loosened.
