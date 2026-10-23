# Code review, 2026-10-23

Read-only. No audio law was changed. 610-A was not touched.

## How a control gets to sound

A control writes `state`, then `syncUI()`. While Play is running, `syncUINow` always calls `scheduleLiveParams()` (`software\static\js\app.js`, line 2992). That posts `heardMix(state)` to `/api/live_params`. Render posts the same `heardMix` body as `params_json`.

`heardMix` turns the desk into wet gains. It strips the raw routing keys and puts back what `routing_scene.js` allows: the master strip as the Bloom keys Play already reads, and an array or room strip only while that strip is on (a preamp chosen, or a compressor whose Amount is above 0). Off adds nothing.

The server (`params_from_body`, then `live_fdn_params`) builds the live dict. `pushParams` in `live_fdn.js` copies a fixed list into the worklet message. `pack_room.js` packs that list. The worklet copies the blob and the side buffers (colour, surfaces, prox, room tone). `live_stereo.c` and `bloom_live.inc` read the sections. Master compressor is section 10, master preamp is section 12, array and room share section 13. Section 4 is always empty.

The two silences from the last runs are fixed in this tree. `onRoute` calls `scheduleLiveParams` after `syncUI`. `pushParams` keeps `bloom` when the list is at least 26 floats, and the Python pack is 40. Default Play (every strip off) still matches the empty live MD5.

## Findings, worst first

1. **Array and Room compressor menus stay silent at Amount 0.** Master, on a change from Off onto a preset, sets Amount to 100 (`armMaster`). Array and Room do not. `onRoute` only arms `route_master_comp`. Amount 0 means the strip is off, so Play posts no section 13 and Render posts no array or room insert. The node test locks that asymmetry. Same heard silence as the master menu, on the other two strips. Wiring only. Do not change Bloom coefficients, oversampling, or 610-A.

2. **`test_a12` is a flake, and its allowlist is also stale.** The full-suite failure ("quiet controls under suite load") passed alone in 89.81 s. The test gives up after 900 ms. A busy machine can miss the animation frame plus the 45 ms Play debounce, so a control that did post looks quiet. That red run is not a product fault. `test_a5` is the same kind of load flake (Play must reach `suspended` inside 8 s). Separately, `_UI_ONLY_IDS` still exempts every routing control, with a comment that Play does not post them. That comment is the R1 pin. After R2 those controls do post when the strip is on, so a green `test_a12` does not prove it. A dropped `scheduleLiveParams` on the routing panel would still pass.

3. **The routing "worklet" tests never run the worklet.** `test_routing.mjs` slices `pushParams` and `packRoom` and checks section 10 and section 13. `test_routing.py` checks the Python live dict (`bloom[0] == 2`, `side` length 217). Neither loads the wasm. A drop inside `bloom_arm` or `load_side_section` would stay green. The names overclaim. The checks they do make are real for the JS pack and the server dict.

4. **Hadamard 64 and 128 stay lit during Play while the player forces 32.** The chips are marked Render only and are disabled once Play is running, but a 64 chosen before Play stays the active chip. `live_stereo.c` keeps 8, 16, or 32 and ignores anything else. Render can use 64 and 128. The label is right. The lit chip during Play is not.

5. **Dead, leave them.** No Mix controls for `mic_hp_on`, `mic_hp_hz`, or `mic_proximity`. `render()` accepts `mic_hp_on` and `mic_proximity` and never reads them. Movement is hidden and forced off. Path and ellipse live on the old Gradio page, not this app. `direct_makeup` is in the live JSON and is not copied by `pushParams`. Do not wire it. Duplicate widgets that already share one state (two diffusion-seed boxes, two height-link boxes, yaw slider plus number) are fine. `colour_impl` posts Play without repainting; the next `syncUI` catches the chrome.

## Fix runs, about an hour each

- **Run 1:** `thursday_prompts\ROUTING_ARM_SIDES_RUN.md`. Arm Array and Room the way Master already arms, and take the routing ids off the `test_a12` allowlist.
- **Run 2:** Give `test_a12` a settle that survives a loaded suite, so a late post is not marked quiet. Do not change product code.
- **Run 3:** One wasm check that a packed section 13 changes a sample, so the routing test matches its name. No coefficient edits.
- **Run 4:** When Play starts on 64 or 128, show 32 on the chip. Play's size law stays.
