# UAD mic-pre models against our "preamps are clean at mic level" claim

*Written 19 Oct 2026, about 13:00 (UK time, BST). Companion to `roadmap\bloom\UAD_COMPARISON_2026-10-19.md`, which has the method, the headless-loading notes and the trust caveats. Data and plots are in `roadmap\bloom\uad\pre\`: `pre_thd_steps.csv`, `pre_freq_response.csv` and `pre_thd_fr.png`. `MIC_CHARACTER_RESEARCH.md` and `mic_character_params.json` were not edited.*

## 1. What was measured

| Plug-in | Settings (Mic input; every EQ, filter and dynamics section off) | Gains tested (small-signal gain at 1 kHz) |
|---|---|---|
| UADx Neve 1073 | Input Mic, Impedance Hi, Pad 0, EQL Out, HPF Off, Output 0 dB | M −30 / −50 / −70 (26.8 / 47.3 / 66.5 dB) |
| UADx 610-A | Mic, Pad Off, Level 0.0 dB, Output 0.00 dB, EQ 0 | Lo / Hi (35.7 / 44.2 dB); also Level −20 dB with Output +12 dB, and a Line-input run |
| UADx 610-B | Mic 500 Ω, Pad Off, Level 10, EQ 0 | Gain −10 / 0 / +10 (26.6 / 35.9 / 46.1 dB); also Level 5 |
| UADx API Vision | Mic, Pad Off, 50 Hz cut Off, 215/235/225/550 all Off | 30 / 45 / 60 dB (26 / 41 / 56 dB) |
| UADx SSL E channel | Mic, Pad Off, Transformer On, Dynamics Out, EQ Out, HP/LP Out | 20 / 40 / 60 dB (9 / 28.8 / 48.8 dB) |
| UADx Manley Tube Preamp | Mic, Low cut Off, Pad 0, Input 10, Transformer In, Output 0 | 40 / 50 / 60 dB (24.9 / 34.6 / 44.3 dB) |

**The tests:**
- **THD.** A level staircase from −90 to 0 dBFS (peak) in 3 dB steps, 1.25 s per step. On the last 1 s of each step I took a Hann-windowed FFT and measured H2–H10 against the fundamental. I did this at 1 kHz and 100 Hz for every gain, and at 40 Hz for the mid gain on Neve, API, SSL E and Manley.
- **Frequency response.** A 4 s exponential sine sweep, 10 Hz–23 kHz, deconvolved to the linear response. I ran it at three drives: "vlow" (output about −40 dBFS), "nom" (output about −20 dBFS) and "hot" (about 3–6 dB below each unit's clip point).

**Level calibration caveat.** UAD doesn't document how dBFS maps to dBu or to mic level. So I quote results as *output level in dBFS* and as *dB below that unit's own 1 %-THD point*. That is the fair way to compare them.

## 2. THD against output level (1 kHz, mid gain)

| Pre | THD at −30 dBFS out | at −18 dBFS out | at −6 dBFS out | at 0 dBFS out | Output at 1 % THD | Dominant harmonic |
|---|---|---|---|---|---|---|
| Neve 1073 (M −50) | 0.09 % | 0.08 % | 0.02 % | 0.012 % | +10.7 to +11.7 dBFS | **H3**, at a fixed absolute level (see §3) |
| API Vision (45) | 0.12 % | 0.046 % | 0.012 % | 0.006 % | +4.0 dBFS | **H3**, fixed absolute level |
| SSL E (40) | 0.0035 % | 0.014 % | 0.056 % | 0.11 % | +3.9 to +5.0 dBFS | **H2**, rising 1 dB per dB of level |
| Manley (50) | 0.0016 % | 0.006 % | 0.025 % | 0.05 % (0.10 % at +5) | +7.6 to +10.3 dBFS | **H2**, rising 1 dB per dB |
| 610-A (Hi, stock trims) | 0.06 % | **0.54–0.69 %** | clipped | clipped | **−16.3 to −18.5 dBFS** | **H2** (H3 close behind near clip) |
| 610-A (Level −20, Output +12) | 0.019 % | 0.08 % | 1.4 % | clipped | −6.0 dBFS | H2 |
| 610-B (0, Level 10) | 0.16 % | **1.6–1.8 %** | clipped | clipped | −17 to −18.5 dBFS | H2 |

At 100 Hz the numbers are within a few percent of the 1 kHz ones, except the Neve near clip: 0.07 % at +6 dBFS out at 100 Hz, against 0.008 % at 1 kHz.

**At 40 Hz, mid gain:**
- **Manley:** 0.35 % at +5 dBFS, against 0.10 % at 1 kHz. That's transformer and low-end saturation.
- **SSL E:** 0.17 % against 0.11–0.14 %.
- **Neve and API:** no low-frequency rise until clip.

**Gain doesn't matter much.** For every pre, THD follows *output* level and hardly changes with the gain setting. Raising the Manley's gain from 40 to 60 dB adds about 4 dB of H2 at the same output, but that's the only notable case.

## 3. Comparison with our claims

| Our claim (`MIC_CHARACTER_RESEARCH.md`) | UAD says | Verdict |
|---|---|---|
| "Datasheet numbers sit in the 0.03–0.1 % THD range at normal operating levels. Character only shows up when you drive them hard." (summary point 5, §7 point 1) | Neve, API, SSL E and Manley are at or below 0.1 % from −30 dBFS up to within about 6 dB of clip. The 610-A and 610-B are **0.5–2 % at a normal −18 dBFS output** with stock trims, and they clip around −12 to −16 dBFS out. | **Holds for 4 of 6.** The UA 610 models are voiced to saturate early. That still fits our own LA-610 bench source (< 0.1 % → > 5 % over about 10 dB), as long as "normal level" for a 610 is taken to be 15 dB or more below its clip. |
| At mic level an input transformer is essentially clean; the iron shows up at line level near clip, and at bass. | No unit shows extra low-frequency distortion at nominal level. Near clip, the Manley's 40 Hz THD is 3.5× its 1 kHz THD. | **Agrees.** |
| Neve 1073: single-ended class-A stages, "so in theory they add H2 (ESTIMATE)"; output transformer adds H3 at low frequency. | UAD Neve is **H3-dominant at every level**. There's a fixed absolute H3 of about −82 dBFS (API about −88 dBFS) that doesn't scale with signal, so relative THD *rises as the signal gets quieter*: 0.1–0.4 % at −30 to −40 dBFS out. H2 only matches H3 in the last dB before clip. | **Contradicts our H2 estimate.** A fixed low-level odd-harmonic floor is the fingerprint of transformer hysteresis or crossover. That's the effect our §6 says the simple saturation model "leaves out". |
| API-ish = symmetric (b ≈ 0), H3. | H3-dominant, the same fixed-floor behaviour, hard clip at +4 dBFS. | **Agrees.** |
| Neve spec ±0.5 dB, 20 Hz–20 kHz | UAD Neve −1.5 dB at 20 Hz, −0.8 dB at 30 Hz, +0.9 dB bump at 18 kHz | UAD is a little outside the published spec. It's probably a modelled unit-specific transformer roll-off. |
| (no FR claims for the others) | API ±0.4 dB. SSL E −3.2 dB at 20 Hz (−1.2 at 30 Hz), flat on top. Manley flat (±0.1 dB). 610-A −3 dB at 20 Hz and −2.7 dB at 20 kHz (−0.8 at 10 k). 610-B −1.3 dB at 20 kHz. | n/a |
| Frequency response vs drive (not claimed) | No change up to clip (≤ 0.1 dB), except the 610-A hot run (20 Hz −4.6 dB against −3.1 nominal; less HF droop) and the 610-B hot run (HF droop shrinks by about 0.4 dB). | Drive changes texture, not tone, until about 3 dB from clip. |

## 4. What it means for the Colour module

Colour is optional, off by default, on the wet returns only, with one Drive knob.

- **The plan holds.** At realistic levels the pres add −60 dB or less, which won't be heard on a tail. Character appears only within about 10 dB of clip.
- **Use two cheap shapes, both of which the data supports:**
  - **"Valve / Manley / SSL / 610" type:** a mostly-H2 shaper whose H2 grows 1 dB per dB of level. That's the classic x + b·x² law. The 610 option should sit closer to its clip at the default Drive.
  - **"Neve / API" type:** a symmetric (H3) clipper **plus an optional fixed low-level odd-harmonic floor** of about −82 to −88 dBFS absolute. That's the hysteresis-like term §6 currently leaves out. On a reverb tail this floor is the only part that could matter at quiet levels, and even there it's around −60 dB relative, so it is a "maybe later".
- **Gain-compensated Drive is the right control.** UAD's THD follows output level and barely depends on the gain switch.

## 5. Proposed edits (not made)

**To `MIC_CHARACTER_RESEARCH.md`:**
1. **Summary point 5 and §7 point 1:**
   - Add "UAD cross-check (19 Oct 2026): Neve/API/SSL E/Manley ≤ 0.1 % up to about 6 dB below clip."
   - Add "UAD's 610-A/B saturate early (0.5–2 % H2 at −18 dBFS out with stock trims; 1 % about 2–3 dB below their hard ceiling)."
2. **§7, Neve paragraph:**
   - Replace the "in theory they add H2 (ESTIMATE)" with "UAD's 1073 is H3-dominant with a level-independent odd floor (≈ −82 dBFS), consistent with transformer hysteresis; H2 only near clip."
   - Change the 1073 preset suggestion (b ≈ 0.1, H2) to b ≈ 0 with an optional hysteresis floor.
3. **§7 table:** add a UAD column: 1 %-THD output point and dominant harmonic for each unit (§2 table above).
4. **§6, the transformer key insight:** add "UAD Manley: at 40 Hz near clip, THD is 3.5× the 1 kHz value; no LF rise at nominal level."
5. **New FR line per pre** (§3 table), including the 610-A's ±3 dB band edges, in case a "610" Colour flavour wants its tone too.

**To `mic_character_params.json`:** no numeric change needed for the current build. If the Colour module is drafted, record the per-pre "1 % point" and "dominant harmonic" as `status: "UAD-measured"`, separate from the datasheet values.
