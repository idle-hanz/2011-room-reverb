# PERROOMK - the decay dial sets the mid decay in every room (2026-10-19)

Read HANDOVER.md **Current pin (2026-10-19) - F13 SECOND PACK** first. That pin is the baseline: WORKLET_VER 59, `live_fdn.js?v=59`, `pack_room.js?v=52`, `app.js?v=62`, wasm `843a6eb8...`, `live_stereo.c` `bbdf5799...`, Temp DLL `dcde61df...` (read the full sha1s and sizes from the pin), two-source `std_lock18` live MD5 key absent `a5dcacc67a269c234c4b5745899b038e`, explicit false `0e94bd03d899b76b43adf31ae87f0cd2`, empty and stored-centre MD5s, GOLDEN_META, decay-8 cube ceiling 2.40 ms shared-off.

Then read: `roadmap\DECISION_PER_ROOM_K_2026-10-19.md`, `roadmap\OPEN_FAULTS_2026-10-18.md` entry **F14**, the last two blocks of `F13_SECOND_PACK_RUN_2026-10-19.md`, and the last two rows of `BUILD_RUN_LOG.md`.

Line numbers below were read on the F13 tree (2026-10-19 ~20:50 BST). Re-find them by search if they have moved.

## Why (Idle, 2026-10-19)
Idle chose "Per-room k: the dial sets the mid decay in every room, physics only shapes the lows and highs".

In plain words: physics decay sets how absorbent the walls are with one number, `k`. Today `k` is solved once on the boot room (6 x 3 x 8 m) so that the boot room's mid decay equals the dial, and that same k is used in every room. A big room with the same walls rings far longer: the 57 x 34.2 x 97 m hall at dial 8 gets k 0.152005, about 34 s mid design and about 37 s measured T30 (flat 31.5-500 Hz, 27 s at 1 kHz, 16 s at 2 kHz); at dial 1.8 it is about 14.5 s, at dial 4 about 24.4 s. This run solves k for each room so the room's own 500 Hz / 1 kHz mean equals the dial. The lows and highs still come from the physics (air, bass panel term, wall cards).

## Where k lives today (VERIFIED by reading, F13 tree)
- `software\engine\surf_loop.py:304` `k_for_dial(dial)`: bisection, 70 steps, `lo, hi = 1e-5, 4.0`, on `cards_with_treatment(default_surfaces(), [])`, room 6 x 3 x 8, humidity 0.35, target `mean(room_target(..., [500, 1000]))`. Cache `_K_CACHE` keyed on `round(dial, 6)` only.
- `ceiling_card_copy(cards, k, s)` (~285): alpha = `clip(k * card_alpha, 0.01, 0.99) + s * bass_alpha(f)`. Bass is 0 from 500 Hz up, so `s` does not move the mid solve.
- `phys_ceiling_row(W, H, L, cards, dial, bands)` (~331) calls `k_for_dial(dial)` (line 339) and then evaluates THIS room's `room_target`, so `mid` already reports the per-room result. `phys_teff_bands` and `phys_ceiling_pack` (~360) go through it.
- Callers of `phys_ceiling_pack` / `phys_ceiling_row`: `software\render_pipeline.py` ~2493 and ~2505 (Render spec), ~2710 `_ceiling_spec` (Play, used by `_live_surf_pack` ~2716/2726), `software\app_server.py` ~1325 `/api/phys_preview` (docstring ~1310 says "k is solved on the boot room").
- Render and Play both get their sections from Python. The worklet and `live_stereo.c` only receive coefficients. **Expected: no C, wasm or worklet change.**

