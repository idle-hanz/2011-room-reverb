# SL1 · Surfaces "Room result": target model + readout (no sound change). Effort: medium. Needs T11 (run order) and T10. Decisions: **D-SL1–9 locked 4 Oct 20:37** (`../DECISIONS_LOCKED_2026-10-04.md`).
**PREBUILT, so integrate; don't redesign.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md` first: its "SL1" integration block, findings 2 and 3, and the test commands. Background: `roadmap\sound_tricks\SURFACES_IN_LOOP.md` §2, §3, §8.
- **Integrate (rg every anchor first; line numbers are for build 51):**
  - Copy `prebuild\sl\engine\surf_target.py` + `surf_panels.py` to `software\engine\`.
  - Apply the `params_from_body` hunks of `prebuild\sl\patches\app_server.py.diff` and **only** the `/api/room_result` route. `/api/auto_treat` and `/api/make_panel` come in SL5/SL6.
  - UI: copy `prebuild\sl\ui\sl_room_result.js` + `.css`. Add 2 tags plus `<script>window.RR_SL_STAGE = 1;</script>` before them (the Surfaces chip is greyed "coming"; Treatment and Auto-treat are hidden). Add the one `syncUINow()` hook line. All of this is in the README.
  - If the D-UI32 redesign has not landed, the panel goes into today's Surfaces tab as-is (it inserts after `.room-net-wrap`). Don't start the redesign here.
- **Tests:** copy `prebuild\sl\tests\*` to `software\tests\`. Run `pytest -q test_sl1_room_target.py` (box: all pass) plus the full suite.
- **Cut line:** model + API + tests first. The panel only if green.
- **Golden impact:** **NONE.** Read-only model; the main golden and all references stay bit-exact.
- **Done when:**
  - `test_sl1_room_target.py` passes on the PC (≤ 1 % vs `proto2\a2_results.json` on the 3 rooms).
  - The panel redraws when a material changes, and the screen matches `prebuild\sl\shots\sl1_stage1_1280.png`.
- **Stop if:** any change reaches the audio path, or the panel moves a control's only copy off-screen at 1280 px.
