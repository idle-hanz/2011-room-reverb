# T3b prebuild · MS sound (D18 + D19, locked 4 Oct 2026 16:43)

**D18 level.** `../t3_ms/ms_presets.js` now has `LEVELS = { legacy: M ×1.5 / S 0 dB, unity_trim: M = S = −3 dB (0.708) }` and `MS_LEVEL = "legacy"`. T3 ships legacy; T3b sets `MS_LEVEL = "unity_trim"` (one line). S:M = 1 → virtual pair ±63° (unit test `test_ms_presets.mjs`, 9/9 pass).

**D19 direct pattern.** `d19_render_pipeline.diff` (against the box build-51 copy `prebuild_app/software/render_pipeline.py`; rg the anchors first, lines may have moved):
1. ~1047 after `LIVE_DIRECT_FOLD`: `has_side_strip(weights)` = any strip with `w[x+"l"] * w[x+"r"] < 0` (route s).
2. ~1080 `render_listen_direct_ir`: if `spikes is None` and `has_side_strip(weights)` → `spikes = direct_capsule_spikes(t)` (Render, one source).
3. ~2212 `live_fdn_params`, before `if binaural_on`: same gate → `buses[ch]["direct_gain"] = sp[idx]` (Play; `pack_room.js` 36 and `_pb_num` 2358 already carry it, no wasm change).
Two-source scenes are unchanged (they already pass spikes). ORTF/AB/XY have no negative fold weight, so they keep (1, 1, 1).

**Proved on the box (temp copy, not the app copy):** with the diff, the 3 strict xfails (`test_t3_ms_presets_draft.py` direct-centred; `test_t3b_ms_sound_draft.py` Render + Play) flip to XPASS; `engine/selfcheck.py` = 1/45 fail both before and after (pre-existing `test_two_source_balance_mirror_and_split`); full-suite failing-test set identical before and after; default and ORTF renders bit-exact (MD5), MS render changes (`suite_compare.txt`).

**Tests:** `../tests_py/test_t3b_ms_sound_draft.py` (D18 weights pass today; D19 Render/Play strict xfails; ORTF has no `direct_gain`).
**Goldens:** MS references only (GOLDEN_META reason "D18/D19"). Main ORTF golden must stay bit-exact.
