# Chapter 13: Per-room decay, the T20 ruler, BLOOM and Character

> Change note 2026-10-20: new chapter. It covers what was locked between 19 and 20 Oct 2026: per-room k, the F9 T20 ruler notes, the BLOOM design (the retry is still pending), and the planned Character control. The sources are the decision and run files in `roadmap\` named below. I have added no measurements beyond the ones in those files.

> **Status: PARTIAL (draft 2026-10-20).** Per-room k and the T20 ruler are **built**. BLOOM is **designed but not in the program**, because the retry is pending. Character is **planned only**.

**Chapter purpose.** The first twelve chapters describe the room. This chapter covers the two things that decide how the room *feels*: how long it rings in each room (per-room k), and the colour that can be laid on top of the tail (BLOOM, and later the Character control). It also explains one measuring fix (the T20 ruler), so that later numbers are read correctly.

---

## 13.1 Per-room k: the dial means the same thing in every room (BUILT)

**Before.** With physics on, the decay dial was turned into a loss setting called *k*. That k was solved once, on the boot room (6 × 3 × 8 m with the default walls), and then used in every room. In a small room that was fine. In the hall (57 × 34.2 × 97 m) the same k made the mids ring far longer than the dial said. At dial 8, the hall mids rang for about 37 s (fault F14, `roadmap\OPEN_FAULTS_2026-10-18.md`).

**The decision (Idle, 2026-10-19).** k is now solved for each room (`k_for_room` in `software\engine\surf_loop.py`). **The dial sets the mid decay in every room.** The physics of the walls and air shapes only the lows and the highs around it (`roadmap\DECISION_PER_ROOM_K_2026-10-19.md`).

**Result (VERIFIED, PERROOMK run, closed 2026-10-20).** At dial 8, the hall went from about 37 s to about 8 s in the mids. The fault entry gives about 9.49 s at 500 Hz and 7.06 s at 1 kHz. Play and Render agreed at 8.123 s for one source and 7.966 s for two. The boot room stayed bit-exact. CPU did not change, and `WORKLET_VER` stayed 59. The listening pair is `roadmap\perroomk\listen\hall_d8_before.wav` and `hall_d8_after.wav`.

> **In plain English.** The decay knob used to be calibrated in one small room. A bigger room took the same setting and rang far too long, a bit like using one oven temperature for every size of cake. Now each room works out its own setting, so "8 seconds" means about 8 seconds in the middle of the sound, whatever the room. The walls still decide whether the bass hangs on a little longer or the top dies away a little sooner.

## 13.2 The T20 ruler (F9 notes; measurement fix, NO SOUND CHANGE)

**What looked wrong.** On 18 Oct the physics path seemed to decay about 20 % long from 500 Hz up and about 12 % short at 125 Hz (F9).

**What was really wrong.** The ruler, not the reverb. The old measurement added the two channels together before filtering into bands. The corrected method filters each channel first and then adds the energies. The proper ruler now lives in `ambience\make_listens.py`. The corrected boot-room T20 is 1.9378 / 2.3200 / 2.3160 / 1.9902 / 1.5721 / 1.1137 / 0.8487 s from 63 Hz to 4 kHz (VERIFIED, F9 closed 2026-10-19). The F9 notes run landed with 156 pytest passes.

> **In plain English.** We thought the room was ringing at the wrong lengths. It turned out the stopwatch was being read wrongly. Once it was fixed, the room was where it should be. Nothing about the sound changed, but every decay figure from now on uses the fixed method.

## 13.3 BLOOM: compressor and preamp colour on the tail (DESIGNED, RETRY PENDING)

**What it is.** BLOOM adds the character of analogue gear (compressors and preamps) to the **reverb tail only**. The direct sound and the early reflections stay clean. It sits on a switch, and when it is off the program is bit-exact with today.

**Presets (locked).** Room Crush, Glue, Nuke, Natural, Swell, 610-A and Neve. Idle allowed the hard-clip preamp models inside BLOOM: 610-A uses the nclip shaper with flux, and Neve has flux, emphasis and memory.

**Order of operations (locked 2026-10-20).** For the compressor presets:
1. gain reduction is applied (the compressor turns the tail down),
2. **then the colour**: oversample, shape, decimate, then a memory low-pass and a DC block,
3. **then the makeup** gain,
4. **then the EQ** (eq_fit).

Swell has no compressor stage. It is colour, then makeup, then EQ. The first overnight attempt put the colour *after* the makeup, so the shaper was driven far too hard and 47 of 80 alias rows failed. Colour before makeup is the fix.

**Oversampling (locked).** Room Crush 1×. Glue and Nuke use ADAA1 (anti-derivative anti-aliasing instead of oversampling). Natural and Swell 2×. 610-A and Neve 8×. Neve at 16× cost 2.934 ms, over the CPU limit, so it stays at 8×.

**Alias gate (locked).** No aliasing image may be worse than the UAD reference's worst image, measured in dBc (relative to the tone), with a 0.5 dB tolerance and the current oversampling. An absolute dBc floor was tried first and failed even on the prototype, so the gate compares against the UAD instead.

**Sidechain low-cut (locked after a stop).** The compressor's detector ignores deep bass through a 100 Hz high-pass. In the retry, Nuke missed the level gate (RT-2) by **+0.057 dB** at −12, −6 and 0 dBFS, against a 0.05 dB limit. The cause: our high-pass was a simple "signal minus low-pass", while the prototype uses a **first-order Butterworth**. They differ by about 0.058 dB at 7 kHz. Idle decided that Render and Play must use the prototype's first-order Butterworth. Build checks Nuke at 7 kHz to within 0.005 dB before the full gate. Room Crush (which has no sidechain high-pass) matched at 0.0000 dB.

**Status.** Not in the program. The retry restored the tree from the preBLOOMRETRY backup after the RT-2 stop. The current pin is still PERROOMK. The retry prompt (`roadmap\thursday_prompts\BLOOM_RETRY_2026-10-20.md`) now carries the Butterworth decision, and the retry runs from Phase 0 again.

> **In plain English.** BLOOM is the "warmth" box. It squeezes and colours only the reverb's tail, the way a tape machine or a vintage preamp would, while the room itself stays honest. The colour has to go on before the level is brought back up, or the colour stage gets hit much too hard and starts adding grit we don't want. The last attempt was stopped by a difference of six hundredths of a decibel, too small to hear, because the rule is to match the reference exactly before anything is tuned by ear.

## 13.4 Character: from a placement room to a warm chamber (PLANNED)

**The idea (Idle, 2026-10-20).** One **Character** control on the main page. At one end is a natural placement room: clear early reflections and an honest decay, which is what you hear today. At the other end is a beautiful, warm analogue chamber. Idle chose this in place of a "2011 sound" dial.

**What it would move.** Character is not a new effect. It moves settings that already exist or are planned, in three places at once:
- **Surfaces**: harder, smoother walls for a brighter, ringing chamber, or softer ones for a warmer, drier room.
- **The engine**: the density and smoothness of the tail, and **Movement**, the slow motion in the tail that makes a chamber sound lush.
- **BLOOM**: more analogue colour towards the chamber end.

Each part would still be adjustable by hand.

**Built today.** Surfaces, Smooth and the decay dial. Movement's code is in the program but **forced off** (`MOVEMENT_FORCED_OFF = True`, `software\render_pipeline.py` line 812) in both Play and Render, because at full depth Play measured 2.718 ms against a 2.40 ms CPU limit. Render has no CPU limit, so Movement could come to Render first, the way shaped rooms are planned. **Planned:** BLOOM (13.3), turning Movement on, and the Character control itself. It is in the ideas backlog, scheduled after BLOOM.

> **In plain English.** Think of Character as one knob that walks you from "a good room to record a guitar in" to "a gorgeous echo chamber". Turning it doesn't add a new effect. It turns several existing ones together: the walls, the thickness and slow shimmer of the tail, and the analogue warmth.