## Hard rules
1. **Boot room bit-exact.** Boot (6, 3, 8) with default surfaces and no treatment must get exactly today's k (0.775791 at 1.8, 0.333073 at 4, 0.152005 at 8; read the full floats in Step 0) and every boot golden, MD5, d18/d4 prefix, the empty and stored-centre MD5, GOLDEN_META, `T14_PHYS_FDN_RMS` -26.71 dB and AMBIENCE pins stay max-abs 0. Achieve this by making the per-room solve the SAME arithmetic as today when (W, H, L, cards) are the boot ones (same bisection bounds, 70 steps, same `room_target` call, same humidity 0.35, return `hi`).
2. **Explicit `phys_ceiling: false` is exact** everywhere (one source and two source, `0e94bd03...` stays). Physics off never calls the solve.
3. **Only k moves.** Do not touch `s` 0.106194, `BASS_KNOTS`, `ALPHA_MIN/MAX`, `ST.room_target`, `surf_target.py`, makeup, `g_decay`, `line_t60`, `planned_fdn_ms`, the decay lock, T60_TOL 0.08, `small_lock08`, `harmonic_pack`, ROOMTONE, PLACE, SRCDIST, D-PROX, Smooth, the limiter, F13's per-bank packs, or the 2.40 ms ceiling. No Bloom, SL4, Movement or shaped rooms.
4. **No audio-thread change expected.** If Step 0 finds the worklet or C must change, that is a report item, not a quiet edit (see Versions).
5. Tag claims VERIFIED / LIKELY / ASSUMED / PROPOSAL / UNKNOWN.

## What changes (the design)

### A. `software\engine\surf_loop.py`
- New `k_for_room(W, H, L, cards, dial)`: the same bisection as `k_for_dial`, but on `(W, H, L, cards)`; humidity 0.35 as today. Target: `mean(room_target(W, H, L, ceiling_card_copy(cards, k, BASS_S), 0.35, [500, 1000])) == dial`.
- `k_for_dial(dial)` stays as a thin wrapper `k_for_room(6, 3, 8, boot_cards, dial)` so any external caller and the boot pins keep working. Update both docstrings ("same k in every room" is no longer true).
- Cards to solve on: **the room's actual cards** (the ones `phys_ceiling_row` already receives, including treatment), so the mid equals the dial whatever the materials. This is the default from the decision file (open question 1); Step 0 reports how many tests/scenes use non-default cards with physics on.
- Cache: key on `(round(W,6), round(H,6), round(L,6), cards fingerprint, round(dial,6))`. The fingerprint must change when any card or treatment changes (for example a sha1 of the alpha values of each card at the octave bands plus the card keys); do not key on `id(cards)`. Bound the cache (for example 512 entries, LRU) because the page calls `/api/phys_preview` on every drag.
- **Unreachable dials.** With alpha clipped to 0.01..0.99, a tiny room at a very long dial or a huge room at a very short dial may not reach the target. Detect it (the bisection ends at a bound, or the reached mid differs from the dial by more than T60_TOL 0.08 relative). Return the clamped k and set a `reachable: False` flag plus `reached_mid` in `phys_ceiling_row`'s dict. Do not raise. Report the reachable dial range for: boot, 4.5 x 6 x 2.8 (SMALLDECAY room), the 57 x 34.2 x 97 hall, the decay-8 cube (side 340/60 m body from F13), and a 2 x 2 x 2 m closet.
- `phys_ceiling_row` calls `k_for_room(W, H, L, cards, dial)` instead of `k_for_dial(dial)` (line 339). Its docstring "k comes from the boot solve" changes. Nothing else in `phys_ceiling_pack` changes.
- Cost: the solve is 70 `room_target` calls on 2 bands. Report its time per cache miss on this PC; if it is over 50 ms, use a tighter start bracket (for example start from the boot k and expand) but keep the boot path bit-exact (rule 1). It runs at pack-design time, never on the audio thread.

### B. `software\app_server.py` `/api/phys_preview` (~1310-1340)
- Docstring: "k is solved for this room so mean_500_1k equals the dial". Add `reachable` and `reached_mid` to the reply ONLY when physics is on and armed (the off/unarmed replies stay byte-identical). `mean_500_1k` should now equal the dial within 0.5 % in every reachable room.
- `app.js` readout: no change needed (it shows "Physical mid ... s, k ..."). If Idle's open question 2 is answered "show max reachable", that is a later UI run; do not do it here.

