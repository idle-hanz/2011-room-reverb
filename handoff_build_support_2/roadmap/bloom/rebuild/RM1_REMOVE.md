# RM1 remove the preamp and compressor

HEAD at start `032f57532c69f512294bc5f8c8555354ae37a798`, equal to `origin/main`. The Mix routing panel, the Audition strip, and the Array, Room, and Master inserts are gone from the page, the posts, the settings table, and Render. Sections 10–13 stay absent. No unity gain was added.

## Pins

Empty MD5 `067adbca1930efcd3f7c83bdd1d4c359`. Centre MD5 `35db578a18557d5729c0450e26f24a9d`. quiet.f32 MD5 `e38862e337b2b5ebf394c9a09f93212b`. GOLDEN_META SHA1 `0bf64ef21a262723573e9d6c6d10d0dbf2397e7c`.

Five golden SHA1s: `play_std_lock18_byp.f32` `7906405d783f784379388803b7eb42c5d25c6c7f`, `play_std_lock18_col.f32` `c20e6894b6f05a69960b360869232548fb42c148`, `play_std_unlocked_byp.f32` `2639f90fffefc08316143511390097bdada89fea`, `play_std_unlocked_col.f32` `9146eaddc1f6a3333c54ad2f489b86f6ffadadc8`, `render_std_unlocked_byp.f32` `2a806e334e06cc475868d4c3da3fc78431c9a0aa`.

Golden rerender max-abs 0. WORKLET_VER 64.

`?v=` bumped with the edits: `app.css` 46, `live_fdn.js` 67, `rr_state.js` 9, `rr_mix.js` 10, `rr_transport.js` 7, `rr_settings.js` 4. `routing_scene.js?v=3` is gone. The rest of PIN_TABLE is unchanged: `sl_room_result.css` 3, `rr_controls.css` 1, `room_shape.js` 9, `maths_look.js` 2, `maths_pattern.js` 2, `maths_distance.js` 1, `maths_db.js` 1, `maths_bands.js` 1, `maths_image.js` 1, `room_math.js` 23, `spectrum_colors.js` 1, `freq_palette.js` 2, `room_view_pose.js` 1, `room_draw.js` 8, `room_3d.js` 27, `room_editor.js` 32, `image_views.js` 23, `colour_surfaces.js` 10, `polar_field.js` 18, `polar_views.js` 10, `mic_desk.js` 29, `source_desk.js` 7, `pack_room.js` 55, `lr_buttons.js` 1, `ms_presets.js` 3, `pair_mode.js` 2, `drag_model.js` 2, `room_window_math.js` 1, `settings_boot.js` 1, `rr_mic.js` 1, `rr_room.js` 5, `rr_source.js` 1, `rr_space.js` 3, `rr_polar.js` 2, `app.js` 110, `sl_room_result.js` 12, `rr_controls.js` 1, `rr_controls_boot.js` 1.

## Kept

Static IR, movement’s driven path, tail SOS after colour, `fdn_wet`, makeup, the direct fold, section 14 Off-axis tail, and `place_l/c/r`. Mic bus `route_l/c/r` and `mic_route_l/c/r`. Surfaces `#surfAudition`. Fit JSON stays. Round-3 scripts load `handoff_build_support_2/roadmap/bloom/uad/round3/data/` (`fit_nuke.json`, `fit_room_crush.json`, `fit_swell.json`, `colour_choice.json`, `eq_fit.json`, and the preamp choice files) and `handoff_build_support_2/roadmap/bloom/compressor_presets.json` without the product module.

`live_fdn.js` still copies `bloom`, `predelay_n`, `pre_colour`, and `side` into the worklet message when those fields are present (lines 491–494). `pack_room.js` still packs sections 10–13 when the message carries them (lines 158–176). Python and the page no longer emit the fields.

## Tests

`test_quick_pins.py` 6 passed. `test_five_goldens_max_abs_zero` 1 passed, max-abs 0. The default pytest addopts skip that slow test, so it was run by name. `engine/selfcheck.py` 45/45. Node `tests/*.mjs` 120/120. `test_settings_table.py`, `test_s_audit_ui.py`, `test_routing.py`, `test_bloom_off.py`, `test_rm1_legacy.py`: 10 passed, 12 slow deselected. `test_a12_visible_controls_post_or_are_ui_only` 1 passed. No skip, xfail, or `_UI_ONLY_IDS` addition.

Deleted because they only covered the removed preamp, compressor, panel, or audition strip: `test_comp_natural_makeup.py`, `test_comp_glue_release.py`, `test_comp_swell.py`, `test_comp_nuke.py`, `test_comp_room_crush.py`, `test_neve_shaper_level.py`, `test_u610a_shaper_level.py`, `test_bloom_panel.py`, `test_bloom_panel.mjs`, `test_audition_strip.py`, `test_audition_strip.mjs`, `test_preamp_ui.py`, `test_preamp_ui.mjs`. Also deleted `software/engine/bloom_dsp.py`, `software/tools/audition_strip.py`, `software/static/js/routing_scene.js`, and `software/static/js/bloom_scene.js`.

`test_routing.py` keeps the capsule-fold check and the empty MD5 with armed old keys. The slow wasm test that expected Array Glue to move a sample is gone. `test_bloom_off.py` keeps the empty MD5 and the absent `bloom` field. `test_routing.mjs` keeps the section 10 and 13 pack checks.

These handoff scripts still import `bloom_dsp` and were not edited: `roadmap/overnight/_scratch/bloom_gates.py`, `bloom_alias_level.py`, `bloom_alias_diag.py`, `roadmap/bloom/make_listens.py`, `roadmap/bloom/uad/round2/scripts/mk_listen_b2.py`. They are not the live product.

## Dead C and wasm

Not edited. Deleting them needs a C edit, a wasm rebuild, and WORKLET_VER 65.

`software/engine/live_stereo.c`: `bloom_arm` 1806 and 1909. `side_apply` 3533, 3598, 3745, 3763, 3877, 3878. `bloom_apply` 3534, 3599, 3746, 3764, 3881, 3882.

`software/engine/bloom_live.inc`: `bloom_apply` 523, `bloom_arm` 614, `side_apply` 722, `live_audition` 896–897.

`software/static/js/fdn_worklet.js`: `live_audition` 187–188 and 229.
