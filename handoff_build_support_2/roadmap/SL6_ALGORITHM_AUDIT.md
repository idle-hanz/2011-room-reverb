# SL6 algorithm audit (2026-10-24)

Verdict: the S1P2 algorithm is right. `design_bus` / `make_spec` match the derivation. The 100 on L is a stamp written after a fallback. The extra bass T20 is in the calibrated FDN tail.

Scene: accepted auto-treat rows on `real_default`, `surf_directional` off, centre bus skipped. No engine edit.

## 1. Fit, guard, clamps

Checked `software/engine/surf_loop.py` against `sound_tricks/SURFACES_IN_LOOP.md` (the rate step, the fit, the guard in §7, D-SL4). VERIFIED.

- Room-average rates give every line the same loss, `G = 60/T(f)`. The delay cancels when the fit hits that loss.
- The fit is three biquads on 56 log frequencies from 20 Hz to 20 kHz. It aims for T at most 2× the longest target.
- The guard rejects a line whose loop would ring longer than 3× that target, or whose octave error is over 50%. It refits shelves only (S1). If that still breaks the loop limit, the line becomes a flat section and the stored errors are set to 1.0.
- Clamps: shelf gain ±40 dB, peak gain ±24 dB, shelf and peak frequencies held inside the same bounds as the derivation, calibration factor clipped to 0.6–1.6.
- The third-octave number in the report is scored from 125 Hz to 8 kHz. The octave centres are 125, 250, 500, 1 kHz, 2 kHz, 4 kHz, 8 kHz.
- System octave error is the delay-weighted sum of the loop loss. On this scene it stays inside 6% (L −5.57% at worst, R −3.83%). VERIFIED, same figures as commit 90c07d7.

## 2. Why L says 100 and R says 9.95

Re-ran the no-impulse designer from that commit. The bus lines came back identical. VERIFIED.

L has one guard. Line 17, 655 samples (13.65 ms), Z axis, kept cut at 21.3 Hz. The loop peaks at +0.45 dB near 0 Hz, so the S1P2 fit blows up. The S1 refit still breaks the 3× limit. The line is replaced by a flat section and the report stores 1.0, which prints as 100. The flat section itself is 34% short at 50 Hz, 13% short at 250 Hz, and 59% long at 8 kHz.

R has one guard on the twin line. Line 17, 658 samples (13.71 ms), same Z cut, loop +0.43 dB near 0 Hz. The S1 refit stays legal and its error is 8.8%, so it does not set the headline. The 9.95 is line 27, on both buses: 2758 samples (57.46 ms), X axis, kept cut at 28.3 Hz, octave error and third error both 9.95%. On L the stamp of 100 hides it. On R it is the worst kept line.

Three samples of delay (655 against 658) are why L falls back to flat and R's shelf refit survives.

## 3. Where the extra T20 comes from

The full room-average render that sits 20–54% long at 50–500 Hz is the calibrated one (the stored 12/23). Re-scored with the mic on, the bass ratios match that score exactly: 1.298, 1.372, 1.461, 1.251, 1.213, 1.296, 0.792, 1.515, 1.536, 1.310, 1.197. VERIFIED.

Same calibration, stages separated. Ratio of T20 to the Mäkivirta target:

| Hz | tail | + early | + direct | + mic |
|---|---|---|---|---|
| 50 | 1.41 | 1.31 | 1.25 | 1.30 |
| 63 | 1.18 | 1.29 | 1.30 | 1.37 |
| 79 | 1.44 | 1.51 | 1.45 | 1.46 |
| 99 | 1.34 | 1.39 | 1.31 | 1.25 |
| 125 | 1.24 | 1.26 | 1.16 | 1.21 |
| 157 | 1.55 | 1.52 | 1.29 | 1.30 |
| 198 | 1.16 | 0.89 | 0.79 | 0.79 |
| 250 | 1.58 | 1.57 | 1.56 | 1.52 |
| 315 | 1.57 | 1.58 | 1.66 | 1.54 |
| 397 | 1.42 | 1.40 | 1.23 | 1.31 |
| 500 | 1.23 | 1.20 | 1.19 | 1.20 |

The tail is already long, from +18% at 63 Hz to +58% at 250 Hz. Adding early, direct, and the mic does not create that length. The one stage is the tail. Bands inside ±10% stay 10, 12, 11, then 12 of 23.

Calibration factors for that pass (125 Hz through 8 kHz): 0.829, 0.782, 0.952, 0.850, 0.878, 0.870, 0.906. All below 1, so the second design reduces the loss. VERIFIED.

One suspected cause: those factors lengthen the tail, and the third-octave T20 stays long after that. The flat fallback line is short in the bass, so it does not make this excess.

The render path, before calibration, reports the R bus at 10.22 with no guard. The 9.95 figure belongs to the no-impulse designer above. Left as a backlog line.
