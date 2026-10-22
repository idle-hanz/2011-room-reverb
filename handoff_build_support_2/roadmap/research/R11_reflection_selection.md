# R11 · Reflection selection: fixed LIVE_32 vs "loudest 32" (U9)

**Today (VERIFIED):** `LIVE_32` (early_field.py 257) is a fixed set of 32 image orders/directions (orders 0–4 as 1/6/11/10/4), chosen in `compute_taps` (1724, table 1773–1784). Every capsule gets the same 32 taps, weighted by its own pattern.

**Measured on the box** (`proto/tap_suppression.py` → `.json`, default room). The question: how many of the 32 taps sit 20 dB or more under the loudest tap, and how much energy would a "loudest 32 from the 128-tap grid" pick gain?

| Setup | taps 20 dB down (L/R) | wasted on both | energy gain, loudest-32 |
|---|---|---|---|
| ORTF | 18 / 15 | 8 | +0.01 dB |
| XY | 19 / 15 | 9 | 0 dB |
| Blumlein ±45° | 19 / 15 | 8 | +0.2 dB |
| MS cardioid M | 15 / 19 | 9 | 0 dB |
| MS omni M | 15 / 19 | 9 | +0.16 dB |
| Fig-8 side pair ±90° | 10 / 9 | 9 | **+1.24 dB** |

**Reading:** the late, quiet taps are quiet because of distance, not because the pattern rejects them. Re-picking by loudness gains ≤0.2 dB in every normal setup, and 1.2 dB only for a pure side-facing fig-8 pair. The Blumlein row showed 0 taps under −20 dB of *pattern* gain, which looks wrong for a fig-8. Flag **ASSUMED / check** in the probe before relying on that row.

**Perception (ASSUMED, not re-read today):** Olive & Toole 1989 (JAES 37, "The detection of reflections in typical rooms") and Barron 1971 (JSV 15) put single-reflection audibility thresholds roughly 10–20 dB under the direct sound, depending on delay and direction. Taps 20 dB down are near or under threshold individually but add up as density.

**Recommendation:** keep LIVE_32. Do not add a per-setup loudness pick: it changes the FDN injection per setup, breaks Play/Render parity tests, and buys ≤0.2 dB. If anything, spend effort on density (R12 scatter) rather than selection.

**Touch points if ever changed:** early_field.py 257, 1773–1784; fdn.py `apply_capsule_weights` 424.

**Tests / goldens:** none now.

**Decision for Idle:** none needed ("info only", U9). Optional: allow a per-setup pick for fig-8 side pairs only (recommend no).
