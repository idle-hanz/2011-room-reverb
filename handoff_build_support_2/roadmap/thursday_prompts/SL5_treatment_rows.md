# SL5 · Treatment rows on Surfaces: porous + air gap, membrane, Helmholtz, room shell. Effort: high. Needs SL4. Decisions: **D-SL6 room shell on by default in Surfaces mode**, D-SL8 (real materials; the default *switch* is SL7b).
**PREBUILT, so integrate and test.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md`: the "SL5" block and **findings 1 and 3**.
- **Already in the prebuild:**
  - `surf_panels.py`: Miki porous with air gap (library presets to ≤ 0.012 α), membrane / Helmholtz f0 + resonant α, `cards_with_treatment`, `validate_rows` (≤ 90 %/face);
  - the room shell row;
  - `/api/make_panel`;
  - the Treatment list UI (`#slTreatment`: on/off, coverage % clamped to 90 % including off rows, + Porous, + Tuned panel, + Room shell).
- **Wire:**
  - `RR_SL_STAGE = 5`.
  - **D-SL6:** add the room-shell rows when a scene enters Surfaces mode (call the `+ Room shell` code from the mode chip; not yet wired).
  - Add the "plaster + parquet" set to the library as a set (`proto2\rooms.py` real_default). **Don't** change the default cards (SL7b).
- **Tests:** `test_sl5_panels.py` and `test_sl5_sl6_render.py -m slow`. Box: shell 125/250 Hz = 1.84 / 2.30 s, target 1.9 / 2.35 ±10 %.
- **Cut line:** model + rows in state/server + tests. UI list only if green.
- **Golden impact:** **NO.** Treatment exists only in Surfaces mode. Flat ignores it (box: Flat with rows is bit-exact). Re-run the SL2 null test.
- **Done when:**
  - toggling a panel row moves the curve at f0 (box: T(125) 2.09 ↔ 2.62 s, 4 kHz < 2 %; `prebuild\sl\shots\sl5_row_off_1600.png`);
  - the shell numbers pass;
  - old scenes load unchanged.
- **Decision for Idle (finding 1):** Helmholtz with wool resonates 5–10 % low at Q ≈ 1–2, not the ASSUMED Q 3. The prebuild keeps the formula. Don't change it without Idle.
- **Stop if:** a treatment row changes a Flat-mode render, or the per-face UI breaks the 434/472 slider builders in `colour_surfaces.js`.
