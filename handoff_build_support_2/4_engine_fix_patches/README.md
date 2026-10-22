# Package 4: engine fix patches, rebased on Build's 28 Sep tree, now with Idle's locked decisions (28 Sep 2026)

> **1 Oct 2026:** for Build's current tree (29 Sep, WORKLET_VER 33) use **`patches_rebased_2026-10-01/`** instead of 01–09. Build has already done 02, 06 and 08 in its own code. See `../NEXT_SESSION_PLAN_2026-10-01.md`.

- **Base:** the `snapshot_2026-09-28_2040/software` tree, which includes Build's IIR colour work.
- **Tested trees on the box:**
  - `work/p4/software`: F2 + F3 + clamp, as before.
  - **`work/p5/software`**: p4 + the decisions in `../DECISIONS_LOCKED_2026-09-28.md`.
- The PC was not touched.

## Patches (apply with `patch -p1` from `software/`, in this order, then rebuild the wasm)

| # | File | Contents | Relative to |
|---|---|---|---|
| 02 | `02_F3_play_rate_delays.diff` | F3: Play delays rounded at the Play rate | snapshot |
| 01 | `01_F2_line_absorption.diff` | F2: per-line loss, g = 1/√N, `line_t60` blob float, WORKLET_VER 31 | after 02 |
| 03 | `03_diffusion_master_clamp.diff` | clamp [−1, 0] (superseded by 05, kept so the chain applies) | after 01 |
| 04 | `04_K1_yaw_convention.diff` | K1: `YAW_X_SIGN` in `early_field.py` / `room_math.js`; `polar_field`, `mic_display`, `mic_desk`; Build's `selfcheck.py` asserts flipped | after 03 |
| 05 | `05_K2_K3_K4_defaults_diffusion.diff` | K2 `air_lp` 0; K3 sx 2.6 / sy 1.2 (plus an empty API body and the mirrored B); K4 faders and `early_wet` enable; diffusion −0.25 with clamp [−0.5, 0] | after 04 |
| 06 | `06_K4_stale_early_lane.diff` | `live_stereo.c` `bus_sample`: always write the early lane(s), read only when on | after 05 |
| 07 | `07_headroom_trim.diff` | `fdn.LOOP_LEVEL_TRIM_DB` + `loop_level_trim_db/lin`; Play (`fdn_wet`) and Render (`render_fdn_ir`) apply it | after 06 |
| 08 | `08_colour_per_rate.diff` | 20 new `sos_tables/44100/*.json`; rate-aware `sos_table`; `MicColour.notice`; payload notice → `live_fdn.js status()`; Render status line | after 07 |
| 09 | `09_versions_and_build_tests.diff` | WORKLET_VER 32 and `?v=` bumps (room_math 14, mic_desk 8, live_fdn 32, app 22); Build test pins 31 → 32; 2 Build unit tests moved to 48 kHz (decision 7); 1 Build test window 15 → 40 ms (K1) | after 08 |
| 00 | `00_ALL_combined_snapshot_to_p5.diff` | Everything above in one file (text only) | snapshot |

Wasm rebuild (the binary is not in any diff):

```
zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=live_stereo -Wl,--max-memory=1073741824 -o static/wasm/live_stereo.wasm engine/live_stereo.c
```

- **Chain:** VERIFIED. 02 → 01 → 03 → 04 → … → 09 on a clean copy of the snapshot reproduces p5 byte for byte, apart from the wasm. So does `00` alone.
- **Hunk split:** `tools/split_hunks.py` (p4 → p5 hunks, classified by content).
  - A few hunks carry two concerns on the same lines (for example `app.js` state lines that hold `air_lp` and `diffusion_master`). K2, K3, K4 and diffusion therefore share patch 05.
- **Intermediate states:** after 04 alone, Build's `test_early_toys_gated_and_colour_per_tap` needs the 40 ms window from 09. After 08 alone, the two 8/16 kHz Build tests need 09. Apply the whole chain.

## Results on p5 (VERIFIED, box, 28 Sep ~22:00 BST)

- **Package 3 suite:** see `../3_phase_acceptance_tests/README.md` (final counts there and in the top README).
- **run_all** (`results/run_all_after_p5.{log,json}`): 9 PASS, 2 FAIL (t13, t18: Play-vs-Render parity, which needs F5), 2 SKIP (goldens not vendored), 5 PENDING.
  - t13 on p5: tail level byp −2.48 / col +1.04 dB (p4 −5.8); balance 500 Hz 2.9 / 2.4 dB, 4 kHz 1.7 / 1.6 dB.
  - t18 FDN-only null +2.0 dB (p4 +1.4).
  - t14 PASS (FDN +0.09 dB, peak 0.559). t15 0.487 / 0.831 ms. t10/t11/t12 as in the tail table.
  - With the build_support goldens (`results/run_all_after_p5_goldens.log`), t03/t04 FAIL as expected, because the defaults, K1 and F3 change the reference scenes. **Regenerate the goldens after review.**
