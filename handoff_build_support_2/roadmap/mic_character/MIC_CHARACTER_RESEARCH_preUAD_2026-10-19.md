# Mic character: research for 2011 Room Reverb

*Researched 18 Oct 2026 for Idle Hanz. Everything here is either **MEASURED** (I computed it from a public measurement set, method below), **PUBLISHED** (a datasheet, paper or credible article, cited by number), or **ESTIMATE** (my reasoning, labelled). No numbers are invented. Machine-readable version: `mic_character_params.json`. Raw third-octave tables: `measured_third_octave.csv`.*

---

## 0. The short version

1. **The biggest "character" a mic gives a reverb is how it hears sound from everywhere at once.** Most of a reverb tail reaches the mic from the sides and back, so the tail is coloured by the mic's *average over all directions* (its **diffuse-field response**), not by its front response. I measured that average for 20 mics from the same Zenodo set we already use. Clear result: **large-diaphragm cardioids (U87, NT2-A, C414, K2, U47 fet) give a darker tail.** It falls 8–14 dB at 16 kHz against their own 1 kHz level. **Small-diaphragm cardioids (Schoeps CMC5-U, AKG C451) only fall 2–4.5 dB.** That's the real, physical reason people call LDC room mics "warm" and SDCs "open".
2. **The engine already does most of the per-direction part.** Since the 27 Sep mic-colour work, each early reflection and each FDN line gets the measured off-axis colour for its own arrival angle (`MEASURED_SHELF` mode, see `software/mic_colour/HOOKS.md`). Three things are still missing: (a) the **on-axis** response, because the fitter sets 0° to 0 dB by design, so presence peaks are flattened away; (b) a true **diffuse-field average** for the tail (today each FDN line uses one seed angle); (c) **elevation**, because the data is horizontal-plane only.
3. **Transient "smear" isn't a separate effect worth modelling.** The measured step rise times for LDCs (21–29 µs) and SDCs (21–26 µs) are within a few microseconds of each other at a 20 kHz bandwidth. What makes one mic "faster" than another is its frequency response, which we already model. Ribbons are slower (42–70 µs) only because they roll off the top end. This corrects my earlier "big diaphragms soften attacks" remark: on measurement, the difference is too small to matter.
4. **Self-noise is not worth modelling** for a reverb (7–18 dB-A SPL for these mics, below a quiet room).
5. **Transformers and preamps are real but subtle at normal levels.** Datasheet numbers sit in the 0.03–0.1 % THD range at normal operating levels. Character only shows up when you drive them hard. On a dense reverb tail it reads as slight density or grit rather than "warmth". It's worth building only as an **optional Colour module, off by default, with one Drive knob**. Cheap models (below) reproduce the published behaviour well.

**Ranked recommendation (detail in §8):** ① diffuse-field tail colour + restore the on-axis response, ② the Colour module (transformer + valve/solid-state stage), ③ elevation-aware colour, ④ hysteresis, self-noise, transient modelling: don't build.

---

## 1. Words used in this note

- **On-axis**: sound coming straight at the front of the mic (0°).
- **Off-axis**: from any other angle. 90° is the side, 180° the back.
- **Polar pattern**: how loud the mic is at each angle. It changes with frequency: real mics get more directional in the treble.
- **Free field**: sound from one direction only, as in an anechoic room. Datasheet curves are free-field, on-axis.
- **Diffuse field**: sound arriving equally from every direction at once. A late reverb tail is close to this.
- **Directivity index (DI)**: how many dB louder the mic is to on-axis sound than to an equal-energy diffuse field. 0 dB means omni. A first-order cardioid is 4.8 dB.
- **Diffuse-field response**: the mic's frequency response in a diffuse field. It equals the on-axis response minus the DI at each frequency.
- **LDC / SDC**: large / small-diaphragm condenser. Neumann's Schneider uses >25 mm for large and 17–22 mm for small [1]. The Zenodo paper uses ≥17 mm for "large" [2].
- **Single vs double diaphragm**: a double-diaphragm capsule (Braunmühl–Weber, e.g. U87, C414, NT2-A) is two cardioids back to back, so it can switch patterns. A single-diaphragm cardioid (e.g. Schoeps) is cardioid only.
- **THD**: total harmonic distortion, the level of the added harmonics (2×, 3×, … the input frequency) relative to the tone.
- **H2, H3**: the 2nd and 3rd harmonic. H2 is one octave up and sounds "warm" or "full". H3 is an octave and a fifth up and sounds "edgy" or "bright".
- **dBu**: voltage level, where 0 dBu = 0.775 V RMS. Line level is about +4 dBu, and microphone signals are roughly −60 to −20 dBu.
- **Hysteresis**: magnetic "memory" in a transformer core. Its state depends on where the signal has been, not just where it is now.

---

## 2. Off-axis colour and the diffuse field

### 2.1 Why this matters for a reverb, step by step

1. In a room, the direct sound arrives from one direction, usually the front of the mic.
2. The early reflections arrive from a few dozen specific directions: walls, floor, ceiling. Most of them hit the mic off-axis.
3. After roughly 50–100 ms (ESTIMATE, room-dependent) there are so many reflections that sound arrives from everywhere: the **diffuse tail**.
4. A mic's sensitivity at the side and back is not just quieter. It's **duller**, because the capsule and housing block short wavelengths more from those directions.
5. So what you hear in the tail is the mic's **power average over the whole sphere**, and its tone is the on-axis tone **minus DI(f)**.
6. If DI rises with frequency (it always does above some kHz), the tail is darker than the direct sound. The faster DI rises, the darker the mic's "room sound".

Schneider (Neumann) makes the same point at the bass end. Double-diaphragm capsules become *less* directional in the bass, so used as ambient mics they "pick up more bass from all directions" and "overemphasize the low frequent parts of the reverberation", while single-diaphragm designs "provide a drier sound" [1]. That's a published, measured design difference, and the data below reproduces it.

### 2.2 The data source