### C. Render and Play
- No change beyond A: both already call `phys_ceiling_pack`. Confirm in Step 0 that Render (`render_pipeline.py` ~2493/2505) and Play (`_ceiling_spec` ~2710) pass the same `cards` (both `cards_with_treatment(surfaces, surf_treatment)`), so Render and Play get the same k.
- F13 two-source: both banks use the same room, so the same k. Re-run the F13 per-bank loop-gain probe on every scene in the suite after the change. **Rooms smaller than the boot room now get a SMALLER k (longer decay)**, which moves loop gain toward 0 dB; the cube margin was only 0.039 dB (cube is larger than boot, so it should gain margin; report it).

### D. Tests
1. `3_phase_acceptance_tests\tests\test_s4b_tail_solo_runaway.py:135` `test_s4b_long_decay_no_runaway` - re-baseline as a **decay-slope check** (same three params: hall two sources decay 8, hall binaural decay 4, hall binaural decay 8; Play, TAIL, 20 s IR):
   - finite;
   - levels fall every 2 s after t = 2 s, or are already below -240 dB (unchanged);
   - least-squares slope of the 1 s levels from 2 s to the last window above -240 dB: falling at least `0.5 * 60 / T_max` dB/s and at most `2.0 * 60 / T_min` dB/s, where `T_max` / `T_min` are the max / min of `phys_ceiling_row(...)["t"]` for that scene (the designed per-band T60s, not a fixed number);
   - mid check: the 500 Hz-1 kHz octave T30 of the IR within 15 % of the dial (this is the per-room-k promise);
   - drop the absolute "18-20 s <= -150 dB" floor (it encoded the old boot-calibrated decay). Keep the docstring history and add the new numbers.
2. `test_s4b_play_tail_has_no_line0_comb` (~185): limit at 19.36 ms `0.20 -> 0.23` **for physics on** (the default, key absent). Keep 0.30 for the 2-60 ms max. Boot room, so per-room k should leave the value at 0.2126; re-measure it after the change and write the measured value in the docstring. If the measured value is above 0.23, STOP (do not raise further). Also add an explicit-false row that keeps 0.20 (the dial path).
3. New `software\tests\test_per_room_k.py`:
   - boot k equals today's three k floats exactly (rule 1);
   - for boot, 4.5 x 6 x 2.8, hall, cube and a mid-size room (for example 12 x 5 x 18): `phys_ceiling_row(...)["mid"]` within 0.5 % of the dial at 1.8, 4 and 8 when reachable;
   - changing a card (or a treatment) changes k and keeps mid on the dial;
   - closet at dial 8 and hall at dial 0.3 report `reachable` correctly and stay finite;
   - `/api/phys_preview` POST on the hall: `mean_500_1k` within 0.5 % of the dial; off and unarmed replies unchanged byte for byte;
   - Render vs Play hall, dial 8, one source: octave T30 500 Hz / 1 kHz within 10 % of each other and of the dial.
4. Update every pin that moves (see Expected movers) with old and new values in the docstring. No other test edits.

## Expected movers (list each by name with old / new values)
- Every physics-on (key absent) scene NOT in the boot room with default walls: the hall (all F13 hall windows and the hall listens), the cube (CPU and loop gain), the 4.5 x 6 x 2.8 SMALLDECAY room (F12 re-measure numbers, `small_lock08` if it uses physics on), the 0.71 mirror hall, `/api/phys_preview` k for non-boot bodies.
- Boot room with non-default materials or treatment (k now follows the cards).
- Two-source `std_lock18` key-absent MD5 `a5dcacc6...` ONLY if `std_lock18` is not the boot room with default cards; Step 0 says which. Explicit false `0e94bd03...` must not move.
- Must NOT move: everything in rule 1 and rule 2.