- **Build's own tests:** `tests/test_live_stereo.py` (native gcc `.so`) plus `tests/test_mic_colour_relative.py`: **27/27 pass**. `engine/selfcheck.py`: **44/44**.
- **Tail vs dial (t10/t12) with diffusion −0.25:** std Play 1.72–1.83 s, small 0.76–0.88 s (500 Hz +10.5 %), hall 3.85–4.02 s, Render 1.70–1.81 s. Table in `../DECISIONS_LOCKED_2026-09-28.md`.
- **Levels:** `results/levels/*.json|log`; tools `tools/measure_levels.py`, `tools/diffusion_sensitivity.py`.
  - **Trim** `fdn.LOOP_LEVEL_TRIM_DB`: f2 −2.81 dB on both paths (lock only), f3 −1.70 dB on Play (always), f5 reserved.
    - Derived at the reference scene with the **locked diffusion −0.25** (air_lp held at 0.25).
    - A first cut derived at −0.5 (f2 play −4.77 / render −11.23) was superseded: with F2 the loop level depends on diffusion (`diffusion_sensitivity.log`).
  - FDN bus at the reference scene: Play −8.86 (latest) → −4.35 (p4) → **−8.72** (p5); Render −8.52 → −5.71 → **−8.88**.
  - Residuals: small +0.52 / +2.74 dB, hall −1.64 / −3.35 dB (Play / Render).
  - t14 FDN −27.18 → **−27.09** (PASS); whole mix +1.61 dB (direct/early not trimmed; open).
  - Full table in the DECISIONS file.
- **CPU** (t09/t15, box, noisy while other jobs ran):
  - silence 0.47/0.48 ms; active 1 source + colour 0.48 ms, 2 sources 0.89 ms (budget 2.67 ms).
  - The stale-early fix adds `tint()` plus one lane write per line while early is off. That is not separable from noise here (p4 read 0.64/1.09 ms under different load).

## Conflict risk with Build's in-progress work (updated)

