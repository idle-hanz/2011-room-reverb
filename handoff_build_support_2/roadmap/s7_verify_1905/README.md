# S7 verification (snapshot_2026-10-02_1905), 2 Oct 2026 19:05–19:50 BST

Box only. The PC was read-only and the app was not restarted. Build's report (t323u) was not readable here; every number is our own box measurement (VERIFIED) unless marked ASSUMED.

## Files
- `s7_measure.py` → `data/s7_measure.json` / `.log`: Play 1905 vs Render 1905 / Render 1815 (pre-S7) / research prototype `research_f5_allpass/sw/R_z1`, five scenes × colour on (col) and Bypass (byp), FDN bus only, 3 s IRs, tail = 80 ms–1 s energy.
- `t19/`: the t19 CPU investigation.
  - `t19_check.py exact` → `exact.json`: the candidate wasm builds are bit-exact (max |diff| 0.0) to the shipped wasm, shared tail off and on.
  - `bench2.py` + `bench_blocks.js` (a copy of the harness `wasm_run.js` that also returns per-block times) → `bench2_1944.json`, `bench2_1944_blocks.npz`: 14 alternating rounds, t19 scene, one tree (1905), four wasm files.
  - `denorm.py` → `denorm.json`: `NOGUARD.wasm` (1905 source with `LS_DC = LS_TINY = 0`) vs the shipped wasm, to see whether median scoring still catches a real denormal climb.
  - `F1_hoist.patch`, `F2_cold_shared_fields.patch`: optional Play micro-fixes, bit-exact; parked (see below).
  - `t19_ab_pc.py`: same-minute A/B for the PC (`python t19_ab_pc.py <software> <harness> 8 ship=ship pre=ship_1630_bbb23260.wasm`).
  - `ship_1630_bbb23260.wasm` = wasm sha1 08a95563546d (16:30, pre shared tail). The shipped 1815/1905 wasm is sha1 69eb8b3bca4c (md5 6188c78c).

## Results (all VERIFIED on the box unless marked)

**1. Render z⁻¹ loop: correct.**
- `fdn.py` Dffs branch: `sv = inj + hy; yv = reads − dffs·sv; hy = g·(H@yv); buf = s + gi·yv`. `_hy` is set to zero in `__init__`; there is no reset method, and the buffers are reset only by constructing a new object. `LOOP_SEMANTICS = "z1_both"`. Render takes the F3 −1.70 dB trim (`render_pipeline.py:676`).
- Measured:

| scene | Play − Render null (L/R dB) | Render 1905 vs R_z1 × trim | Render 1905 − 1815 tail (col / byp dB) |
|---|---|---|---|
| default | −72.3/−72.0 (col), −72.7/−72.6 (byp) | −149 dB (bit-equal in float) | −3.14 / −3.50 |
| default, no Dffs | −70.2/−70.1, −70.9/−71.1 | −149 | −1.70 / −1.70 (= 1815 × trim, −149 dB null) |
| default, reaktor_parity | −72.8/−71.9 (col) | +2.3 (expected: R_z1 has H·D ungated by parity; 1905 uses plain H under parity, as 1815 did) | −3.07 (col) |
| big room 57×34×97 | −64.9/−64.2, −66.2/−65.9 | −150 / −147…−153 | −1.71 / −1.70 |
| Hall preset (parity) | −61.5/−62.0, −62.7/−63.2 | −12 / −11 (parity H, as above) | −1.55 / −1.56 |

- Play and Render tail levels are equal to 0.01 dB in every case, and the t13-like band balance and T30 ratios are 1.00.

**2. Default tail delta −3.34 (Build) vs −3.1 (estimate).** Measured: −3.14 dB with colour on and −3.50 dB in Bypass. These are −1.70 trim + D3 alone (−1.44 col / −1.80 byp), matching `research_f5_allpass` §4.3 exactly. Build's −3.34 lies between the two. ASSUMED: a different window or colour mode (the mean of the two is −3.32). Not a defect.

**3. Binaural Render.** `render_binaural_fdn_ir` has zero callers. Build's 19:19 edit applies `loop_level_trim_lin("render", False)` (F3 only; F2 off because the function has no line_t60). Fine and harmless; goldens are unaffected.

**4. colour-parity failure.** A stale needle. The shared-tail edit (17:53) renamed `line->inj` to `injUse` at `live_stereo.c:1703-1708` (B side 1726-1731). Build's 19:19 test edit accepts both strings. We recommend asserting only the new strings, since the old one no longer exists.

**5. t19.**
- Wasm sha1 08a95563546d is 16:30 (pre shared tail); 69eb8b3bca4c is 1815/1840/1905.
- 14 alternating rounds on the box, one tree, t19 scene. The box was loaded (another worker ran 6 node jobs).

| wasm | median of per-run medians (ms) | paired median vs 08a9 | p10 paired | per-run mean range |
|---|---|---|---|---|
| 08a9 (16:30) | 1.983 | — | — | 1.99–3.11 |
| 69eb (shipped now) | 1.945 | −2.1 % | −1.8 % | 1.94–3.25 |
| 69eb source rebuilt with zig 0.16 | 1.904 | −4.2 % | −2.7 % | 1.95–3.13 |
| F2 (rebuilt + cold shared fields + hoist) | 1.871 | −5.4 % | −4.3 % (−2.4 % / −1.8 % vs rebuilt) | 1.88–3.05 |

- The flag branches have no measurable cost; the shared-tail build is not slower.
- Spikes over 3× the median are 0.5–4.7 % of play blocks (up to 12 %). They inflate the run mean by 3–11 % (median) and up to 26 %.
- Build's PC numbers (ASSUMED, as quoted): identical bytes read 2.09–2.10 and later 2.15–2.16, a 3 % drift with no code change. That is the same size as the "2.03 → 2.10" step.
- The variance argument is sound.
- `std_lock18` runs three tanks (`mic_gain_c` 1.0, non-zero centre injects); VERIFIED in the packed params.
- Median scoring and denormals (`denorm.json`):

| case | late-silence ÷ play, mean | late-silence ÷ play, median |
|---|---|---|
| guarded 0.3 s | 0.97 / 0.97 | 0.97 / 0.97 |
| guarded 1.8 s byp | **1.34** (would fail the t09 mean rule) | 1.07 |
| guarded 1.8 s col | 1.13 | 0.96 |
| no guard 0.3 s byp / col | 2.28 / 2.20 | 2.48 / 2.12 |
| no guard 1.8 s byp / col | 1.44 / 1.50 | 1.42 / 1.83 |

  A real denormal climb is sustained (the per-second medians stay at about 2×), so the median catches it, and it removes the spike false alarm.
- Recommendation: score CPU tests by the median (harness only; prompt in `S7_FOLLOWUP_PROMPT.md`). Park F2 (bit-exact, about 2 %) for S5.
