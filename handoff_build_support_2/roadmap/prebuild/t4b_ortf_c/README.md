# T4b prebuild · ORTF C off + "ORTF + C" preset (D20, locked 4 Oct 2026 16:43). GOLDEN CHANGE

Today choosing ORTF posts `third_mic "centre"`, `mic_gain_c 1` (`../tests_py/fixtures/ui_body_ortf.json`), and an empty API body folds C at 0 dB (L + 0.5 C, R + 0.5 C, the 477 fold). R15: C raises early L/R correlation 0.00 → 0.14.

Integration points (box build-51 copy; rg first):
- `static/js/app.js` 26–30 MIC_PRESETS `ortf`: add `ortf_c` (same geometry, label "ORTF + C").
- app.js 87 state `third_mic: "centre"` → `"off"` (the boot preset is ORTF, 3144).
- app.js 375 `loadDeskPreset`: `state.third_mic = (id === "ortf") ? "off" : "centre";` and `ortf_c` → `"centre"`.
- app.js ~1840 `matchPresetId`: recognise `ortf_c` (C on) vs `ortf` (C off).
- `static/index.html` 551: add `<option value="ortf_c">ORTF + C</option>` after ORTF.
- `app_server.py` 493–494: with no `third_mic` and no `mic_gain_c` in the body and `mic_setup` empty or `"ortf"`, `gain_c = 0.0`. Explicit fields always win, so saved scenes recall unchanged.
- Leave `desk_matrix.py` 179 and app_server 1010/1261 defaults alone (they read the already-parsed params).

**Tests:** `../tests_py/test_t4b_ortf_c_off_draft.py`: "ORTF + C" = 477 fold (passes today), ORTF without C drops the centre (passes), today's UI body posts C on (invert after T4b), empty-body default has no centre (strict xfail → flips).
**Goldens:** **YES, main golden.** Regenerate every ORTF reference with GOLDEN_META reason "D20 ORTF C off", in the same commit. Other setups must not move.
**Check after T4b:** do XY / NOS / AB also include C by default (same `third_mic` default)? Report; change only ORTF (D20).