**Franco Hernández, Brookes & De Sena, "A Multi-Angle, Multi-Distance Dataset of Microphone Impulse Responses", JAES 2022** [2]. Data on Zenodo, doi:10.5281/zenodo.4633508, CC-BY-4.0 [3]. It's the set the project's fitter already uses. It has 25 mics, 72 angles (5° steps, horizontal plane), 0.5 / 1.25 / 5 m, 48 kHz, quasi-anechoic, plus a Class-1 NTi M2211 measurement mic as reference.

Other sets exist: IEM Graz **DirPat** (3-D directivity incl. some microphones, SOFA format) [4]. Neumann publishes polar plots per model on its product pages, but as images, not data.

### 2.3 What I computed (MEASURED, method)

From the **5 m raw IRs** (far field, so no proximity effect [1]) for 20 mics/patterns plus the NTi reference:

- Took the first 900 samples (18.75 ms, the files are already time-windowed) with a 200-sample half-Hann taper and an 8192-point FFT.
- **On-axis response** = mic 0° ÷ NTi 0° (this removes the loudspeaker), 1/3-octave power-smoothed, normalised to 0 dB at 1 kHz.
- **Diffuse-field power** = sin θ-weighted average of |H(θ)|² over 0–180°, with left and right halves averaged. This **assumes the pattern is rotationally symmetric about the mic axis** (ESTIMATE for side-address LDCs at HF, see caveats).
- **DI** = 10·log10(on-axis power ÷ diffuse power).

**Sanity check that the method works:** first-order theory gives a cardioid DI of 4.8 dB, hypercardioid 6.0 dB, figure-8 4.8 dB and omni 0 dB [10]. At 1 kHz I measured cardioids 4.0–5.9, C414 hyper 6.0, ribbons (figure-8) 4.6–4.8 and omnis 0.1–0.4. The method agrees with theory where theory applies.

**Reliability limits:** below about 125 Hz the 18.75 ms window limits accuracy, so treat 125 Hz as indicative. At 16 kHz the off-axis values are very sensitive to exact angle and mounting, so treat 16 kHz as ±3 dB (ESTIMATE). All data comes from one unit per model.

### 2.4 Directivity index by octave (MEASURED, dB)

| Mic | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 16k |
|---|---|---|---|---|---|---|---|---|
| Røde NT2-A (cardioid) | +3.3 | +4.2 | +4.7 | +5.0 | +4.9 | +5.1 | +5.7 | +12.4 |
| Røde NT2-A (omni) | +0.1 | +0.3 | +0.3 | +0.2 | -0.0 | -1.2 | +2.1 | +9.5 |
| Røde NT2-A (fig-8) | +5.1 | +5.0 | +5.1 | +5.1 | +5.2 | +5.5 | +5.8 | +9.5 |
| Neumann U87 Ai (cardioid) | +2.8 | +3.8 | +4.3 | +5.0 | +4.6 | +5.1 | +4.9 | +13.1 |
| Neumann U87 Ai (omni) | -0.1 | +0.1 | +0.1 | +0.1 | -0.3 | -1.8 | +1.3 | +10.3 |
| Neumann U87 Ai (fig-8) | +5.4 | +5.4 | +5.3 | +5.4 | +5.4 | +5.5 | +5.9 | +10.1 |
| Neumann U47 fet (cardioid) | +4.1 | +4.9 | +5.4 | +5.9 | +5.7 | +6.1 | +6.2 | +12.0 |
| AKG C414 (cardioid) | +2.9 | +3.8 | +4.3 | +4.7 | +4.0 | +5.5 | +6.0 | +11.7 |
| AKG C414 (omni) | -0.0 | +0.1 | +0.1 | +0.2 | -0.0 | +1.3 | +2.0 | +8.8 |
| AKG C414 (hyper) | +4.9 | +5.6 | +5.8 | +6.0 | +5.6 | +6.3 | +7.0 | +11.0 |
| AKG C414 (fig-8) | +5.8 | +5.8 | +5.8 | +5.7 | +5.6 | +5.8 | +6.6 | +8.2 |
| Sony C800 (cardioid) | +3.3 | +3.6 | +4.5 | +5.3 | +4.9 | +5.1 | +6.8 | +10.9 |
| Røde K2 (cardioid, valve) | +2.7 | +3.9 | +4.4 | +4.9 | +4.5 | +4.9 | +5.8 | +12.0 |
| Schoeps CMC5-U (SDC cardioid) | +4.5 | +4.5 | +4.4 | +4.9 | +5.0 | +5.3 | +4.4 | +7.8 |
| Schoeps CMC5-U (SDC omni) | +0.0 | +0.1 | +0.2 | +0.4 | +0.3 | +1.4 | +4.4 | +8.2 |
| AKG C451 (SDC cardioid) | +3.6 | +3.7 | +3.8 | +4.0 | +4.0 | +4.1 | +3.5 | +7.8 |
| DPA 4006 (SDC omni) | +0.1 | +0.1 | +0.1 | +0.1 | +0.5 | +1.3 | +3.4 | +7.3 |
| Royer R-121 (ribbon) | +4.8 | +4.8 | +4.9 | +4.8 | +5.0 | +5.0 | +6.3 | +1.9 |
| Coles 4038 (ribbon) | +4.8 | +4.8 | +4.6 | +4.6 | +4.5 | +4.7 | +5.5 | +2.0 |
| Røde NTR (ribbon) | +4.8 | +4.7 | +4.7 | +4.8 | +4.9 | +4.9 | +3.8 | +7.3 |
| NTi M2211 (measurement ref.) | +0.0 | +0.0 | +0.1 | +0.2 | +0.4 | +1.1 | +2.4 | +5.4 |

How to read it: a cardioid LDC sits near 5 dB through the mids, then jumps to 11–13 dB at 16 kHz. The SDCs (Schoeps, C451) only reach about 8 dB, and the ribbons stay near 5 dB until the top octave.

### 2.5 Diffuse-field (tail) response, relative to the mic's own 1 kHz (MEASURED, dB)

This is **the EQ the late tail gets from each mic**, ignoring overall level:

| Mic | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 16k |
|---|---|---|---|---|---|---|---|---|
| Røde NT2-A (cardioid) | -0.9 | -0.3 | -0.4 | -0.0 | -0.3 | +0.2 | -2.0 | -7.9 |
| Røde NT2-A (omni) | +0.4 | +0.5 | -0.0 | +0.0 | +0.4 | -0.2 | -2.1 | -8.8 |
| Røde NT2-A (fig-8) | -4.6 | -1.7 | -0.7 | +0.0 | -0.1 | +1.6 | -1.7 | -5.4 |
| Neumann U87 Ai (cardioid) | -0.8 | +0.0 | +0.0 | -0.0 | -0.1 | +0.3 | -0.5 | -13.9 |
| Neumann U87 Ai (omni) | -0.6 | +0.2 | -0.4 | +0.0 | -0.6 | -1.1 | -1.5 | -17.6 |
| Neumann U87 Ai (fig-8) | -5.7 | -2.1 | -0.7 | +0.0 | -0.1 | +2.0 | -2.7 | -12.7 |
| Neumann U47 fet (cardioid) | -1.9 | -0.8 | -0.6 | +0.0 | +0.8 | +1.2 | +0.5 | -9.6 |
| AKG C414 (cardioid) | +0.6 | +1.0 | +1.0 | +0.0 | +0.8 | +1.5 | +0.3 | -8.2 |
| AKG C414 (omni) | +1.7 | +1.7 | +1.3 | -0.0 | +1.2 | +0.8 | -0.2 | -8.3 |
| AKG C414 (hyper) | -1.3 | +0.1 | +0.5 | +0.0 | +0.2 | +2.0 | +0.8 | -6.4 |
| AKG C414 (fig-8) | -3.6 | -0.9 | -0.1 | +0.0 | -0.6 | +2.4 | +0.8 | -4.8 |
| Sony C800 (cardioid) | +1.4 | +1.2 | +0.5 | -0.0 | -0.5 | -1.7 | -2.3 | -6.9 |
| Røde K2 (cardioid, valve) | +0.2 | +0.0 | -0.1 | -0.0 | +0.3 | +0.7 | -2.0 | -8.3 |
| Schoeps CMC5-U (SDC cardioid) | -3.5 | -0.9 | -0.2 | -0.0 | -0.8 | -0.8 | +0.6 | -4.5 |
| Schoeps CMC5-U (SDC omni) | -0.1 | +0.0 | -0.2 | +0.0 | -0.4 | -0.9 | -3.7 | -9.2 |
| AKG C451 (SDC cardioid) | -2.7 | -0.7 | -0.3 | +0.0 | +0.5 | +0.9 | +1.2 | -2.1 |
| DPA 4006 (SDC omni) | +1.8 | +1.6 | +1.1 | +0.0 | -1.8 | -3.7 | -2.1 | -7.3 |
| Royer R-121 (ribbon) | -6.5 | -1.5 | -1.1 | +0.0 | +0.0 | -0.1 | -2.3 | -4.1 |
| Coles 4038 (ribbon) | -4.4 | +0.6 | +1.7 | +0.0 | -0.8 | -1.8 | -4.2 | -10.0 |
| Røde NTR (ribbon) | -1.5 | +0.3 | -0.3 | -0.0 | -0.7 | -1.2 | -4.2 | -5.2 |
| NTi M2211 (measurement ref.) | +0.1 | +0.1 | +0.0 | -0.0 | -0.2 | -0.9 | -2.3 | -5.2 |

What this tells you in plain terms:

- **U87 Ai cardioid:** flat tail through 8 kHz, then −13.9 dB at 16 kHz. It's the darkest top end of the cardioids here.
- **NT2-A cardioid:** −2 dB at 8 kHz and −7.9 dB at 16 kHz. It's a little more open on top than the U87.
- **C414 cardioid:** +1 dB from 250–500 Hz and +1.5 dB at 4 kHz, so a fuller, slightly forward tail, −8.2 dB at 16 kHz.
- **Schoeps CMC5-U cardioid** (single diaphragm, SDC): −3.5 dB at 125 Hz, the "drier" bass Schneider describes, and only −4.5 dB at 16 kHz. It gives the brightest, leanest tail.
- **Ribbons:** the R-121 loses the bass in the far field (−6.5 dB at 125 Hz) and is fairly flat on top. The Coles 4038 is darker from 4 kHz up.
- **Double-diaphragm omni (U87 omni):** −17.6 dB at 16 kHz. This matches Schneider's finding that dual-capsule omnis become strongly directional at HF, with a "propeller" pattern and DI up to about 10 dB [1].

### 2.6 How to apply it in the engine

**Early reflections (per arrival).** Keep what's there: per tap, look up the measured H(θ_tap, f) and filter. Two refinements:
- Use the **true 3-D angle** between the mic look direction and the image, not just azimuth. Until 3-D data is used, the horizontal-plane H at that angle is the best available approximation (ESTIMATE).
- Make sure the tap's level comes from the measured |H| **or** from `pattern_gain`, not both. R05 already flagged this possible double-count as an open check.

**Late tail (one filter per mic):**
1. From the measured set, compute P_diff(f) = Σ_θ w(θ)·|H(θ,f)|² with w(θ) ∝ sin θ.
2. The tail EQ, relative to on-axis, is G_tail(f) = 10·log10(P_diff(f) / |H(0,f)|²) = −DI(f).
3. Fit that curve with the existing K=3 SOS fitter (LS + HS + PK) and apply it once to each mic's FDN output bus, instead of the per-line seed-angle colour.

Why: with 32 lines and a handful of seed angles, the current sum is a coarse sampling of the sphere, and it weights angles by where seeds happened to land. The diffuse average is the physically right answer for a mixing tail. It also costs less: one filter per bus instead of one per line.

Practical blend (ESTIMATE): crossfade from the per-tap colour (early) to the diffuse colour (tail) over the same early-to-late transition the engine already uses. Then nothing jumps.

**Fallback for presets with no measurement** (first-order theory [10]):
pattern gain g(θ) = a + (1−a)·cos θ, so the random-energy efficiency is REE = a² + (1−a)²/3 and DI = −10·log10(REE). Cardioid a = 0.5 gives 4.77 dB. This is frequency-flat, so add a high-frequency DI rise as an ESTIMATE high shelf, scaled by capsule size. The measured LDC vs SDC rows above give the targets (roughly +7 dB at 16 kHz for an LDC and +3 dB for an SDC, relative to mid-band).

