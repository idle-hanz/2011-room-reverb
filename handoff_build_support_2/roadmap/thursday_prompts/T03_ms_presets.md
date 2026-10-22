# T3 · MS presets a/b/c (D-UI29). Effort: medium. Decisions: D-UI29 locked. D18 (unity −3 dB) and D19 (MS direct) are **locked but land in T3b**, not here: ship with `RRMS.MS_LEVEL = "legacy"` so no reference moves.
Read `handoff_build_support_2\roadmap\prebuild\t3_ms\README.md`; integrate `ms_presets.js` (MIC_PRESETS 5–60, loadDeskPreset 403–415, select 546–557, msSetup 1538, matchPresetId 1840, B4 auto fig-8 in paintMicModel 1985–2000). Copy `test_ms_presets.mjs` and `tests_py\test_t3_ms_presets_draft.py` (+ fixtures).
- **Cut line:** preset b + B3 (no "Custom" flip: set `ms_decode`) + B4. Presets a and c may move to T7.
- **Golden impact:** main golden NO. New MS null tests only. After B3 is fixed, invert `test_ui_body_fixture_still_flips_to_custom`. The strict xfails stay xfail (T3b flips them).
- **Stop if:** the default (ORTF) golden moves, or preset b differs from today's ms_classic in anything but the mic models.
