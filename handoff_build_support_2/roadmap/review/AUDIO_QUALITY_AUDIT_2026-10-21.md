# Audio quality audit (2026-10-21)

Read-only review. No code, goldens or binaries were changed and pytest was not run. Line numbers are for the tree at the PERROOMK pin (BLOOM retry not landed). "UNVERIFIED" marks claims based on reading code, not measurement.

## Summary

| Worry | Verdict |
|---|---|
| 1. Number precision / float-int noise | **Fine.** Everything runs in float64 (Render) or double maths with float32 storage (Play). The only integer steps are WAV in and WAV out, both done correctly. |
| 2. Aliasing | **Fine now, with one small risk.** The current engine is linear except the output safety limiter. BLOOM is where aliasing matters, and the retry gates it. |
| 3. Zipper noise | **Mostly fine; a few things jump.** Level, pan, makeup, delay and mic moves are smoothed. Decay, Surfaces filter and some structure changes swap instantly while the tail rings. |
| 4. Compressor lifting quiet tails | **Fine (non-issue in practice).** Floating-point noise scales with the signal, so turning a reflection down by distance doesn't move it closer to any noise floor. The worst lift is far below the headroom. |

No new real bugs. Only lower-priority risks (see the end).

---

## 1. Number precision and noise. Verdict: FINE

**The idea in plain words.** With integers (fixed point), a quiet signal sits closer to a fixed noise floor. With floating point, rounding error is always a tiny fraction of the signal itself: about -313 dB for float64 and about -144 dB for float32, per operation. The program converts to integers only at the two ends.

- **WAV in.** 16-bit is divided by 32768, 24-bit is sign-extended and divided by 2^23, and 32-bit is divided by 2^31. All of these go straight to float64 (`render_pipeline.py:206-230`). These are exact conversions, with no added noise. Float WAVs (format 3) are refused by Python's `wave` module rather than misread (`render_pipeline.py:223` comment). That's fine.
- **Render maths.** float64 throughout (`render_pipeline.py:203`, `hann_window` `:328-331`, `surface_colour.py:829`). Some filter coefficients are deliberately rounded to float32 (`render_pipeline.py:1093-1098`, `surface_colour.py:753-754`, `engine\fdn.py:613`). This is so Render and Play use the *same* filter. It changes the filter shape by a tiny fixed amount but adds no noise.
- **WAV out (Render).** 24-bit PCM, rounded to nearest, **no dither**, hard clip at ±1 (`render_pipeline.py:305-325`). The rounding floor is about -144 dBFS. Without dither, the last bits of a fading tail turn into very low-level distortion instead of hiss, at around -140 dBFS, which is far below hearing.
  - Fix (optional, cosmetic): add TPDF dither of ±1 LSB before `np.rint` at `:317`.
- **Old 16-bit writers.** `engine\early_field.py:2450-2451`, `engine\fdn.py:1360-1361` and `moving_room_demo.py:108` use `astype("<i2")`, which truncates rather than rounds, with no dither. That's about -96 dBFS with a small bias. UNVERIFIED whether the app still uses them; they look like legacy/demo paths. The app's Render goes through `write_wav_stereo` (24-bit).
  - Fix: route them through the 24-bit writer, or add `np.rint`.
- **Play (live_stereo.c).** Maths runs in `double`. Delay-line storage, FFT convolution buffers and audio I/O are `float` (`live_stereo.c:444-456`, `:978-993`; writes like `write_lane(..., (float)(mixed + gi*y))` at `:2656`, `:2757`, `:2824`; `out[i] = (float)buf[i]` at `:2986`). So each pass round the tank adds float32 rounding at about -144 dB relative to the signal. Even after hundreds of recirculations, uncorrelated rounding builds up only to roughly -120 to -130 dB relative (UNVERIFIED estimate), which is inaudible.
- **Browser boundary.** Web Audio is float32 by design. The worklet passes float32 in and out, and loads the Surfaces sections as Float64 (`static\js\fdn_worklet.js:146-180`). There is no int16 step anywhere in Play.
- **Denormals (very tiny numbers that slow the CPU, not a noise issue).** The Surfaces cascades flush states below 1e-20 (`live_stereo.c:128`, `:596-621`). The tank adds a 1e-18 offset after the excitation (`:129`, `:2520`). `sub_apply` (`:2506-2513`) has no flush of its own.
  - My reading: the tank keeps the 1e-18 offset circulating, so the low-cut's input is never exactly zero and its states sit near 1e-18, far above the denormal range (about 1e-308 for double). So the earlier review's slowdown risk is probably not triggered in practice. UNVERIFIED (not measured).
  - Fix: add the same `LS_TINY` flush to `z1`/`z2` anyway. It's 2 lines and costs nothing.

