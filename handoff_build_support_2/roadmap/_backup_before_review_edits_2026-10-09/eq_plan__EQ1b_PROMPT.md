# EQ-1b Build prompt: Movement knob + Render through the loop (paste in after EQ-1a is merged)

**Session EQ-1b (one session, self-contained).** **Baseline = the tree after EQ-1a**, with Smooth at whatever default EQ-1a shipped. Idle locked this on 4 Oct. Work in `software\`. First re-read the current code.

Reference in `handoff_build_support_2\roadmap\eq_plan\`:
- `EQ_PLAN.md` §4e/§4f
- `proto_mod\fdn_mod_proto.diff` (box Python prototype)
- `proto_mod\analyse2.py` (metrics)
- `proto_mod\proto_mod.json` (the mod10/mod15 sizes)

## Build
1. **Movement knob on the Room tab, default 0.**
   - 0 = off, shown as "Off". 0–50 % ramps the peak depth from 0 to 0.10 ms; 50–100 % ramps it from 0.10 to 0.15 ms.
   - Save it in presets; old presets load at 0.
2. **Frenette modulation, in one shared C implementation for Play (`live_stereo.c`) and Render:**
   - sine LFO, 0.7 Hz × per-line factor 0.6–1.4 (golden-ratio spread)
   - phases k·112.5°
   - **16 of 32 lines**: every other line by sorted delay, per bus
   - **first-order allpass read on the modulated lines only**: N = floor(D − 0.5), η = (1 − Δ)/(1 + Δ), coefficient updated every sample
   - mean delay unchanged
   - The LFO phase comes from an absolute sample counter starting at t = 0. Reset it at engine reset and at impulse or parity capture.
   - Unmodulated lines keep today's read.
3. **Render runs the dry signal through the loop when Movement > 0.**
   - Convolve each line's inject with the dry signal, then run the FDN loop, as the prototype does.
   - At Movement 0, keep the IR + `fft_convolve` path, byte-for-byte unchanged.
   - Report the Render time for a 12 s guitar at Movement 50 %.
4. **Forced off** in `reaktor_parity`, flat cards and the mirror/null test modes, whatever the UI says.

## Gates (report each with numbers)
- **G1 Bit-exact at Movement 0.**
  - Render and Play match the post-EQ-1a tree at max-abs 0 on the golden scenes.
  - Parity, flat and mirror modes are bit-identical at any Movement setting.
  - **No golden changes at all.**
- **G2 CPU (paired t19, 12-round pair, PC).**
  - Shared-off ≤ 2.40 ms and shared-on ≤ 2.133 ms, measured at Movement 0 and at 100 %.
  - Report the deltas against post-EQ-1a.
- **G3 Movement, statistical** (default room, Render through the loop, compared with Movement 0 at the same Smooth state):
  - Late-tail peakiness (method as `analyse2.py`) ≥ 0.5 dB lower at 50 % and ≥ 0.7 dB lower at 100 %.
  - Wobble on a sustained 440 Hz tone: p95 ≤ 1.0 cent at 100 %.
  - Octave T30 at 125 Hz–8 kHz within ±5 %.
  - Two identical Renders are bit-identical.
- **G4 Play vs Render at 50 %.**
  - Third-octave tail level within ±1 dB at 200 Hz–8 kHz.
  - Peakiness within ±0.3 dB.
  - Report the t18-style null.
- **G5 Existing tests.**
  - t18 at defaults (Movement 0) unchanged from post-EQ-1a.
  - `test_mirror_exact` ≤ −120 dB.
  - All other tests pass.

## Stop rule
If G2, G3 or G4 can't pass, ship with **the Movement knob hidden and forced to 0**. The engine code can stay, but it must not be reachable. G1 and G5 must then pass, so the software behaves exactly as after EQ-1a. Report what blocked it. The software must build, run and pass the tests at the end of the session.

## Out of scope
D-INT (44.1 kHz interpolation), resonance control, the Output strip, Idle's lean convolution plugin mode, and delay changes.

## Report back (short)
- A gate table with numbers.
- Files changed.
- Render time.
- Three loudness-matched default-room guitar renders at Movement 0 / 50 / 100 % in `handoff_build_support_2\roadmap\eq_plan\eq1_out\`.
