# SL2 · Surfaces mode in the Render loop (room average, 3 biquads/line). Effort: high. Needs SL1. Decisions: D-SL1 (opt-in), D-SL3 (per-axis cuts replaced in Surfaces mode), D-SL7 (S1P2 everywhere).
**PREBUILT, so integrate and test.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md` first: the "SL2" block and findings 4, 6, 8.
- **Integrate (rg every anchor first):**
  - Copy `prebuild\sl\engine\surf_loop.py` (S1P2 `design_line`, guard at 3× on a DC–Nyquist grid, stab report, `KEEP_CUT_BELOW_HZ = 30` = D-SL3).
  - Apply `prebuild\sl\patches\engine_fdn.py.diff` (`surf=` hook, `_init_surf`, the section loop after `reads *= lg`, and the C-core condition) and `render_pipeline.py.diff` (`decay_mode` / `surf_*` kwargs, `_surf_bus`, the `render()` wrapper, `info["surf"]` with `stab`).
  - Switch the UI to `RR_SL_STAGE = 2` (the Surfaces chip is live; Render only, Play shows "Render only" until SL3).
- **The C core:** the prebuild runs Surfaces on the Python path (Flat keeps `fdn_core.so`). Porting the section loop into `fdn_core.c` is optional and below the cut line. It must match Python to ≤ −100 dB, or revert it.
- **Tests:** `test_sl2_loop.py` (fast, then `-m slow`; box: 8 fast + 4 slow pass) and `hash_scenes.py`. **Compare the default render with the main golden hash in HANDOVER**: box result 9/9 scenes bit-exact (`prebuild\sl\proof\flat_bitexact.json`).
- **Cut line:** engine + tests first. UI wiring only if green.
- **Golden impact:** **NO.** Flat (2011) stays bit-exact. Surfaces references are new files only.
- **Done when:**
  - Every line's max loop gain is < 0 dB from DC to Nyquist, and every IR is finite.
  - The room average before calibration is within the prototype's numbers. On the box: −12 / −33 % at 125 / 250 Hz (prototype −10 / −32 %), ±15 % from 500 Hz up. SL4's calibration brings 125/250 in.
  - CR2 (`research\room_validation\scene.py` body 1,1,1.8) is rendered and its T20 is reported.
- **Stop if:**
  - the default golden moves by one bit;
  - any IR saturates or goes non-finite.
