# Demo: "virtual speakers are virtual omni mics" (rough, 7 Oct 2026)

A quick listening test of the Chapter 11 idea. **It was built with a small stand-in room model, not the real 2011 Room Reverb engine.** Nothing in `software\` was touched.

## The files
| File | What it is |
|---|---|
| `blind_X.wav`, `blind_Y.wav`, `blind_Z.wav` | **Listen to these first.** They are A, B and C in a random order. |
| `BLIND_KEY_dont_peek.txt` | Which blind file is which. Open it only after you've scored them. |
| `demo_A_binaural.wav` | A: one binaural "head" at the listener, i.e. today's kind of binaural render. |
| `demo_B_omni_at_speakers.wav` | B: 5 omni mics on a 2 m circle at the 5.0 speaker angles (0, ±30, ±110°). Each mic feeds a virtual speaker at its own angle. The speakers are dry (no room) and go to your ears through HRTFs. |
| `demo_C_omni_cube.wav` | C: same as B, but the 5 mics sit on a small array about 1 m across (0.5 m radius, 2L-cube style). The speakers stay at the 5.0 angles. |
| `IR_A/B/C_*.wav` | The stereo impulse responses (48 kHz, 24-bit). You can load them into any convolution plugin and try your own material. |
| `plan_view.png` | Room plan showing source, listener, B mics/speakers and C mics. |
| `checks.json` | The measured numbers below. |
| `make_demo.py` | The script that made all of this. It's reproducible. |

All audio is 48 kHz, 24-bit stereo and about 14 s long (12.5 s of the project's own `dry_test_48k.wav` plus the tail).

## How to listen
1. Use headphones, at a fixed comfortable volume.
2. Play X, Y and Z blind. Switch between them as often as you like.
3. Score each one 1–5 on the sheet below.
4. Then open the key and listen again knowing which is which.

| | X | Y | Z |
|---|---|---|---|
| Outside the head (externalisation) | | | |
| Envelopment (the room around you) | | | |
| Direction and width (source sits front-left, clear and the right size) | | | |
| Depth (source feels about 2.5 m away) | | | |
| Colouration / comb filtering (5 = clean) | | | |
| Tail smoothness (5 = smooth, no flutter or phasiness) | | | |
| Overall | | | |

**Head-turn stability can't be tested here.** There's no head tracking, so the sound turns with your head. That is a known reason binaural can sound "inside the head".

Pass rule from the research: B or C has to beat A on envelopment **without** losing direction.

## The setup
- **Room:** 6 m wide × 8 m long × 3 m high. Walls and ceiling are plaster (absorption 0.06), the floor is parquet (0.10). One absorption value per surface, the same at all frequencies. Sabine RT60 is about **1.58 s**. That's fairly live, because the values are bare-plaster ones and there's no furniture. (ASSUMED values, not the project's Surfaces material tables.)
- **Positions:** listener at (3, 3, 1.2) m, facing the long way. Source 2.5 m away, 30° to the left.
- **Early part (first 80 ms):** a shoebox image-source model, order 5 (1,848 images). Reflections are frequency-flat, with 1/distance level and true delay to each mic.
- **Late tail:** for each mic, an independent noise burst in three bands that decays exponentially to match the RT (highs die faster). It fades in after 80 ms.
  - For A, the tail comes from 24 random directions, each with its own noise, all rendered through the HRTFs. That is a fair diffuse tail, not a mono one.
  - For B and C, each mic gets its own noise seed, so the five tails are decorrelated.
- **HRTFs:** the project's own vendored table `SADIE2_KEMAR` (48 kHz SOS fit, 60 directions, nearest node, Apache-2.0 per the file). The fit only models the frequency balance, so I added time differences between the ears with a simple spherical-head formula (head radius 9 cm). (VERIFIED: the file and licence are as stated. ASSUMED: that this is a fair stand-in for the full HRIRs.)
- **Loudness match:** all three clips were set to the same RMS (−26.0 dBFS, both channels together), then one common gain was applied. Plain RMS, not LUFS.

## Sanity checks (VERIFIED, measured from the files)
| | A binaural | B omni at speakers | C omni cube |
|---|---|---|---|
| RMS (dBFS) | −26.02 | −26.02 | −26.02 |
| Peak (dBFS) | −2.2 | −2.4 | −2.2 |
| Tail L/R correlation, broadband, after 150 ms | 0.08 | 0.18 | 0.19 |
| Tail L/R correlation, 200–1000 Hz | 0.21 | 0.17 | 0.10 |
| L−R level, first 4 ms of the sound (front-left source, should be > 0) | **+8.3 dB** | +3.8 dB | +0.3 dB |
| L−R level, first 50 ms | +1.5 dB | +1.3 dB | +0.1 dB |

- **No clipping.** All peaks are below −2 dBFS.
- **Loudness match within 0.01 dB** (target was 0.5 dB).
- **Correlation: the test came out mixed, so don't read it as "decorrelation worked".**
  - In the 200–1000 Hz band, B and C are lower than A, as hoped.
  - Broadband, B and C are slightly *higher* than A. The reason is that A's tail is already a properly diffuse binaural tail with very low correlation, not a mono tail. In ears terms, all three tails are well decorrelated.
- **Left/right balance: the useful finding.** The very first sound arrives clearly on the left in A (+8 dB) and a bit less in B (+4 dB). In C it is almost centred (+0.3 dB). With closely spaced omnis, all five mics hear nearly the same direct sound, so it plays out of all five speakers almost equally. That predicts C will sound wide and enveloping but with a vague direction. It matches the research: spaced omnis give a good room but weak images, and real 2L-cube recordings rely on spacing, timing and often directional mics.

## What's simplified compared with the real engine (ASSUMED to matter)
- This is not the project's Render engine. There's no FDN, no Surfaces materials, no air absorption and no mic colour. The reflections are flat with frequency and the tail is shaped noise.
- The HRTFs are a nearest-node magnitude fit plus a modelled ear-time difference, not the measured full HRIRs.
- Everything is in one horizontal plane, with no height speakers (5.0 only).
- The virtual speakers are dry. There is no second "listening room", which avoids the room-doubling problem on purpose.

## What this demo cannot tell us
- Whether the real engine would behave the same way.
- How it holds up when you turn your head (no tracking).
- Whether 7.1.4 (with height) beats 5.0.
- Whether it works on loudspeakers rather than headphones.
- How the best mic spacing for C changes with room size.

One person's blind scores on one room are a hint, not proof.
