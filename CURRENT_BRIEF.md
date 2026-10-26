# Current brief (2026-10-23)

Read this instead of `HANDOVER.md`. The Current pin in `HANDOVER.md` still wins if this page and that pin disagree. Prompts live in `handoff_build_support_2\roadmap\thursday_prompts\`. Next run: not written. SL6 stopped 2026-10-24. SL7a and SL7b stay dropped. One goal per run. `RUN_RULES.md` in that folder.

## Pins

ROUTING R2 landed 2026-10-23 (Play array and room). Off-axis tail colour landed 2026-10-23, key `offaxis_tail`, default off. Play `pushParams` copies the 45 floats (2026-10-24). The Mix page posts `offaxis_tail` (default off) on the live request (2026-10-24). Movement un-forced 2026-10-23. The Room knob is visible. Default stays 0. Shared-off at knob 100 measured 1.876 ms. `WORKLET_VER` 63. `live_fdn.js?v=64`. `app.js?v=96`. `sl_room_result.js?v=7`. `sl_room_result.css?v=2`. While Play runs, the Hadamard chip stays on the stored size. 64 and 128 stay selectable and read "64 lines: Render uses 64, Play is using 32" (same for 128). The lattice follows that selection. Play audio still uses 32. `pack_room.js?v=55`. `app.css?v=40`. `routing_scene.js?v=3`. `room_editor.js?v=25`. `room_shape.js?v=7`. `room_draw.js?v=5`. `room_3d.js?v=24`. `image_views.js?v=21`. `room_math.js?v=20`. `colour_surfaces.js?v=9`. Wasm sha1 `555414f1cf3df653f285f1bacdc7f68022594124` (393117 bytes). `live_stereo.c` sha1 `c7bdd7949885bbcefac3c073900a10c24114dc88`. `bloom_live.inc` sha1 `a3b508245f026fad9a222c07894145ff8f5ea765`.

SL4 (2026-10-23): Surfaces posts `surf_directional`. Calibrate (`POST /api/surf_calibrate`) stores seven `surf_cal` factors on the scene. Play reuses that list and the face hits. Flat, and a missing flag, stay room average. `sl_room_result.js?v=4`. `RR_SL_STAGE` 4. s′ stays 0.5. The untreated-plaster EDT/T30 gap vs Flat still fails the 0.15 rule at 2 kHz, 4 kHz and 8 kHz (xfail). A/B 3 and 4 already put directional against room average at ≤ 1 dB, so directional ships. `software\proof\sl4_directional_results.json`.

SL5 (2026-10-23): Treatment rows are in Surfaces mode. `RR_SL_STAGE` 5. `sl_room_result.js?v=5`. `colour_surfaces.js?v=5`. Entering Surfaces adds the room-shell rows (90 Hz, Q 1, 30 % of each wall). Flat ignores rows. Helmholtz stays on the formula, Q 3. The library set "Plaster + parquet" paints walls and ceiling `plaster_smooth` and the floor `wood_parquet`. Default cards stay the plaster-ish 0.05–0.22 curve. Shell T20 on this PC: 2.007 s at 125 Hz and 2.470 s at 250 Hz (targets 1.9 / 2.35, inside ±10 %). Toggling the 125 Hz panel moves the model curve 2.09 s to 2.62 s. 4 kHz moves under 2 %. Auto-treat render scored 13/23 (box 16/23). That was SL6's gate. Harness t03 and t04 max-abs 0. t19 shared-off medians 1.619 ms then 1.626 ms (delta +0.007). The second shared-on median is 1.782 ms. Both benches passed the 2.40 ms and 2.133 ms ceilings. Spikes 0.

SL6 (2026-10-24): room-average auto-treat holds the 125, 250 and 500 Hz `surf_cal` factors at 1. The highs stay the measured octave factors. The proved list is `[1, 1, 1, 0.850, 0.878, 0.870, 0.906]`, rendered T20 16/23. Holding only 125 and 250 scored 15/23; the 500 Hz hold brought 315 Hz from 1.138 back to 1.093. Directional calibrate is unchanged. Amount is 0–100 on the Auto-treat block, missing means 100. `RR_SL_STAGE` 6. Accepted coverage scales on the Play, Render, and Room-result copy. Shell rows stay. Stored `surf_cal` posts at 100% and the key is omitted below. Play posts on pointer release. Decay lock is unchanged. `POST /api/auto_treat` suggests rows and does not write the scene. Do not render that scene again to re-score the proved list.

Treatment sets decay (2026-10-25): a switch beside Amount, default off, visible at `RR_SL_STAGE` 6 only. On, Surfaces posts the decay lock off. Play then uses the same 500 Hz–1 kHz material mean Render already arms when the lock is off, so Amount moves length and tone. The plan's 500 Hz–2 kHz means on real_default are 2.633 s bare and 0.791 s full. Off restores the lock and the dial the user had. Flat ignores the switch. Key `treat_sets_decay`, missing is off. `app.js?v=93`. `sl_room_result.js?v=7`.

Pair room mic (2026-10-25): Mic setup XY 90, XY 120, NOS, DIN, AB omni, and AB card place the centre strip back in the room at 4 m, 1.5 m, 2 m, yaw 0, or the nearest point 0.10 m inside the walls. The Mix strip reads Room mic. The plan draws that spot. The centre fader stays 0.0 dB. ORTF stays centre off. `app.js?v=93`. `room_editor.js?v=24`.

MS (2 mics) (2026-10-25): Mic setup `ms_2` is a cardioid mid on route both and a fig-8 side at 90° on route s. Weights match `ms_b`: 0.707946, −0.707946, 0.707946, 0.707946, 0, 0. The Right strip is muted and reads off. The M/S pair button is the active pair button. `ms_a`, `ms_b`, `ms_c`, and `ms_classic` stay. `app.js?v=93`. `ms_presets.js?v=3`.

Mix labels (2026-10-25): Physical ceiling, Rumble filter, and Off-axis tail keep those names. Beside them: Room limits the tail, 15 Hz rumble cut, and Darken the tail. Each row has a tooltip. The physical readout no longer says "off with two sources". Defaults stay. `app.js?v=93`.

Mix bypass (2026-10-25): The Routing panel and the Host fader are off the page. Bypass on the Buses desk starts off. On, Play and Render post dry_gain 1 and direct_wet, fdn_wet, and early_wet 0. The colour-mode Bypass stays. Sections 10, 12, and 13 stay in the code. `app.js?v=93`.

Pair link (2026-10-26): Mirror, Linked, and Split are off the page. Stereo pair sets link_mode mirror. Independent sets link_mode split. A saved linked or mirror value maps to Stereo pair. A saved split or independent value maps to Independent. M/S stays M/S. Yaws and gains are not rewritten by the map. `app.js?v=93`. `pair_mode.js?v=2`.

3rd mic (2026-10-26): The three buttons read 3rd mic: None, 3rd mic: Centre, and 3rd mic: Room mic. The posted values stay off, centre, and room.

Proximity slider (2026-10-26): The page has no mic_proximity slider. The posted default stays 0.25. `app.js?v=93`.

Polar once (2026-10-26): Measured drawing and Play/Render tap levels use the fitter alone. The Zenodo fit is already H(θ)/H(0°), so the ideal pattern is not multiplied again. Bypass and User defined keep the ideal pattern. Splay live MD5 `5f757d04e47eea6cda87b32c35daa901`.

Polar tab (2026-10-26): The Polar tab opens on One mic. The other pages are All mics summed and At the speakers. The banner reads "Measured: real mic response, relative to on-axis" in Measured, and "Ideal pattern" in Bypass and User defined. The server note does not replace it. Each plot has dB rings at 0, −6, −12, −18 and −24, marks at 0/90/180, and a front arrow. The frequency key uses FreqPalette. Click a band to solo it. Measured plots draw a dashed ideal pattern over the curve. The L/C/R boxes read Left capsule, Centre capsule, and Right capsule. The plot refreshes with the mic. Refresh is hidden. The Mic tab source plane is a link to Polar. Hypercardioid is its own pattern, a=0.25, so 0/90/180 read 1 / 0.25 / 0.5. Supercardioid stays a=0.37. Empty and centre stay cardioid, so the live MD5s, the five golden sha1s and WORKLET_VER 63 are unchanged. `app.js?v=102`. `polar_field.js?v=13`. `mic_desk.js?v=24`. `room_math.js?v=21`. `app.css?v=41`.

Advanced locks (2026-10-26): The page has no Reaktor parity checkbox and no 2011 Air 1-pole. Posts of those keys are ignored. Play packs air_lp 0 and loop_semantics 0. The worklet one-pole stays. `room_math.js?v=20`. `room_3d.js?v=24`. `room_editor.js?v=25`. The 2011 Reaktor snapshot and the Colour filter stay on sos until `?dev=1` or `window.RR_DEV`. `app.js?v=95`.

D-UI38 (2026-10-23): a missing mic id is Neumann U87 Ai cardioid on L, C and R. Empty MD5 `067adbca1930efcd3f7c83bdd1d4c359`, centre MD5 `35db578a18557d5729c0450e26f24a9d`, two-source key-absent `a4c2cf1a9c81672dc0932534eda58a71`, two-source explicit false `c804fc7c80a8624760a6007cc54cdaac`, `GOLDEN_META` `52bfce749715e335d8fa2418a16e8593e9a54040`. Coloured Play goldens moved. Bypass Play goldens and the Render BYPASS golden held. Five golden sha1s are in `software\tests\test_quick_pins.py`. Explicit SM57 stays Shure SM57.

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
