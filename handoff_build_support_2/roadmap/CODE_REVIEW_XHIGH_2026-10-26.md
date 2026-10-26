# Code review for Ben Supper (read-only), 2026-10-26

Audience: tidy and scrutable first, then a tighter rebuild. No product file was edited. Long comments are left out of this list on purpose.

Pins every batch below must keep: empty MD5 `067adbca1930efcd3f7c83bdd1d4c359`, centre MD5 `35db578a18557d5729c0450e26f24a9d`, the five golden sha1s in `software\tests\test_quick_pins.py`, `WORKLET_VER` 63. Do not edit `engine\live_stereo.c` in these batches. A C edit rebuilds the wasm. The earlier note `roadmap\CODE_REVIEW_2026-10-26.md` still says `MOVEMENT_FORCED_OFF` is in the tree. That flag is already gone (`c4a1645`).

## Line count

One method, used for the total below. `software\**\*.py` and `software\**\*.js` only. Skip any path that contains `.venv`, `node_modules`, `vendor`, or `__pycache__`. Count non-blank lines, the same rule as PowerShell `Measure-Object -Line`.

Current tree (`361059d`): **45,246**. Python 101 files, 28,653 non-blank. JavaScript 44 files, 16,593 non-blank. Physical lines on that same filter are 49,850. `vendor\three.min.js` is 7 lines and is excluded.

The last two runs counted commit `e1df12a` (solo match landed, plaster law not yet in). They used two counters:

| Run | Counter | vendor JS | Python | JavaScript | Sum |
|---|---|---|---|---|---|
| 49,508 | every physical line (`Get-Content.Count`) | included (7 lines) | 100 files, 32,005 | 45 files, 17,503 | 49,508 |
| 44,942 | non-blank (`Measure-Object -Line`) | excluded | 100 files, 28,349 | 44 files, 16,593 | 44,942 |

The gap is 4,566. Blank lines are 3,656 in Python and 903 in JavaScript (4,559). The other 7 are `three.min.js`. Same commit. Later plaster work (`84ea47a`, `361059d`) moved the non-blank total from 44,942 to 45,246.

## 1. Files over 1,500 lines, functions over 150

Physical lines. A split moves lines. Net saving is 0 unless the row also names a delete.

| File | Lines | Split |
|---|---|---|
| `engine\live_stereo.c` | 4,174 | Later rebuild only. `bus_sample` 2634–2948 (315), `mix_partition` 3717–3921 (205), `run_partition` 3949–4129 (181), `live_load_room` 1773–1928 (156). Leave it while the pins include this wasm. Saving now: 0. |
| `render_pipeline.py` | 3,798 | Three modules: early IR (`render_early_ir` 585, `render_fdn_ir` 1186, `combined_ir` 1578), the offline render, the live pack. Saving: 0. |
| `engine\early_field.py` | 2,501 | Move the RBJ copies out (section 2). Leave `compute_taps` 1709–1957 (249) as the shoebox tap list. Saving: about 70, in batch B. |
| `static\js\mic_desk.js` | 1,748 | `create` is the file, 144–1742 (1,599). Lift each drawing pass to a sibling in the same file so `PIN_TABLE` stays. Saving: 0. |
| `app_server.py` | 1,719 | No function over 150. Cut at the route groups already marked: page and live (`926`), render (`1365`), catalogues (`1649`). Saving: 0. |
| `engine\fdn.py` | 1,615 | No function over 150. Matrix, process loop, and the CLI can be three files. Saving: 0. |

Other functions over 150 lines:

| Where | Lines | One-line fix | Saving |
|---|---|---|---|
| `static\js\room_editor.js:22` `RoomEditorCreate` | 1,273 | Same as mic desk: sibling functions in this file. | 0 |
| `static\js\room_3d.js:18` `create` | 1,095 | Same. | 0 |
| `render_pipeline.py:1764` `_render_core` | 900 | Three functions: two-source, still IR, moving path. The decay block is copied at 2086, 2325, and 2560. | 0 from the split. About 40 once the block is one helper (batch C). |
| `static\js\image_views.js:12` `create` | 853 | Sibling functions in this file. | 0 |
| `render_pipeline.py:3026` `live_fdn_params` | 539 | One scene builder, then the pack. `solo_match._scene` calls that builder. | about 90 (batch D) |
| `static\js\source_desk.js:23` `create` | 440 | Sibling functions in this file. | 0 |
| `polar_field.py:441` `compute_polar_field` | 437 | The mesh is one function. `surfaces`, `diffusion_seed`, `lambda_ref`, `hadamard_n` are deleted at 494. Drop those four parameters. | about 6 |
| `tweak_app.py:249` `build_ui` | 348 | Delete the Gradio app with the file (batch A). | 610 for the file |
| `settings_table.py:98` `_rows` | 274 | This is the settings list. Leave it. | 0 |
| `static\js\rr_transport.js:188` `syncUINow` | 179 | Leave it until a UI batch. It is the post path. | 0 |
| `image_geometry.py:169` `build_images_payload` | 165 | Leave it. Display payload. | 0 |
| `engine\poly_room.py:485` `compute_poly_taps` | 161 | Leave it beside `compute_taps`. Merging the two tap builders is the later rebuild. | 0 |

Test functions over 150 (`test_s_audit_ui.py:532` 237, `test_mic_colour_relative.py:828` 225 and `:484` 155, `selfcheck.py:948` 158) are long asserts. Leave them. They pin behaviour.

## 2. Duplicated maths

Python already has `engine\maths_*.py` with JS twins and `tests\test_maths_parity.py`. The rows below are the copies still outside those modules.

| Sites | One-line fix | Saving |
|---|---|---|
| `surface_colour.py:74` `rbj_peaking`, `:89` high-shelf, `:105` low-shelf, and the same three at `engine\early_field.py:1502`, `:1622`, `:1605`. Bodies match. The comment at 1606 says the copy exists to avoid an import cycle. | New `engine\rbj.py`. Both files import it. Leave `source_radiation.py:190` (it clamps `f0` to `0.45*fs`). | about 70 |
| `engine\fdn.py:95` `unscaled_hadamard_signs` and `engine\fdn_stub.py:20`. Same Sylvester loop. `inject_tap_into_fdn` is in both (`fdn.py:303`, `fdn_stub.py:32`). | Delete `fdn_stub.py`. Point `early_field.py:43` at `fdn.stub_note`. | 49 |
| Decay-lock block. Render at `render_pipeline.py:2086`, `:2325`, `:2560` (delays use the default channel `"mean"`, `g_loop` when `line_t60 > 0.05`). Play at `:3204` (channel `"c"`, `g_loop` when `line_t60 > 0.0`). `solo_match.py:213` follows Play. | One helper. The caller passes the channel and the threshold. | about 40 |
| Knee. `live_stereo.c:587` `soft_limit` and `render_pipeline.py:397` `ls_exp` plus `:421` `soft_limit` (hand-copied polynomial). `tests\test_live_stereo.py:19` `soft_py` uses `math.exp` and is what the wasm test calls (`:232`). | Keep both product copies (C stays). Point the test at `render_pipeline.soft_limit` as well as `live_soft`. If that assert fails, stop and report the delta. | about 8 in the test |
| Solo hold. `solo_match.py:73` `resolve_gain` and `static\js\live_fdn.js:103` `soloMatchHold`. Display dB is `20 * Math.log10` at `live_fdn.js:125` while `maths_db.js` already has `linToDb`. | Call `RRDb.linToDb` from `formatSoloMatch`. Leave the two hold functions. They are the server measure and the page hold. | about 2 |