---

## 3. On-axis presence, air and low-frequency roll-off

### 3.1 Measured on-axis response (5 m, relative to 1 kHz, MEASURED, dB)

| Mic | 125 | 250 | 500 | 1k | 2k | 4k | 8k | 16k |
|---|---|---|---|---|---|---|---|---|
| Røde NT2-A (cardioid) | -2.5 | -1.1 | -0.7 | +0.0 | -0.4 | +0.3 | -1.3 | -0.6 |
| Røde NT2-A (omni) | +0.4 | +0.5 | +0.1 | +0.0 | +0.2 | -1.5 | -0.2 | +0.5 |
| Røde NT2-A (fig-8) | -4.5 | -1.8 | -0.7 | +0.0 | +0.1 | +2.0 | -0.9 | -1.0 |
| Neumann U87 Ai (cardioid) | -3.1 | -1.2 | -0.7 | -0.0 | -0.5 | +0.4 | -0.6 | -5.8 |
| Neumann U87 Ai (omni) | -0.8 | +0.2 | -0.3 | +0.0 | -1.0 | -2.9 | -0.3 | -7.4 |
| Neumann U87 Ai (fig-8) | -5.7 | -2.1 | -0.8 | -0.0 | -0.1 | +2.1 | -2.3 | -8.0 |
| Neumann U47 fet (cardioid) | -3.7 | -1.8 | -1.1 | -0.0 | +0.6 | +1.4 | +0.8 | -3.4 |
| AKG C414 (cardioid) | -1.3 | +0.1 | +0.5 | -0.0 | +0.2 | +2.3 | +1.5 | -1.2 |
| AKG C414 (omni) | +1.5 | +1.6 | +1.2 | -0.0 | +1.0 | +1.9 | +1.7 | +0.3 |
| AKG C414 (hyper) | -2.4 | -0.3 | +0.3 | +0.0 | -0.2 | +2.3 | +1.7 | -1.4 |
| AKG C414 (fig-8) | -3.5 | -0.7 | +0.1 | -0.0 | -0.7 | +2.5 | +1.8 | -2.3 |
| Sony C800 (cardioid) | -0.7 | -0.5 | -0.4 | -0.0 | -1.0 | -1.9 | -0.9 | -1.3 |
| Røde K2 (cardioid, valve) | -1.9 | -1.0 | -0.6 | -0.0 | -0.1 | +0.7 | -1.0 | -1.2 |
| Schoeps CMC5-U (SDC cardioid) | -3.9 | -1.2 | -0.7 | +0.0 | -0.7 | -0.4 | +0.1 | -1.6 |
| Schoeps CMC5-U (SDC omni) | -0.5 | -0.2 | -0.4 | -0.0 | -0.5 | +0.1 | +0.3 | -1.3 |
| AKG C451 (SDC cardioid) | -3.1 | -1.1 | -0.5 | +0.0 | +0.4 | +1.0 | +0.7 | +1.7 |
| DPA 4006 (SDC omni) | +1.8 | +1.6 | +1.1 | -0.0 | -1.4 | -2.5 | +1.3 | -0.2 |
| Royer R-121 (ribbon) | -6.6 | -1.5 | -1.0 | -0.0 | +0.2 | +0.1 | -0.9 | -7.0 |
| Coles 4038 (ribbon) | -4.2 | +0.8 | +1.6 | +0.0 | -0.9 | -1.7 | -3.3 | -12.7 |
| Røde NTR (ribbon) | -1.4 | +0.3 | -0.3 | +0.0 | -0.5 | -1.1 | -5.2 | -2.6 |
| NTi M2211 (measurement ref.) | +0.0 | +0.0 | +0.0 | +0.0 | +0.0 | -0.0 | +0.0 | -0.0 |

### 3.2 Peaks and HF limit (MEASURED; rise time in §4)

| Mic | Presence peak (1/6-oct, re 1 kHz) | On-axis HF −3 dB | Step rise 10–90 % (µs) |
|---|---|---|---|
| Røde NT2-A (cardioid) | 5.3 kHz, +1.4 dB | 17.7 kHz | 23.4 |
| Røde NT2-A (omni) | 11.2 kHz, +4.0 dB | 18.4 kHz | 18.2 |
| Røde NT2-A (fig-8) | 5.3 kHz, +2.8 dB | 9.2 kHz | 33.9 |
| Neumann U87 Ai (cardioid) | 3.2 kHz, +0.9 dB | 14.0 kHz | 28.6 |
| Neumann U87 Ai (omni) | 11.1 kHz, +1.5 dB | 13.7 kHz | 28.6 |
| Neumann U87 Ai (fig-8) | 5.2 kHz, +2.3 dB | 9.2 kHz | 39.1 |
| Neumann U47 fet (cardioid) | 9.2 kHz, +2.0 dB | 15.6 kHz | 26.0 |
| AKG C414 (cardioid) | 5.5 kHz, +2.7 dB | 18.4 kHz | 23.4 |
| AKG C414 (omni) | 13.0 kHz, +5.4 dB | 22.6 kHz | 20.8 |
| AKG C414 (hyper) | 3.2 kHz, +3.1 dB | 18.4 kHz | 26.0 |
| AKG C414 (fig-8) | 3.2 kHz, +3.7 dB | 17.1 kHz | 28.6 |
| Sony C800 (cardioid) | 9.2 kHz, -0.3 dB | 18.8 kHz | 119.8 |
| Røde K2 (cardioid, valve) | 5.2 kHz, +1.8 dB | 17.3 kHz | 20.8 |
| Schoeps CMC5-U (SDC cardioid) | 7.7 kHz, +0.4 dB | 17.6 kHz | 26.0 |
| Schoeps CMC5-U (SDC omni) | 3.3 kHz, +1.7 dB | 17.9 kHz | 20.8 |
| AKG C451 (SDC cardioid) | 9.7 kHz, +2.4 dB | 19.1 kHz | 26.0 |
| DPA 4006 (SDC omni) | 11.8 kHz, +3.1 dB | 17.7 kHz | 250.0 |
| Royer R-121 (ribbon) | 5.0 kHz, +1.1 dB | 10.2 kHz | 41.7 |
| Coles 4038 (ribbon) | 2.0 kHz, -0.8 dB | 8.0 kHz | 70.3 |
| Røde NTR (ribbon) | 3.1 kHz, +0.3 dB | 8.0 kHz | 70.3 |
| NTi M2211 (measurement ref.) | 2.0 kHz, +0.0 dB | >20 kHz | 15.6 |

