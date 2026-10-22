# S7 finish + t19 scoring fix (paste into the same Build window)

> Hi Build. Same window: finish S7 and fix the t19 scoring. **Harness and test files only. Do not touch `live_stereo.c`, the wasm or the worklet.**
>
> Our box check of S7 passes (`handoff_build_support_2\roadmap\s7_verify_1905\README.md`):
> - Play vs Render null: −72 dB at default (colour and Bypass), −70 dB with no Dffs, −72 dB under parity, −65 dB in the big room, −62 dB on the Hall.
> - Play − Render tail: 0.00 dB in every scene.
> - Render matches the research prototype R_z1 × −1.70 dB to −149 dB. With no Dffs, Render equals 1815 × −1.70 dB exactly.
> - Default tail change: −3.14 dB with colour on, −3.50 dB in Bypass. Your −3.34 sits between the two.
>
> t19 is noise plus mean scoring, not code:
> - Alternating box A/B over 14 rounds: wasm 69eb8b3bca4c is 2 % faster than 08a95563546d by median, so the shared-tail flag costs nothing.
> - Scheduler spikes (blocks over 3× the median) push the mean of a run up by 3–11 %, and by up to 26 %.
>
> 1. **Keep your 19:19 edits.** The F3 trim in `render_binaural_fdn_ir` is fine: the function has no callers, and F2 stays off because that loop has no line_t60. Tighten the colour-parity needle in `tests/test_mic_colour_relative.py`, because the old string is gone from the C: assert `"0.5 * xA * injUse"`, `"0.5 * xB * injUse"` and `"double injUse = line->inj;"`. Don't use an `or` with the old text.
> 2. **`harness\lib\wasm_run.js` bench:** also return `play_median_ms`, `play_p90_ms` and `play_spikes` (the count of blocks over 3× the median). Keep `play_mean_ms` and `silence_late_median_ms`.
> 3. **Score CPU by medians** in `run_all.py`:
>    - t15 and t19 pass when `play_median_ms ≤ limit × BUDGET_MS × perf_scale`.
>    - The silence checks in t09 and t19 use `silence_late_median_ms ≤ 1.3 × play_median_ms` and `≤ limit`. Use the same in `tests/test_p0_engine.py` P0.1, at 1.5×.
>    - Put mean, median, p90 and spikes in each result dict. Don't raise `--perf-scale` to make a test pass.
>
>    Box evidence that medians still catch a denormal climb: with the guards removed (`LS_DC = LS_TINY = 0`), late-silence median ÷ play median was 2.48 / 2.12 / 1.42 / 1.83 (decay 0.3 or 1.8 s, Bypass or colour). All are above 1.3. With the guards in, it was 0.96–1.07. The mean rule failed a guarded build: 1.34 at decay 1.8 Bypass, where the median gave 1.07.
> 4. **Goldens: already done, don't regenerate.** You rewrote only `render_std_unlocked_byp.f32` and put the reason in `GOLDEN_META.json`. That's right. Don't run `--regen-golden`, because it would rewrite the Play files too. Just print the SHA1 of every `play_*` golden and confirm they're still the 16:07 bytes.
> 5. **Run with the PC quiet** (S-UI1 not running):
>    - run_all in full (t01–t19), 3 times. Print the t19 mean, median and p90 for each run.
>    - Phase `--slow`, including `test_p0_4*`, `test_s4b_*`, `test_binaural_play_tail_coherence_matches_head` and the ensemble IC test.
>    - The software tests and selfcheck.
>    - Print the t13, t18 and T30 (t10/t12) numbers. Expect t18 near −72 dB and a t13 tail level of 0.00 dB.
> 6. Add to the S7 section in HANDOVER.md:
>    - Render now has z⁻¹ in both, with equal −1.70 dB trims.
>    - The binaural Render helper is unwired.
>    - CPU tests are scored by the median.
> 7. Report the numbers, the golden files that changed (names and SHA1) and the reason string.
>
> Optional, only if asked: `roadmap\s7_verify_1905\t19\t19_ab_pc.py` runs a same-minute PC A/B of the shipped wasm against `ship_1630_bbb23260.wasm`. Two bit-exact Play micro-fixes, `F2_cold_shared_fields.patch` and `F1_hoist.patch`, are parked for S5, where Play gets more expensive. F2 is about 2 % faster on the box.