## Versions
- Expected: no change to `live_stereo.c`, wasm, Temp DLL, `fdn_worklet.js`, `live_fdn.js`, `pack_room.js` or `app.js`. **WORKLET_VER stays 59**, `app.js?v=62`, and BLOOM keeps its planned 59 -> 60 and `app.js?v=62 -> 63`.
- If Step 0 finds the worklet must change after all: WORKLET_VER 59 -> 60 here, and then BLOOM must move to **WORKLET_VER 61 and `app.js?v=64`** (`pack_room.js?v=53` unchanged rule). Report it; the parent edits `BLOOM_RUN_2026-10-19.md`, not this run.
- If `app.js` must change (for example a reachable flag in the readout): `app.js?v=63` here and BLOOM's goes to 64. Prefer not to.

## Step 0 - Review (plan mode, high effort, read-only)
Report, tagged:
0. Live pins vs the F13 pin (all sha1s, MD5s, WORKLET_VER, every `?v=`).
1. Every caller of `k_for_dial` / `phys_ceiling_row` / `phys_ceiling_pack` with file:line, and that Render and Play pass the same cards.
2. Today's k floats for boot at 1.8 / 4 / 8 (full repr) and a scratch (no tree edit) per-room solve for boot, 4.5 x 6 x 2.8, hall, cube, closet, 12 x 5 x 18 at 1.8 / 4 / 8: k, reached mid, reachable, per-band T at 63-4000 Hz. Confirm the boot scratch k is bit-equal to today's.
3. Which goldens / MD5s / pins are boot-room-default-cards with physics on (stay) and which are not (move). Name `std_lock18`'s room and cards.
4. Scratch F13 per-bank loop-gain probe with per-room k on every two-source scene and the cube: worst `max_loop_db`. Any scene at or above 0 dB is a STOP for the plan.
5. Solve time per cache miss.
6. Proposed slope bounds for the no-runaway test with the scratch numbers for the three hall params (would they pass?), and the scratch line-0 comb value.
7. Whether any audio-thread / JS file must change (expected none) and the resulting version plan.
8. Any finding that touches the sound or a locked decision: report, do not decide.
Write the review as a ROUND 1 REVIEW block appended to this file only after the parent accepts it.

## Step 1 - Build
1. **Backup first.** `software_backup_<YYYY-MM-DD>_prePERROOMK.zip` in the project root, excluding `.venv` and `__pycache__`. Report the size.
2. A, then B, then D. (C is check-only.)
3. **Prove rule 1 and rule 2 BEFORE the test edits:** boot k bit-equal, one-source and boot goldens max-abs 0, empty and centre MD5 unchanged, d18 / d4 prefix max-abs 0, explicit-false pins exact, two-source explicit false `0e94bd03...`. Report these numbers before going on. Any miss is a STOP.
4. Then the hall check: Play and Render, hall, dial 8, one and two sources, key absent: octave T30 31.5 Hz-8 kHz, and the 1 s windows for 20 s. Mid must be within 15 % of 8 s.
5. Gates, listen files, docs.

