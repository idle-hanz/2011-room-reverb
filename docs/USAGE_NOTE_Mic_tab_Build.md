# Usage note — Mic tab Build vs quota (2026-09-23, v2.6)

Still **one phase per session**. A short session should not start Phase 1.

| Phase | Meaning |
|-------|---------|
| **1** | One pass: 3D aim·ray angle and fitter colour together. Do not render twice. Direct spikes **before** the fold, amplitude 1. FDN lines **before** the sum, not on the inject. Early toys gated in `render_early_ir`. Server defaults SM57. Air lowpass untouched. No wall switch. No Structure mic pole. No Mic UI. |
| **2** | Mic tab UI + polar hero. Bypass is the mode enum, not a second checkbox. |
| **3** | Done (2026-09-24). Play uses the same minimum-phase FIR at the AudioContext rate, on the direct read, the early read, and FDN y. `ASSUMED_TOYS` keeps the old shelf. |
| **4** | Designer knobs + pattern chips |
| **5** | Wall-tone switch only (`early_only` / `per_trip` / `on_exit`). Default stays today’s early-only cards. |
| **6** | After Phase 3 has been heard. Remove the air lowpass. Replace the assumed shelf with the ISO studio preset. Both Render and Play. Brighter tail is expected. `1/r²` stays. |

Canonical brief: `docs/GROK_BUILD_BRIEF_Mic_tab_measured_colour.md` **v2.6** (mirror under `mic_fitter/` must match). Capsule angle is aim · incoming ray, not the floor-plan angle.