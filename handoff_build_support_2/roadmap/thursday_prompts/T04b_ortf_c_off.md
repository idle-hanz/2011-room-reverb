# T4b · ORTF without C by default + "ORTF + C" preset (D20). Effort: medium. Needs T4. Decisions: D20 locked 4 Oct 16:43. **GOLDEN CHANGE.**
Read `handoff_build_support_2\roadmap\prebuild\t4b_ortf_c\README.md`. Touch points (rg first): app.js MIC_PRESETS `ortf` 26–30 (add `ortf_c` copy), state `third_mic` 87, `loadDeskPreset` 375 (`ortf` → "off", `ortf_c` → "centre"), `matchPresetId` ~1840; index.html 551 (add `<option value="ortf_c">ORTF + C</option>`); app_server.py 493–494 (empty body / ORTF without `third_mic` or `mic_gain_c` → C 0). Copy `tests_py\test_t4b_ortf_c_off_draft.py`.
- **Cut line:** whole session or nothing: code + regenerated references + GOLDEN_META reason "D20 ORTF C off" in one commit.
- **Golden impact:** **YES, main golden** (ORTF default loses C). It is the only change in this session.
- **Done when:** the draft passes (strict xfail flipped, marker removed); "ORTF + C" nulls against today's ORTF (≤ −120 dB); old saved scenes with `third_mic: "centre"` recall unchanged.
- **Stop if:** any non-ORTF setup's references move, or the reference regeneration cannot finish this session (revert, leave nothing half-done).
