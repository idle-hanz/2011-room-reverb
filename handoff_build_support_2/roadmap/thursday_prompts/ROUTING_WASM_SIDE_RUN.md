# One wasm check that section 13 moves a sample

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`. One goal. Do not open `HANDOVER.md`. Do not open the app. Do not touch 610-A, Bloom coefficients, oversampling, makeup, the decay lock, or the 2.40 ms ceiling. Do not edit `live_stereo.c`, `bloom_live.inc`, `app.js`, or `routing_scene.js`. Do not rebuild wasm.

Review: `handoff_build_support_2\roadmap\CODE_REVIEW_2026-10-23.md`, finding 3.

`test_routing.mjs` ("an on array strip reaches the worklet as section 13") only slices `pack_room.js`. `test_routing.py` checks the Python live dict. Neither loads `software\static\wasm\live_stereo.wasm`. `wasm_run.js` already copies `side` when it has at least 217 floats.

Score this before any edit. From the repo root, two short Play IRs. The on body is the default scene plus array Glue at Amount 100, preamp off. That pack is `side` length 217 with the array comp flag at index 3. Colour off. No 610.

```
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\lib\dump_params.py software "{}" C:\Users\IdleHanz\AppData\Local\Temp\side_off.json 48000
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\lib\dump_params.py software "{\"array_preset\":\"glue\",\"array_amount\":100,\"array_pre\":\"off\"}" C:\Users\IdleHanz\AppData\Local\Temp\side_on.json 48000
node handoff_build_support_2\3_phase_acceptance_tests\harness\lib\wasm_run.js software C:\Users\IdleHanz\AppData\Local\Temp\side_off.json "{\"colour_on\":false}" ir 0.25 C:\Users\IdleHanz\AppData\Local\Temp\side_off.f32
node handoff_build_support_2\3_phase_acceptance_tests\harness\lib\wasm_run.js software C:\Users\IdleHanz\AppData\Local\Temp\side_on.json "{\"colour_on\":false}" ir 0.25 C:\Users\IdleHanz\AppData\Local\Temp\side_on.f32
```

Left channel of the on file must differ from the off file (max-abs > 0). If they match, stop and report that max-abs. Do not edit the wasm.

If a sample moves, add this pair to `software\tests\test_routing.py`. Keep the IR at 0.25 s. Do not rename the node test. Empty live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`. `app.js?v=70` and `routing_scene.js?v=3` stay.

QUICK, from `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_routing.py tests\test_quick_pins.py -q -p no:cacheprovider
node --test tests\test_routing.mjs
```

No FULL. Report under 20 lines: the max-abs, and whether the new test landed.