`live_stereo.c` FWHT (`2225`) and `fdn.py` Sylvester stay as the Play and Render pair until the rebuild. `selfcheck.py:573` already checks the Python signs.

## 3. Dead code, unused parameters, stale flags

`MOVEMENT_FORCED_OFF` and `RR_SL_STAGE` are already deleted. What is still here:

| Site | Safe to delete? | One-line fix | Saving |
|---|---|---|---|
| `tweak_app.py` (610). Gradio UI. `Launch Tweak App.bat` does not start it. | Yes for the four pins. | Delete the file. | 610 |
| `engine\moving_room_demo.py` (431). No importer. `render_pipeline.py:1900` only names it in a comment. | Yes. | Delete the file. | 431 |
| `engine\polygonal_stub.py` (224). No importer. Live polygons are `poly_room.py`. | Yes. | Delete the file. | 224 |
| `engine\fdn_stub.py` (49). Only `early_field.py:43` imports `stub_note`, and only the CLI prints it (`:2467`). | Yes, after that import moves to `fdn.py`. | Delete the file. | 49 |
| `render_pipeline.py:1812` `mic_hp_on`, `:1813` `mic_hp_hz`, `:1815` `mic_proximity`. The names appear only in the signature. The body never reads them. | Yes, from `_render_core` and the call sites. Leave the settings rows. The page still posts `mic_proximity` 0.25 (`CURRENT_BRIEF`). | Stop passing them into `render()`. | about 15 |
| `solo_match.py:53` `SMOOTH_S`. Nothing reads it. The 50 ms ramp is on the page. | Yes. | Delete the constant. | 1 |
| `polar_field.py:494` four parameters deleted on entry. | Yes, from this function, once callers stop passing them. | Drop the four names. | about 6 |
| `tests\test_movement_knob.py:62` asserts the flag attribute is absent. The rest of the test pins the 0 / 0.10 / 0.15 ms curve. | The one assert, yes. Keep the curve asserts. | Delete that line. | 1 |
| Routing preamps and compressors, default off. | No. Idle left them until asked. | Leave the code. | 0 |
| The air one-pole in `live_stereo.c`. Play packs `air_lp` 0 at `render_pipeline.py:3063`. | No, in these batches. Removing it rebuilds the wasm. | Leave it. | 0 |

## 4. Play and Render compute the same thing on different formulas

These stay different. The batches name them. They do not merge them.

| What | Play | Render | One-line fix | Saving |
|---|---|---|---|---|
| Stock plaster on a hit face | `tap_reflect_gain` (`render_pipeline.py:877`) multiplies `√(1−mean α)`, then `_surf_rel_stages` (`:909`) adds a peaking bell per band relative to that mean, then `fit_line_cascade`. | Early uses `surface_filter_stages` (`surface_colour.py:780`): seven absolute bells, `20·log10(√(1−αᵢ))`, no separate mean. FDN inject uses the Play formula (`_scale_inject_reflect`, `:975`). | Leave both. A shared name in a comment at each call is enough. | 0 |
| Decay-lock loop gain | Centre delays, `line_t60 > 0.0` (`:3204`, `:3211`). | Mean of L/C/R delays (default channel `"mean"`, `fdn.py:816`), `line_t60 > 0.05` (`:2093`). | Pass channel and threshold into the helper from batch C. Do not pick one. | 0 beyond batch C |
| Hadamard size | `live_fdn_params` `:3055` keeps 8, 16, 32. `live_stereo.c:1414` does the same. 64 and 128 stay on 32 lines. | `hadamard_n` on `_render_core` (`:1795`) can be 64 or 128. | Rename the Play local to `play_n` at `:3055`. | 0 |
| Solo-match early | `solo_match.py:249` sums integer-delay spikes times `tap_reflect_gain`. The tail is full `render_fdn_ir`. | Render does not apply this gain (`solo_match.py:1`). The page applies a GainNode. | Leave it. It is a meter, not a second reverb. | 0 |

