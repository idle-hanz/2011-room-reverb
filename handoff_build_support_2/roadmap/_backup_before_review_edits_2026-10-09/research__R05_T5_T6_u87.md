# R05 · T5/T6 U87 Ai Cardioid vs SM57, and the A/B plan (D-UI30)

**Key finding (VERIFIED, mic_fitter presets, relative_db, on-axis = 0 dB by design):** the U87 picks up about 6 dB more from the rear and stays brighter off-axis. So a room will sound **wider, more ambient and with a stronger tail** after the switch, not just "a different mic colour".

| Mic | 90° 1 k / 8 k | 180° 1 k / 8 k |
|---|---|---|
| SM57 | −9.3 / −10.7 dB | −16.3 / −18.2 dB |
| U87 Ai Cardioid | −6.8 / −8.9 dB | −10.3 / −13.0 dB |
| CMC5-U Cardioid | −6.1 / −5.7 dB | −9.4 / −8.3 dB |

The SM57's on-axis presence peak is **not** modelled (on-axis is flat by design), so the A/B mostly hears the off-axis difference. Fit quality: SM57 holdout RMSE 2.85 dB, U87 4.15 dB. Data: Franco et al., Zenodo 10.5281/zenodo.4633508. **VERIFIED** (preset files)

**Open check (ASSUMED):** the measured H may double-count the first-order pattern gain that `compute_taps` already applies. T5 must confirm by rendering a single tap at 90° and 180° for each mic: is the level the measured H, or the measured H plus the pattern?

**A/B plan (box job, no Build usage):**
1. Do it after T4, on the post-T4 tree.
2. Scenes: the golden scene, plus a dry guitar through ORTF.
3. Mics: SM57 ×3, U87 Ai Cardioid ×3, and CMC5-U ×3 as a third reference.
4. Loudness-match to −23 LUFS integrated, render both Play-equivalent and Render, and give the files blind names (A/B/C).
5. Hand Idle one folder plus a one-line sheet. **T6 runs only after his OK.**

**Touch points (T6):**
- app.js 97
- app_server.py 636 / 1028–1030 / 1317–1319
- render_pipeline.py 1351–1353
- regenerate ~77 references, plus the GOLDEN_META reason

**Tests / goldens:** **YES** (every default render). `prebuild/tests_py/test_t6_u87_default_draft.py` is skip-until-merged.

**Decisions for Idle:** OK after listening (blocks T6). Optional: the HPF default (the U87 has a switchable ~140 Hz HPF; recommend off, as now).
