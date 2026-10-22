# R12 · Scatter (t06) and smear: CPU options

**Today (VERIFIED, THURSDAY_LIST L1/R4 and S5_CPU_DECISION.md):**
- The early field is sparse (Hall echo density 0.02–0.09).
- Rough-wall scatter (S5 items 2–3) was never started.
- Play runs at about 2.23–2.30 ms against a **2.40 ms hard ceiling** (D-S5c-2), so headroom is about 0.1 ms.

**Options:**

| Option | What | Play CPU | Sound |
|---|---|---|---|
| A. Render-only scatter | t06 in the offline renderer only; Play stays as is | 0 | Play/Render differ in early density (breaks parity gates) |
| B. Shared velvet-noise smear | one sparse FIR per lane (≈ 20–40 taps, 20 ms) after the early taps | small, ASSUMED ≈ 0.03–0.06 ms | denser early field, same in Play and Render |
| C. Per-tap allpass | 1–2 short allpasses per tap × 32 taps | ASSUMED ≈ 0.15–0.3 ms, over budget | best match to real scatter |
| D. Free CPU first (R14 tank gating) | helps only while the FDN fader is at 0 | — | no help in normal use |

**Sources (ASSUMED, not re-read today):** Järveläinen & Karjalainen 2007 (velvet noise perception); Välimäki et al. 2017 "Late reverberation synthesis using filtered velvet noise" (Applied Sciences 7(5):483); Vorländer, *Auralization* (2008), on scattering coefficients (ISO 17497-1).

**Recommendation:** **B**. It is the only option that keeps Play = Render and fits the 0.1 ms headroom. First measure its cost on the PC with the paired A/B method from D-S5c-2. Keep the scattering amount per face as a Surfaces material property (scattering coefficient), so it lands in the redesigned Surfaces tab (R17).

**Touch points:** the early-tap stage in live_stereo.c (output build at 2490/2500/2601/2712 uses `fdn_wet`; early taps upstream) and render_pipeline.py early stage. This needs a Build session of its own (L, not Thursday).

**Tests / goldens:** **YES** when on. Default off keeps goldens.

**Decision for Idle:** **D-SCATTER**: option B (recommend), A or C; and default on or off (recommend off until heard).
