# F13 SECOND PACK - source B gets its own physics sections (2026-10-19)

Read HANDOVER.md **Current pin (2026-10-19) - PHYSDEFAULT** first. That pin is the baseline: WORKLET_VER 58, `pack_room.js?v=52`, `live_fdn.js?v=58`, `app.js?v=62`, `sl_room_result.js?v=3`, wasm `a6dbef83527c1531748c9b6fe7c1af0eb53558f8` (278388 B), `live_stereo.c` `5741ceba7e57bdca12187aba6901d2f33b332f2a`, Temp DLL `%LOCALAPPDATA%\Temp\live_stereo.dll` `de0d8f2fc5bbe188ac95a295c4d82295538b1a9e` (285184 B), GOLDEN_META `a362cf5e490089807b39346ba207633b88511548`, empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`, stored-centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`, decay-8 cube ceiling 2.40 ms shared-off.

Then read: `roadmap\OPEN_FAULTS_2026-10-18.md` entry **F13**, `roadmap\MIRROR_PHYS_DIAG_2026-10-19.md`, `roadmap\MIRROR_PHYS_BUILD_DIAG_2026-10-19.md`, the last three blocks of `PHYSDEFAULT_RUN_2026-10-19.md`, and the last two rows of `BUILD_RUN_LOG.md`.

Line numbers below were read on the PHYSDEFAULT tree (2026-10-19 ~15:40 BST). Re-find them by search if they have moved.

## Why (Idle, 2026-10-19)
Idle chose "stopgap now, proper fix next". PHYSDEFAULT landed with the stopgap. This run is the proper fix.

In plain words: when two sources are on, the reverb runs two tanks, one per source. The physics decay is a set of small filters on every delay line, and each filter is fitted to the length of the line it sits on. Today Play fits one set to source A's line lengths and then puts the same set on source B's lines, which are different lengths. In a small room that is a slight mistake. In a big hall some of B's lines then gain level on every pass instead of losing it, and B's tail grows from -83 dB to almost 0 dB in 12 s. Render already fits each tank on its own lines and is correct. The fix gives source B its own fitted set in Play, then removes the stopgap so two-source scenes get the physics decay again, the same way one-source scenes already do.

One source does not change at all: bank B never runs with one source (`live_stereo.c:2551`), and the one-source pack and live dict stay byte-identical.

## Hard rules
1. **One-source is byte-identical.** With `two_sources` off, `live_fdn_params` returns exactly today's dict: no new key, same `surf_sos` values, same `surf_stab`. The bank-A sample path in C stays as it is (same reads, same order of operations). All one-source goldens and MD5s stay exact (rule 7 list).
2. **Explicit `phys_ceiling: false` stays exact** for one source, and for two-source Flat (no sections are sent, no `surf_sos_b`). Two-source `std_lock18` with explicit false must still give live MD5 `0e94bd03d899b76b43adf31ae87f0cd2` and a Play IR max-abs 0 against the PHYSDEFAULT tree.
3. **No retune.** Do not touch `surf_loop.py` (`design_bus`, `phys_ceiling_pack`, `phys_ceiling_row`, `k_for_dial`), `surf_target.py`, `s` 0.106194, `k` 0.775791 / 0.333073 / 0.152005, the bass knots, makeup, `g_decay`, `line_t60`, `planned_fdn_ms`, `harmonic_pack`, `sub_hp`, 1/r, SRCDIST, D-PROX, Smooth, the limiter, 0.7, the 0.55 fold, PLACE, ROOMTONE (HARM_Q 8, HARM_DB -0.3, HARM_MAX 16), the decay lock, T60_TOL 0.08, `small_lock08`, or the 2.40 ms ceiling. Do not start Bloom, SL4, Phase 4 or Movement. Do not fold B's tail into A's tank. Do not put a 32x32 multiply on the audio thread. Do not fetch wasm from the worklet.
4. **No extra per-sample work.** Bank B already runs `SL_SEC` (3) sections per line. Only the coefficient pointer changes. Expected memory: one more 1440-double buffer plus one more coefficient table, about 23 KB of state.
5. **Rejected patches** (both diagnoses): a bus swap of A's sections, a line permutation of A's sections, a denormal flush in `surf_batch`, explicit false in the mirror / sh_p7 / p6 tests, raising 2.40 ms. Any of these is a STOP.
6. Tag claims VERIFIED / LIKELY / ASSUMED / PROPOSAL / UNKNOWN in the report.