## 2. Aliasing. Verdict: FINE now, small risk at the limiter

**The idea in plain words.** Aliasing only comes from *non-linear* stages: anything that bends the waveform (clip, saturate, compress fast). Filters, delays, EQ, gains and convolution can't alias.

- **Mic models.** The mic models are linear: polar patterns and fitted EQ (`engine\mic_pattern.py`, `mic_colour\`). No tanh, clip or saturation was found outside BLOOM and the limiter. So they can't alias, and they add no distortion.
- **Preamps (610-A, Neve).** These exist only in BLOOM. They are not in Play or Render today.
- **Output limiter (Render and Play).** It's the same per-sample soft knee: untouched below 0.95 (-0.45 dBFS), then a tanh curve to 0.999 (`render_pipeline.py:415-425`, `live_stereo.c:520-528`). It runs at 1x, with **no oversampling and no true-peak detection**. It only bends the signal when a peak goes over -0.45 dBFS, and the app reports when that happens (`render_pipeline.py:428-431`, `live_stereo.c:534-544`).
  - Risk (low): if you drive into it, it can alias a little on those few samples. Inter-sample peaks can still go slightly over 0 dBFS after a DAC.
  - Fix: either leave it as a "safety only" limiter and keep mix peaks under about -1 dBFS, or later oversample it 4x and add a true-peak meter.
- **BLOOM (pending retry).**
  - The planned oversampling is in the leftover code: Room Crush 1x, Glue and Nuke with ADAA at 1x, Natural and Swell 2x (`engine\bloom_dsp.py:634`), and 610-A and Neve 8x via a cascaded half-band (`:691-729`, `:1011-1061`).
  - The gate is "each alias image no worse than the UAD's worst image in dBc, +0.5 dB tolerance". So BLOOM will be at least as clean as the plug-ins Idle is matching. That standard is sensible.
  - Room Crush at 1x with no ADAA is the most alias-prone choice. It's acceptable only because the gate measures it against the UAD. If it fails the gate in the retry, the cheap fix is ADAA1, as Glue and Nuke use.
  - BLOOM affects the tail only, and on a dense reverb tail alias products are heavily masked.

## 3. Zipper noise. Verdict: MOSTLY FINE; some coefficient jumps

**Smoothed (no zipper):**
- **Desk gains.** FDN, direct, early and dry levels, room makeup, and the six speaker/pan weights: 10 ms linear ramps (`live_stereo.c:116-123`, `:325-333`, `:3048-3100`). The first load snaps (`:3084-3088`), which is correct.
- **Delay times.** Delay times and direct-path delays glide with a one-pole at 0.0025 per sample, about an 8 ms time constant (`live_stereo.c:127`, `:2536-2552`). A big move gives a short pitch glide, not a click.
- **Mic proximity/move gains.** A 15 ms ramp (`live_stereo.c:2453-2498`). This matches the 15 ms decision.
- **Mute.** The tank keeps running and the output gain ramps (`live_stereo.c:1353-1354`).

**Jumps without smoothing (could tick while a tail is ringing):**
- **Decay (`g`).** The global and per-line feedback values are set directly on blob load (`live_stereo.c:1226`, `:1417`). No ramp was found (UNVERIFIED by listening). Gain steps inside a feedback loop are usually soft, but a large dial jump can give a small step.
- **Surfaces filter coefficients.** The per-line biquad cascades are overwritten in place on reload (`live_stereo.c:1459-1501`), while the states keep running. In a recirculating loop this can give a small tick (UNVERIFIED by listening).
- **Sub low-cut coefficients.** Overwritten in place (`live_stereo.c:1805-1813`). The earlier review already flagged a possible click when it is switched back on.
- **FDN order change.** Changing the FDN order cuts the whole tail on purpose (`live_stereo.c:1355`). Changing the shared-option/delay set also does (`:1605-1612`). These are deliberate hard cuts, not zipper noise, but they are audible.
- **Room switch / IR swap.** Partition buffers are zeroed and restarted cold (`live_stereo.c:1820-1830`, `:2903`, `:3482`, `:3501`). No crossfade was found between the old and new room (UNVERIFIED).

**Fixes, in order of value:**
1. Ramp `g` over about 10-20 ms. It's the same pattern as `arm_ramps`.
2. For Surfaces and low-cut coefficients, either interpolate the coefficients over about 10 ms, or run old and new filters in parallel for one block and crossfade.
3. A short (20-50 ms) crossfade on room switch and order change, instead of a hard cut.

## 4. A compressor lifting a quiet reflection or tail back up. Verdict: FINE (non-issue in practice)

**Your example.** A far reflection is turned down by distance (1/r, so 20 m is -26 dB against 1 m), then BLOOM's makeup brings it back up. Does that also lift noise?

**Short answer: it lifts only what is really in the audio, not the maths.**

- **Rounding noise rides with the signal.** In floating point, rounding noise is a fixed *fraction* of the signal: about -313 dB for float64 and about -144 dB for float32 (see 1). Turning a reflection down by 26 dB turns its rounding noise down by 26 dB too. Lifting it back by 26 dB brings both back together, so the ratio never changes. Fixed-point gear would behave worse here; this program doesn't use it inside.
- **Fixed tiny values.** The anti-denormal offset is 1e-18 (-360 dBFS, `live_stereo.c:129`) and the flush threshold is 1e-20 (-400 dBFS, `:128`).
  - Worst lift: the largest room makeup seen is Hall at +36 dB over boot (`faults_1009\INVESTIGATION_REPORT.md:97`). BLOOM's net boost is capped at +Amount dB. The bloom law clamps the wet gain to between -MaxDuck and +Amount (`compressor_presets.json` "bloom_law"; `bloom_dsp.py:119`). Amount is at most 12 dB (Nuke `amount_cap_db`, `compressor_presets.json:729`). The other defaults are 3-10 dB (`:135`, `:449`, `:600`, `:936`).
  - So the total worst case is about +48 dB. That puts these values at about -312 dBFS, still about 170 dB below the 24-bit output floor (-144 dBFS). Non-issue.
- **Inside BLOOM.** The new order is: pre-gain `10^(-GR/20)`, colour (oversample, shaper, decimate), then makeup `10^((W+GR)/20)`. The makeup stage alone can be large: about 30x (+29.7 dB) for Room Crush and 7.7x (+17.7 dB) for Nuke on test tones (last Build report). It does lift the colour stage's own residue (alias images and filter rounding) by that amount. That is exactly why the alias gate is measured **at BLOOM's output in dBc against the UAD**, so the lift is already counted. float64 rounding lifted by 30 dB is still about -280 dB.
- **What can really come up.** The source recording's own noise (for example tape hiss, or the -96 dB floor of a 16-bit file). It is part of the signal, so the tail lifts it like any compressor would. BLOOM's detector is keyed on the dry signal, so the tail gets the most lift when the dry stops: that is the "bloom". With a noisy source that could make hiss swell in the tail. Fix if heard: lower Amount, or add an optional expander/gate on the wet below about -70 dBFS (backlog idea).
- **Makeup frozen vs. distance.**
  - The **room** makeup is frozen at the stand (D-MAKEUP-FREEZE, `render_pipeline.py:1397` `makeup_at_stand`). It drops the mic positions before computing makeup (HANDOVER notes `overnight\_pre_BLOOM\HANDOVER.md:165`). The boot offset comes from the placed stand (D-SRC-DIST-LEVEL, `BUILD_RUN_LOG.md:36`). So moving a source or mic further away does **not** raise makeup. The distance drop stays real. Play applies that single makeup value through the ramped `RG_MK` gain (`live_stereo.c:1231`, `:3055`, `:3319`, `:3412`, `:3430-3431`).
  - BLOOM's makeup comes from preset W and the fitted GR, not from distance (no distance terms in `bloom_dsp.py`/`bloom_live.inc`). It is pending, because the retry has not landed.

## Real bugs found

None new. Lower-priority items:
1. `sub_apply` lacks a denormal flush (`live_stereo.c:2506-2513`). It's probably harmless because of the 1e-18 offset, but it's a cheap fix.
2. There are no ramps on decay `g` or on Surfaces and low-cut coefficient swaps, so these could tick on edits.
3. Room switch and order change cut the tail hard.
4. The output limiter is 1x, not true-peak.
5. The legacy 16-bit writers truncate.
6. Render's 24-bit output is undithered. That's cosmetic only.

Suggested measurement (one small Build task later): render a -60 dBFS sine through Hall plus +12 dB makeup, and check that the noise floor in the gaps is below -140 dBFS. Then sweep the decay dial live and listen or measure for steps.
