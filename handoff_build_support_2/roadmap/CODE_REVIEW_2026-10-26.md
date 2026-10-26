# 2011 Room Reverb: structural code review (read-only), 2026-10-26

Scope: `software\` on Idle Hanz's PC, plus repo layout. No edits, commits or test runs. Line counts come from a PowerShell scan while Build was editing, so expect small drift. Function lengths are approximate (measured from one def to the next).

## 1. Size
| File | Lines | Biggest functions |
|---|---|---|
| static/js/app.js | ~4,270 | one monolith: no top-level `function` decls found, so it's all closures/arrow fns inside one scope |
| engine/live_stereo.c | ~4,170 | bus_sample ~316, wire_defaults ~222, mix_partition ~206, run_partition ~183 (119 functions) |
| render_pipeline.py | ~3,780 | _shape_taps ~375, _sum4 ~219, _render_core ~211, _pad_m ~187 |
| engine/early_field.py | ~2,630 | _shelf ~177, enumerate_scaled_grid ~134, hadamard_n_for_grid ~131 |
| app_server.py | ~1,780 | params_from_body ~271, _render_impl ~189, api_colour ~118 |
| static/css/app.css | 1,668 | |
| static/js/mic_desk.js | ~1,650 | |
| engine/fdn.py | ~1,610 | process_block_poly ~146, __init__ ~130 |
| room_editor.js, colour_surfaces.js, room_3d.js, selfcheck.py, bloom_dsp.py, index.html | 1,000–1,360 each | |

The verbosity is in the code itself, not the comments. Comment lines are only 1–6% per file. What Ben is reacting to is long functions, long parameter plumbing (params_from_body is 271 lines of key-by-key mapping), and one 4k-line app.js.

## 2. Duplicated logic (Render Python, Play C/WASM, UI JS)
Keyword hits across files that don't import each other:
- **Polar/pattern maths:** cardioid etc. in early_field.py, pattern_map.py, polar_field.py, app_server.py, app.js, mic_desk.js, ms_presets.js and room_math.js. This is the hypercardioid bug and the polar double-count from last week: the same formula lives in about 5 places and they drift apart.
- **Hadamard/FDN:** fdn.py, fdn_stub.py, early_field.py, render_pipeline.py, live_stereo.c, app_server.py, image_geometry.py, tweak_app.py and app.js.
- **Biquads:** in 12 files (early_field, fdn, bloom_dsp, surf_loop, surface_colour, render_pipeline, tail_diffuse, sos_fit, design, moving_room_demo, live_stereo.c, fdn_core.c).
- **Air absorption:** early_field, fdn, render_pipeline, moving_room_demo.
- **Pan law:** desk_matrix, fdn, app_server, app.js.

Python vs C duplication is deliberate (Render vs Play), but there's no single spec for both. Recommended: one Python module per maths topic (pattern.py, biquad.py, air.py) that is the reference. The C copy gets a parity test against it, and the JS fetches computed values from the server (/api/polar already exists) instead of re-deriving them.

## 3. Dead or stale code
- `MOVEMENT_FORCED_OFF = False` (render_pipeline.py:814) has an `if` branch that never runs and a test that only asserts the flag is False.
- `RR_SL_STAGE` (sl_room_result.js:22) is a build-stage switch that's always 6. A test asserts the HTML string `RR_SL_STAGE = 6`.
- Flag/legacy hits (parity, air_1pole, link_mode, mic_proximity, FORCED_OFF, legacy/deprecated): render_pipeline 35, app_server 17, app.js 16, early_field 14, surface_colour 8, desk_matrix 6, lr_buttons 6, pair_mode.js 5, fdn 5. Build's queued tidy-ups take out most of these.
- `.orig` files are sitting in the source tree: engine/live_stereo.c.orig, static/index.html.orig, tests/test_mic_colour_relative.py.orig.
- Python defs with no other textual reference include: _add3, _norm3, _bad_param, anchored_target, apply_capsule_colour, diffusion_extra_stages, discrete_boost_db, diverg_approx_from_toe_half_deg, early_toys_for, effective_surfaces, fit_resonance, iso_path_loss_db, k_for_dial, live_triples, material_legal, membrane_*_physical, perforated_alpha_physical, porous_alpha, mirror_point_through_facet, model_path_loss_db, omitted_unique_ids, os_factors, pack_blob_v2, pattern_gain, phys_teff_bands, render_binaural_fdn_ir, render_direct_ir, room_shell_rows, theory_b_db, preview_path. The api_* names are Flask routes, so those are false positives. Every one needs checking before deletion (dynamic dispatch, tests, scripts).
- Demo and prototype modules inside the shipped engine: moving_room_demo.py, fdn_stub.py, tweak_app.py (546 lines).

## 4. Verbosity and noise
- Run-history markers (dates, "run N", golden/sha1/bit-exact notes): live_stereo.c 28, render_pipeline 13, early_field 8. These belong in git history, not in the code.
- Cache pins (`?v=NN`) are asserted in about 11 tests (test_room_shape_3d 4, test_quick_pins 3, others 1–2). Every UI run has to bump the pins and fix these tests. Replace them with one generated asset hash, or a single test that the pins are consistent.
- Tests that only pin a flag or string (MOVEMENT_FORCED_OFF, RR_SL_STAGE) should go along with their flags.
- 71 test files and 227 pytest cases. FULL took 30+ minutes. Profile with `--durations=20`, then mark the slow audio/golden tests and run them only before a push.

## 5. Repo clutter (move out of the shipped repo; archive elsewhere)
- `data/` holds a 1.4 GB Zenodo zip. Download it on demand, and gitignore it.
- `software_backup_2026-10-02_preS4b.zip` (390 MB), `mic_fitter_v2_backup_20260923_0853/` (94 MB), mic_fitter_desktop_v1/v2/v3, nt2a_addon and polar3d tarballs (~50 MB).
- `handoff_build_support_2/` (2,632 files, 972 MB), handoff_build_support (93 MB), handoff_binaural, handoff_source_radiation_for_build, handoff_surfaces_for_build, research_shared_fdn (213 MB), findings, ensemble, demos (28 MB).
- *.bak prompt/backlog backups under handoff_build_support_2/roadmap.
- software/renders (93 MB) and software/proof (13 MB) are generated outputs. Keep only the goldens the tests need.
- Dated notes in the root: MIC_ROUTING_PLAN_2026-10-25.md, OSC_PORT_AUDIT_2026-10-25.md. Move them to docs/notes/.
- Check that .venv (1.1 GB), .pytest_cache and __pycache__ are gitignored, not committed.
- Suggested shipped layout: software/, the fitters as tools/ (mic_fitter, air_fitter, surfaces_fitter), docs/, README, HANDOVER.

## 6. Clean-up plan (ordered Build runs, one goal each, low risk first)
1. **Repo clutter out.** Move everything in section 5 to an archive folder outside the repo and update .gitignore. No code. Risk: none, as long as the golden reference files stay.
2. **Delete the .orig/.bak files and stale dated notes.** Risk: none.
3. **Strip run-history comments** (dates, run numbers, golden notes) from all source. Comments only. Risk: none, but live_stereo.c edits trigger a WASM rebuild, so check WORKLET_VER 63 and confirm the build is byte-identical.
4. **Replace the cache-pin tests** with one generated hash or a single pin test. Risk: none to audio.
5. **Remove the always-off flags:** MOVEMENT_FORCED_OFF (and its branch), RR_SL_STAGE (hardcode stage 6), and the tests that only pin them. Risk: low. Goldens, empty MD5 and centre MD5 should not move.
6. (After Build's queued tidy-ups land) **Dead function sweep:** delete the unreferenced defs in section 3 after checking each one, and move demo/stub/tweak modules out of engine/. Risk: low. Run QUICK plus FULL once.
7. **Split app.js** into modules: state/posts, mic tab, room tab, render, bypass/buses. No behaviour change. Risk: UI only; cache pins move, audio doesn't.
8. **Table-drive params_from_body and the Play param posts:** one schema (key, type, default, range) shared by server, JS and C wire_defaults. Risk: medium, because a wrong default changes the sound. Empty MD5, centre MD5 and all five goldens must hold.
9. **One reference module per maths topic** (pattern, biquad, air, pan law, hadamard). Python Render and JS use it, and C gets a parity test against it. Do the pattern module first, together with the hypercardioid fix and the polar double-count fix, since those are a deliberate sound change for that preset. Risk: high for goldens. Hold every golden bit-exact except the ones with a stated reason.
10. **Break up the long functions** (_shape_taps, bus_sample, _render_core, mix_partition, params_from_body) into named stages. Risk: medium/high. Goldens must stay bit-exact. C changes rebuild the WASM and should be checked against WORKLET_VER 63. Play must stay under 2.40 ms.
11. **Test-suite triage:** run `--durations`, add slow/fast markers, merge overlapping tests. FULL runs only before a push.

## Addendum (2026-10-26): goal and server routes

**Goal (from Ben via Idle):** make this code tidy and scrutable so Ben can read it, cut it up, and build a tighter, faster, optimised version. Readability and one-source-of-truth beat cleverness. Long comments are fine; messy code is not.

**Server routes run (after the shared settings list):** the app uses one port (7860) but 22 HTTP routes, 4 with no caller (`/api/geometry`, `/api/mic_presets/{id}`, `/api/surfaces`, `/api/colour`). Delete the 4 unused routes. Merge the rest into about three groups: scene plus readouts, render plus preview WAV, and catalogues. Optionally give Play's updates one live connection. No sound change; goldens, MD5s and WORKLET_VER 63 must hold.
