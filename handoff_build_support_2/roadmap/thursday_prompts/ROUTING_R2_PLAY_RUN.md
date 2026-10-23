# Array and room inserts in Play (one goal)

Start at `CURRENT_BRIEF.md`. RUN_RULES 17-22. Do not reconcile `HANDOVER.md`. Do not open the app. Do not touch 610-A.

Play already posts the master strip. Array and room inserts are still Render only. Put those two on Play, lean. Pack with `play=True` (Neve 1x, Room Crush colour 1x). That cheaper oversampling is the one to use. 610-A stays 8x on both paths. Do not edit its flux or `os_factors`. If the ceiling fails only with a 610 strip on, stop and report that median. Do not lower 610. The gate body has no 610.

Default scene stays bit-exact. Empty live MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`. Centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`. An off strip adds no live-dict field. `heardMix` deletes the route keys and assigns `masterScene` only. Post `array_*` and `room_*` only when that strip is on, same names as `renderScene`. Amount 0 stays off. Do not arm array or room.

`live_fdn_params` packs one `bloom` and one `pre_colour` when `bloom_is_on`. `pack_room.js` sends those as sections 10 and 12. `bloom_apply` is one coeff set. Render order is `_route_buses` then `_apply_chain`. Play matches that: the side insert for that bus, then the master chain. Direct and early stay outside. A missing place stays array. The room insert runs on a bus only when its place is room. Place stays out of the live blob while both side strips are off.

This edits `live_stereo.c`. Before the first wasm edit, confirm the empty MD5 above. A mismatch stops the run. A match continues in the same session. Do not score-and-stop. Today's wasm cannot run this gate. `t19` benches the default scene only.

Gate, one number. Shared off, master off, one source, the default scene plus these keys: array Neve 6 dB then Glue 100, room Room Crush 100 with the preamp off, `place_c` room. Same timer as t19. From the repo root:

```
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\lib\dump_params.py software "{\"array_preset\":\"glue\",\"array_amount\":100,\"array_pre\":\"neve1073\",\"array_drive_db\":6,\"room_preset\":\"room_crush\",\"room_amount\":100,\"place_c\":\"room\"}" C:\Users\IdleHanz\AppData\Local\Temp\r2_play.json 48000
node handoff_build_support_2\3_phase_acceptance_tests\harness\lib\wasm_run.js software C:\Users\IdleHanz\AppData\Local\Temp\r2_play.json {} bench 4 10
```

`play_median_ms` ≤ 2.40. Silence-late under that same 2.40. Report the off-body median from the same session (`bench 4 10` on `{}`). Do not raise 2.40 or 2.133. Do not add a shared-on bench.

Side checks, not a second gate. Update `test_array_keys_stay_out_of_the_live_dict`: the on body gains a field, the off body stays the empty MD5, Neve's play factor is 1. A short `wasm_run.js` `ir` of the array-on body differs from the off body on the left channel. Room off leaves the centre. No wav in the repo.

QUICK, from `software\`, after each step:

```
node --test tests\test_routing.mjs
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_routing.py -q -p no:cacheprovider
```

Wasm rebuild uses the venv zig. There is no emcc. Commit before the first `live_stereo.c` edit. After the gate passes, update the one Play-posts-master sentence in `CURRENT_BRIEF.md` and the matching sentence in the HANDOVER Current pin, plus any version token you bumped. Then FULL once, the block in `CURRENT_BRIEF.md`. Acceptance `--slow` stays off. If the gate fails, stop before FULL. Report under 20 lines: the median, the empty MD5, and that 610 stayed 8x.