On one stock wall at 48 kHz the early bells and the Play mean-plus-relative bells differ by up to **0.50 dB** across 50 Hz–18 kHz. That number is from running the two functions on `_STOCK_ABSORB`.

## 5. Names a new reader will misread

| Site | One-line fix | Saving |
|---|---|---|
| `card_absorb_kind` (`surface_colour.py:739`) returns `stock`, `uniform`, `shaped`, `empty`, `mute`. `cards_are_flat` (`render_pipeline.py:748`) is true only when every band equals the mean. Stock plaster `(0.05 … 0.22)` is `stock`, and it is not `cards_are_flat`. The empty scene is stock. A flat card is `uniform`. | Say "stock plaster" and "one α on every band" at the two call sites that still say "flat" for the default room. | 0 |
| `hadamard_n` is one key and two sizes (section 4). | `play_n` at the clamp. | 0 |
| `g_loop` uses `> 0.05` in Render and `> 0.0` in Play. | Name the arguments `t60_gate_s` on the helper. | 0 |

## 6. Tests

| Site | One-line fix | Saving |
|---|---|---|
| `tests\test_t3_ms_presets_draft.py:21` expects centre weights 1.5. `_harness.py:42` defaults `m_gain=1.5`. The page default is `MS_LEVEL = "unity_trim"` (`ms_presets.js:21`). `tests\test_ms_presets.mjs` already pins both levels. | Delete the draft. | 40 |
| `tests\test_t2_lr_null_draft.py` (46), `test_t3b_ms_sound_draft.py` (41), `test_t4b_ortf_c_off_draft.py` (55), `test_t7_room_spots_draft.py` (148). Prebuild drafts next to newer `.mjs` tests. | Delete a draft only after the `.mjs` file asserts the same numbers. | up to 290 |
| `tests\test_sl5_wire.py:76` asserts the source text has no `RR_SL_STAGE` and that two function names exist. | Keep the shell-row behaviour test. Drop the three source-text asserts. | about 4 |
| `tests\test_live_stereo.py:19` pins the wasm knee to `math.exp`, not to `render_pipeline.soft_limit`. | Add the product function beside `live_soft`. Stop if they disagree. | about 8 |
| `tests\test_movement_knob.py:62` pins a deleted attribute. | Delete that assert. Keep the curve. | 1 |
| `test_quick_pins.py:121` and `:126` pin `WORKLET_VER` and the `?v=` table. | Leave both. A new script tag updates `PIN_TABLE`. | 0 |

## (a) `solo_match.py` from `e1df12a`

The commit added 428 lines. The file is still 428. The gain math is `match_lin` (`:59`) and `resolve_gain` (`:73`), about 40 lines, and it stays.

What can go:

| Lines | Cut | Saving | Pins |
|---|---|---|---|
| `_scene` `:150–242` | Call the Play scene builder from batch D. This is a second MicStand, `compute_taps`, colour, and decay-lock `g`. | about 90 | Holds if the builder is a move. `test_solo_match` still expects about −9.9 dB. |
| `SMOOTH_S` `:53` | Unused. | 1 | Holds. |
| `_tail_key` `:286–331` | A tuple of the fields `render_fdn_ir` already takes, instead of a hand-built JSON blob. | about 20 | Holds if the key still changes when the tail changes. |
| `_early_stereo` `:249–279` | This is the simplified spike sum. Replacing it with `render_early_ir` moves the −9.9 dB figure. | about 30 | Do not cut it in a pin batch. |

Leave `play_early_energy` (`:404`). The test calls it. Leave the tail render and the cache. Render, presets, and the goldens do not read this module (`:1`).

## (b) Stock plaster from `84ea47a`

The new law cannot reproduce the old one exactly. The old branch stays.

Stock list: `_STOCK_ABSORB` `(0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22)` at `surface_colour.py:147`. Mean α = 0.118571. Broadband gain `√(1−mean)` = 0.938844 (−0.548 dB).