*"On-axis HF −3 dB" is the first frequency above 8 kHz where the on-axis response falls 3 dB below 1 kHz. For fig-8 modes that is often a dip, not the final roll-off.*

### 3.3 What the capsule designers say (PUBLISHED)

From David Bock's *Tape Op* capsule article [5]:
- **K47** (U47, U47 fet): a single backplate, dual membrane with a centre-fixed membrane. Bock describes it as having a "relatively low resonant freq … low mid signature … lack of high frequency (HF) peak".
- **CK12** (C12, C414 lineage): "very flat midrange and 10–12 kHz peak".
- **K67/K87** (U67, U87): "aggressive in the mids, typically peaking @5k, and has a HF peak @12–13 kHz".

Our single-unit 5 m measurements only partly show those peaks. The C414 has +2.3 dB at 4 kHz and the U87 a slight rise near 3 kHz. 1/3-octave smoothing and the far-field set-up flatten narrow peaks, so the fitter should use the raw 1/6-octave data for presence (ESTIMATE).

### 3.4 LF roll-off

In the far field, directional mics roll off the bass because there is no proximity boost [1]. Measured at 125 Hz on-axis: cardioid LDCs −0.7 (Sony C800) to −3.7 dB (U47 fet), Schoeps cardioid −3.9 dB, ribbons −1.4 (NTR) to −6.6 dB (R-121), and omnis roughly flat (−0.8 to +1.8 dB). The engine's existing proximity shelf should **add** to this for near sources only. A late tail is a far, diffuse source, so it gets **no** proximity boost (see §9).

### 3.5 Recommendation

Restore the on-axis response as a separate, small filter on the **direct** sound and early field. A K=3 SOS fit from the 1/6-octave on-axis data covers the presence peak, HF air and LF roll-off. Off-axis H then stays relative to on-axis, as now. Without this, every mic sounds the same head-on, and only the off-axis differs, which R05 already noted for the SM57.

---

## 4. Diaphragm transient response

### 4.1 The physics, simply

A diaphragm is a mass on a spring (its tension), with damping from air in the backplate holes. That gives a resonance, and designers deliberately tune and damp it with blind holes and backplate geometry [5]. Bock: "the membrane tension determines in-band resonance", and dual-backplate designs put the resonance higher [5].

Key point: **a microphone is a linear system.** Its response to a click (impulse), a step or a drum hit is completely fixed by its frequency response, magnitude *and* phase. "Transient response" is not an extra property. It's the time-domain view of the same response. A resonance peak of +3 dB at 12 kHz *is* a short ring at 12 kHz.

### 4.2 Measured step rise times (MEASURED)

I deconvolved each mic's 0° IR by the NTi reference, band-limited to 20 Hz–20 kHz, upsampled ×8, and measured the 10–90 % rise of the step response (table in §3.2):
- NTi measurement mic: **15.6 µs** (the 20 kHz band-limit floor)
- LDC cardioids: **20.8–28.6 µs** (NT2-A 23.4, U87 28.6, C414 23.4, U47 fet 26.0, K2 20.8)
- SDC cardioids: **26.0 µs** (Schoeps, C451)
- Ribbons: **41.7 µs** (R-121) and **70.3 µs** (4038, NTR)
- The Sony C800 (119.8 µs) and DPA 4006 (250 µs) results are almost certainly **artefacts** (a polarity or time-alignment issue in those files). The DPA 4006 is a reference-grade omni, so treat these two as unreliable.

**Conclusion:** in this data the LDC vs SDC difference is a few microseconds. At 48 kHz that's under a quarter of a sample. The ribbons are slower only because they roll off the top. **No separate "transient" model is needed:** a minimum-phase fit of the measured magnitude (which the SOS fitter already gives) reproduces it.

### 4.3 If you ever want an explicit resonance (ESTIMATE)

Model it as a 2nd-order peak inside the on-axis filter: H_res(s) = (s² + (ω₀/Q_z)s + ω₀²) / (s² + (ω₀/Q_p)s + ω₀²), with ω₀ = 2π·f₀. The ratio Q_p / Q_z sets the peak height. f₀ and the gain come from the presence-peak table, e.g. 5–5.5 kHz, about +1.5 to +3 dB, for the K67-style and CK12-style capsules here. I found **no published Q values** for these capsules, so any Q would be fitted to the measured curve, not taken from a datasheet.

---

## 5. Self-noise (PUBLISHED)

| Mic | Self-noise (A-weighted, SPL) | Sensitivity | Source |
|---|---|---|---|
| Røde NT2-A | 7 dB-A | −36 dBV/Pa (16 mV/Pa) | [6] |
| AKG C414 XLII | 6 dB-A | 23 mV/Pa | [7] |
| Neumann U87 Ai | 12 dB-A (cardioid); 15 omni, 14 fig-8 | 28 mV/Pa (cardioid) | [8] |
| Neumann U47 fet | 18 dB-A | 8 mV/Pa | [9a] |
| Neumann KM 184 (SDC) | 13 dB-A | 15 mV/Pa | [9b] |
| Audio-Technica AT4050 | 17 dB-A | −36 dBV/Pa (15.8 mV/Pa) | [11] |
| Royer R-121 (ribbon, passive) | no active electronics, so noise is set by the preamp | −47 dBV/Pa | [12] |

Is it worth modelling? **No.** The highest figure is 18 dB-A. A quiet studio's background noise is usually above that (ESTIMATE, rooms vary). In a virtual room there's no real background anyway, so adding hiss would only lower the reverb's signal-to-noise. If it's ever wanted for realism: add a fixed-level, pink-tilted noise per capsule, uncorrelated between capsules, at (self-noise SPL − reference SPL) relative to the signal calibration.