## Gates (full suite)
- Full `software` pytest with `software\.venv\Scripts\python.exe` (F13: 155 passed, 1 failed - the known F10 flake `test_colour_stays_finite_and_realtime`, passes alone). Expect +the new file.
- Node tests: `node --test *.mjs` from `software\tests`, 38 pass.
- Selfcheck `software\engine\selfcheck.py` 45/45.
- Harness `run_all.py` t01-t19: 16 pass, 0 fail, 1 skip, 1 pending, 1 xfail.
- Acceptance pytest `handoff_build_support_2\3_phase_acceptance_tests\tests` **with `--slow`**: F13 had 14 failures (the 6 known + 8). After this run expected: the 6 known (same shapes, `test_sh_p1_off_bit_exact` def_1_on 0.012090981006622314 report-only) + the 4 that were already failing before PHYSDEFAULT (name them, same shapes) = 10. The 3 `test_s4b_long_decay_no_runaway` params and `test_s4b_play_tail_has_no_line0_comb` must PASS. Report every failure by name and shape. Also run without `--slow` and report.
- **CPU limit 2.40 ms (2.133 ms where pinned), measured with the wasm bench, not estimated:** t19 flat and Surfaces shared on/off, the decay-8 cube (key absent and explicit false), the hall dial 8 two sources. Report median, mean, p90, silence-late, spikes. Coefficients count does not change, so CPU should not move; any move over 0.05 ms is a report item.
- `/api/phys_preview` on boot, hall, cube, 4.5 x 6 x 2.8, two sources hall: `on`, `k`, `mean_500_1k`, `reachable`.
- Mix tab on a fresh load (free port such as 8766, leave 7860 alone): hall preset, dial 8, the readout says "Physical mid 8.0 s" (or within 0.5 %) with the new k; boot room readout unchanged. No page errors.
- Timing tests that miss under load (`test_p6_two_source_cpu`, t19, the cube, `test_colour_stays_finite_and_realtime`): re-run alone on an idle PC before calling a STOP; report both numbers. Another low-priority background job (the UAD round 3 measurement) may be running on this PC; do not kill it. Do not raise any ceiling.

## STOP rules
1. Boot k is not bit-equal, or any rule-1 pin moves.
2. Explicit false is not exact (rule 2).
3. Any scene's per-bank loop gain reaches 0 dB with the pack on, or any tail stops falling.
4. Hall mid (500 Hz / 1 kHz T30) is more than 15 % off the dial at 1.8, 4 or 8 in Play or Render, or Render and Play disagree by more than 10 %.
5. The line-0 comb re-measures above 0.23, or any limit would need loosening beyond what this prompt names.
6. CPU over 2.40 ms (or 2.133 ms where pinned) after an idle re-run.
7. A new software or acceptance failure that passed on the F13 tree (after an idle re-run for timing tests), or a test edit outside section D and the named movers.
8. The fix needs a change to `s`, the bass knots, `ALPHA_MIN/MAX`, `room_target`, makeup, or any audio-thread file.

## Listen files (for Idle)
If every gate passed, write to `handoff_build_support_2\roadmap\perroomk\listen\`, 24-bit 48 kHz WAV, about 12 s each, limiter off, the clean guitar named in `roadmap\ambience\listen\listen_report.json`, one source, Play path, hall 57 x 34.2 x 97 m, dial 8:
- `hall_d8_before.wav` - the F13 tree (boot-calibrated k 0.152005; render from the backup or with the old `k_for_dial` monkeypatched in-process, say which).
- `hall_d8_after.wav` - this run (per-room k).
- Optional second pair at dial 1.8: `hall_d18_before.wav` / `hall_d18_after.wav`.
Same gain within each pair, no normalising. The hall files are quiet (F13 hall peaks were -36 / -40 dBFS): apply the SAME fixed boost to both files of a pair so the louder one peaks near -3 dBFS, and say the boost in dB. Write `listen_report.json` with the bodies, k, peaks, boost, and per-octave T30. Note for Idle: "before" rings about 34-37 s, "after" should have about 8 s mids with shorter highs.

## Docs
- HANDOVER: new **Current pin (2026-10-19) - PERROOMK**. Dial = mid T60 in every room with physics on; boot unchanged. List the hall / cube / small-room k and mid values, the reachable ranges, any moved MD5 (old -> new), the unchanged pins, WORKLET_VER 59 (or as changed), CPU numbers. Keep the F13 pin as the previous pin.
- BUILD_RUN_LOG: one row in the house format.
- `roadmap\OPEN_FAULTS_2026-10-18.md`: mark **F14 closed** with the date, before/after hall mid, the slope test numbers and the comb value. Keep the BOM if the file has one.
- `roadmap\IDEAS_BACKLOG_2026-10-19.md`: mark the per-room k row landed.
- Do not edit `BLOOM_RUN_2026-10-19.md`; report whether its version plan (60 / 63) still stands.

## Next
Run Step 0 (review only) in a fresh session. Build runs only after the Round 1 review is accepted and appended here.