Three formulas are in the tree:

1. Play and Render FDN, stock only. Broadband `√(1−mean)`, clamped at 0.95, times seven RBJ peaks at Q 0.9 whose gains are `20·log10(√(1−αᵢ)) − 20·log10(√(1−mean))`. Then `fit_line_cascade`. `_line_is_exact` (`render_pipeline.py:944`) returns false for stock, so the empty live pack is that fit.
2. Render early, stock only. Seven absolute peaks, no broadband mean (`surface_colour.py:795`).
3. Shaped cards. `fit_absorb_stages` (`surface_colour.py:1032`) fits biquads to the interpolated curve `20·log10(√(1−α))` and does not multiply the mean. A uniform card is one scalar `√(1−α)` and no peaks (`uniform_reflect_lin`, `:766`).

On one stock wall at 48 kHz, formula 1 and formula 3 differ by up to **0.41 dB** on a 240-point log grid. Formula 2 and formula 3 differ by up to **0.91 dB**. Formula 3 returned **2** biquads. Formula 1 starts from **7** peaks and then fits them again. The packed floats cannot match, so the empty MD5 would move. A single scalar `√(1−mean)` drops the relative bells (several tenths of a dB) and moves the pack as well.

There is no `sqrt(1−α)` target whose float32 cascade equals today's stock pack. Delete the stock branch only in a run that is allowed to re-pin the empty MD5.

## Top 10 batches

Each batch is one run. Each keeps the four pins. None edits `live_stereo.c`, the decay-lock numbers, the movement curve, the routing preamps, or the stock plaster branch.

1. **Reference modules.** Delete `tweak_app.py`, `moving_room_demo.py`, `polygonal_stub.py`, and `fdn_stub.py` after `early_field.py` prints `fdn.stub_note`. About 1,314 lines.
2. **One RBJ designer.** `engine\rbj.py` replaces the matching designers in `surface_colour.py` and `early_field.py`. Leave `source_radiation.py:190`. About 70 lines.
3. **One loop-gain helper.** Replace the three Render copies and the Play copy. Arguments are the delay channel and the `line_t60` gate (`"mean"` / `0.05` for Render, `"c"` / `0.0` for Play and `solo_match`). About 40 lines.
4. **Solo scene.** `solo_match._scene` calls the Play builder from batch 3's neighbourhood (`live_fdn_params`). Delete `SMOOTH_S`. Shorten `_tail_key` to a tuple. About 110 lines. `test_solo_match` stays on −9.9 dB.
5. **Unread render parameters.** Remove `mic_hp_on`, `mic_hp_hz`, and `mic_proximity` from `_render_core` and its callers. Leave the settings rows. About 15 lines.
6. **Split `_render_core`.** Two-source, still IR, moving path. No formula change. 0 lines.
7. **JS `create` functions.** In `mic_desk.js`, `room_editor.js`, `room_3d.js`, `image_views.js`, and `source_desk.js`, lift the inner passes to siblings in the same file. No new script tag, so `PIN_TABLE` stays. 0 lines.
8. **Draft tests.** Delete `test_t3_ms_presets_draft.py` (the 1.5 centre gain). Delete another draft only when its `.mjs` twin asserts the same numbers. 40 lines, up to about 330.
9. **Knee test.** Assert `render_pipeline.soft_limit` against `live_soft` next to the existing `math.exp` check. Stop on a miss. Do not retune the knee. About 8 lines.
10. **Names only.** At `live_fdn_params:3055` call the clamped order `play_n`. On the loop-gain helper, name `t60_gate_s`. At the stock call sites, say "stock plaster" where the sentence currently reads as the uniform flat card. 0 lines.

Explicitly later, after a run that may re-pin: replacing the stock mean-plus-peaks path with `fit_absorb_stages` (section b), and splitting `live_stereo.c`.
