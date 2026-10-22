# SMALLDECAY listen files: distortion / artifact diagnosis (2026-10-18)

Read-only. Scripts and raw output: %TEMP%\smalldecay_diag\ (diag.py, diag2.py, diag.json). No project files edited.
The generator script for the listen files was not found on disk, under software\, roadmap\ or %TEMP%. listen_report.json says: guitar first 8 s convolved with render() of a unit impulse, then the soft knee. Files are 48 kHz, int32 stereo, 10.79 s.

## Two artifacts in every file, off and on, both coming from the test guitar file
1. **Sub-sonic / DC build-up (the main "distortion").** Source test_guitar_dualmono.wav (int16, peak -1.9 dBFS) has DC -0.0046 plus sub-5 Hz drift. The FDN's DC/near-DC gain multiplies it. In every output, energy below 5 Hz is 0.4-4 dB of the total power, so it is the largest component (welch peak in the lowest bins).
   Output DC (L): boot off -0.021, on -0.038; 4.5x6 off -0.043, on -0.077; 3x4 off -0.092, on -0.141; 2x2.5 off -0.047, on -0.033.
   That is about 5x-31x the source DC. _on is higher because the bass/DC tail is longer (matches the build's 2.1-2.3 s bass).
2. **Clicks every 0.5 s.** The guitar file has hard step discontinuities at exact 0.5 s marks (for example, at 0.5 s 0.066 -> -0.249 -> -0.498; at 1.0 s -0.055 -> -0.567). It looks like a spliced or looped test file. Every output keeps them: 8 kHz-HP peaks at each 0.5 s mark are about 12-16 dB above the HF background in _off and 16-20 dB above in _on. They are more audible in _on because the reverb highs that masked them are gone.

## Per file
| file | sample peak / true peak | overs, flat runs | verdict |
|---|---|---|---|
| boot_6x3x8_off | -5.0 / -4.9 | none | DC drift + 0.5 s clicks (source) |
| boot_6x3x8_on | -4.2 / -4.2 | none | same; DC 1.8x higher, clicks more exposed |
| 4.5x6x2.8_off | -1.2 / -1.2 | none | DC drift + clicks |
| 4.5x6x2.8_on | -0.13 / 0.0 | 1 TP over, 3 limiter samples at 6.5-7.6 s | DC drift lifts the late part into the knee; clicks |
| 3x4x2.5_off | 0.0 / +0.46 | 5858 samples >=0.999, 13911 TP overs, flat runs up to 30 samples | hard limiting 0.7-7.6 s; peak is -2.6 dBFS after 30 Hz HPF, so the clipping comes from DC/sub-sonic |
| 3x4x2.5_on | 0.0 / +0.86 | 59162 samples >=0.999, 63401 TP overs, flat-tops up to 1083 samples (22 ms) | heavy flat-topping, the worst file; -5.3 dBFS after 30 Hz HPF, so all of it is DC/sub-sonic |
| 3x4x2.5_surfaces_on | 0.0 | clipped | same as 3x4 on; -4.8 dBFS after HPF |
| 2x2.5x2.2_off | -3.6 / -3.5 | none | DC drift + clicks |
| 2x2.5x2.2_on | -6.6 / -6.6 | none | DC drift + clicks (most exposed) |

No NaN/inf anywhere. No unstable or growing line: every file's tail falls steadily after 8 s (on: boot -28 -> -78 dB over 2.5 s). The line-20 0.52 dB excess shows no audible growth. No new tonal lines in _on that are absent from _off. The strong late lines (246, 592, 791 Hz and so on) are guitar notes and are present in the source.

## Ranked root causes
1. The test signal has DC and sub-5 Hz drift, and the FDN has large gain at DC (no DC blocker in the tank or the listen path). This causes the 3x4 limiter/clipping (off and on) and the 4.5x6 on near-over, and uses up headroom everywhere. Pre-existing; worse in _on.
2. The test guitar has splice clicks every 0.5 s. Pre-existing in the source; more audible in _on.
3. The soft knee in the listen path flat-tops (up to 22 ms on 3x4 on) because of cause 1.

## What a fix would touch (no code changed)
- Listen harness: high-pass (about 20 Hz) and remove DC from the guitar before convolving, use a clean, click-free test file, and check true peak.
- Engine: add a DC blocker / sub-sonic HPF (about 10-20 Hz) at the FDN inject or output. It is a sound change, so it moves goldens and needs a gate decision. Alternatively, clamp the physical ceiling below 63 Hz so DC loss is not near zero (the boot on bass/DC tail is longer than the dial).
- Then re-measure the 3x4 clip. It should disappear.
