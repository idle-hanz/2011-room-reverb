# SL3 · Surfaces mode in Play (same coefficients). Effort: high. Needs SL2. Decisions: D-SL3 (reuse the per-axis slot), D-SL7.
**C core PREBUILT and benched; the glue is yours.** Read `handoff_build_support_2\roadmap\prebuild\sl\README.md`: the "SL3" block.
- **Integrate:**
  - Apply `prebuild\sl\patches\engine_live_stereo.c.diff`. It adds per-line SoA sections (`slBuf` = `[bus][line][section][b0 b1 b2 a1 a2]`, 3×32×3×5 Float64), `surf_batch()` after the 4 read loops, and `live_surf_ptr` / `live_load_surf(st, on)`, which refuses non-finite or unstable sets.
  - Rebuild the wasm as usual.
- **Build (not prebuilt):**
  - `live_fdn_params` → `surf_sos`, designed by `surf_loop.design_bus` with the **live** bus delays, lg and kept peaks (Render = Play);
  - pass it through in `live_fdn.js`;
  - in `fdn_worklet.js`, fill `live_surf_ptr` and call `live_load_surf`;
  - bump WORKLET_VER (51 → next).
- **Box numbers:** wasm +0.031 ms per 128-sample block (Flat 0.677 → 0.708), native +0.058. Flat-off and identity sections are bit-exact against pristine (`prebuild\sl\play_c\bench_*.json`; re-run with `bench_play_wasm.mjs`).
- **Cut line:** coefficients sent + applied + a Play-vs-Render tail test. UI chip ("Surfaces in Play") only if green.
- **Golden impact:** **NO.** Flat Play stays bit-exact against today's Play captures. Render goldens are untouched.
- **Done when:**
  - In Surfaces mode, the Play T20 per octave matches Render within 5 %.
  - Flat Play nulls against today's Play.
  - CPU on t19 is ≤ +0.10 ms per block over Flat, with no xruns.
- **Stop if:**
  - CPU goes over +0.12 ms. Ship Render-only and report; don't try GEQ (D-SL7).
  - Float32 storage pushes any loop gain ≥ 0 dB. The prebuild stores Float64.
