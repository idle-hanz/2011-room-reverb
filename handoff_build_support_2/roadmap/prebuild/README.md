# Thursday prebuild (4 Oct 2026, box)

Standalone, tested pieces for T1, T2, T3, T7/T8 and the T10 tab redesigns, so the Build sessions only integrate.
Line numbers are for the current app copy (`ui_audit_1004/app/software`, build WORKLET_VER 51 = the 13:54 zip of the PC `software\`). Check them with one `rg` before editing; they can drift by a few lines.

| Folder | What | Tests | Proof in the box app copy |
|---|---|---|---|
| `t1_knob/` | `rr_controls.js` (+css, boot): relative-drag knobs, Shift fine, detents, double-click reset, wheel, PageUp/Down, click-to-type on every slider readout | `node --test test_rr_controls.mjs` (8 pass) | `prove_t1.py` → `shots/t1_*.png`, `t1_results.json` (injected into the real Mix tab) |
| `t2_mixer/` | `lr_buttons.js`: L/R buttons with Ø → existing routes; truth table U7 / D-UI31 | `node --test test_lr_buttons.mjs` (11 pass) + `tests_py/test_t2_lr_null_draft.py` (12 pass, real `fold_for`) | `prove_t2.py` → `shots/t2_*.png` (demo page with app CSS) |
| `t3_ms/` | `ms_presets.js`: presets a/b/c (D-UI29), decode maths, D18 levels (`MS_LEVEL`) | `node --test test_ms_presets.mjs` (9 pass) + `tests_py/test_t3_ms_presets_draft.py` | `prove_t3.py` → `shots/t3_ms_m35.png`, `t3_ms_m0.png` |
| `t3b_ms_sound/` | D19 `d19_render_pipeline.diff` (MS direct pattern, Render + Play) + D18 switch | `tests_py/test_t3b_ms_sound_draft.py` (2 pass, 2 strict xfail → XPASS with the diff); `suite_compare.txt` (ORTF/default renders bit-exact) | — |
| `t4b_ortf_c/` | D20 ORTF C off + "ORTF + C": integration points (golden change) | `tests_py/test_t4b_ortf_c_off_draft.py` (3 pass, 1 strict xfail) | — |
| `t7_t8_drag/` | `drag_model.js`: wall/corner/ceiling drag, mic drag (Mirror/Linked/Split), per-strip room spots | `node --test test_drag_model.mjs` (12 pass) + `tests_py/test_t7_room_spots_draft.py` | `prove_t8.py` → `shots/t8_*.png` |
| `mockups/` | Static Surfaces, Polar and Space (non-rect) redesigns, app CSS | — | `shoot.py` → `shots/mock_*.png` |
| `tests_py/` | pytest drafts + `_harness.py` + UI body fixtures | `pytest tests_py` on the box: 22 pass, 2 skip (T6 not merged), 4 strict xfail (flip in T3b/T4b) | — |
| `sl/` | **SL1–SL6 Surfaces in the loop** (4 Oct 22:00): `engine/surf_*.py`, `patches/` (fdn, render_pipeline, app_server, live_stereo.c), `play_c/` benches, `ui/sl_room_result.js/.css`, see `sl/README.md` | `sl/tests`: 36 fast pass; slow SL2 4/4, SL4 4 + 1 xfail (finding), SL5/6 2/2; Flat bit-exact 9/9 | `sl/ui/prove_sl_ui.py` → `sl/shots/*.png`, `sl_ui_results.json` (port 7873) |
| `app_copy_files/` | The exact files as served by the box app copy (`static/prebuild/`, `static/mockups/`) | — | — |

How the proof was run (box): copy of the app at `/workspace/build_support_2/prebuild_app`, served by uvicorn on 127.0.0.1:7872; modules copied to `static/prebuild/`, mockups to `static/mockups/`. Only two edits to the box copy: three tags after `index.html` line 901 and one hook line in `app.js` `syncUINow()` after line 2414. The PC `software\` was not touched.

To run the proofs again on the box: start the server (`cd prebuild_app/software && /workspace/ui-venv/bin/python -m uvicorn app_server:app --port 7872`), then `python t1_knob/prove_t1.py http://127.0.0.1:7872/ shots/` etc.
