# R15 · N18: ORTF has the centre mic at 0 dB (the 2011 "477 fold")

**Today (VERIFIED):**
- Choosing ORTF posts `mic_gain_c = 1`, `third_mic = "centre"`, `mute_c = false` (captured UI body `prebuild/tests_py/fixtures/ui_body_ortf.json`).
- The idle desk uses the 477 fold: L + 0.5·C, R + 0.5·C (`fold_for` weights ll 1, cl 0.5, cr 0.5, rr 1).
- So "ORTF" is really ORTF plus a front cardioid at −6 dB in each side. Its mono contribution equals one of the pair mics.

**Measured on the box (`proto/n18_ortf_c_probe.py` / `.txt`, direct + early, 0–80 ms, colour bypass):**
- Switching C off changes the early field by a null of only −8.3 dB (a large change).
- L/R correlation goes from **0.001 (C off) to 0.138 (C on)**: the centre mic narrows and centres the early image.
- Absolute energies are not comparable (the render appears level-normalised; ASSUMED).

**Norm:** ORTF is a two-mic technique (17 cm, ±55°; Radio France). A centre fill is a Decca/"ORTF + C" choice, not ORTF. **ASSUMED** source: standard texts, not re-read.

**Options:**

| Option | Sound | Golden |
|---|---|---|
| (a) Keep C at 0 dB (2011 parity) | as now | none |
| (b) ORTF = C off; offer "ORTF + C" as its own preset | wider, truer ORTF | **YES** (default scene) |
| (c) C at −3 dB / −6 dB (lower than the fold) | between | **YES** |

**Recommendation:** (b), because the name should match the setup. But it changes the default sound (golden YES), so it is Idle's call. Ideally decide it before T6, so the goldens are regenerated once, not twice.

**Touch points:** the app.js ORTF preset (26–30) and `loadDeskPreset` (third_mic / mute_c), app_server DEFAULTS, `desk_matrix` 477 fold. Then regenerate references.

**Decision for Idle:** **N18**: (a) keep / (b) C off + "ORTF + C" preset / (c) lower C.
