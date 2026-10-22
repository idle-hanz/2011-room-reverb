# GROK BUILD BRIEF: cheap mic colour (SOS K=3 + w-table)

Written 27 Sep 2026 (BST). Background and numbers: `research/cheap_colour/FINDINGS.md`. Implement when Idle says go. This fits roadmap P7.3 ("colour FIR win"), or pull it forward if P6 goes over 80%.

## Outcome

Play colour cost drops from about 0.66 ms to about 0.08 ms per block (1 source). Play is then ~0.58 ms/block cheaper for 1 source and ~0.52 ms for 2 sources (VERIFIED box bench). The colour response is within 0.46 dB of today's FIR at every mic and angle (VERIFIED w-table study). Render may keep its FIR, or switch for parity (step 5).

## Steps

1. **C engine (Play):** apply `research/cheap_colour/diffs/live_stereo.sos_colour.diff` to `engine/live_stereo.c`. It applies cleanly to the snapshot and to `engine/work/sw_fix_same`. Rebuild the wasm with the usual `zig cc -O3 -msimd128` command.
   - Blob record per colour entry: `float32[] = [-2011, K, b0,b1,b2,a1,a2 (×K)]` (a0 = 1). K ≤ 6. FIR entries are unchanged, so old blobs still work.
   - When the v2 blob lands (roadmap P1), give the SOS records their own typed section instead of the magic-number overload. Keep the TDF-II double-state kernel.
2. **Tables (offline, Python):** productionise `research/cheap_colour/tools/wtable_study.py` as `mic_colour/sos_table.py build`. For each of the 20 mics, write `mic_colour/sos_tables/<mic_id>.json`: `{schema: "colour_sos_wtable.v1", K: 3, layout: ["LS","HS","HS"], w: [...], params: [[log2 f, gain_db, log2 Q] × 3] per node}`, using the same warm start, continuity repair and adaptive bisection (REFINE_DB = 0.2). Also rebuild whenever `mic_fitter` presets change (store the preset hash in the table).
3. **Packer (Python, `mic_colour/live_bank.py` + `app_server.live_fdn_params`):** per colour entry (capsule × angle bucket or line), compute θ → w = angle_weight(θ, p), then binary search and linearly interpolate the parameters, then RBJ biquads (`sos_fit.params_to_sos`). If the preset has an HPF and it is engaged, append exact Butterworth HPF sections (`scipy.signal.butter(order, fc, 'highpass', fs, output='sos')`, order = slope/6). Emit the SOS record. `colour_mode: BYPASS` stays as it is today.
4. **Fallback switch:** add `colour_impl: "sos" | "fir"` (default `"sos"`) so A/B listening and bisecting stay possible.
5. **Render (optional, recommended for Play = Render parity):** in `_colour_apply`, use `scipy.signal.sosfilt` with the same SOS. Keep the FIR behind `colour_impl: "fir"`.

## Acceptance tests (add to `engine/tests/run_all.py`)

- **AT-C1 accuracy:** for 20 mics × θ = 1…180° (1° steps), the |dB| error of the packed SOS vs the analytic model `relative_db` (20 Hz–20 kHz, 600 log points) is ≤ **0.5 dB** max and ≤ 0.25 dB p95. With the HPF engaged, error vs the analytic model + HPF (`stack_hpf`) is ≤ 0.5 dB.
- **AT-C2 Play null:** scenes `lock18`, `unl` and `two` (the same dumps as `tools/null_test.py`). The Play IR null of SOS vs FIR must be ≤ **−40 dB**, with octave-band energy differences ≤ 0.1 dB, 63 Hz–16 kHz. (Measured −48 dB and 0.03 dB.) Skip the HPF-engaged cases here: the FIR is the one that is wrong there (FINDINGS §2).
- **AT-C3 CPU:** `tools/bench_colour.py`-style run, median of 3. 1 source ≤ **colour-off + 0.12 ms**, 2 sources ≤ colour-off + 0.2 ms.
- **AT-C4 44.1 kHz:** repeat AT-C1 at fs = 44100 with the 48 k tables (the parameters are sample-rate independent). Max ≤ 0.6 dB. If it fails, build per-sample-rate tables.
- **AT-C5 bypass / legacy:** a FIR-only blob (old format) renders bit-exact vs the pre-patch wasm. `colour_on=false` is bit-exact vs pre-patch.
- **AT-C6 sample-0 check (report only, does not fail):** print `x[0] / max|x[15:7200]|` in dB for the Play IR of each scene. Today it is −24 to −32 dB in default scenes and about −8 to −10 dB at DM −0.5 (the FDN diffuser feed-forward click). Colour must not change it (SOS = FIR within 0.1 dB). Whether to remove the click is a separate decision (it waits for the 2011 captures, see research/reference_2011).

## Notes / risks

- K = 3 layout LS + HS + HS matches the preset form (dual shelf + soft pole). If new presets add resonances, move to K = 4 (LS HS HS PK). The patch already allows 6 sections.
- Parameter interpolation can pass through a branch jump in a tiny w-interval (the worst midpoint was still 2.1 dB on SchoepsCMC5UOmni, inside a 1/1024-wide w-slot). The 1° sweep never hit it. If a user reports a glitch at one exact angle, raise the bisection depth.
- CPU: the F1–F3+F5 tree measured +0.28/+0.46 ms (1/2 sources) over the snapshot even with colour off. That is outside this brief, but it decides whether the full roadmap fits under 80% (FINDINGS §5).
