# R03 · T3 MS presets, decode maths, +3.5 dB Mid, back-to-back gain matching

**Key findings:**
1. **+3.5 dB Mid is a width choice, not a standard.** With a cardioid M, a unity decode (L = M+S, R = M−S) equals a virtual pair at ±63°, hypercardioid-like. Today's M × 1.5 gives ±53°, supercardioid-like. Common practice is a unity matrix, often with −3 dB on the outputs to keep the level. Schoeps "MS Technique" https://schoeps.de/en/knowledge/knowledge-base/recording-techniques/ms-technique.html (formulas **VERIFIED**). Sound On Sound MS articles (**ASSUMED**, not re-read today).
2. **Back-to-back cardioids:** cL − cR is exactly a unity fig-8 (tested at every 15°). A gain mismatch of δ leaks omni at (1−g)/(1+g): 1 dB → −24.8 dB, 0.5 dB → −30.8 dB. The preset must lock both strips' gains together. **VERIFIED** (maths)
3. **B3 root cause (VERIFIED):** `loadDeskPreset` never sets `state.ms_decode`, so `matchPresetId()` 1840 never matches and the UI posts `mic_setup: "custom"`. The body is captured in `prebuild/tests_py/fixtures/ui_body_ms_classic.json`. It is harmless to the sound: the active desk turns the legacy ms_decode branch off (app_server.py 487–492).
4. **New sound finding (VERIFIED offline render, Play ASSUMED same):** with one source the direct spike ignores the mic pattern (render_pipeline.py 1050–1063). In MS the S strip therefore adds the same +1/−1 for every source angle: **direct-only MS sits 11.2 dB left at every source position** (`proto/ms_direct_image.json`). See R18.

**U87 dual-diaphragm note:** the U87 Ai is a dual-diaphragm (back-to-back) capsule, so its fig-8 is itself two cardioids. **ASSUMED** (Neumann product page not re-read).

**Recommended design:** presets a/b/c from `prebuild/t3_ms/ms_presets.js`. Default b = U87 Ai Bidirect S + U87 Ai Cardioid M (D-UI29). Keep `ms_classic` as an alias. Keep M × 1.5 until Idle answers Q2. Demo with both settings: `prebuild/shots/t3_ms_m35.png`, `t3_ms_m0.png`.

**Touch points:** `prebuild/t3_ms/README.md`:
- `MIC_PRESETS` 5–60
- `loadDeskPreset` 403–415
- select 546–557
- `msSetup` 1538
- `matchPresetId` 1840
- B4 auto fig-8 in `paintMicModel` 1985–2000

**Tests / goldens:** main golden NO (default is ORTF). MS references only. 8 node tests, 3 pytest drafts plus 1 strict xfail (the R18 direct image).

**Decisions for Idle:** **Q2** M level: keep +3.5 dB (narrower) or unity (recommend unity + output trim −3 dB, as is common). **Q-MS-DIRECT**: see R18.
