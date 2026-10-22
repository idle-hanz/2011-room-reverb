# SL4 · Directional per-line decay + one Render calibration pass. Effort: medium. Needs SL2 (SL3 for Play). Decisions: **D-SL2 directional**, **D-SL4 one calibration pass, Render only**.
**PREBUILT, so integrate, test and listen.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md`: the "SL4" block and **finding 5**.
- **Already in the prebuild:**
  - `surf_loop.line_rates` (directional: faces hit per line, s′ = max(mean scattering, 0.5), κ normalised);
  - `calibration_factors` (T20/T_target, 0.6–1.6);
  - the `render(..., surf_directional=True, surf_cal=[7])` kwargs.
- **Wire:** "Calibrate" runs Render → `t20_per_octave` → factors → Render. Store `surf_cal` in the scene; Play reuses it.
- **Tests:** `test_sl4_directional.py -m slow`.
  - Box: **21/21 octave bands within ±10 %** after calibration (default room at 1.8 s, studio, brick).
  - Calibration factors 0.73–1.09. L−R tail balance change 0.17 dB. Guard hits 0–7 lines per bus.
- **Known finding (xfail in the test, decide here):** in the untreated plaster room the directional lines show a mild double slope. EDT/T30 is 0.62 / 0.46 / 0.57 at 250 Hz / 4 k / 8 k against Flat 1.04 / 0.85 / 0.89. Listen to A/B 3–4. If it is audible, ship room average (D-SL2 fallback) and report.
- **Cut line:** directional rates + tests. Calibration only if green.
- **Golden impact:** **NO** (Surfaces mode only). Re-run the SL2 null test.
- **Done when:**
  - the 12-render set reaches ±10 % in ≥ 76/84 octave bands;
  - L−R tail balance changes by ≤ 0.5 dB;
  - the double-slope decision is written down.
- **Stop if:** s′ < 0.5 is needed to pass anything, or calibration makes any band worse by > 10 %. Then ship room average and report.
