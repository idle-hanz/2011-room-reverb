> **SUPERSEDED 4 Oct 2026 22:05 BST** by `../START_HERE.md` and `../NEXT_SESSION_PLAN.md`. Kept for history; do not follow.

# NEXT SESSION PLAN for Grok Build: 1 Oct 2026

> **Update 1 Oct, about 16:20 BST:** Build has done items 1, 1b part A, 2, 3 and most of 5 (VERIFIED on the 15:50 snapshot). The remaining work and the new order are in **`BIG_JOBS_ROADMAP_2026-10-01.md`**.

- **Written:** on the box, 1 Oct 2026, about 07:36–08:10 BST.
- **Inputs:**
  - A fresh read-only snapshot of the PC `software\`, taken **1 Oct 07:36 BST** (`snapshot_2026-10-01_0736`, box only).
  - `handoff_build_support_2` (packages 1–6, `DECISIONS_LOCKED_2026-09-28.md`).
  - The binaural pack (`/workspace/binaural`, `DECISIONS_LOCKED_2026-09-30.md`).
- **PC:** `software\` was only read with `tar`; nothing in it was written, and the app was not touched.
- **Tags:** VERIFIED = measured or run by a script/test on the box; ASSUMED = judgement.

## A. What Build changed since the 28 Sep 20:40 snapshot (VERIFIED, file diff)

- **When:** all edits are dated 29 Sep, 20:50–22:00 BST. Nothing changed on 30 Sep or 1 Oct.
- **Files changed:** 13 (plus the 20 new `sos_tables/44100/*.json`). The text diff is in `4_engine_fix_patches/patches_rebased_2026-10-01/build_diff_0928_to_1001_for_reference.diff` (excluding the wasm and the 44100 tables); summary below.

| Area | What Build did | Relation to our handoff |
|---|---|---|
| **Colour per rate (decision 7)** | `sos_table.py` `SUPPORTED_RATES` (44100, 48000), `rate_supported`, `unsupported_rate_notice`, `tables_dir(sr)`, `_load_one(mic, sr)` with a `fit_fs` check; `MicColour.notice`; live-bank `notice`; `colour_notice` in the Render info and status line; `live_fdn.js` `colourNotice()`; **20 tables in `sos_tables/44100/`** | **Already applied, in Build's own words.** The 44.1k tables are **byte-identical** to ours (patch 08). Patch 08 is obsolete |
| **Colour entry cap** | `MAX_IRS` 64 → **128** (C + worklet). Over the cap, colour is turned off **with a status line** ("Mic colour is OFF: N entries, cap 128") instead of failing silently | New. This is half of our "64-entry limit" item |
| **F3 (Play delays at the Play rate)** | `live_fdn_params` uses the posted `sample_rate` for delays, decay-lock mean, air, shelf and peaking (broader than our 02) | **Already applied** (patch 02 obsolete) |
| **K4 stale early buffer** | `bus_sample` always tints and writes the early lanes, reads them only when Early is on; new Build test `test_early_lane_written_while_fader_down` | **Already applied, Build's own version** (patch 06 obsolete). Our replay test passes on it |
| **Versions** | `WORKLET_VER` 30 → **33**, `live_fdn.js?v=33`; Build tests pinned to 33 | **Conflicts** with our 31/32 → the rebased set uses **34** |
| Build tests | 8k/16k unit tests moved to 48k; 44.1k accuracy over all 20 mics × 180°; unsupported rates; cap 128 | Same intent as our 09 |

**Not applied yet (VERIFIED by grep and the acceptance suite):**
- **F2** (per-line loss, `line_t60`, BLOB_LEN 1982).
- **K1** (`YAW_X_SIGN`; capsules still crossed: ORTF direct L−R −8.6 dB for a left source).
- **K2 / K3 / K4 defaults:** `air_lp` 0.25, source 3.0/1.5, `fader_direct` 0.5, `early_wet` 0.
- The **diffusion_master** −0.25 default and its [−0.5, 0] clamp.
- The **headroom trim**.

**IIR colour work:** finished for what was asked (SOS at 44.1k/48k, notice at other rates, cap with a notice). Still open:
- **Render SOS speed:** `sos_fit.apply_sos` is unchanged, a per-sample Python loop. scipy is in `requirements.txt`, but Build's tests assert scipy is *not imported* (`test_mic_colour_relative.py:34-36, 469, 587`).
- **Two sources with the K3 default source** need 146 entries (see B).

**Side effect live in Build's tree today (VERIFIED, `levels_p6_dm025_air025.log`):**
- Build's F3, without F2 and without a trim, makes the **Play FDN bus +3.0 dB hotter** at the reference scene: −5.83 vs −8.86 dB; small +1.8 dB, hall +3.2 dB.
- t14 Play: peak 0.624 and RMS −14.0 dB, vs 0.498 and −16.4 dB before. Render is unchanged.
- Patches R01 + R07 bring Play back to −8.72 dB at the reference scene (−0.14 dB from pre-F3).

## B. Test results (VERIFIED, box, 1 Oct 07:40–07:50 BST)

`new` = Build's tree as of 1 Oct, `p6` = new + the rebased patches (R01–R09).

| Suite | new (unpatched) | p6 (new + rebased patches) |
|---|---|---|
| Package 3 acceptance (84 tests, `--slow`): PASS / FAIL / XFAIL / SKIP | **36 / 0 / 48 / 0** ¹ | **60 / 2 / 22 / 0** |
| Build `tests/test_mic_colour_relative.py` | 15/15 | 15/15 |
| Build `tests/test_live_stereo.py` (native gcc .so) | 13/13 | 13/13 |
| Build `engine/selfcheck.py` | 44/44 | 44/44 |
| run_all: pass / fail / skip / pending | 5 / 6 / 2 / 5 (t10–t14, t18 fail: tail 4.5–12.7 s for 1.8 s, no F2) | **9 / 2 / 2 / 5** (t13, t18 = F5) |
| Binaural pack (61 proofs + 22 acceptance xfail) | 60 pass / **1 fail** ² / 22 xfail | **61 pass** / 22 xfail |

¹ The run printed 36/1/47. The 1 FAIL was a bug in our informational whole-mix test, which raised instead of XFAILing when the trim is absent. It is fixed in `test_decisions_2026_09_28.py` and re-run: XFAIL.

² `test_engine_tail_coherence_matches_head`: the tail level changes by 0.89 dB (limit 0.5) on the unpatched FDN. The ASSUMED cause is the pre-F2 double-slope loop. It passes with the patches.

**The 2 FAILs on p6:**
1. `test_colour_play_bank_fits_two_sources_apart`: **146 entries > 128**, so Play colour is off with two sources (now with a visible notice).
   - The cause is **K3's default source position** (VERIFIED):

     | Case | Entries |
     |---|---|
     | p6, 2.6 / 1.2 defaults | 146 |
     | p6, source pinned at 3.0 / 1.5 | 90 |
     | p6, one source | 87 |
     | new tree, unpatched | 90 |

   - Build's own test uses `mirror_b: false` and still passes (64 < n ≤ 128).
   - The 28 Sep note that blamed K1 was ASSUMED and is wrong; corrected here.
2. `test_p0_2_t60_play_within_8pct[small_lock08]`: 500 Hz T30 0.885 s (+10.6 %) against ±8 %. This is unchanged from p5 and is a tolerance decision.

**Patch status (VERIFIED):**
- **Old chain on the new tree:** 02, 06 and 08 fail, because Build already did them. 09 fails on versions. 01 fails only on its version-pin hunks. 03, 04, 05 and 07 apply.
- **Rebased chain:** `4_engine_fix_patches/patches_rebased_2026-10-01/` holds R01, R03, R04, R05, R07, R09 and `00_ALL_build_0929_to_p6.diff`. It applies with `patch -p1` to a clean copy of Build's 1 Oct tree and reproduces p6 **byte for byte, apart from the wasm**.
- **wasm:** it must be rebuilt. t02 (wasm vs C) passes on the rebuilt one.
- **Levels on p6:** identical to p5 (FDN Play/Render, dB):

  | Scene | Play | Render |
  |---|---|---|
  | std | −8.72 | −8.88 |
  | small | −9.07 | −7.11 |
  | hall | −9.16 | −8.00 |

  So Build's version of F3 and ours have the same effect once F2 is in, and the trim table is still valid. t14 FDN −27.10 vs ref −27.18 dB: PASS.

## C. Ordered plan (dependencies first)

| # | Item | Why | Read | Tests that prove it | Risk / merge notes | Size |
|---|---|---|---|---|---|---|
| **1** | **Merge the rebased engine set: F2 + clamp + K1 + locked defaults + headroom trim + version 34** (R01 → R03 → R04 → R05 → R07 → R09, or the single `00_ALL`) and **rebuild the wasm** | The tail is 4.5–12.7 s for a 1.8 s dial without F2. Capsules are crossed (K1). Build's F3 already made Play +3 dB hotter, which the trim corrects. Every later item (binaural, goldens, F5) assumes this tree | `DECISIONS_LOCKED_2026-09-28.md`, `4_engine_fix_patches/README.md`, `patches_rebased_2026-10-01/README.md` | Package 3 suite → 60/2/22/0; `test_decisions_2026_09_28.py` (K1 L louder and earlier for XY/ORTF/NOS/DIN/MS, 29 delays, K4, trim); run_all t01/t02/t08–t12/t14 PASS; Build tests 28/28; selfcheck 44/44 | **Apply R01 and R09 together.** R01 changes the blob (BLOB_LEN 1982), and only R09 bumps WORKLET_VER to 34, so a browser could pair an old cached worklet with the new blob. R04 flips 5 of Build's selfcheck asserts and one Build test window (15 → 40 ms in R09). Build should agree that its old asserts encoded the crossed image. Low conflict now (only Build's 29 Sep tree underneath) | **M**: about 1–2 h with review. The diff is 829 lines |
| **1b** | **Mirror symmetry (added 1 Oct, about 11:30 BST, after Idle's report).** (A) Give source B its own FDN colour map (`colour.fdn_b`, route 230 → 326, `fdnIdxB`/`yBlkB` in `live_stereo.c`, MAX_FILT 112 → 176). (B) Use a mirror-symmetric `LIVE_32` (index 23 → (−1,−1,0)) in the line order τ = (b0 b4)(b1 b3). This keeps H exactly, keeps `i % 3` and keeps **(0,2,0) on line 0**. Keep the Reaktor table for `reaktor_parity` | With Two sources + Mirror, Play colours B's reverb and early lanes with **A's** filters. Moving Balance A → B changes bands by up to **13 dB**, ILD by **26 dB** and level by 8 dB; at centre the image leans (ILD 9.8 dB). One source: 1.5 dB from the table gap and the line order. **No pending patch fixes it** (VERIFIED on p6). Binaural (item 5) reuses the same per-line B routing and image table, so fix it first | `MIRROR_ASYMMETRY_BRIEF.md`, `7_mirror_symmetry/README.md`, `prototype/MIRROR_on_p6.diff` | `tests/test_mirror_symmetry.py`: 10 tests, XFAIL → PASS (A vs mirrored B ≤ 0.1 dB per 1/3-octave band, null ≤ −60 dB; the prototype is bit-exact). t14 FDN level stays within ±0.5 dB (+0.13 dB on the prototype). Build tests 28/28. Phase suite unchanged apart from the new tests | **Apply on top of item 1** (the diff is against p6). **Line 0 must keep a weak image:** putting the direct image on line 0 made the FDN +6.23 dB hotter. Update 2 selfcheck asserts (`LIVE_32[2]`, 29 unique). Bump WORKLET_VER to 35 (route length changes). Goldens change, so do this before item 4. It raises the non-mirrored two-source cap case 146 → 180 entries (0 extra for mirrored sources), so decide item 2 with it. Two-source CPU with colour on +7–15 % (0.96 → 1.03–1.16 ms of 2.67). Build is working on this asymmetry now: compare its change against the test | **M** (about 1–2 h) |
| **2** | **Decide and fix the two-source colour cap** (146 > 128 with the K3 default) | With item 1, two sources placed apart turn colour off (now visibly). Options: raise `MAX_IRS` (192 fits 146 with margin; memory is `MAX_IRS × 8192` floats in wasm, 6.3 MB at 192), size IR slots by record length (SOS records are tiny), or bucket θ coarser | `6_colour_per_rate/README.md` (limit options), `1_iir_colour_verification/README.md` | `test_colour_play_bank_fits_two_sources_apart`; Build's cap test; run_all t15 CPU with 2 sources **with colour actually on** (today's 0.815 ms is with colour off) | CPU rises with filters (ORTF, 87 filters, one source ≈ 4 % of one core; 146 is ASSUMED ≈ 6–7 %). Bump WORKLET_VER again if the C changes. Build's call | **S** |
| **3** | **Render SOS speed** | Render colour runs a per-sample Python loop (0.27–0.36 s for a 5 s signal in our benchmark). The numpy version is 14–22× faster (error ≈ 1e-13); scipy `sosfilt` is 115–180× faster | `6_colour_per_rate/README.md`, `tools/apply_sos_fast.py`, `results/bench_apply_sos.log` | `test_colour_numpy_sos_matches_loop`; Build's colour tests | numpy keeps Build's "scipy not imported" tests green; scipy needs those 3 asserts changed. **Build's / Idle's call** | **S** |
| **4** | **Regenerate goldens and settle the small-room tolerance** | t03/t04 skip without goldens; after item 1 the reference scenes changed on purpose (defaults, K1, F2) | `3_phase_acceptance_tests/README.md` | `run_all.py --regen-golden` on the merged tree, then t03/t04 PASS; P0.2 small_lock08 (±8 % vs ±10 % for rooms under about 100 m³) | Do it only after item 1 (and 2 if C changed) | **S** |
| **5** | **Binaural mode** (presets, ears and ITD, `BinauralColour` + bank branch, early-tap routing to its own node record in `live_stereo.c`, `binaural_rear32`, diffuse-tail IC mixer, UI) | Idle's locked binaural decisions (30 Sep) | `/workspace/binaural/DECISIONS_LOCKED_2026-09-30.md`, then `BINAURAL_MODE_BRIEF.md` §2–§8, `binaural_fitter/reference.py`, `tail_ic.py`, `rear_images.py` | `tests/test_binaural_mode_acceptance.py`: 22 xfail → PASS, including the tail IC (max \|ΔIC\| ≤ 0.15, RMS ≤ 0.06), two-source bank ≤ cap at head yaw 0/90/180, unsupported-rate notice; plus the pack's 61 proofs (pass on p6 now) and the package 3 suite unchanged | **Depends on item 1:** K1 `YAW_X_SIGN` (ears at ±90° in that convention), F2 (tail proof fails without it), WORKLET_VER after 34. **Uses Build's per-rate loader** (done; the binaural tables need the same `fit_fs` check). The cap is fine: ≤ 60 records (max 38 seen) under 64 or 128. `MAX_SOS` 6 = K6. The early-target routing change touches `bus_sample` / `early_target` in `live_stereo.c` (same area as Build's K4 fix). The 513-tap tail FIR adds 5.3 ms latency on the tail only (ASSUMED inaudible; 257 is the fallback). The presets already sit in the PC `mic_fitter\presets\binaural\` (dated 30 Sep) | **L–XL** (2–3 sessions). Split: 5a engine and taps → 5b colour bank and C routing → 5c tail mixer → 5d UI |
| **6** | **F5 (same-sample loop, Play = Render network)** and fill `LOOP_LEVEL_TRIM_DB["f5_same_sample"]` | t13 and t18 (Play vs Render parity) still fail; F5 makes Play about +5.8 dB hotter, which the trim row takes back | `4_engine_fix_patches/README.md` (F5 note), DECISIONS file "F5 later" | t18 null ≤ −30 dB; t13; t14 FDN ±0.5 dB after filling the row; re-run the binaural tail IC test | Changes the Play network. If done after item 5, re-verify the binaural tail. **Idle to choose its slot** | **L** |
| **7** | Small cleanups | Known gaps the suite reports | Package 5 `RECONCILED_PARAMETERS.md`, K4 brief | P0.5: client loads `/api/defaults` (server/client mismatches), `loop_mix` dead payload, the FDN-lane freeze (K4 brief) | Low | **S** each |

## D. Needs Idle's decision (none blocks item 1)

1. **Two-source colour:** raise the cap, size slots by record length, or coarser θ buckets (item 2). This decides whether two sources keep colour at the new default source.
2. **Render SOS:** numpy or scipy (item 3).
3. **F5 slot:** before or after binaural (item 6). The recommendation is after, because binaural does not depend on it; re-check the tail IC after.
4. **Mirror fix (item 1b):** keep the Reaktor 32-image order bit-exact under `reaktor_parity` (recommended), or drop it. Also, with the fix, a non-mirrored two-source scene needs up to about 180 colour entries, so the cap choice in item 2 should cover it (192 does).
5. Still open from 28 Sep:
   - confirm decay 1.8 s by ear;
   - trim direct/early too (t14 whole mix +1.61 dB)?
   - compensate `air_lp` 0 (+2.45 dB FDN)?
   - small-room 500 Hz tolerance;
   - K2 distance unit after the 2011 captures.

## E. Paste-ready opening message for Build

> Hi Build. The plan for this session is in `handoff_build_support_2\NEXT_SESSION_PLAN_2026-10-01.md`. Your 29 Sep colour-per-rate, MAX_IRS 128, F3 and stale-early work is already in, and the 44.1k tables match ours exactly. Please do the following, in order:
> 1. Apply `4_engine_fix_patches\patches_rebased_2026-10-01\` (R01, R03, R04, R05, R07, R09, or the single `00_ALL_build_0929_to_p6.diff`) with `patch -p1` from `software\`. This adds F2, the diffusion clamp, the K1 yaw flip, the locked defaults (air_lp 0, source 2.6/1.2, FDN-first faders, diffusion −0.25), the headroom trim and WORKLET_VER 34. Then rebuild `live_stereo.wasm`. Apply R01 and R09 together.
> 1b. Then fix the two-source mirror asymmetry from `MIRROR_ASYMMETRY_BRIEF.md`: give B its own FDN colour map and use the mirror-symmetric, Hadamard-ordered 32-image table that keeps (0,2,0) on line 0. `7_mirror_symmetry\prototype\MIRROR_on_p6.diff` is a reference. Keep the Reaktor order for parity, bump WORKLET_VER to 35, update the 2 Reaktor-table selfcheck asserts (`LIVE_32[2]`, 29 unique), and make `tests\test_mirror_symmetry.py` pass.
> 2. Run your tests and selfcheck (expect 28/28 and 44/44), then `3_phase_acceptance_tests\run_phase_tests.py --sw software --slow` (expect 60 pass / 2 fail / 22 xfail before 1b; with the 10 new mirror tests, 62 / 2 / 30 before 1b and 70 / 2 / 22 after 1b). The 2 fails are two-source colour (146 > 128) and the small-room 500 Hz T30.
> 3. Tell me your choice for the two-source colour cap and for numpy vs scipy for Render SOS. Then regenerate the run_all goldens.
> 4. Then start binaural mode from `binaural\DECISIONS_LOCKED_2026-09-30.md` and `BINAURAL_MODE_BRIEF.md`, in parts 5a to 5d. Keep `YAW_X_SIGN` and bump WORKLET_VER past 34.
> Don't start F5 until I say.
