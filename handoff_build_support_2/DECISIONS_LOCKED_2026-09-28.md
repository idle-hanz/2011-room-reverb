# DECISIONS LOCKED, 28 Sep 2026 (Idle): read this first

Idle decided the open items from build_support_2 on 28 Sep 2026, about 21:25 BST.
- Everything below is **implemented and tested** on the box tree `work/p5/software`: the 28 Sep 20:40 snapshot + F2 + F3 + these decisions.
- It ships as split patches in `4_engine_fix_patches/patches/`.
- The PC `software\` was **not** touched, and the app was not run or changed.
- Tags: **VERIFIED** = measured by a script/test in this folder; **ASSUMED** = judgement.

| # | Decision (locked) | What was done | Patch | Test(s) (package 3) | Result on p5 |
|---|---|---|---|---|---|
| K1 | **Fix** the crossed capsules with **one convention flip**, not per-preset sign edits | `YAW_X_SIGN = +1` in `engine/early_field.py` (was −1 in effect), mirrored as `RoomMath.YAW_X_SIGN` in `room_math.js`. Every look/angle formula uses it (`look_vector`, `direction_angles`, `arrival_cos_xz`, `polar_field`, `mic_display`, `mic_desk` handle + drag). Stored yaw numbers unchanged. Build's `selfcheck.py` (which asserted the crossed image) and one Build unit test window were updated | `04_K1_yaw_convention.diff` (+ test edit in `09`) | `test_k1_single_yaw_convention`; `test_k1_left_source_L_louder_and_earlier_play[xy_90,xy_120,ortf,nos,din,ms]`; `..._render[ortf,xy_90,ms]` (slow) | **PASS**. Source 32° left: direct L−R +3.5…+8.9 dB and early +1.4…+8.7 dB (were −1.7…−8.7). L arrives first (spaced) or no later (coincident). VERIFIED |
| K2 | **Keep** the Structure air 1-pole code; **default mix `air_lp` = 0**. Revisit after the 2011 captures reveal the distance unit | Server fallbacks, `render_pipeline` fallback, `app.js` state and slider → 0. HF air loss at the default comes from the air shelf (ISO 9613-1 not implemented yet, P2) | `05_K2_K3_K4_defaults_diffusion.diff` | `test_k2_air_1pole_default_zero` | **PASS** |
| K3 | Default source **x 2.6 m, height 1.2 m** | Server DEFAULTS (and an empty API body), `app.js` state (+ mirrored B 3.4 / 1.2), height slider | `05_…` | `test_k3_default_source_29_distinct_delays` (and empty body), `test_k3_client_default_matches` | **PASS**: 29 / 29 / 29 distinct delays per bus (was 20 / 12 / 20). VERIFIED |
| K4 | **FDN-first:** FDN fader on, direct and early faders 0, `early_wet` = 1.0 so raising the early fader works at once. **Fix the stale early buffer** | `fader_direct` 0 (state + HTML), `fader_fdn` 0.5, `fader_early` 0. `early_wet` is now the early-bus enable: heard send = `early_wet × fader`. C `bus_sample` writes the early lane(s) every sample and reads only while on | `05_…`, `06_K4_stale_early_lane.diff` (+ wasm rebuild) | `test_k4_fdn_first_defaults`, `test_k4_raise_early_fader_no_stale_replay` (new `wasm_run.js switch` mode) | **PASS**. Stale replay before: null −1.0 dB, burst 0.059 (−24.6 dBFS). After: bit-identical. VERIFIED |
| 5 | `diffusion_master` default **−0.25** (Structure), clamp **[−0.5, 0]** | `fdn.DIFFUSION_MASTER_DEFAULT = LIVE = −0.25`, `DIFFUSION_MASTER_MIN = −0.5`; server `_span(…, −0.25, −0.5, 0)`; all fallbacks and `app.js` → −0.25 | `05_…` | `test_p0_5_diffusion_master_clamped`, `..._single_value` | **PASS**. Tail vs dial, see below |
| 6 | **Headroom:** a fixed makeup trim compensating F2+F3, so the same fader gives the same loudness as before; the design must take F5's later +5.8 dB the same way | `fdn.LOOP_LEVEL_TRIM_DB`: one row per loop change (`f2_line_absorption`, `f3_play_rate_delays`, `f5_same_sample` reserved at 0), per path (play/render), with a `when` flag (lock-only / always). The trim is applied to the FDN send only (Play: `fdn_wet` in `live_fdn_params`; Render: `render_fdn_ir`). Trims only reduce level. **Values:** f2 play −2.81 / render −2.81 dB (lock only), f3 play −1.70 dB (always), derived at the reference scene with the locked diffusion −0.25 | `07_headroom_trim.diff` | `test_headroom_trim_table`, `test_headroom_t14_fdn_level_matches_pre_f2`, `test_headroom_t14_whole_mix_informational`; run_all t14 updated | FDN bus at the reference scene **+0.09 dB** vs pre-F2 (t14, PASS ±0.5). Whole mix +1.61 dB (XFAIL, see below). VERIFIED |
| 7 | **Colour:** separate SOS tables for 44.1 and 48 kHz; other rates turn colour **off with a visible notice**. Render speed-up and the 64-entry limit are Build's call | 20 tables in `sos_tables/44100/` (same fitter; 48k refit reproduces Build's tables exactly); `sos_table` picks the table by rate; `MicColour.notice`; payload `notice` → `live_fdn.js status()`; Render status line | `08_colour_per_rate.diff` (+ 2 Build unit tests moved from 8/16 kHz to 48 kHz in `09`) | `test_colour_at_c4_44k1_within_0p6db`, `test_colour_44k1_tables_match_presets`, `test_colour_unsupported_rate_disabled_with_notice[32k/88.2k/96k]`, `test_colour_numpy_sos_matches_loop` | **PASS**: 44.1k worst 0.408 dB (was 0.692). See `6_colour_per_rate/README.md` for scipy vs numpy |

## Tail vs dial with diffusion_master −0.25 (VERIFIED, run_all t10/t12 on p5; p4 = −0.5 for comparison)

| Scene (dial) | p4 (−0.5) T30 500 / 1k / 2k / 4k / 8k | **p5 (−0.25)** T30 500 / 1k / 2k / 4k / 8k |
|---|---|---|
| std Play (1.8 s) | 1.77 / 1.76 / 1.80 / 1.80 / 1.80 | **1.72 / 1.83 / 1.74 / 1.79 / 1.80** |
| small Play (0.8 s) | 0.72 / 0.81 / 0.78 / 0.78 / 0.79 | **0.88 / 0.80 / 0.78 / 0.78 / 0.76** |
| hall Play (4.0 s) | 3.92 / 3.87 / 4.01 / 4.00 / 4.00 | **3.85 / 3.92 / 4.00 / 4.02 / 4.00** |
| std Render (1.8 s) | 1.75 / 1.80 / 1.78 / 1.81 / 1.80 | **1.72 / 1.70 / 1.81 / 1.81 / 1.80** |
| Play 9 / 11 kHz late T60 | 1.81 / 1.80 | **1.80 / 1.80** |

- 14 of the 15 Play band×scene values are within ±8 % of the dial. The exception is small 500 Hz at **0.884 s (+10.5 %)**; with −0.5 it was 0.722 s (−9.8 %).
- The small-room 500 Hz band swings either side of the dial when diffusion changes, which points to estimator variance in a small room with few modes (ASSUMED).
- The phase test `test_p0_2_t60_play_within_8pct[small_lock08]` still FAILs on that one value.
- Render std is within −5.6 %…+0.6 %.
- run_all t13 Play-vs-Render: 125 Hz balance improved (5.2 → 0.3 dB); worst bands now 500 Hz 2.9 dB and 4 kHz 1.7 dB. The ASSUMED cause is the −0.25 diffusion.

## Level, before and after (VERIFIED; FDN-only impulse-response energy, `4_engine_fix_patches/results/levels/`)

Source pinned at the old default (x 3.0, y 1.5), `air_lp` held at the old 0.25, diffusion at the locked −0.25. Only F2 + F3 (+ K1) and the trim differ. latest = snapshot, p4 = + F2 + F3, p5 = + trim (+ K1 etc.).

| Scene | Play latest → p4 → **p5** (Δ p5 vs latest) | Render latest → p4 → **p5** (Δ) | p5 Play − Render |
|---|---|---|---|
| std 6×3×8, 1.8 s (**reference**) | −8.86 → −4.35 → **−8.72 (+0.14)** | −8.52 → −5.71 → **−8.88 (−0.36)** | +0.16 |
| small 4×2.5×5, 0.8 s | −9.58 → −4.71 → **−9.06 (+0.52)** | −9.85 → −3.25 → **−7.11 (+2.74)** | −1.95 |
| hall 20×10×30, 4.0 s | −7.52 → −4.70 → **−9.16 (−1.64)** | −4.65 → −5.07 → **−8.00 (−3.35)** | −1.16 |

- **Trim re-derived at the locked diffusion (−0.25), not at the old −0.5.**
  - The first cut measured at −0.5 gave f2 play −4.77 / render −11.23 dB. It left **±11.4 dB** Render residuals, and at the new defaults it put Render 6.6 dB below Play.
  - Cause (VERIFIED, std scene, `4_engine_fix_patches/results/levels/diffusion_sensitivity.log`): with F2 the loop level depends on `diffusion_master`. Going from −0.5 to −0.25 moves p4 Render by −9.1 dB and Play by −2.0 dB. On the latest tree it moves them by only −0.7 / 0.0 dB.
  - At −0.25 the F2 step is the same on both paths (**−2.81 dB**), and the residuals shrink to the table above (Play ≤ 1.6 dB, Render ≤ 3.4 dB).
  - Files: `levels_{latest,p4}_dm025.*` and `levels_p5_dm025_air025.*`. The superseded first cut is in `levels_latest_vs_p4.*` and `levels_p5_superseded_trim_dm05.*`.
- **run_all t14** (Play, noise ±0.3, 3 s; pins sx 3 / sy 1.5 / air_lp 0.25 / diffusion −0.25; the reference was re-measured on latest with the same pins):

  | Measure | latest (ref) | p4 | **p5** |
  |---|---|---|---|
  | FDN bus RMS | −27.18 dB | −22.73 (+4.37) | **−27.09 (+0.09) PASS** |
  | Whole mix RMS / peak | −16.37 / 0.512 | −13.84 / 0.674 | **−14.76 (+1.61) / 0.560** |
  | Tree defaults (t14 first line) RMS / peak | −16.4 / 0.498 | −13.5 / 0.727 | **−16.24 / 0.559** |

- **p5 at the locked diffusion −0.25 and air_lp 0** (source still pinned, `levels_p5_defaults.*`):
  - FDN Play −6.27 / −6.63 / −6.68 dB (std / small / hall), Render −6.43 / −4.66 / −5.51.
  - `air_lp` 0 adds **+2.45 dB** FDN energy vs 0.25 (mostly HF; K2 is Idle's choice, so it is **not** trimmed; add an `air_lp` note if Idle wants that compensated too).
- **Why the whole mix is +1.61 dB:** F3 also removed a fractional-delay loss on the Play **direct** (+2.4 dB) and **early** (+1.3 dB) buses. Play direct now equals Render direct exactly (+0.03/+0.04 dB).
  - Trimming them would re-open that Play/Render gap, so they were **not** trimmed.
  - With the K4 FDN-first defaults (direct and early faders at 0), what Idle hears first is the FDN bus, which is matched (+0.09 dB).
  - The table can take `direct`/`early` rows if Idle wants the t14 mix back within 0.5 dB. **Open decision.**
- **Unlocked (Feedback slider):** F2 is off. F3 raised Play FDN by +1.70 dB (−5.01 → −3.31), and the `f3` row takes it back. Render unlocked is unchanged (−3.51 / −3.51).
- **F5 later:** measure Play FDN at the reference scene (same pins, diffusion −0.25) before/after F5 with `tools/measure_levels.py --dm -0.25 --extra '{"air_lp":0.25}' --buses fdn`. Then put the negative delta in `LOOP_LEVEL_TRIM_DB["f5_same_sample"]["play"]` (about −5.8 dB expected) and re-check t14. F5 should also shrink the Play − Render column above.

## Still open

0. **Small-room 500 Hz T30** +10.5 % (one value outside ±8 %; see the tail section).

1. **Decay 1.8 s:** confirm by ear now that the tail really is 1.8 s.
2. **F5** (same-sample loop): not applied. Its trim row is ready. t13/t18 Play-vs-Render parity still FAIL, pending F5 (p5: t13 tail level −2.48 / +1.04 dB byp/col, t18 null +2.0 dB).
3. **Headroom:** whether to trim direct/early too (whole mix +1.61 dB), and whether to compensate the +2.45 dB from `air_lp` 0 (above).
4. **FDN lane freeze** when the FDN fader goes to −∞ and back (brief in K4; Build's call).
5. **MAX_IRS 64:** two sources placed apart now need **146** entries (was 90 on the latest tree), so Play colour is off with two sources. Build's call (`6_colour_per_rate/README.md`).
6. **Render SOS speed:** scipy `sosfilt` vs the numpy version. Build's call.
7. **K2 unit:** revisit `air_lp` after the 2011 captures reveal the distance unit.
8. **Goldens:** t03/t04 goldens differ, as intended (defaults, K1, F3). Regenerate with `run_all.py --regen-golden` after review.