## What changes (the design)

### A. Python, `software\render_pipeline.py`
- `_sos_from_spec` (2605-2668) gets an optional `taps_b=None`. With `taps_b`, it designs a second 3x32x3x5 set from `fdn_delays_from_taps(taps_b, sr=rate, c=c, n=n_had, channel=ch)` (the same call the blob uses for B's delays at 3028), with B's own `lg` from B's delays (same formula as 2639-2642), the same `peaks` and the same `spec["rates_for"]`. Peaks still follow the line index modulo 3 (2627-2632), as in Render.
- The loop-gain guard (2650-2652, 2657-2658) takes the worst `max_loop_db` over **both** banks. If either bank is at or above 0 dB, or either bank fails the shape / finite check (2654-2655), the whole pack is refused (`surf_on` 0) so both tanks behave the same. `identity_n` counts both banks.
- The output gains `surf_sos_b` (1440 floats) **only when `taps_b` is given**. When two sources are on, `surf_stab` may also carry `max_loop_db_a` and `max_loop_db_b`; with one source `surf_stab` stays exactly `{"max_loop_db": ...}`.
- The Surfaces branch of `_live_surf_pack` (2706-2774, design loop 2747-2763, guard 2764-2765) gets the same treatment. Best done by having the Surfaces branch call the same per-bank helper, as long as the one-source Surfaces output stays byte-identical (prove it, rule 7).
- `_live_surf_pack` (2688) gets `taps_b=None` and passes it to both branches. The call at 3180 passes `taps_b` only when `two and taps_b is not None` (same test as 3095 / 3198). Lines 3181-3190 copy `surf_sos_b` into `out` when present.
- Render (`engine\fdn.py:1011-1012`, `render_pipeline.py` 1997 / 2040) is already per tank. Do not change it. Step 0 confirms Render's own guard per tank and says whether Play's all-or-nothing refusal can disagree with Render on any scene (report, do not change Render).

### B. Page and harness message
- `software\static\js\live_fdn.js` 395-398: forward `surf_sos_b` as a `Float64Array` when `params.surf_sos_b` has length 1440, else `null`.
- `software\static\js\fdn_worklet.js` 146-162: when the A set loads, write `surf_sos_b` into `live_surf_ptr_b(st)`; **if `surf_sos_b` is absent, copy the A set into the B buffer** (so a stale B from an earlier two-source scene can never survive). Guard on `this.api.live_surf_ptr_b` existing. Then the existing `live_load_surf(st, 1)`.
- **Required harness forward (not a DSP edit, same kind as PHYSDEFAULT's `render_ir.py` forward):** `handoff_build_support_2\3_phase_acceptance_tests\harness\lib\wasm_run.js` `msgFrom` 53-58 builds its own message ("Mirrors live_fdn.js"). Add `if (p.surf_sos_b && p.surf_sos_b.length === 1440) m.surf_sos_b = Float64Array.from(p.surf_sos_b);` inside that block. Without it every harness, acceptance and software test that plays through `wasm_run.js` (including `test_b2_render_length`, `test_b3_limiter`, `test_b4_ramps` and the mirror tests) would send no B set, the worklet would copy A into B, and the bug would still be measured. This is the only harness edit allowed.

### C. C and wasm, `software\engine\live_stereo.c`
- Next to `slBuf` (210) and `slC` (211) add `double slBufB[3 * N * SL_SEC * 5];` and `LS_ALIGN16 double slCB[3][SL_SEC][5][N];` (or one `slC[2][3][SL_SEC][5][N]`, as long as the bank-0 arithmetic is unchanged). `slZ` (212) already has the bank axis.
- Export `live_surf_ptr_b` next to `live_surf_ptr` (1018), with `LS_EXPORT`.
- `live_load_surf` (1027-1045): run the same finite check (1031) and Jury check (1032-1035) on `slBufB` too; any failure leaves `slOn` 0, as today. Copy `slBufB` into `slCB` in the same loop as 1036-1037. Update the comment at 1014-1017.
- `surf_batch` (2235-2250): pick the table by bank, for example `const double (*C)[5][N] = bankB ? st->slCB[b] : st->slC[b];` and read `c0..c4` from it. Bank B's call is 2754 (after the `delayB` read at 2749-2753). Bank-A calls 2557, 2576, 2692 stay as they are. Shared tail on BUS_C goes through the same `surf_batch`, so it is covered.
- Step 0 confirms that B's `lgB` in `read_raw_lg` (2752) is built from `delayB` with the same `line_t60` formula Python uses for B's `lg`. If not, STOP: the Python fit and the C loop would disagree.
- Rebuild the wasm with the header command (live_stereo.c 17-20), with venv zig 0.16, passing arguments as a PowerShell array (PowerShell splits `-Wl,--export=...` on commas):
  `& "software\.venv\Scripts\python.exe" -m ziglang cc -target wasm32-freestanding -O3 -msimd128 -nostdlib -ffreestanding "-Wl,--no-entry" "-Wl,--export-memory" "-Wl,--export=live_stereo" "-Wl,--max-memory=1073741824" -o software/static/wasm/live_stereo.wasm software/engine/live_stereo.c`
- Rebuild the Temp DLL from the same C file (`software\tests\test_live_stereo.py:14` loads it and does not build it):
  `& "software\.venv\Scripts\python.exe" -m ziglang cc -shared -O3 -o "$env:LOCALAPPDATA\Temp\live_stereo.dll" software/engine/live_stereo.c`
- Record new wasm sha1 and size, `live_stereo.c` sha1, DLL sha1 and size.

### D. Remove the stopgap, `software\app_server.py`
- Line 642 goes back to `"phys_ceiling": _b(body["phys_ceiling"], True) if "phys_ceiling" in body else True,`. Delete the stopgap comment at 641; keep 640. `two_sources` (528) is no longer used on this line.
- `/api/phys_preview` (1307-1339) then returns real `k`, `mean_500_1k` and `bands` for two-source bodies. Do not add a second default anywhere in `render_pipeline.py`.

### E. Mix-tab readout, `software\static\js\app.js`
Cause of today's "Physical mid NaN s, k NaN": `/api/phys_preview` returns `on: false, armed: true` with no `k` or `mean_500_1k` (1321-1322), and `pullPhysPreview` (697-727) only checks `data.armed` before formatting (710-720). After D, two-source bodies return real numbers, but the page must never print NaN:
- In `pullPhysPreview`, if `data.on === false`, show a plain line such as "Physical ceiling is off for this scene." (or hide the readout); if `k` or `mean_500_1k` is not a finite number, show "Physical ceiling" without numbers. No other app.js change.
- Bump `app.js?v=62` -> `63` (index.html 969, `software\tests\test_quick_pins.py` 75, `software\tests\test_b2_render_length.py` 56) because app.js changes. If Step 0 finds a reason not to change app.js, leave v=62 and say why.

### F. Tests (new and updated)
1. **`software\tests\test_physdefault_two_source.py` is rewritten** (it currently asserts the stopgap, lines 59-74). New guard:
   - `std_lock18` + `two_sources: True`, key absent: `params_from_body` gives `phys_ceiling` True; the live dict has no `phys_ceiling` field, `surf_on` 1, `surf_sos` and `surf_sos_b` both length 1440, and `surf_stab` worst `max_loop_db` < 0 for **both** banks (every line of A and B below 0 dB loop gain).
   - Same body with explicit false: `surf_on` 0 (or absent), no `surf_sos_b`, live MD5 `0e94bd03d899b76b43adf31ae87f0cd2`.
   - One source, key absent: dict has no `surf_sos_b`, `surf_sos` 1440, `surf_on` 1, and the T30 `PIN` import check (lines 85-97) stays.
2. **New hall no-runaway test** (software\tests, for example `test_f13_hall_no_runaway.py`): the mirror-test hall from acceptance `test_mirror_symmetry.py` (`HALL` lines 20-26: 57 x 34.2 x 97 m, `decay_s` 0.71, lock on), `_body("twoB")` (two sources, `mirror_b`, `source_balance` +1, B only), key absent, Play IR 12 s through `ctx.play_ir`. 1 s RMS windows (as `%TEMP%\mirror_diag\play_probe.py` `win_db`) must fall every second (ignore windows below -300 dB), and window 12 must be at least **40 dB** below window 1. Today's tree: -83.1 ... -0.7 dB (rising). Also assert `_body("twoA")` still falls. Report all 12 windows for A and B.
3. **New two-source Render vs Play check** (software\tests): the same hall, two sources mirrored, key absent. Render through a direct `render()` call with `two_sources=True` and both dry channels set (the harness `render_ir.py:44` forces `two_sources=False` and cannot do this; MIRROR_PHYS_BUILD_DIAG "Render" section shows how). Gates: Render mirror metrics within `test_mirror_symmetry.TOL`; Play twoA vs twoB mirror metrics within the same TOL; Play vs Render T30 per octave 125 Hz-4 kHz within 10% (the t13 / `test_p0_4` gate). Report every number.
4. **Surfaces two-source mirror** (`decay_mode: surfaces`, hall and boot, explicit false so only Surfaces sections run): Play twoA vs twoB within TOL. Report before and after.
5. The four acceptance tests (`test_mirror_play_two_sources_hard` x2, `test_mirror_play_two_sources_centre_is_self_mirror`, `test_sh_p7_mirror`) must pass **as they are**, key absent, physics on. Do not edit them.
6. Version asserts for WORKLET_VER 58 -> 59 (below). No other test body changes. Any other test edit is a STOP.

## Pins
**Must stay exact (any move is a STOP):**
- `play_std_lock18_byp` `d011bafca80f4e46ae768db40becd762e78dcada`, `play_std_lock18_col` `d9470bfad67211180fedc1a07cd2352eaf4b14c7`, `play_std_unlocked_byp` `91738c70220b4edce512aebe3548dfdbd894cc41`, `play_std_unlocked_col` `a0ae72d9fb690cb7b3bbd54632abc466cefa0d24`, `render_std_unlocked_byp` `2a806e334e06cc475868d4c3da3fc78431c9a0aa` (`test_quick_pins.py` 32-36, `test_smix_desk.py` 44-48). Re-render them with the new wasm and compare max-abs 0; do not re-save.
- GOLDEN_META `a362cf5e490089807b39346ba207633b88511548` (`test_quick_pins.py` 38).
- Empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88` (`test_quick_pins.py` 39, `test_s_audit_api.py` 25, `test_b6_heights.py` 45).
- Stored-centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30` (`test_quick_pins.py` 40, and `_ORTF_PLUS_C_LIVE_MD5` in `test_s_audit_api.py` 26). This body is **one source** (`third_mic` centre), so it must not move.
- `d18.f32` `4f936928a3650a808005d53f76a87470f2549152`, `d4.f32` `919c333452defcf40075b29118154922c1caccb2` (prefix max-abs 0, `test_b2_render_length.py` 168-183).
- The explicit-false AMBIENCE pins in the Current pin (GOLDEN_META `a19329940c4fb471ae0b7ef8ef6a00e9c00d2fb9`, lock18 byp `0aa7f69d...`, col `b9aee4bd...`, empty `ce009a4c...`, centre `35972c29...`).
- T30 pin `test_physdefault_t30.py` (2.271852 / 2.214763 / 2.017107 / 1.561790 / 1.160893 / 0.853239 s), T14 rows (-24.55 dB explicit false, -26.71 dB physics), corrected F9 row, `T60_TOL` 0.08, `small_lock08`.
- Two-source `std_lock18` explicit false live MD5 `0e94bd03d899b76b43adf31ae87f0cd2` and its Play IR.

**Allowed to move (report old -> new):**
- Wasm sha1 / size, `live_stereo.c` sha1, Temp DLL sha1 / size, `render_pipeline.py`, `app_server.py`, `fdn_worklet.js`, `live_fdn.js`, `app.js`, `index.html`, `wasm_run.js` sha1.
- WORKLET_VER 58 -> 59: `software\static\js\live_fdn.js` 20; `index.html` 964 `live_fdn.js?v=59`; `test_quick_pins.py` 73-74; `test_live_stereo.py` 614 and 616; `test_mic_colour_relative.py` 989 and 990. Acceptance `test_p1_blob.py` 17-24 checks they agree; run it. `pack_room.js?v=52` is unchanged (sections are off-blob).
- `app.js?v=62` -> `63` (section E).
- Two-source live MD5s, by name: two-source `std_lock18` key absent (`0e94bd03d899b76b43adf31ae87f0cd2` -> new; it gains `surf_on`, `surf_sos`, `surf_sos_b`); any two-source body with `decay_mode: surfaces` (gains `surf_sos_b`, even with explicit false). No test pins a two-source live MD5 today (VERIFIED by search); record the new `std_lock18` two-source value in the Current pin.
- Two-source Play output with physics on, or with Surfaces on. Two-source Render with physics on returns (it was forced off by the stopgap).

## Step 0 - Review only (plan mode, high effort, no edits)
Fresh session, plan mode, high effort, report only. Read this file and the files listed at the top. Check every line number and claim against the live tree, and answer:
- Is every place that builds or reads the Play section message covered (`render_pipeline.py`, `live_fdn.js`, `fdn_worklet.js`, harness `wasm_run.js`, any other Node or Python driver)? Is there any path that posts `surf_sos` without `surf_sos_b` on a two-source scene after the change?
- Does C build `lgB` from `delayB` with the same formula as Python's B `lg` (rule C)? Does any other C path (shared tail, `mix1`, `mixB`/`anyDffsB`) run bank B outside `surf_batch(..., 1, ...)` with section coefficients?
- Can the Surfaces branch share the per-bank helper and stay byte-identical for one source? If not, propose the smallest separate edit.
- Which two-source bodies does the suite exercise (t19, decay-8 cube, mirror, sh_p7, `test_colour_stays_finite_and_realtime`), and which of them now gain sections? Expected CPU change for each.
- Does any scene in the suite refuse the two-source pack (loop gain >= 0 on B but not A)? List it; that scene would fall back to no sections for both tanks.
- Does `pullPhysPreview` need the app.js guard once D lands (any remaining `on: false` path with a ticked box)?
- Any conflict with `BLOOM_RUN_2026-10-18.md`, which also plans WORKLET_VER 58 -> 59 and `app.js?v=62`.
Write the review as a ROUND 1 REVIEW block appended to this file only after the parent accepts it.

## Step 1 - Build
1. **Backup first.** `software_backup_<YYYY-MM-DD>_preF13.zip` (the run day's date) next to the earlier backups in the project root, excluding `.venv` and `__pycache__`. Report the size.
2. Python (A), then the page and harness message (B), then C (C). Rebuild the wasm and the Temp DLL.
3. **Prove rules 1 and 2 BEFORE removing the stopgap**, with the stopgap still in: one-source goldens max-abs 0 with the new wasm, empty and centre MD5 unchanged, d18 / d4 prefix max-abs 0, explicit-false AMBIENCE pins exact, two-source explicit false `0e94bd03...` and Play IR max-abs 0. Then a scratch check with the stopgap bypassed in-process (no tree edit): the hall twoB 12 s windows now fall. Report these numbers before going on. Any miss is a STOP.
4. Remove the stopgap (D). Then the app.js readout guard (E). Then the tests (F) and version asserts.
5. Gates (below). Then the listen files (optional, below). Then the docs.

## Gates
- Full `software` pytest (PHYSDEFAULT: 151 passed, 1 failed `test_colour_stays_finite_and_realtime` timing, passed alone). Use `software\.venv\Scripts\python.exe`.
- Node tests: `node --test *.mjs` from `software\tests`, 38 pass.
- Selfcheck `software\engine\selfcheck.py` 45/45.
- Harness `run_all.py` t01-t19: 16 pass, 0 fail, 1 skip, 1 pending, 1 xfail. **t19 two-source CPU** (now with physics on): shared-off median and silence-late under **2.40 ms**, shared-on under 2.133 ms. Expected near 1.62 ms; physics added about 0.02 ms in the diagnosis.
- Decay-8 cube (shared off, two sources, colour on, Surfaces on), key absent (now physics on) and explicit false: both at or under 2.40 ms. Report median, mean, p90, silence-late, spikes, `surf_sos` / `surf_sos_b` lengths.
- Acceptance pytest `handoff_build_support_2\3_phase_acceptance_tests\tests`: back to the **6 known failures** (the five F11 tests plus `test_lock_no_air_on_fdn_return_play`, same shapes, `test_sh_p1_off_bit_exact` def_1_on 0.012090981006622314 report-only), with `test_mirror_play_two_sources_hard[fdn-MEASURED_SHELF]`, `[fdn-BYPASS]`, `test_mirror_play_two_sources_centre_is_self_mirror`, `test_sh_p7_mirror` and `test_p6_two_source_cpu` **passing with physics on** (key absent). Report their null / band / ILD / T30 numbers.
- New tests F1-F4 pass. Report the hall windows, the two-source Render vs Play numbers, and the Surfaces mirror numbers.
- Memory: report `live_bytes(48000)` before and after (expected about +23 KB).
- `/api/phys_preview`: one source key absent, explicit false, two sources key absent, two sources explicit false. Report `on`, `k`, `mean_500_1k`.
- Mix tab on a fresh load (free port such as 8766, leave 7860 alone): load a stereo file so the Two sources button enables, turn two sources on, and confirm the readout shows "Physical mid ... s, k ..." with real numbers and never NaN. Untick the box: the readout hides. No page errors.
- **Timing tests that miss under load** (`test_p6_two_source_cpu`, t19, the cube, `test_colour_stays_finite_and_realtime`): re-run alone on an idle PC before calling a STOP; report both numbers. Another low-priority background job may be running on this PC; do not kill it. Do not raise any ceiling.

## STOP rules
1. Any pin in the "must stay exact" list moves, or a one-source live dict gains a key.
2. Explicit false is not exact (rule 2).
3. Any two-source bank has a line at or above 0 dB loop gain with the pack still on, or the hall twoB tail does not fall.
4. A mirror / sh_p7 test still fails with the key absent after the fix, or two-source Render vs Play misses its gates.
5. CPU: t19 or the cube over its ceiling after an idle re-run.
6. A new acceptance or software failure that passed on the PHYSDEFAULT tree (after an idle re-run for timing tests), or any test edit outside section F.
7. The fix would need a change to `surf_loop.py`, `s`, `k`, makeup, or any rejected patch (rule 5), or C's `lgB` disagrees with Python's B `lg`.
8. A scene that had sections on PHYSDEFAULT now refuses the pack (both tanks lose sections). Report the scene and both banks' `max_loop_db`.

## Listen files (optional, for Idle)
If every gate passed, write short files to `handoff_build_support_2\roadmap\f13\listen\`, 24-bit 48 kHz WAV, about 8 s each, limiter off, the clean guitar from `roadmap\ambience\listen\listen_report.json` (or the AMBIENCE dry file it names), two sources on, Play path:
- `boot_two_phys.wav` (boot room, dial 1.8, key absent) and `boot_two_dial.wav` (same, explicit false).
- `hall_two_phys.wav` and `hall_two_dial.wav` (57 x 34.2 x 97 m; use dial 4, `sx` 24 if the 0.71 mirror hall is too long to hear in 8 s, and say which).
Same gain within each A/B pair, no normalising; if a file clips, scale both files of that pair by the same factor and say so. Write `listen_report.json` with the bodies, peaks and per-octave T30. Note for Idle: in a big hall the physics decay is much longer than the dial number (the dial picks wall hardness on the boot room), so the hall pair will differ a lot. That is the existing design, not this fix.

## Docs
- HANDOVER: new **Current pin (2026-10-19) - F13 SECOND PACK**. Two sources get physics again; each tank has its own sections in Play. List every new sha1 and size, WORKLET_VER 59, `live_fdn.js?v=59`, `app.js?v=63` (or 62), the new two-source `std_lock18` live MD5, CPU numbers, the hall windows, and the unchanged one-source pins. Remove the stopgap and "NaN" wording from the pin and from the top paragraph ("Two sources force it off"). Keep the PHYSDEFAULT pin as the previous pin.
- BUILD_RUN_LOG: one row in the house format.
- OPEN_FAULTS_2026-10-18.md: mark **F13 closed** with the date, the fix, the before/after hall windows and the mirror numbers. Update the F11 paragraph's last sentence ("cleared by the F13 stopgap") to say the mirror tests now pass with physics on. Keep the BOM if the file has one.
- Do not edit `BLOOM_RUN_2026-10-18.md`; report that its version bumps (WORKLET_VER 59, `app.js?v=62`) are now taken and must move to 60 / 64.

## After this run
Bloom runs from the new Current pin. Its version numbers move up by one.

## Next
Run Step 0 (review only) in a fresh session. Build runs only after the Round 1 review is accepted and appended here.

## DECISION (Idle, 2026-10-19 15:38) - BINDING
Two-source Surfaces IS fixed in this run (section A's Surfaces bullet stays). Two-source Surfaces output moving, even with physics off, is an expected and allowed mover; list it by name in the report. This overrides the F13 entry's 'Do not fix Surfaces here' line, which was about the stopgap only.

## ROUND 1 REVIEW ACCEPTED (2026-10-19 16:40) - BINDING, overrides earlier sections where they differ
Step 0 found no STOP. Pins verified: wasm a6dbef83527c1531748c9b6fe7c1af0eb53558f8, live_stereo.c 5741ceba7e57bdca12187aba6901d2f33b332f2a, Temp DLL de0d8f2fc5bbe188ac95a295c4d82295538b1a9e. Probe: every two-source scene's own A and B packs stay under 0 dB (worst cube Surfaces -0.03858 dB, hall physics -0.28101 dB); no scene refuses.
Constraints for Step 1:
1. Pass taps_b to the pack whenever `two and taps_b is not None` (the 3095 test), not the 3198 test that also needs stand_b/prep_b.
2. Surfaces branch shares _sos_from_spec(make_spec(...)). Copy into the live dict ONLY surf_sos, surf_sos_b, surf_keep, surf_peaks, and surf_stab. One-source surf_stab stays {"max_loop_db": ...}; max_loop_db_a / max_loop_db_b only when taps_b is passed. identity_n, ceiling_hz and ceiling_t stay out of the live dict. Surfaces keep-cut stays make_spec's default KEEP_CUT_BELOW_HZ (30 Hz).
3. bank B uses its stored lgB from delayBT (same formula as Python); the gliding delayB is not put into the gain. No change there.
4. The worklet copy of A into B when surf_sos_b is absent is REQUIRED (a zero B buffer passes the Jury check and would silence bank B). Forward surf_sos_b in live_fdn.js, fdn_worklet.js AND harness lib\wasm_run.js msgFrom. roadmap\robotic_1240\wasm_run_file.js and the SL prebuild benches are outside the suite: leave them, note them in BUILD_RUN_LOG.
5. Section E (app.js NaN guard) is DROPPED. Once the stopgap is gone, phys_preview returns real k and mid values for two sources. Instead add a pytest that POSTs a two-source locked body to /api/phys_preview and asserts on:true with finite k and mean_500_1k. app.js?v stays 62. Bloom therefore inherits WORKLET_VER 60 and app.js?v=63; report that, do not edit BLOOM_RUN.
6. Expected movers also include every key-absent two-source body that now gains a physics pack: test_mic_colour_relative 962-977, test_s5_surf_tail 452-453, hash_scenes two_sources, and the acceptance two-source scenes in test_s3_source_b, test_binaural_play_and_gaps and test_colour_sos. List each by name with old/new values. Explicit-false flat std_lock18 two-source MD5 0e94bd03d899b76b43adf31ae87f0cd2 must stay exact.
7. The hall no-runaway test (F3) must call render() directly, because render_ir.py:44 forces two_sources=False.
8. Cube: the decay-8 cube body is reconstructed (side 340/60 m, server-default source). If a recorded cube body exists anywhere in the tree or logs, re-run the loop-gain probe on it before building; its margin is only 0.039 dB. Report the result in the run log.
9. Measure CPU with the wasm bench, don't estimate it: t19 flat/shared on and off, t19 Surfaces, cube, hall. Limits stay at 2.40 ms (2.133 ms where pinned). Timing misses are re-run alone before any STOP.
Step 1 may now start.