---

## 6. Transformers

### 6.1 How a transformer distorts, step by step (PUBLISHED, Whitlock / Jensen [13])

1. The core's magnetic flux is the **time integral** of the voltage across the winding. For a fixed voltage, **flux doubles each time the frequency halves**.
2. The core material has a curved B–H characteristic. At high flux it **saturates**. At very low flux, **hysteresis** adds a little nonlinearity.
3. The curve is symmetric, so the distortion is **"nearly pure third harmonic"** [13]. Even harmonics (H2, H4) appear only if DC flows in a winding or the core is magnetised [13].
4. Distortion is set by **voltage and source impedance, not power**. A low driving impedance "shorts out" the core's nonlinearity [13].
5. Measured result: for 84 % nickel cores, THD **"roughly quarters for every doubling of frequency, dropping to less than 0.001 % above about 50 Hz"** [13]. Steel cores fall off more slowly.
6. Because the distortion is frequency-selective (bass only), its IM distortion is far lower than an amplifier with the same THD. Whitlock's example is the Jensen JT-10KB-D: about 0.03 % THD at +26 dBu, 60 Hz, but only about 0.01 % SMPTE IM [13].
7. **Low-frequency response:** the primary inductance forms a 1st-order high-pass with the source impedance. Whitlock's example is a 10 H primary with 600 Ω source → −3 dB at about 10 Hz, or 1.6 Hz with 50 Ω [13]. Rising permeability at very low frequencies makes the real slope gentler than 6 dB/octave, with less phase shift than a capacitor [13].
8. **High-frequency response:** leakage inductance and winding capacitance form a 2-pole low-pass. Under-damped, it peaks and rings on square waves. Properly damped, it rolls off cleanly [13]. Jensen tunes theirs to a Bessel response.

### 6.2 Published numbers