| File | Build's recent edits | Our patches | Risk |
|---|---|---|---|
| `mic_colour/sos_table.py`, `colour.py`, `live_bank.py`, `sos_tables/` | **Build's active colour work** | 08: rate-aware loader, notice, new `44100/` dir | **HIGH.** Same functions (`_load_one`, `pack_for`, `build_live_bank`). Merge by hand; the design is small (≈ 60 lines) |
| `static/js/live_fdn.js` | colour bank / `takeColour` | 08 `colourNotice()` before `takeColour`; 09 WORKLET_VER | **HIGH** on WORKLET_VER (bump once to whatever follows Build's) and on `takeColour` |
| `engine/live_stereo.c` | `run_sos` / `design_sos`, colour arrays | F2 (Line/LiveStereo/load_room/read_peaked) + 06 (`bus_sample` early block) | Medium (06 is in `bus_sample`, away from the colour code) |
| `render_pipeline.py` | colour_impl / MicColour wiring | F2/F3, fallbacks, trim in `render_fdn_ir` + `live_fdn_params`, `colour_notice` in 4 info dicts | Medium |
| `engine/early_field.py`, `polar_field.py`, `mic_display.py`, `static/js/room_math.js`, `static/js/mic_desk.js` | not in Build's 28 Sep diff | 04 K1 | Low (new overlap). But **any new Build code with its own `-sin(yaw)` must use `YAW_X_SIGN`** |
| `engine/selfcheck.py`, `tests/test_mic_colour_relative.py`, `tests/test_live_stereo.py` | Build's tests | 04 flips 5 crossed-image asserts; 09 pins/rates/window | Medium: Build's own K1-era asserts would fail on the fixed image |
| `static/js/app.js`, `static/index.html`, `app_server.py` | colour_impl key | 05 defaults, 09 `?v=` | Low–medium (same lines as any default edit) |
| `engine/fdn.py` | not touched | F2, diffusion constants, trim table | None |

---

*Earlier notes for p4 (F2 + F3 + clamp), kept for reference:*


**Base:** `snapshot_2026-09-28_2040/software`, which includes Build's IIR colour work.

**Patched and tested tree on the box:** `/workspace/build_support_2/work/p4/software`. The PC was not touched.

## Summary

| Fix | State | Patch |
|---|---|---|
| **F1** denormal guard (tint air/shelf states, FDN inputs, FIR partitions) | **Already landed by Build** (VERIFIED: `LS_TINY`/`LS_DC`, `ls_flush` in `tint()`, `LS_DC` on the FDN inputs, FIR silent-partition guard). The old F1 hunks in `build_support/engine/briefs/live_stereo.c.fix.diff` are **not needed**. | none |
| **F2** per-line loss `lg_i = 10^(−3·d_i/(sr·T60))`, loop at `g = 1/√N`, new trailing blob float `line_t60` | New, rebased | `patches/01_F2_line_absorption.diff` |
| **F3** Play delays rounded at the actual Play sample rate | New, rebased | `patches/02_F3_play_rate_delays.diff` |
| **diffusion_master clamp** (K6) | New | `patches/03_diffusion_master_clamp.diff` |
| All three in one file | — | `patches/00_ALL_F2_F3_clamp_combined.diff` |

**Apply order:** `02` → `01` → `03`, or just `00`, with `patch -p1` from `software/`. Then **rebuild the wasm**, because the binary is not in the diff:

```
zig cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding -Wl,--no-entry -Wl,--export-memory -Wl,--export=live_stereo -Wl,--max-memory=1073741824 -o static/wasm/live_stereo.wasm engine/live_stereo.c
```

- VERIFIED: applying 02, 01, 03 (or 00) to a clean copy of the snapshot reproduces the tested tree byte for byte, apart from the wasm.
- The zig on the box is 0.16. The wasm is not byte-identical to Build's, but run_all t02 (wasm == C behaviour) passes.

## What each patch does

**01 F2** (reuses the logic of `build_support/engine/briefs/*.fix.diff`, rebased onto the current code):

- **`engine/fdn.py` (Render FDN):**
  - `FDN(..., line_t60=0.0)`.
  - When `line_t60 > 0.05`: the limit becomes `1/√N` (not `0.99/√N`), `self._lg[i] = 10^(−3·d_i/(sr·T60))`, and `reads *= lg` in `process_block_poly`.
  - The C fast path is disabled when lg is in use.
- **`engine/live_stereo.c` (Play):**
  - `Line.lg`/`lgB` (init 1.0) and `LiveStereo.lineT60`.
  - `load_room` reads a trailing float `line_t60` and sets `lg = exp(−6.9078·delayT/(sr·T60))` from the **target** delay at the Play rate `st->sr`.
  - `read_peaked` multiplies the line read by lg.
  - The F1 code is untouched.
- **`static/js/fdn_worklet.js`:** `BLOB_LEN` 1981 → 1982, and `a.push(num(data.line_t60, 0))` at the end of `packRoom`.
- **`static/js/live_fdn.js`:** passes `line_t60` and bumps **WORKLET_VER 30 → 31**.
- **`index.html`:** `live_fdn.js?v=31`.
- **Both repo test files:** version pins 30 → 31.
- **`render_pipeline.py`:**
  - `live_fdn_params` returns `g = g_loop` (1/√N when locked), `g_decay` (the old g, still used for makeup) and `line_t60 = decay_s` when decay_lock is on (otherwise 0).
  - Render (`render`, `combined_ir`, `render_fdn_ir`, the two-source path, and the moving-path path) passes `line_t60` and `loop_g`.
  - `loop_mix` is built with `g_loop`.
- **decay_lock off** (Feedback slider): `line_t60 = 0` and g unchanged. VERIFIED by package 3 `test_p0_2_decay_lock_off_unchanged`.

**02 F3:**

- **`render_pipeline.py` `live_fdn_params`:** FDN delays (bank A and bank B) are rounded at `dsr` = the client's reported Play rate (`sample_rate`, sent by `app.js:328` once the AudioContext exists), else `sr`.
- Before, lines were rounded at 44.1 kHz and read at 48 kHz, so they were fractional, and the linear-interp read acted as an in-loop LPF.
- Residual risk (ASSUMED): the very first request before the AudioContext exists still rounds at 44.1k. It is corrected on the next param push. The same mechanism already governs colour (K11).

**03 clamp:**

- **`app_server.py:342`:** `diffusion_master` goes from `_f(..., -0.5)` (unclamped) to `_span(..., -0.5, -1.0, 0.0)`.
- The C loop keeps its own per-line clamp `dffs ∈ ±0.98` (`live_stereo.c:687,706`), and run_all t08 checks stability at ±0.98.
- The Structure range is 0…−0.5 (`fdn.py:195-198`). Using −0.5 as the lower bound instead of −1.0 is a **DECISION FOR IDLE** (it limits the range available today).

## Before / after (VERIFIED, run_all.py on the box; logs in `results/`)

| Test | Before (latest snapshot) | After (p4) |
|---|---|---|
| t08 FDN stability | **FAIL**: dffs +0.98 tail not decaying (−39.6 → −34.8 dB) | **PASS**: last 5 s at −105.7 / −91.8 / −68.6 / −81.2 dB (dffs 0 / +0.98 / −0.98 / as-is) |
| t09 silence CPU (F1, Build's) | PASS 0.47 / 0.59 ms | PASS 0.50 / 0.58 ms |
| t10 Play T30, std 1.8 s | **4.2 / 5.4 / 7.5 / 8.8 / 12.6 s** (500 Hz–8 kHz) | **1.77 / 1.76 / 1.80 / 1.80 / 1.80 s** |
| t10 small 0.8 s | 2.2–5.5 s | 0.72 / 0.81 / 0.78 / 0.78 / 0.79 s |
| t10 hall 4.0 s | 4.9–5.4 s | 3.92 / 3.87 / 4.01 / 4.00 / 4.00 s |
| t11 9 / 11 kHz late T60 (dial 1.8) | **21.7 / 25.0 s** | **1.81 / 1.80 s** |
| t12 Render T30 | 3.5–4.2 s | 1.75 / 1.80 / 1.78 / 1.81 / 1.80 s |
| t13 Play-vs-Render parity | FAIL: T30 2.9–5.9 vs 2.4–2.9 s; direct −3.35 dB | FAIL, but only on tail level (−5.8 dB), octave balance (+5.2 dB at 125 Hz, +4.2 at 1 kHz) and L/R correlation (0.58 vs 0.35). **T30 now agree, and the direct level error is gone.** The remainder is F5 (loop semantics) |
| t14 level sanity | PASS: peak 0.498, RMS −16.4 dB | PASS: peak 0.727, RMS −13.5 dB (**+2.9 dB hotter**) |
| t15 CPU colour on, 1 / 2 sources | 0.585 / 1.003 ms | 0.638 / 1.094 ms (+0.05–0.09 ms; lg multiply plus noise) |
| t18 FDN-only tail null | FAIL +0.8 dB | FAIL +1.4 dB (needs F5) |
| t03 Play goldens | FAIL (SOS colour changed `play_std_unlocked_col`) | FAIL (F3 changes all Play delays). **Expected: regenerate the goldens** with `run_all.py --regen-golden` after review, and record "F3 + SOS colour" |
| t01 / t02 / t04 | PASS | PASS (blob_len 1982) |

Build's own tests on p4 (box, native `.so` in place of the DLL):
- `tests/test_live_stereo.py`: 12/12 pass.
- `tests/test_mic_colour_relative.py`: 15/15 pass.

Package 3 on p4: 38 PASS / 3 FAIL.
- Two of the FAILs are colour bugs that exist in both trees.
- The third is small room 500 Hz T30 −9.8 % against the ±8 % asked for (±10 % in the roadmap).

## Not done here (stays with Idle)

- **F5** (Play consumes the same-sample loop matrix `M`, `build_mix`): diff at `build_support/engine/briefs/live_stereo.F5_same_sample.diff`. It is **not** applied. It is a sound decision (P0.4 loop semantics).
  - The prototype brought the FDN-only null to −47.5 / −48.3 dB.
  - It makes the Play tail about **+5.8 dB** louder, to match Render. On top of the +2.9 dB from F2+F3, that needs a **headroom / makeup decision**.
- **F4** (Play air/shelf coefficients computed at 44.1 kHz while Play runs at 48 kHz) is not in scope. It is noted in package 1.

## Overlap with Build's in-progress files (conflict risk)

Build touched these files on 28 Sep and these patches also touch them:

| File | Build's edit | These patches | Conflict risk |
|---|---|---|---|
| `engine/live_stereo.c` | `run_sos` / `design_sos` (around lines 733–745, 1223+), colour arrays | Line struct (+2 fields at 87), LiveStereo (+1 at 124), init (480), end of `load_room` (714–737, **adjacent to `design_sos` at 733**), `read_peaked` (966) | **Medium**: the load_room hunk sits just above `design_sos` |
| `static/js/live_fdn.js` | colour bank / takeColour | WORKLET_VER line 18, params object line 247 | **High on WORKLET_VER**: bump once, to whatever number follows Build's |
| `static/index.html`, `tests/test_live_stereo.py`, `tests/test_mic_colour_relative.py` | `?v=30` pins | `?v=31` pins | High (same lines); trivial to resolve |
| `render_pipeline.py` | colour_impl / MicColour wiring (around 1394–1408) | F3 at 1426–1440 and 1536–1540; F2 across render / live_fdn_params | Low–medium |
| `app_server.py` | colour_impl key | line 342 only | Low |
| `static/js/fdn_worklet.js` | comment only | BLOB_LEN + one push | Low |
| `engine/fdn.py` | not touched by Build | F2 | None |
| Build's colour files (`mic_colour/*`, `sos_tables/*`) | — | not touched | None |
