# Code review, 2026-10-24

Read-only pass over the live tree (`software\`, the tests, and the Surfaces notes). No product file was edited. The 23 October wiring runs have landed: Array and Room arm like Master, `test_a12` waits 200/2500 ms, and a packed section 13 changes a Play sample.

Shelved, and absent from the runs below: routing preamps and compressors, the 610-A flux trim, and Auto-treat.

## Findings, worst first

1. **Auto-treat stays shelved.** Three scores on the treated room, all short of 16/23. The room-average calibrated render is 12/23 (`roadmap\SL6_ALGORITHM_AUDIT.md`). The reverted `surf_loop.py` try was 12/23 (`CURRENT_BRIEF.md`). Idle's score with the factors left off is 6/23. That 6 is not printed in the audit. Calibrate is what moves 6 to 12. It also overshoots the bass.

   The audit's factors for the calibrated pass are 0.829, 0.782, 0.952, 0.850, 0.878, 0.870, 0.906, all below 1, so the second design reduces the loss. The tail is already long before early, direct, or the mic are added: about +18% at 63 Hz and +58% at 250 Hz. The flat fallback line is short in the bass, so it is not the excess. One suspected cause, from the audit: those factors lengthen a tail that is already long, and the third-octave T20 stays long after that.

   The button is still hidden (`RR_SL_STAGE` 5, `sl_room_result.js?v=5`). `POST /api/auto_treat` suggests rows and does not write the scene. `calibrate()` in `sl_room_result.js` sets `surf_directional` true before it posts, so that button is the directional pass. The 12/23 above is the room-average pass. `software\proof\sl6_treated_results.json` still says `n_ok` 13 from the earlier directional render. The fast test still locks the model at 20/24 and its comment still says the render was 16/23 on the box (`software\tests\test_sl6_auto_treat.py`). No run below edits `surf_loop.py`, the calibration clamps, or the button.

2. **FULL still runs the slow Surfaces renders.** `software\tests\conftest.py` marks `slow` as a real render of 30–120 s. Nothing skips that mark. The FULL line in `CURRENT_BRIEF.md` is pytest with `test_b2` ignored, and it collects these tests.

   Last measured software pytest is 156 passed in 38 min 11 s (F9 notes, 2026-10-19), before SL4 and the SL5/SL6 render file. Those files add eleven 1.5 s impulse renders on top of that suite. `test_sl4_directional.py` renders three rooms twice (before and after calibration) and one flat room, in one module fixture. `test_sl5_sl6_render.py` renders twice per test, two tests. At the marker's own 30 s floor that is about six minutes, which puts FULL past 40 minutes. At the top of the marker's range it is much longer.

   `test_auto_treat_plan_rendered` is an xfail, so the suite stays green, and the test still does both renders and writes `software\proof\sl6_treated_results.json` before the assert. A FULL run can change that committed proof. The two 400 ms bit-exact tests in `test_sl2_loop.py` are marked slow as well. They are the cheap lock that Flat ignores treatment rows. `test_a12` alone is about 100 s and was already inside the 38 minute run.

3. **Hadamard 64 and 128 stay lit during Play.** `syncHadamardUI` in `software\static\js\app.js` marks the chip active from `state.hadamard_n`. While Play is running it disables 64 and 128 and leaves the lit chip where it was. `live_stereo.c` keeps 8, 16, or 32 and leaves the order at 32 for anything else. Render can use 64 and 128. The "Render only" title is right. The lit chip during Play is the order the player is not using. This was run 4 on 23 October. It has not landed.

4. **Off-axis tail and Movement are locked at the blob.** `test_offaxis_tail.py` checks that the key packs section 14 (45 floats) and that the Python source mentions the tail after Bloom. It never calls the wasm. `test_movement_knob.py` checks that knob 100 packs section 8 as 0.15 ms. It never runs a block. Section 13 grew a sample check after the last review (`test_array_glue_moves_a_play_sample`). Sections 8 and 14 did not. A dropped `mod_apply` or a dropped `tail_sos_part` stays green. The off-axis listen wavs are Python renders.

5. **A polygon preset has no impulse lock.** `test_room_shape.py` keeps the shoebox live MD5, matches the box lattice, and checks that splay, lede, and live each fill the 32-tap quota. It never renders. Play is meant to ignore `room_shape`. Render is the path that can go wrong in silence. `poly_room.py` states the other half on purpose: every tap keeps `n = (0, 0, 0)`, so shoebox wall cards stay off this path. The test locks that. Leave the wall letters alone.

## Left as they are

`render()` still accepts `mic_hp_on` and `mic_proximity` and does not read them. `direct_makeup` is still in the live JSON and `pack_room.js` still has no field for it. Do not wire them. `test_a4_binaural_hides_dead_rows` stays a known flake (F10). Routing preamps and compressors stay in the tree, default off. 610-A stays untrimmed.

## Fix runs, about an hour each

- **Run 1.** Keep `@pytest.mark.slow` out of FULL. Add `-m "not slow"` to the FULL line in `CURRENT_BRIEF.md`. Take the slow mark off the two 400 ms bit-exact tests in `test_sl2_loop.py` so Flat-ignores-rows stays in FULL. Leave the full-length SL4 and SL5/SL6 renders, including the auto-treat xfail, on the slow mark. Point their proof writes at a temp file so a later opt-in does not rewrite `software\proof\`. Update the 16/23 comment in `test_sl6_auto_treat.py` to the PC scores. No DSP edit. No Auto-treat edit.
- **Run 2.** While Play is running, show 32 on the Hadamard chip when the stored size is 64 or 128. Play's size law stays. UI only. Do not edit `live_stereo.c`.
- **Run 3.** One wasm check that section 14 changes a sample, same shape as the section 13 test. Off-axis on against the key absent. No coefficient edit. No listen render.
- **Run 4.** One wasm check that section 8 changes a sample. Knob 0 against knob 100. The curve stays 0 / 0.10 / 0.15 ms. Parity, flat cards, mirror/null, and direct-only still force 0.
- **Run 5.** One short Render IR. Absent and `box` match. `splay` differs. Do not add A–F letters. Do not teach Play the key.