| Device | Spec | Source |
|---|---|---|
| Jensen JT-115K-E (1:10 mic input) | −3 dB at 2.5 Hz and 90 kHz; max input at 20 Hz (1 % THD) −2.5 dBu; THD at 20 Hz 0.065 % (level not stated in Jensen's table); 20 Hz / 20 kHz response −0.26 / −0.13 dB | [14] |
| Jensen JT-16-A (1:2) | max at 20 Hz +10 dBu; THD at 20 Hz 0.025 % | [14] |
| Jensen JT-10KB-D (line input) | ~0.03 % THD at +26 dBu, 60 Hz; ~0.01 % SMPTE IM | [13] |
| API 2503 output transformer | 75 Ω primary, 75/300/600 Ω secondary; vintage spec max +30 dBm | [15] |

**The key insight for a reverb:** a mic *input* transformer sees mic level (about −60 to −20 dBu, ESTIMATE typical). The JT-115K-E reaches 1 % at 20 Hz only at −2.5 dBu. So at mic level an input transformer is essentially clean. The audible "iron" in real chains comes from **output transformers driven at line level near clipping** and from deliberately overdriven inputs.

### 6.3 DSP model A: flux-domain saturation (cheap, recommended)

Signal x[n] at the transformer, with 1.0 = full scale:

```
φ[n]   = c·φ[n−1] + (ω_ref/fs)·x[n]          # leaky integrator = flux; c = exp(−2π·f_leak/fs), f_leak ≈ 2 Hz
r[n]   = φ_sat·tanh(φ[n]/φ_sat) − φ[n]        # how much the core "falls short" of linear
y[n]   = x[n] + (fs/ω_ref)·(r[n] − r[n−1])    # differentiate back to voltage and add
y      = HPF_1st(y, f_L) → LPF_2nd(y, f_H, Q_H) # inductance HP + leakage/capacitance LP
```

I verified it numerically (`verify_models.py`). It gives **pure H3**, falling **12 dB per octave** of frequency, which is the "quarters per doubling" Whitlock describes. It rises 12 dB for every +6 dB of level. With ω_ref = 2π·20 Hz and φ_sat = 1, a peak amplitude of 0.2 gives H3 = −40 dB (1 %) at 20 Hz, −52 dB at 40 Hz and −64 dB at 80 Hz.

**Calibration to the JT-115K-E:** set the input scaling so that −2.5 dBu at 20 Hz gives H3 = −40 dB. Hysteresis (next section) adds extra low-level distortion that this model leaves out. That's why Jensen's 0.065 % is higher than this model predicts at low level (ESTIMATE).

Drive mapping: the Drive knob scales x before the model and the inverse after, so the level is unchanged and only the distortion grows.

### 6.4 DSP model B: Jiles–Atherton hysteresis (accurate, costly)

- Holters & Zölzer, DAFx-16: inductor/transformer model using the Jiles–Atherton magnetisation ODE in a circuit simulator, validated on hysteresis, saturation and a valve-amp output transformer [16].
- Chowdhury, DAFx-19: real-time Jiles–Atherton tape hysteresis solved with Runge–Kutta. It's open source (CHOW Tape Model), with RK2/RK4, Newton–Raphson and state-transition-network variants for speed [17].

Five J-A parameters (M_s, a, α, k, c) describe a core. Cost: about 4–10× a tanh per sample, plus oversampling (ESTIMATE). **Not worth it for a reverb return.** The low-level hysteresis distortion it adds sits around −60 to −70 dB on bass only, under the tail.

---

## 7. Preamps

### 7.1 Published behaviour

| Unit | Published figure | Source |
|---|---|---|
| AMS Neve 1073 | THD ≤ 0.07 % 50 Hz–10 kHz at **+20 dBu** output (600 Ω, 80 kHz BW); max output > +26 dBu; ±0.5 dB 20 Hz–20 kHz | [18] |
| API 512c (2520 op-amp, transformer output) | THD < 0.05 % at +4 dBu, < 0.1 % at +28 dBu; clip +30 dBu | [19] |
| UA LA-610 Mk II (valve), stock | < 0.1 % at +5 dBm, > 5 % at +15 dBm into 600 Ω; into 1.5 kΩ about 1 % (mainly H2) near +15 dBu; ECC82 mod: 1 % H2 at +20 dBu | [20] (independent bench test, medium confidence) |
| SSL VHD | The Drive control blends from mainly 2nd-harmonic to mainly 3rd-harmonic distortion | [21] |
| Hamm 1973 (JAES) | Clean in normal range ("all three amplifiers sounded very clean"); they differ only in the **early-overload** region. Triodes: H2 dominant, then H3, H4 3–4 dB later. Pentodes: H3 dominant, H2 about 3 dB later. Transistors/op-amps: strong H3, symmetric, near-square clipping | [22] |

**Neve 1073:** I found no credible public harmonic-by-harmonic measurement, only forum posts and unsourced web articles, which I didn't use. Its single-ended class-A transistor stages are asymmetric, so in theory they add H2 (ESTIMATE, following [13] and [22]). The output transformer adds H3 at low frequency.

**U47 (valve):** I found no published measurement of its harmonic signature. Not parametrised.

### 7.2 What "drive" does, step by step

1. At normal level every unit above is at or below 0.1 % THD, about −60 dB. That's inaudible under music and certainly under a reverb tail.
2. Turning up the input gain (and the output down to match) pushes peaks toward the stage's overload point.
3. Close to overload, the distortion rises quickly. Asymmetric stages (single-ended triode, class-A transistor) rise mostly in H2. Symmetric stages (push-pull, op-amp) rise mostly in H3 [22].
4. Past overload, all harmonics rise together and the waveform flattens. Transistors and op-amps hit a hard wall sooner [22].

### 7.3 DSP model C: asymmetric static waveshaper (recommended)

```
y = [tanh(a·(x + b)) − tanh(a·b)] / (a·sech²(a·b))   # zero output for zero input, unity small-signal gain
y = DCblock(y)                                        # 1st-order HP ≈ 5 Hz
```

Small-signal harmonic levels for a sine of peak A (derived by Taylor expansion, checked numerically to ±0.3 dB, ±1 dB at the extreme setting):
- **H2 / H1 ≈ a·tanh(a·b)·A / 2**
- **H3 / H1 ≈ a²·|1 − 3·tanh²(a·b)|·A² / 12**

So **b** (the bias) sets the H2/H3 balance: b = 0 gives pure odd harmonics, "solid-state". **a** sets how hard it bends. Examples from the numerical check: a=1, b=0.2, A=0.1 → H2 −40.2 dB, H3 −62.7 dB (valve-like); a=1, b=0, A=0.1 → H3 −61.6 dB only.

Presets that follow the published behaviour (ESTIMATE settings, PUBLISHED character):
- **Clean:** bypass.
- **Valve (triode, after Hamm):** b ≈ 0.2–0.3, so H2 is well ahead of H3.
- **Class-A solid state (1073-ish):** b ≈ 0.1 with a mild transformer model A after it.
- **Op-amp / API-ish:** b ≈ 0, slightly harder knee, with transformer model A after it.
- **VHD-style:** one knob morphs b from about 0.3 to 0, sweeping H2 → H3, as SSL describes [21].

**Pre/de-emphasis option:** put a gentle tilt before the shaper and its exact inverse after. Then the bass or treble distorts first, and the clean tone is unchanged.

**Anti-aliasing:** use first-order ADAA (Parker, Zavalishin & Le Bivic, DAFx-16 [23]): y[n] = (F(x[n]) − F(x[n−1])) / (x[n] − x[n−1]), where F is the antiderivative of the shaper; for tanh, F(u) = log cosh(u). Or use 2× oversampling. At the low drive a reverb needs, ADAA alone is enough (ESTIMATE).

---

## 8. Audibility on a reverb return, and what to build

| Item | Audible on a reverb return? | Build? |
|---|---|---|
| **Diffuse-field tail colour** | **Yes, clearly.** Differences between mics are 5–10 dB at 16 kHz and 2–4 dB in the bass (§2.5). This is the "LDC warm vs SDC open" room sound. | **Yes, rank 1.** One SOS per mic bus, from data we already have. |
| **On-axis response restored** (presence, air, LF) | Yes on direct and early sound (±1–4 dB). Little effect on the tail itself. | **Yes, with rank 1.** Small change, same fitter. |
| **Per-reflection off-axis colour** | Yes, and already shipping (`MEASURED_SHELF`). | Keep; resolve the R05 double-count check. |
| **Elevation (3-D) colour** | Moderate: floor and ceiling reflections on side-address LDCs. | Rank 3, needs 3-D data (DirPat [4]) or an assumed model. |
| **Transformer saturation (model A)** | Only when driven. At realistic levels it's −60 dB or lower, on bass only. Driven, it adds density and thickness to the low end. | **Rank 2, as part of the Colour module**, off by default. |
| **Valve / solid-state stage (model C)** | Only when driven. On a dense tail, H2/H3 mostly reads as slight density or grit, not "warmth" (ESTIMATE). | **Rank 2, same module**, one Drive knob, type selector. |
| **Hysteresis (Jiles–Atherton)** | No, not on a tail. | No. |
| **Diaphragm transient model** | Already inside the frequency response. | No. |
| **Self-noise** | No; would only add hiss. | No. |

**Where the Colour module goes (ESTIMATE, matching real signal flow):** after the mic colour and before the mix bus and limiter, on the wet returns only. Give it a gain-compensated Drive, so turning it up changes texture, not level. That keeps it compatible with Bloom, since Bloom works inside the reverb, before the mics. At Drive 0 or Type Clean it should be bit-exact bypass, so goldens don't move.

---

## 9. How this maps onto `apply_capsule_colour` (early_field.py, read-only review)

What it does today: it has no callers and is marked ASSUMED. It runs on the stereo wet signal after the IR:
1. an optional RBJ high-pass (`hp_hz`, the panel's High Pass)
2. an RBJ low-pass at `MIC_RES_HZ` (the "Mic Response", snapshot 10 kHz)
3. a low-shelf at 120 Hz of `proximity × (1 − a) × 6 dB` (more bass for more directional patterns).

How the research maps onto it:
- **Step 2 → replace with the measured diffuse-field EQ.** Instead of one assumed 10 kHz low-pass, use the per-preset SOS fit of the §2.5 curve. This becomes the function's real job: *the colour the mic gives the tail*. For unmeasured presets, use the first-order DI fallback (§2.6) plus a capsule-size HF shelf.
- **Step 3 → remove the proximity shelf from the tail.** Proximity effect only exists for near sources [1]. A diffuse tail has none. The real, measured low-end difference in the tail is the **double-diaphragm DI drop** (DI falls from about 5 dB at 1 kHz to about 3 dB at 125 Hz for U87, NT2-A, C414 and K2, against about 4.5 dB for the single-diaphragm Schoeps), and the diffuse EQ already contains it. The existing D-PROX shelf on near or direct sound is unaffected.
- **Step 1 (HP)** stays as is. It's the mic's own switchable low-cut, e.g. the U87's.
- **Argument changes (suggested):** `preset_id` (to look up the diffuse SOS), and `polar_a` only for the fallback. `polar_mean` and `proximity` are no longer used on the tail path.
- **Where it's called (suggested):** once per capsule bus on the FDN output (tail), replacing the per-line seed-angle colour for the tail, and crossfading with the per-tap early colour. Per HOOKS.md, colour must stay outside the Hadamard loop and off `inject`. A post-FDN-bus filter satisfies both.
- **Goldens:** any change to the tail colour moves every render, so it should sit behind a switch first, the same way SMALLDECAY and AMBIENCE do.

---

## 10. Caveats

- One unit per model. Production spread for LDCs can be ±1–2 dB in the top octave (ESTIMATE).
- Horizontal plane only. The diffuse average assumes rotational symmetry about the mic axis. For side-address LDCs at HF, the vertical-plane pattern differs, because the diaphragm is edge-on differently (ESTIMATE). Expect ±2–3 dB at 8–16 kHz from this.
- LF below about 125 Hz is window-limited. Above 16 kHz, off-axis data is sensitive to alignment.
- The diffuse-field calculation uses the **5 m** set. At 1.25 m, directional mics show a proximity bump below about 135 Hz [1].
- Measurement artefacts: the Sony C800 and DPA 4006 step rise times; possibly the R-121 16 kHz DI (1.9 dB).

---

## References

1. M. Schneider (Neumann), "Microphone Choice: Large or Small, Single or Double?", AES 128th Convention, London 2010. http://www2.users.ak.tu-berlin.de/akgroup/ak_pub/2010/Schneider_2010_AES2010_Large_and_Small.pdf
2. J. C. Franco Hernández, T. Brookes, E. De Sena, "A Multi-Angle, Multi-Distance Dataset of Microphone Impulse Responses", JAES 2022. doi:10.17743/jaes.2022.0027
3. Zenodo record 4633508 (CC-BY-4.0). https://zenodo.org/records/4633508
4. IEM Graz, DirPat database. https://opendata.iem.at/projects/dirpat/
5. D. Bock, "Microphones: Understanding Classic Condenser Microphone Capsules", Tape Op. https://drbraukmann.com/DESN275/275_New_Reading/Condenser_Microphone_Capsules.pdf
6. Røde NT2-A manual. https://edge.rode.com/pdf/products/73/nt2-a_product_manual.pdf
7. AKG C414 XLS/XLII manual. https://www.akg.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw0d863e9c/pdfs/AKG_C414XLS_C414XLII_Manual.pdf
8. Neumann U 87 Ai product page and manual. https://www.neumann.com/en-gb/products/microphones/u-87-ai
9. (a) Neumann U 47 fet. https://www.neumann.com/en-us/products/microphones/u-47-fet-i (b) Neumann KM 184. https://www.neumann.com/en-us/products/microphones/km-184-series-180/
10. First-order directivity, REE = a² + (1−a)²/3: standard textbook result, e.g. Boré & Peus, *Microphones* (Neumann, 1999), cited in [1]; also Eargle, *The Microphone Book*. The DI values were checked against the measured set in §2.3.
11. Audio-Technica AT4050 spec sheet. https://docs.audio-technica.com/us/p52150_at4050_spec_sheet.pdf
12. Royer R-121. https://royerlabs.com/r-121/
13. B. Whitlock, "Audio Transformers", *Handbook for Sound Engineers* 3rd ed. (Jensen). https://www.jensen-transformers.com/wp-content/uploads/2014/08/Audio-Transformers-Chapter.pdf
14. Jensen mic-input transformer table and JT-115K-E data sheet. https://www.jensen-transformers.com/transformers/mic-input/
15. CAPI EA2503 / API 2503 output transformer spec. https://www.capi-gear.com/catalog/images/gallery/2503/2503-specs.pdf
16. M. Holters, U. Zölzer, "Circuit Simulation with Inductors and Transformers Based on the Jiles-Atherton Model of Magnetization", DAFx-16. https://www.dafx.de/paper-archive/2016/dafxpapers/08-DAFx-16_paper_10-PN.pdf
17. J. Chowdhury, "Real-time Physical Modelling for Analog Tape Machines", DAFx-19. https://www.dafx.de/paper-archive/2019/DAFx2019_paper_3.pdf ; code https://github.com/jatinchowdhury18/AnalogTapeModel
18. AMS Neve 1073 specifications. https://www.ams-neve.com/outboard/1073-range/1073-mic-preamp-equaliser/
19. API 512c. https://apiaudio.com/product/512c-mic-pre/
20. B. Fox (Fox Audio Research), "LA-610 Mk II simple improvements" (bench measurements). https://www.foxaudioresearch.ca/LA610.htm
21. Sound On Sound review, SSL XLogic VHD Pre. https://www.soundonsound.com/reviews/ssl-xlogic-vhd-pre ; SSL VHD Pre module guide. https://solid-state-logic.co.jp/docs/VHD-Pre-Module-User-Guide.pdf
22. R. O. Hamm, "Tubes Versus Transistors — Is There an Audible Difference?", JAES 21(4), 1973. https://aes.org/e-lib/browse.cfm?elib=1980
23. J. Parker, V. Zavalishin, E. Le Bivic, "Reducing the Aliasing of Nonlinear Waveshaping Using Continuous-Time Convolution", DAFx-16. https://www.dafx.de/paper-archive/details/vem_XXF5qBbfiWOH2RVVAA
