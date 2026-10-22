# T3 prebuild: MS presets a/b/c (D-UI29) and decode maths

**Files:** `ms_presets.js` (presets + maths, no DOM), `test_ms_presets.mjs` (8 pass), demo `../app_copy_files/mockups/t3_ms_demo.html`, `prove_t3.py`, Python draft `../tests_py/test_t3_ms_presets_draft.py`.

## Presets
- `ms_a`: fig-8 S (U87 Ai Bidirect) + omni M (U87 Ai Omni).
- `ms_b` (**default**): fig-8 S (U87 Ai Bidirect) + cardioid M (U87 Ai Cardioid). Same geometry and patterns as today's `ms_classic` (app.js 46–50, loadDeskPreset 403–415). Only the mic models change.
- `ms_c`: two U87 Ai Cardioids back to back as S. L faces +90 on route s, R faces −90 on route s with Ø, so S = L − R. The Mid is a cardioid.
- (d) is dropped. `ms_classic` stays as an alias of `ms_b` so old scenes recall.
- Mid level: `LEVELS.legacy` (M ×1.5 = +3.5 dB, today's `gain_exact_c`) is what T3 ships (`MS_LEVEL = "legacy"`). **D18 locked** (16:43): `unity_trim` (M = S = −3 dB, ±63°) lands in T3b with the MS references.

## Maths (Schoeps MS page, VERIFIED formulas)
- M = (1−a) + a·cosβ, S = cos(β−90°), L/R = M ± kS.
- The virtual pair sits at ±atan(k/a). Its gradient share is √(k²+a²)/((1−a)+√(k²+a²)).
- Cardioid M at 1:1 = ±63°, hypercardioid-like (0.69). Today's +3.5 dB M = ±53°, supercardioid (0.63). So +3.5 dB only narrows the image a little; it is not a standard.
- Omni M + fig-8 at 1:1 = two cardioids at ±90°.
- Back-to-back gain mismatch: 1 dB leaks omni at −24.8 dB, 0.5 dB at −30.8 dB.

## Findings for T3 (box, 4 Oct)
1. **B3 confirmed at body level:** choosing MS classic in the UI posts `mic_setup: "custom"` and `ms_decode: false`. It also posts `colour_mode` ASSUMED_TOYS instead of the ORTF body's MEASURED_SHELF (captured bodies in `tests_py/fixtures/`). Cause: `matchPresetId()` (1823–1844) needs `state.ms_decode` true (1840), but loadDeskPreset never sets it. Fix: set `state.ms_decode = true` in the ms block (403–415), or drop that line in matchPresetId. `ms_presets.js` sets `ms_decode: true` in `desk`.
2. **Sound finding (Q-MS-DIRECT, now LOCKED as D19, fixed in T3b — see `../t3b_ms_sound/`):** with one source the direct spike ignores the mic pattern (render_pipeline.py `direct_capsule_spikes` **1050–1063**, "One source stays (1, 1, 1)", ASSUMED by design). In MS the Side strip adds +1 to L and −1 to R for every source angle. Direct-only MS classic measured **11.2 dB louder in L at every source position** (`research/proto/ms_direct_image.json`). ORTF is unaffected. Recommendation: in MS (any strip on route s), use the pattern spikes (`spikes=` path already used for two sources) for the direct sound. That changes the sound of MS scenes only (MS reference renders, no main golden). The xfail test `test_ms_direct_sound_is_centred_for_a_front_source` pins it. The same rule means coincident pairs (XY, Blumlein) have no level image in the direct sound at all; see `research/R18_direct_sound_pattern.md`.

## Integration (current app copy)
1. Copy `ms_presets.js` to `static/js/`, script tag before app.js (index.html ~900).
2. `MIC_PRESETS` (app.js 5–60): add `ms_a/ms_b/ms_c` from `RRMS.build(id).mic`. Keep `ms_classic` = `ms_b`.
3. `loadDeskPreset()` (368): replace the `ms_classic` block (403–415) with `Object.assign(state, RRMS.build(id).desk)` for ids starting `ms_` (or `ms_classic`). Set `mic_preset_l/c/r` from `.mics` (the select fill is at 2154–2157).
4. index.html mic_setup select (546–557): replace the `ms_classic` option (555) with three options.
5. `msSetup()` (1538): `return /^ms_/.test(state.mic_setup) || !!state.ms_decode;`
6. `matchPresetId()` 1840: `(id.indexOf("ms_") === 0)` instead of `=== "ms_classic"`.
7. B4 (cardioid S in Measured): the S strip must use a fig-8 preset when `family_l === "bi"`. Pick `NeumannU87AiBidirect` automatically (`paintMicModel` 1985–2000).

## Stop conditions
Stop if the main golden changes (it must not: the default is ORTF). MS reference renders change only in T3b (D18/D19, locked).
