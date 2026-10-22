# SL6 · Auto-treat (suggests rows) + "Make it a panel" on resonance rows. Effort: medium. Needs SL5. Decisions: **D-SL5 suggest, never auto-apply**, **D-SL9 dial target + "EBU control room" preset with pass/fail**.
**PREBUILT, so integrate and test.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md`: the "SL6" block and **findings 4 and 7**.
- **Already in the prebuild:**
  - `surf_autotreat.auto_treat`: axis-balanced broadband on F/D/A/C (best of 4 porous presets), up to 4 tuned panels at the worst Mäkivirta excess, EBU Tm + per-band pass/fail. If the target is longer than the room, it fits the shape only (`shape_only`, `t_fit`);
  - `make_it_a_panel`;
  - `/api/auto_treat` (seconds or `"ebu"`);
  - the UI: Auto-treat field defaulting to the dial, EBU button, suggested rows with Accept / Accept all / Discard, and a lock note.
- **Wire:**
  - Remove `RR_SL_STAGE` (default 6).
  - Add "Make it a panel" on EQ_PLAN resonance rows below 300 Hz (`/api/make_panel {f0}`), only if N5 resonance control has landed. Rows above 500 Hz stay cuts.
- **Tests:** `test_sl6_auto_treat.py` (box: reproduces `proto2\target_treated.json` exactly: 4″+4″ at 21 % on F/D/A/C, panels 62.5 / 125 / 157.5 / 198.4 Hz) and `test_sl5_sl6_render.py -m slow`.
- **Cut line:** algorithm + suggestion API + tests. Button and "Make it a panel" only if green.
- **Golden impact:** **NO.** Suggestions don't change sound until they are accepted, and only in Surfaces mode.
- **Done when:**
  - The box plan is reproduced.
  - Rendered T20 reaches ≥ 16/23 ⅓-octaves within ±10 %. Box: 16/23 with D-SL3 as "keep cuts below 30 Hz"; 15/23 if all cuts are dropped. Report which reading is used.
  - The UI matches `prebuild\sl\shots\sl6_suggestions_1600.png` / `sl6_after_accept_1600.png`.
- **Stop if:** the algorithm ever writes rows without Accept, or exceeds 90 % on a face.
