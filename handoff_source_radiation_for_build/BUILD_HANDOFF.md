# BUILD HANDOFF: Source radiation

## Read order
1. `briefs/GROK_BUILD_BRIEF_Source_radiation.md` (engine; the one to build from)
2. `briefs/GROK_BUILD_BRIEF_Source_UI.md` + `mockups/mockup_source_desk.png`, `mockups/mockup_floor_facing.png`
3. `source_fitter/FIT_REPORT.md` (which presets to ship, and their confidence)
4. `prototype/PROTOTYPE_REPORT.md` + `prototype/radiation.py` (reference maths to port; null test)
5. `findings/source_radiation_c_offload.md` (CPU, C core, smoothing)
6. `findings/source_radiation_research.md`, `findings/source_size_and_dimension.md` (background, citations)

## Decisions made (ASSUMED, please confirm by listening)
- Model: `radiation_shelf_plus_soft_one_pole`, the same DSP family as the mic model. Per image it is 1 gain + 1 RBJ shelf + 1–2 one-poles, with an exact bypass on axis and for omni.
- The source stage is the **first** in each image's serial cascade. The direct path is per capsule. The FDN inject gets **one diffuse (power-averaged) filter per source**, so the tail does not move with yaw by default.
- Size = beaming onset (f0, lp_hz scaled). Size jitter and multi-point come later and stay separate from the surfaces diffusion.
- Play phase 1: coefficients are computed in Python (the same function as Render) and shipped per line in the blob (like the existing per-line air shelf). The C side only filters and ramps.
- Level reference defaults to on-axis once a preset is chosen, with an optional power-matched mode. Omni is the default preset.

## Shipping presets (recommended first set)
`omni`, `talking_head`, `singer_soprano`, `acoustic_guitar`, `trumpet`, `violin`, `cello`, `cab_1x12_closed` (assumed), `cab_4x12_closed` (assumed), `piano_grand_lid_open` (assumed placeholder).
- `combo_*` are research-only (fit RMSE ~5 dB).
- The `tu_*` library is optional (NC licence).

## Open items / blockers
- **Aligned with the scattering stream** (live_play_fix_audit.md, c_wasm_performance_roadmap.md, the scattering brief):
  - It goes into the same `live_stereo.c` core, with one shared blob version bump.
  - The source stage sits on the early-lane write side; scattering sits on the read side.
  - Denormal guard first.
  - Combined two-source budget: ~80 % → trimmed to 76–78 % (see offload §7.3).
- User PC went offline mid-task. Some live files (surface_colour.py, mic_colour/*, fdn_stub.py, absorb_masks.py) were not copied, so `render_pipeline` was read but not executed on the box. The prototype uses `early_field` directly.
- No open anechoic data for a 4x12, a closed-back 1x12 or a piano, so those presets are ASSUMED. DirPat cab data was rejected (licence, not anechoic).
- Guitar-combo fits are low confidence. The v2 model needs a frequency-limited dipole term.
- TU Berlin data is CC BY-NC-SA 4.0, so derived presets are non-commercial unless cleared.
- WASM benchmarked with zig (wasm32-wasi, -msimd128) in Node on the box. The user's PC was not measured.
