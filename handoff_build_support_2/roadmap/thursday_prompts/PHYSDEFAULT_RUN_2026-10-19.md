# PHYSDEFAULT - physics path on by default (2026-10-19)

Read HANDOVER.md **Current pin (2026-10-18, AMBIENCE)** first. That pin is the baseline: WORKLET_VER 58, `live_fdn.js?v=58`, `app.js?v=61`, `pack_room.js?v=52`, wasm `a6dbef83527c1531748c9b6fe7c1af0eb53558f8`, `live_stereo.c` `5741ceba7e57bdca12187aba6901d2f33b332f2a`, five TLAW goldens (AMBIENCE re-pins), GOLDEN_META `a19329940c4fb471ae0b7ef8ef6a00e9c00d2fb9`, empty MD5 `ce009a4ccc3d85f87aa6547f59eda0e4`, stored-centre MD5 `35972c29a63dbe5b33d228b68e6e575b`, decay-8 cube ceiling 2.40 ms shared-off.

## Why (Idle, 2026-10-19 07:57)
SMALLDECAY locked `phys_ceiling` off until Idle had listened. He listened to the AMBIENCE files (`roadmap\ambience\listen\`, B_phys / C_phys_dial4 / D_phys_dial8), loved them, and chose (widget): **make the physics path the default.** The bass panel term `s = 0.106194` and the wall-hardness `k` (0.775791 / 0.333073 / 0.152005 at dials 1.8 / 4 / 8) stay exactly as AMBIENCE landed them. Idle already accepted that at dial 8 the lows are thinner than the mids.

In plain words: the "Physical ceiling" tick box on the Room page now starts ticked, and a fresh session, an empty request, Play and Render all use the physics decay unless someone unticks it. Nothing about how the physics path sounds changes. Only its starting position changes.

This supersedes the HANDOVER lines "`phys_ceiling` stays off. Do not flip `phys_ceiling`." for this run only. The build rewrites those lines in the new Current pin.

## Hard rules
1. **Only the default changes. No DSP change.** No edit to `surf_loop.py`, `surf_target.py`, `live_stereo.c`, the wasm, `fdn_worklet.js`, `phys_ceiling_pack`, `phys_ceiling_row`, `design_bus`, `s`, `k`, the bass knots, `chamber_to_specular`, makeup, `g_decay`, `line_t60`, `planned_fdn_ms`, or `harmonic_pack`. Wasm and `live_stereo.c` sha1 must be unchanged at the end.
2. **Explicit false is bit-exact, proven FIRST.** Before any re-pin, with the flip in place, a body with explicit `phys_ceiling: false` (and `sub_hp` absent, so on) must reproduce today's AMBIENCE pins exactly: the five TLAW goldens max-abs 0 against the current files, empty-body-with-explicit-false MD5 = `ce009a4ccc3d85f87aa6547f59eda0e4`, stored-centre-with-explicit-false MD5 = `35972c29a63dbe5b33d228b68e6e575b`, `d18.f32` / `d4.f32` prefix max-abs 0. The live dict grows no key (`phys_ceiling` is still not a live-dict field). Report these numbers before touching any pin. Any miss is a STOP.
3. **Absent key = on.** `app_server.py` `params_from_body` line 641 becomes the same shape as `sub_hp` on line 643: `_b(body["phys_ceiling"], True) if "phys_ceiling" in body else True`. Fix the comment on line 640. An explicit false stays off.
4. **`sub_hp` stays default on.** Not touched.
5. **Play and Render both follow.** Both read `p["phys_ceiling"]` from `params_from_body` (`render_pipeline.py` `render()` 2459 via `app_server.py` 1135; `_ceiling_spec` 2670-2684 and `_live_surf_pack` 2687-2700 for Play). Do not add a second default anywhere in `render_pipeline.py`. Note `render()` line 2459 still pops with a `False` default for direct Python callers. Leave it: tests and the harness call `render()` with explicit kwargs. Step 0 must list every direct `render()` / `render_fdn_ir` caller that relies on that False and say whether it is a test helper (fine, report) or a user path (STOP).
6. **Client matches server.** `software/static/js/app.js` line 128 `phys_ceiling: false` becomes `true`. `software/static/index.html` line 307 `<input type="checkbox" id="phys_ceiling" />` gets `checked`, same as `sub_hp` on line 311. `paintPhysReadout` (app.js 676-) already paints from state; confirm the readout and `/api/phys_preview` fetch run on boot with the box ticked. Acceptance test `test_p0_engine.py::test_p0_5_server_defaults_equal_client_state` must agree after the flip.
7. **`/api/phys_preview`** (`app_server.py` 1306-1336) goes through `params_from_body`, so an empty body now returns `on: true` with `k`, `s`, and the row. Explicit false still returns `on: false`. Check both and report.
8. **T60_TOL 0.08 and `small_lock08` unchanged, else STOP.** If harness t10 `small_lock08` or any test using `T60_TOL` fails because the physics row is no longer the dial, that is a STOP. Do not loosen, do not add explicit false to make it pass without Idle.
9. **CPU.** Decay-8 cube (shared off, two sources, colour on, Surfaces on) at or under **2.40 ms** with the new default (keys absent) and with explicit `phys_ceiling: false`. AMBIENCE measured 1.743 ms (both on) and 1.717 ms (both off). Over is a STOP. Do not raise the ceiling.
10. **No other test moves.** Only the pins listed below may change. If any other test, assert, or harness row moves, STOP and report the test, the line and the before/after.
11. **No listed fault may worsen** (OPEN_FAULTS_2026-10-18.md F9-F12, and F4/F5/F8 in OPEN_FAULTS_2026-10-10.md). F9 is the physics path's own +20 % / -12 % decay bias. It now ships by default; it must not grow (re-measure boot dial 1.8 T20 row, report against the F9 numbers, a band more than 0.02 relative worse is a STOP). F12 (926 Hz ring) re-measure is report-only unless it is longer than 3.8 s (STOP).
12. Do not retune 1/r, SRCDIST, D-PROX, Smooth, the limiter, 0.7, the 0.55 fold, Surfaces, PLACE, ROOMTONE (HARM_Q 8, HARM_DB -0.3, HARM_MAX 16), makeup, `g_decay`, or the decay lock. Do not start SL4, Phase 4, Movement or Bloom.
13. A version bump only where a browser-loaded file changes. Expected: `app.js` 61 -> 62 (state default) and `index.html` (checkbox). `live_fdn.js` / WORKLET_VER 58 and `pack_room.js?v=52` change **only** if those files change. Step 0 confirms whether they need to (expected: no, because `phys_ceiling` is server-side and not on the pack message). Do not bump a file that did not change.

## Step 0 - Review only (plan mode, high effort, no edits)
Fresh session, plan mode, high effort. Read this file, the HANDOVER Current pin, `BUILD_RUN_LOG.md` tail, `AMBIENCE_RUN_2026-10-18.md`, `SMALLDECAY_RUN_2026-10-15.md`, `OPEN_FAULTS_2026-10-18.md`, and `roadmap\ambience\listen\listen_report.json`. Check every line number and claim here against the real code, and answer:
- Every place `phys_ceiling` is read or defaulted (server, `render_pipeline.py`, `surf_loop.py`, `app.js`, `index.html`, harness `lib\dump_params.py` / `lib\pack.py` / `lib\render_ir.py`, `/api/phys_preview`). Does the harness get the new default through `params_from_body`, or does any harness path pass its own default?
- Which goldens actually move. Expect the two `lock18` goldens and both live MD5s (lock armed by default) to move, and the three `unlocked` goldens to stay put (pack omitted with the lock off). Confirm or correct from the code.
- Which tests assume T60 equals the dial on a default body (`T60_TOL`, harness t10 `small_lock08`, `test_b2_render_length.py` T30 / duration checks, decay-lock tests). For each: does it move? If a test needs explicit `phys_ceiling: false` to keep testing the dial path, list it as a proposed test edit for Idle, not a silent fix.
- Does `test_b2_render_length.py` (168-183) move? `planned_fdn_ms` still reads the dial, so length should hold, but the prefix content moves if the default body arms the pack.
- Whether `pack_room.js` / `live_fdn.js` need a change at all.
Write the review as a ROUND 1 REVIEW block appended to this file only after the parent accepts it.

## Step 1 - Build
1. Backup `software_backup_2026-10-19_prePHYSDEFAULT.zip`, excluding `.venv` and `__pycache__`. Report size.
2. Flip the three defaults (server line 641, `app.js` 128, `index.html` 307). Fix any docstring that says "default off" (`render_pipeline.py` 2454, `app_server.py` 640).
3. **Prove rule 2 first** and report the numbers.
4. Re-render and re-pin (list below). Report every pin old -> new.
5. Gates (below). Report CPU, F9 row, F12 ring, `/api/phys_preview` both ways.
6. Write the new HANDOVER Current pin (2026-10-19, PHYSDEFAULT): `phys_ceiling` defaults **on**, explicit false is off and bit-exact with the AMBIENCE pins; keep the AMBIENCE pins listed as "explicit-false pins". Remove "Do not flip `phys_ceiling`" from the top paragraph and from the pin. Add a BUILD_RUN_LOG row.
7. Note in the physics UI that the checkbox now starts ticked (the `physCeilingRow` tick box shows checked on a fresh load; screenshot or Playwright check).

## Re-pin list (old -> new, report each)
- Five TLAW goldens in `handoff_build_support_2\3_phase_acceptance_tests\harness\golden\` and `GOLDEN_META.json` (old `a19329940c4fb471ae0b7ef8ef6a00e9c00d2fb9`; reason `PHYSDEFAULT phys_ceiling default on, 2026-10-19`). Only files that really move get re-saved; an unmoved golden keeps its sha1.
- `software\tests\test_quick_pins.py` 31-37 `TLAW_SHA1`, 38 `GOLDEN_META_SHA1`, 39 `EMPTY_MD5` (`ce009a4c...`), 40 `CENTRE_MD5` (`35972c29...`).
- `software\tests\test_smix_desk.py` 43-49 `GOLDEN_SHA1`.
- `software\tests\test_s_audit_api.py` 25 `_DEFAULT_LIVE_MD5`, 26 `_ORTF_PLUS_C_LIVE_MD5`.
- `software\tests\test_b6_heights.py` 45 `_DEFAULT_LIVE_MD5` (empty MD5 only).
- `software\tests\test_b2_render_length.py` 168-183: `d18.f32` / `d4.f32` prefixes (first 72001 frames). Re-save only if the default body now arms the pack and the prefix moves. Prefix max-abs against the re-saved file must be 0.
- Version asserts (only if the file changed, rule 13):
  - `app.js?v=61` -> `62`: `software\static\index.html` 969, `software\tests\test_quick_pins.py` 75, `software\tests\test_b2_render_length.py` 56.
  - WORKLET_VER 58 (expected unchanged): `software\static\js\live_fdn.js` 20, `index.html` 964, `test_quick_pins.py` 73-74, `test_live_stereo.py` 614 and 616, `test_mic_colour_relative.py` 989 and 990, acceptance `test_p1_blob.py` 18-23 (reads them).
  - `pack_room.js?v=52` (expected unchanged): `index.html` 963.

## Gates
- Full `software` pytest.
- Node tests (38) and selfcheck (45/45).
- Harness `handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py` (t01-t19). AMBIENCE: 16 pass, 0 fail, 1 skip, 1 pending, 1 xfail.
- **Also the separate acceptance pytest suite** `handoff_build_support_2\3_phase_acceptance_tests\tests` (137 collected; CLEANUP 93 passed, 28 skipped, 11 xfailed, 5 failed). Run it **before the flip** (on the AMBIENCE tree) and **after**. This settles fault **F11**: report the state of each of the five (`test_k1...[ms]`, `test_p0_5_server_defaults_equal_client_state`, `test_s3_mirror_b_follows_a_directivity`, `test_s3_b_pose_single_rule`, `test_sh_p1_off_bit_exact`), whether the test or the code is stale, and any test whose result changed between the two runs. Do not fix the five in this run. A new failure after the flip that was passing before is a STOP.
- CPU (rule 9), F9 row, F12 ring.

## STOP rules
1. Explicit `phys_ceiling: false` not bit-exact with the AMBIENCE pins (rule 2).
2. Any test or harness row outside the re-pin list moves (rule 10), including T60_TOL / `small_lock08` (rule 8).
3. CPU over 2.40 ms either way.
4. Any listed fault worsens (rule 11), or a new acceptance-suite failure after the flip.
5. Any change would need a DSP edit or a change to `s` / `k`.
6. A user path still defaults off after the flip (Play and Render disagree on an empty body).

## After this run
Bloom (`BLOOM_RUN_2026-10-18.md`) runs next. Its pins come from the new HANDOVER Current pin written by this run, not from AMBIENCE.

## Next
Run Step 0 (review only) in a fresh session. Build runs only after the Round 1 review is accepted and appended here.


## LOCATION NOTE (2026-10-19)
The Physical ceiling checkbox lives on the Mix tab (per HANDOVER and the AMBIENCE build, which clicked it there), not the Room page. Step 0: confirm in index.html/app.js and treat any 'Room page' wording above as Mix.


## IDLE DECISION (2026-10-19 08:37), BINDING: decay-accuracy tests (amends rules 8 and 10)

After the flip, the default bodies take the physics path. F9 measures that path at about +20% from 500 Hz up (+19.7/+21.9/+25.8/+22.6% at 500/1k/2k/4k on boot `std_lock18`), so the following tests, which assume T30 = dial ±15%, would fail:
- harness `t12_t60_render` (run_all.py ~271)
- harness `t10_t60_play` scene `std_lock18` (run_all.py ~251–261)
- harness `t10` `small_lock08`
- `hall_lock40` (and any other lock-armed T60/T60_TOL decay check Step 0 finds)

Option (a), approved by Idle:
1. **Keep these tests on the dial path.** Each one sends an explicit `phys_ceiling: false` so it keeps testing the dial path with its tolerances unchanged (T60_TOL 0.08 and ±15% stay). List every test edited, with file:line. These edits are allowed and are NOT a STOP. Any OTHER change to a tolerance or expectation is still a STOP.
2. **Add one new physics-row pin test.**
   - Scene: boot `std_lock18` with the default body (physics on).
   - Pin: the measured per-octave T30 from 125 Hz to 4 kHz, at the values measured in this run, within 0.02 relative.
   - Purpose: it guards F9 from getting worse, and it is the test the F9 fix will deliberately re-pin later.
   - Report the pinned values.
3. Rule 10's "any test outside the re-pin list moves" now excludes the explicit-false edits in point 1.
4. Step 0 must find every caller of these checks, and every other lock-armed decay test, and confirm whether each passes `params_from_body` (physics on after the flip) or calls `render()` directly (stays off).

Note: F9 is being investigated read-only in parallel (`roadmap\F9_DIAG_2026-10-19.md`). Its fix will run as a separate prompt after PHYSDEFAULT and before BLOOM.


## ROUND 1 REVIEW ACCEPTED (2026-10-19 08:52), BINDING; overrides earlier blocks where they differ

Pins verified: wasm a6dbef83527c1531748c9b6fe7c1af0eb53558f8 (278388 B); live_stereo.c 5741ceba7e57bdca12187aba6901d2f33b332f2a; GOLDEN_META a19329940c4fb471ae0b7ef8ef6a00e9c00d2fb9; WORKLET_VER 58; index.html 963 pack_room.js?v=52, 964 live_fdn.js?v=58, 969 app.js?v=61.

1. **Location.** The checkbox is on the Mix tab (#mixViews; #phys_ceiling at index.html 306–307). Every "Room page" wording here and in BLOOM_RUN means Mix.
2. **Three product defaults only.**
   - app_server.py 641: `_b(body["phys_ceiling"], True) if "phys_ceiling" in body else True`, with the comment at 640 updated.
   - app.js 128: `phys_ceiling: true`.
   - index.html 307: `checked`.
   - `_render_ceiling`'s pop at render_pipeline.py 2459 STAYS False. Its docstring at 2454 may note that the server default is on.
   - DEFAULTS (app_server 80–134) gets no new key.
   - Versions: app.js?v=61 becomes 62. WORKLET_VER 58 and pack_room.js?v=52 are unchanged. pack.py, pack_room.js, live_fdn.js and wasm_run.js are not edited.
3. **Required harness forward.** In harness lib/render_ir.py, after the sub_hp block at 86–89, add: `if p.get("phys_ceiling"): kw["phys_ceiling"] = True`. Without it, harness Render stays on the dial path while Play is physics. This is not a DSP edit.
4. **Explicit-false edits allowed** (tolerances unchanged; T60_TOL 0.08, ±15% and ±8% all stay):
   - run_all.py t10_t60_play, play_ir at ~256, for std_lock18, small_lock08 and hall_lock40: `extra={"phys_ceiling": False}`.
   - run_all.py t12_t60_render, body at ~274: `"phys_ceiling": False`.
   - test_p0_engine.py test_p0_2_t60_play_within_8pct (~50): extra false on each of the three scenes.
   - test_p0_engine.py test_p0_2_t60_play_independent_of_dffs (~60): `ctx.params("std_lock18", {"phys_ceiling": False})`.
   - test_p0_engine.py test_p0_2_t60_render_within_8pct (~98): body false.
   - test_b3_limiter.py, quiet body ~68 and hot body ~86: false (quiet.f32 must not move).
   - test_b6_heights.py gate4 body ~372: false. Do NOT push the flag into `_render` (gate3's tilt must not move).
   - test_s5_surf_tail.py test_play_cascade_off_matches_pre_s5, lock-on scene ~312: false, next to the existing sub_hp false.
5. **Leave on the default body** (no pre-emptive false):
   - t13, t18, test_p0_4 (Play vs Render, now physics vs physics after the forward). If the null or the 10% T30 gate misses, STOP. Do not widen them.
   - test_b4_ramps (80, 125), t11 and test_p0_2 hf_residue, and test_p0_2_decay_lock_off_unchanged.
   - test_smix_desk and _harness: these force lock off.
   - test_passivity_carpet_ls (test_s5 ~465). If its ±3% misses, STOP and report. Explicit false is the repair only after that report.
   - Direct render() callers keep the False pop: selfcheck, hash_scenes, _harness.render_body, test_smix_desk._render, test_s5 one(), test_b5_mono, test_b6._render, test_b3 hot worker, _sl_render, moving_room_demo and tweak_app. Do not edit them.
6. **Goldens.**
   - Expected to MOVE: play_std_lock18_byp.f32, play_std_lock18_col.f32, both live MD5s, and the d18/d4 prefix content (after the forward; length is unchanged).
   - Expected to STAY: the three unlocked goldens.
   - Any other movement is a STOP.
7. **New pin test.**
   - Scene and method: boot std_lock18 with the key absent, measured as T30 per octave from 125 Hz to 4 kHz, within 0.02 relative, at the values this run measures.
   - Do not copy F9's T20 row into it.
   - STOP if any band is more than 0.02 relative worse than the F9 row.
   - F12 is report-only unless the 926 Hz ring is longer than 3.8 s.
8. **CPU.** Decay-8 cube, keys absent and explicit false: ceiling 2.40 ms. Re-measure the t19 flat two-source bench (AMBIENCE 1.594 ms), which now gains the cascade. Do not raise the ceiling.
9. **F11.** Run the acceptance pytest before AND after the flip. Do not edit the five known failures. A test that newly fails is a STOP. Report any change in the shape of an already-red failure, but do not fix it.
10. **Remaining STOPs:**
    - explicit false is not bit-exact with the AMBIENCE pins
    - any pin outside the list moves
    - cube or t19 goes over 2.40 ms
    - F9 grows by more than 0.02 relative, F12 goes over 3.8 s, or a new acceptance failure appears
    - any DSP edit, or any change to s or k
    - Play and Render disagree on an empty body after the forward
11. **Order and gates.**
    - Order: backup; three defaults plus the forward plus the explicit-false edits; rule-2 bit-exact proof BEFORE any re-pin; then goldens, MD5s, d18/d4, version asserts and the new pin test.
    - Gates: full software pytest, node 38, selfcheck 45/45, harness t01–t19, acceptance pytest before and after, cube CPU, F9 row, F12 ring, phys_preview both ways, and the Mix checkbox ticked on a fresh load.
    - Report old to new for every pin.

Step 1 may now run in a fresh session at HIGH effort.


## F9 DIAG NOTE (2026-10-19 09:00), BINDING; overrides the F9/F12 gates above

F9_DIAG_2026-10-19.md (read-only) found that F9 was a measuring error. The listen scripts combined L and R with np.hypot before band-splitting. Measured correctly, the boot room is within about 1% of target from 125 Hz to 2 kHz. Therefore:

- **F9 gate.** Wherever a block says "F9 row", compare against the CORRECTED boot row in F9_DIAG: −9.5/−0.9/+0.7/−1.0/−1.1/+0.2/+6.4% versus the T_eff target at 63–4k Hz. Measure it the same way: band-filter each channel first, then sum the energies, or use the L+R sum the tests use. Never use hypot(L,R). STOP only if a 125 Hz–4 kHz band is more than 0.02 relative further from target than that row.
- **F12 gate.** Re-measure the 926 Hz ring the correct way. It is report-only and is no longer a STOP.
- **No other changes.** Do not edit make_listens.py, the HANDOVER boot IR line or the SMALLDECAY notes in this run. That correction is a separate run (F9 notes fix).


## STOP RESOLUTION: test_passivity_carpet_ls (2026-10-19 10:30), BINDING

Diagnosis: roadmap\CARPET_PASSIVITY_DIAG_2026-10-19.md (read-only).

**Cause.** The cause is a test assumption, not a defect. The `_flat()` reference sets all six faces to 0.119, while carpet leaves five faces at 0.08. At 500 Hz the area-weighted alpha is 0.096 for carpet against 0.119 for the reference, so physics correctly gives carpet a longer decay at 500 Hz and a shorter one above it. The ±3% T30 gate was written for the dial path only (S5_PROMPT_D-UI26 item 6). Do NOT change any code to make carpet match flat.

**Repair (rule 5, test-only).**
1. In `software\tests\test_passivity_carpet_ls`, add `"phys_ceiling": False` to `body.update` (around line 470). The loud and flat scenes inherit it. Update the docstring to say the T30 gate is for the dial path. Expected ratios are 0.92–1.00 (dial-path column), and every gated band passes.
2. Add a new test, `test_passivity_carpet_ls_physics`, alongside it:
   - Key absent (physics on).
   - Compare against the UNFLATTENED default body.
   - Assert no runaway over 20 s.
   - Assert carpet T30 is at most 1.03 × default at 500 Hz, 1 kHz, 2 kHz and 4 kHz. Diagnosis values: 0.861 / 0.756 / 0.692 / 0.749.
   - Print the ratio against the target but do not gate it.
   - Measure left-channel T30 with the test's own `t60_bands`.

**Unchanged by this repair.** No audio, pins, goldens, wasm, WORKLET_VER or CPU changes. The pins already written stay as written (GOLDEN_META a362cf5e…, app.js?v=62). Do not re-render them.

**Then finish every remaining gate from the earlier blocks:**
- rerun this test file, then the full software pytest
- node 38, selfcheck 45/45, harness t01–t19
- acceptance-after: the five known failures plus test_lock_no_air_on_fdn_return_play were already red BEFORE, so they are not new failures; report any change in their shape
- decay-8 cube CPU (absent key and explicit false) and the t19 bench, both under 2.40 ms
- the corrected F9 remeasure per the F9 DIAG NOTE, and the F12 ring (report-only)
- the Mix-tab checkbox ticked on a fresh load
- then the HANDOVER and BUILD_RUN_LOG updates

Add an OPEN_FAULTS note that acceptance test_lock_no_air_on_fdn_return_play was already red before PHYSDEFAULT. All other STOP rules still apply.


## STOP RESOLUTION: t14_level_sanity (2026-10-19 12:30), BINDING

**Cause.** This is an expected consequence of the approved flip, not a defect. The physics target falls with frequency: about 1.16 s at 2 kHz and 0.85 s at 4 kHz on a 1.8 dial, where the dial path holds 1.8 s flat. A shorter HF tail stores less noise energy in the FDN, so the broadband FDN-only RMS drops. A drop of −2.16 dB is the expected size. Makeup is frozen (SRCDIST) and follows decay/feedback by design. Idle already approved this level by listening (the AMBIENCE B_phys files used the same engine and makeup).

**Peak headroom is unaffected.** Hot-noise peak is 0.618, under the 0.95 line. The tail got quieter, not louder.

**Do NOT add makeup, change gains, or loosen ±0.5 dB.**

**Repair (test-only, same pattern as rule 4):**
1. Change only the t14 pin scene: give `T14_PIN` / its body `"phys_ceiling": False`, so the existing −24.55 dB ±0.5 dB gate keeps testing the dial path. Expected: it passes at about the AMBIENCE value. If it does NOT pass with explicit false, STOP and report, because that would mean a real level change.
2. Add a physics row to t14 with the key absent:
   - Pin the FDN-only RMS at the value this run measures (about −26.71 dB), within ±0.5 dB.
   - Also report the whole-mix delta and the Play peak. Gate the peak at ≤ 0.95.
   - Label it "PHYSDEFAULT 2026-10-19 physics row".
3. Add a note to OPEN_FAULTS: the default tail's broadband FDN level is 2.16 dB lower than on the dial path at dial 1.8, because of the falling-HF physics decay. It is approved by listening. A tail-level trim is a possible later option for Idle (BACKLOG), not this run.

**Then:**
- rerun the harness: expect 16 pass, 0 fail
- acceptance-after
- decay-8 cube CPU (absent key and explicit false, both ≤ 2.40 ms; t19 already passed at 1.610 ms)
- the corrected F9 row per the F9 DIAG NOTE, and the F12 ring (report-only)
- the Mix-tab checkbox ticked on a fresh load
- then HANDOVER (new Current pin), BUILD_RUN_LOG and OPEN_FAULTS

The software pytest, node and selfcheck results from this run stand. Rerun the software pytest only if a software file changes. All other STOP rules still apply.

## STOP RESOLUTION: two-source mirror failures (2026-10-19 14:15) — BINDING

Idle chose: stopgap now, proper fix as its own later run. Evidence: roadmap\MIRROR_PHYS_DIAG_2026-10-19.md and roadmap\MIRROR_PHYS_BUILD_DIAG_2026-10-19.md (both agree). Real Play bug: bank B runs source A's physics sections on B's delays (render_pipeline.py:3180, live_stereo.c:211 / 2235-2241). In the mirror hall a B line reaches +6.5 dB loop gain (runaway). Render is correct.

1. The only product edit: `software\app_server.py:641`. Physics is forced OFF whenever two sources are on, for both Play and Render, whatever the key says:
   `"phys_ceiling": (_b(body["phys_ceiling"], True) if "phys_ceiling" in body else True) and not two_sources,`
   (`two_sources` is parsed at line 528, before this dict.) Add a one-line comment pointing to the OPEN_FAULTS entry. Do NOT patch `_live_surf_pack` only (Play and Render would disagree). Do NOT touch live_stereo.c, the wasm, fdn_worklet.js, render_pipeline.py, WORKLET_VER or pack_room.
2. Do NOT set explicit false in the mirror, sh_p7 or p6 tests. They must pass on the key-absent default.
3. New guard test in software\tests (for example test_physdefault_two_source.py): a two-source body with the key absent gives the same live dict and the same Play IR (max-abs 0) as that body with explicit false, and no live `phys_ceiling` field. Also a one-source body with the key absent must still have physics on (T30 pin from test_physdefault_t30.py unchanged).
4. Bit-exact checks: every single-source pin written this run is unchanged (lock18 byp/col, empty and centre MD5, GOLDEN_META a362cf5e…, d18/d4). Any two-source live MD5 (for example `_ORTF_PLUS_C_LIVE_MD5`) must match its AMBIENCE value. If any of these moves, STOP.
5. Re-run acceptance. Expected: back to the 6 known failures, 92 passed. The 5 new failures must pass. `test_sh_p1_off_bit_exact` def_1_on at 0.012091 is report-only (single-source, already red). If `test_p6_two_source_cpu` misses again, re-run it alone on an idle PC before calling a STOP; report both numbers. Do not change the 2.40 ms ceiling.
6. UI: with two sources on, the Mix-tab physics checkbox may still show ticked while physics is off. Report what it shows; do not change the UI in this run.
7. OPEN_FAULTS: add a new entry (next free F number) "Two-source Play shares source A's physics sections; physics forced off for two sources (stopgap 2026-10-19)", with the +6.5 dB / −83 → −0.7 dB runaway evidence, both diag file paths, and the proper fix (second pack from taps_b, slCB bank in live_stereo.c, WORKLET_VER 58 → 59) marked as the next run.
8. Then finish every remaining gate (decay-8 cube, corrected F9 row, F12 ring, Mix checkbox) and the HANDOVER / BUILD_RUN_LOG / OPEN_FAULTS updates. Stop and report at any other STOP rule.
