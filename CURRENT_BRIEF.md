# Current brief (2026-10-23)

Read this instead of `HANDOVER.md`. The Current pin in `HANDOVER.md` still wins if this page and that pin disagree. Prompts live in `handoff_build_support_2\roadmap\thursday_prompts\`. Next run: not written. SL6 stopped 2026-10-24. SL7a and SL7b stay dropped. One goal per run. `RUN_RULES.md` in that folder.

## Pins

ROUTING R2 landed 2026-10-23 (Play array and room). Off-axis tail colour landed 2026-10-23, key `offaxis_tail`, default off. Play `pushParams` copies the 45 floats (2026-10-24). The Mix page posts `offaxis_tail` (default off) on the live request (2026-10-24). Movement un-forced 2026-10-23. The Room knob is visible. Default stays 0. Shared-off at knob 100 measured 1.876 ms. `WORKLET_VER` 63. `live_fdn.js?v=64`. `app.js?v=87`. `sl_room_result.js?v=7`. `sl_room_result.css?v=2`. While Play runs, the Hadamard chip lights 8, 16, or 32. A stored 64 or 128 lights 32. The stored size stays. `pack_room.js?v=55`. `app.css?v=38`. `routing_scene.js?v=3`. `room_editor.js?v=24`. `room_shape.js?v=7`. `room_draw.js?v=5`. `room_3d.js?v=23`. `image_views.js?v=20`. `room_math.js?v=19`. `colour_surfaces.js?v=9`. Wasm sha1 `555414f1cf3df653f285f1bacdc7f68022594124` (393117 bytes). `live_stereo.c` sha1 `c7bdd7949885bbcefac3c073900a10c24114dc88`. `bloom_live.inc` sha1 `a3b508245f026fad9a222c07894145ff8f5ea765`.

SL4 (2026-10-23): Surfaces posts `surf_directional`. Calibrate (`POST /api/surf_calibrate`) stores seven `surf_cal` factors on the scene. Play reuses that list and the face hits. Flat, and a missing flag, stay room average. `sl_room_result.js?v=4`. `RR_SL_STAGE` 4. s′ stays 0.5. The untreated-plaster EDT/T30 gap vs Flat still fails the 0.15 rule at 2 kHz, 4 kHz and 8 kHz (xfail). A/B 3 and 4 already put directional against room average at ≤ 1 dB, so directional ships. `software\proof\sl4_directional_results.json`.

SL5 (2026-10-23): Treatment rows are in Surfaces mode. `RR_SL_STAGE` 5. `sl_room_result.js?v=5`. `colour_surfaces.js?v=5`. Entering Surfaces adds the room-shell rows (90 Hz, Q 1, 30 % of each wall). Flat ignores rows. Helmholtz stays on the formula, Q 3. The library set "Plaster + parquet" paints walls and ceiling `plaster_smooth` and the floor `wood_parquet`. Default cards stay the plaster-ish 0.05–0.22 curve. Shell T20 on this PC: 2.007 s at 125 Hz and 2.470 s at 250 Hz (targets 1.9 / 2.35, inside ±10 %). Toggling the 125 Hz panel moves the model curve 2.09 s to 2.62 s. 4 kHz moves under 2 %. Auto-treat render scored 13/23 (box 16/23). That was SL6's gate. Harness t03 and t04 max-abs 0. t19 shared-off medians 1.619 ms then 1.626 ms (delta +0.007). The second shared-on median is 1.782 ms. Both benches passed the 2.40 ms and 2.133 ms ceilings. Spikes 0.

SL6 (2026-10-24): room-average auto-treat holds the 125, 250 and 500 Hz `surf_cal` factors at 1. The highs stay the measured octave factors. The proved list is `[1, 1, 1, 0.850, 0.878, 0.870, 0.906]`, rendered T20 16/23. Holding only 125 and 250 scored 15/23; the 500 Hz hold brought 315 Hz from 1.138 back to 1.093. Directional calibrate is unchanged. Amount is 0–100 on the Auto-treat block, missing means 100. `RR_SL_STAGE` 6. Accepted coverage scales on the Play, Render, and Room-result copy. Shell rows stay. Stored `surf_cal` posts at 100% and the key is omitted below. Play posts on pointer release. Decay lock is unchanged. `POST /api/auto_treat` suggests rows and does not write the scene. Do not render that scene again to re-score the proved list.

Treatment sets decay (2026-10-25): a switch beside Amount, default off, visible at `RR_SL_STAGE` 6 only. On, Surfaces posts the decay lock off. Play then uses the same 500 Hz–1 kHz material mean Render already arms when the lock is off, so Amount moves length and tone. The plan's 500 Hz–2 kHz means on real_default are 2.633 s bare and 0.791 s full. Off restores the lock and the dial the user had. Flat ignores the switch. Key `treat_sets_decay`, missing is off. `app.js?v=87`. `sl_room_result.js?v=7`.

Pair room mic (2026-10-25): Mic setup XY 90, XY 120, NOS, DIN, AB omni, and AB card place the centre strip back in the room at 4 m, 1.5 m, 2 m, yaw 0, or the nearest point 0.10 m inside the walls. The Mix strip reads Room mic. The plan draws that spot. The centre fader stays 0.0 dB. ORTF stays centre off. `app.js?v=87`. `room_editor.js?v=24`.

D-UI38 (2026-10-23): a missing mic id is Neumann U87 Ai cardioid on L, C and R. Empty MD5 `b20cf5dc675f613992aa6a31c2cd74f4`, centre MD5 `ba1bbc6d386ed75bf484156f08043f37`, two-source key-absent `0e11f5ce3415eb555a61655c6c0e6737`, two-source explicit false `8ea544b008a4677b94a3a553c6a2f39b`, `GOLDEN_META` `52bfce749715e335d8fa2418a16e8593e9a54040`. Coloured Play goldens moved. Bypass Play goldens and the Render BYPASS golden held. Five golden sha1s are in `software\tests\test_quick_pins.py`. Explicit SM57 still hashes to the old empty and centre MD5s.

Non-rectangular rooms stage 2 landed 2026-10-24. Key `room_shape`. Absent or `box` is the shoebox and stays the live MD5. Presets `splay`, `lede`, `live` build Play taps with `compute_poly_taps`, the same call Render uses. The page posts the key when it is on the scene. Harness t03 and t04 max-abs 0. t19 shared-off medians 1.659 ms then 1.675 ms (delta +0.016). The second shared-on median is 1.815 ms. Both benches passed the 2.40 ms and 2.133 ms ceilings. Spikes 0. Splay one-source shared-off median 0.654 ms, 32 taps. Room shape UI landed 2026-10-24. The Room page and the Space tab share one Shape picker (Box, Splay, LEDE, Live room, Gable, or Hex, default Box). One `room_shape` paints both rows, the plan, the Room 3D, and the Space views, and posts `room_shape` on Render and Play. The plan draws that polygon. Mic and source drag stay inside it. Surfaces lists every wall in its material colour. LEDE and Live room are left/right symmetric, so each mirrored pair is the linked Left + Right card and the switch stays hidden, the same as Splay. LEDE has two mirrored side pairs and both use the A and C material. Play bench, burst 4 s and total 10 s, 32 taps, spikes 0: listen-scene medians box 0.886 ms, LEDE 0.779 ms, Live room 0.780 ms. Two-source talking-head plus trumpet: box 1.457 ms, LEDE 1.217 ms, Live room 1.223 ms. All under 2.40 ms. Box has a Mirror left/right walls switch at the top of the Surfaces wall list, default on (Idle 2026-10-24). On, Left and Right are one linked card, Left + Right (mirrored). Off, two cards. The page copies left onto right and posts `mirror_lr`. Splay stays that same linked card and shows no switch. Front, back, floor and ceiling stay independent. Default left and right materials match, so empty and centre MD5s stay. The 3D room and the Space tab draw the polygon (display only, 2026-10-24): angled walls, trapezoid floor and ceiling, each wall in its Surfaces colour. Lattice draws the same taps Play uses (`hadamard_n` from `compute_poly_taps`; 8, 16, or 32 while Play runs, otherwise the chip). Paths and Last legs keep the home shell and those paths. The image lattice is hidden there, the same rule as box. Heard rooms still fade in 15 ms. Box drawing is unchanged. Engine preset `gable` (2026-10-24) is a shoebox floor with the ridge along the length at x = W/2, eaves at 0.75*H and the ridge at H. It uses `compute_poly_taps`. The picker includes Gable. The plan is that rectangle with the ridge line drawn. Mic and source drag stay inside the box and under the sloped roof. Surfaces lists every face, both roof planes and both gable ends, in the material colour. Gable is left/right symmetric, so Left + Right (mirrored) is one card and the switch stays hidden. The Room tab 3D and the Space tab draw the pitched roof and the same taps Play uses (`hadamard_n` from `compute_poly_taps`; Lattice, Paths, and Last legs follow the box rule). Display only. The engine was not changed. Empty and centre MD5s were not re-pinned. Engine preset `hex` (2026-10-24) is a hexagon floor inside the W × L box, vertices (W/4, 0), (3W/4, 0), (W, L/2), (3W/4, L), (W/4, L), (0, L/2), flat ceiling at H, built with `_prism`. It uses `compute_poly_taps`. The picker includes Hex. The plan draws that hexagon. Mic and source drag stay inside it. Surfaces lists every wall in its material colour. Hex is left/right symmetric, so both angled side pairs are the linked Left + Right (mirrored) card and the switch stays hidden. Front and back stay independent. The Room tab 3D and the Space tab draw the hexagon and the same taps Play uses (`hadamard_n` from `compute_poly_taps`; Lattice, Paths, and Last legs follow the box rule). Display only. The engine was not changed. Empty and centre MD5s were not re-pinned.

Play / Render oversampling: Natural 2/2, Glue ADAA 1/1, Room Crush 1/2, Nuke ADAA 1/1, Swell 2/2, Neve 1/8, 610-A 8/8. The Mix page Routing panel (array, room, master) replaces the Bloom panel. Play posts the master strip, and an array or room strip only while that strip is on. All three default off. Python is `software\.venv\Scripts\python.exe`.

## Play lean, Render perfect

Play is a rough preview and must fit 2.40 ms. It may use lower Bloom and preamp oversampling. Render is the high-quality path and has no CPU ceiling. Shared-on Play ceiling stays 2.133 ms. Do not raise either ceiling.

## Do not touch

Do not retune 1/r, the 0.55 Direct fold, the desk, makeup freeze, source-distance makeup, Smooth, the limiter, or the decay lock. Do not force Play and Render onto one decay-lock `g`. Do not retune 610-A or chase its 9 kHz spike. Do not re-pin the five goldens on a bare continue. Do not start Phase 4, T9b, S-OUT, scatter, smear, or CPU fallbacks (c) and (d). Do not retune the Movement curve. The knob default stays 0. `c` stays 340. Do not flip L/R or floor X. Do not fold B into A's tank. Do not edit the original `.ens` files. Do not wire A–F bit tables into the audio path.

2026-10-23 Idle: routing preamps and compressors are shelved. Preamps distort badly and the compressors don't sound nice. Leave the code as is, default off, and no runs touch it until Idle asks.

## Where files live

Canonical root is this folder (`HANDOVER.md`, `ensemble\`, `software\`, `findings\`). Live app: `software\Launch Tweak App.bat` at `http://127.0.0.1:7860`. Goldens: `handoff_build_support_2\3_phase_acceptance_tests\harness\golden\`. Backlog: `handoff_build_support_2\roadmap\IDEAS_BACKLOG_2026-10-19.md`. Pinned listen wav: `software\renders\out_20261013_115900.wav`. Screenshots stay in `C:\Users\IdleHanz\Pictures\Screenshots\`. Do not treat `2011-Room-Reverb-publish\`, Desktop zips, or `docs-*-tmp\` as the live tree.

## QUICK (after each step)

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test (Get-ChildItem tests\*.mjs | % FullName)
```

Add `pytest` for the test file you touched. Leave `test_b2_render_length.py` out.

## FULL (once, at the end)

Acceptance pytest, harness `--slow`, harness t05, and extra CPU benches stay off.
`@pytest.mark.slow` Surfaces renders stay off. `software\pytest.ini` addopts are `-m "not slow"`.

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest -q -m "not slow" --ignore=tests/test_b2_render_length.py
```

## SURFACES (only when the prompt is a Surfaces run)

The slow Surfaces renders (full-length SL2, SL4, SL5/SL6, including the auto-treat xfail). Proof JSON goes to a temp file. `software\proof\` is not rewritten. The two 400 ms Flat bit-exact tests are not in this tier. They stay in FULL.

From `software\` (`-m slow` overrides the default addopts):

```
.\.venv\Scripts\python.exe -m pytest -q -m slow --ignore=tests/test_b2_render_length.py
```

From the repo root, after that pytest:

```
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t03,t04
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t19
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t19
```

The two `t19` lines are the CPU delta: same boot, back to back, nothing else rendering. Each must pass the 2.40 ms Play ceiling. The delta is the second median minus the first.
