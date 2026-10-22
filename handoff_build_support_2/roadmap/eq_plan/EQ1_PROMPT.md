> **SUPERSEDED (4 Oct, 11:00): split into `EQ1a_PROMPT.md` (Smooth) and `EQ1b_PROMPT.md` (Movement). Do not paste this file.**

# EQ-1 Build prompt: Smooth + Movement (paste into Build after S-AUDIT is merged)

**Session EQ-1 (one session).** Idle locked this on 4 Oct. Work in `software\`. First re-read the current code: the line numbers below come from the 18:29 audit copy and may have moved. Reference material is in `handoff_build_support_2\roadmap\eq_plan\`:
- `EQ_PLAN.md` §4e/§4f
- `proto_mod\fdn_mod_proto.diff`: box Python prototype, reference only
- `proto_mod\analyse2.py`: the metrics
- `proto_mod\proto_mod.json`: expected sizes

## What to build
1. **Smooth (switch, default ON).**
   - Cap the diffuser gain at |Dffs| ≤ 0.7, at the single place where Dffs is made (`tap_dff` results in `render_pipeline.py`, used by both the offline FDN and `live_fdn_params`). Play and Render then get identical values from one source.
   - **Decay correction.** In the prototype the uncorrected cap lengthened T30 by +4–8 % at 63–500 Hz, with HF unchanged. Make T30 meet gate G2.
   - The correction must be computed, not hand-tuned per room. The likely cause is that the diffuser allpass group delay changes the effective loop time, so fold it into the existing per-line decay lock (`lg`) or another existing per-line coefficient.
   - Add no new in-loop filter slot unless G3 still passes. If neither works, stop and report.
   - Smooth off must be today's engine, bit-exact.
2. **Movement (knob on the Room tab, default 0).**
   - Mapping: 0 = off; 0–50 % ramps the peak depth from 0 to 0.10 ms; 50–100 % ramps it from 0.10 to 0.15 ms.
   - Frenette set:
     - sine LFO, 0.7 Hz × per-line factor 0.6–1.4 (golden-ratio spread)
     - phases k·112.5°
     - **16 of 32 lines**: every other line by sorted delay, per bus
     - **first-order allpass read on the modulated lines only**: N = floor(D − 0.5), η = (1 − Δ)/(1 + Δ), coefficient updated every sample
     - mean delay unchanged
   - One shared C implementation for Play (`live_stereo.c`) and Render.
   - The LFO phase comes from an absolute sample counter starting at t = 0. Reset it at engine reset and at impulse or parity capture, so Render is deterministic.
3. **Render runs the dry signal through the loop when Movement > 0.**
   - Convolve each line's inject with the dry signal, then run the FDN loop, as the prototype does.
   - At Movement 0, keep today's IR + `fft_convolve` path unchanged.
   - Report the Render time for a 12 s guitar at Movement > 0.
4. **Forced off:** both Smooth and Movement in `reaktor_parity`, flat cards and the mirror/null test modes, whatever the UI says.
5. **UI.**
   - Movement knob on the Room tab, showing "Off" at 0.
   - Smooth switch next to Decay on the Room tab. That placement is ASSUMED, so keep it easy to move.
   - Both are saved in presets. Old presets load with Smooth ON and Movement 0.

## Gates (all must pass; report each with numbers)
- **G1 Bit-exact off.**
  - With Smooth off and Movement 0: Render and Play outputs match the pre-session tree at max-abs 0 on the existing golden scenes.
  - Parity, flat and mirror modes are bit-identical to pre-session for any Smooth or Movement setting.
- **G2 Decay (Smooth on).**
  - Rooms: default, box (3 × 2.4 × 4 m, Decay 0.8 s) and one carpet room.
  - Octave T30 at 125 Hz–8 kHz is within ±5 % of Smooth off, which equals within 5 % of the Decay setting wherever today's engine already meets the dial. Report 63 Hz too.
  - Mid T30 (500 Hz–1 kHz) is within ±5 % of the Decay setting.
- **G3 CPU (paired t19, 12-round pair, PC).**
  - Shared-off ≤ 2.40 ms and shared-on ≤ 2.133 ms.
  - Measure with Smooth on at Movement 0 and at Movement 100 %.
  - Report the deltas against pre-session.
- **G4 Movement, statistical** (default room, Render through the loop, same Smooth state as the reference, compared with Movement 0):
  - Late-tail peakiness (method as `analyse2.py`): ≥ 0.5 dB lower at 50 % and ≥ 0.7 dB lower at 100 %. Prototype: −0.70 and −0.93.
  - Wobble on a sustained 440 Hz tone: p95 ≤ 1.0 cent at 100 %. Prototype: 0.55.
  - Octave T30 within ±5 % of Movement 0.
  - Two identical Renders are bit-identical.
  - Play capture against Render at 50 %: third-octave tail level within ±1 dB at 200 Hz–8 kHz and peakiness within ±0.3 dB. Also report the t18-style null.
- **G5 Goldens.**
  - Regenerate **only** the goldens whose diff comes from Smooth defaulting to ON, with the reason "EQ-1: Smooth default ON (Dffs cap 0.7 + decay correction)".
  - Each regenerated scene, rendered with Smooth off, must still match its old golden bit-exactly.
  - Any other golden change is a fail.
- **G6 Existing tests.**
  - t18 parity at defaults (Smooth on) ≤ −60 dB, target the current −71.8 dB.
  - `test_mirror_exact` ≤ −120 dB.
  - All other tests pass.

## Out of scope
D-INT (44.1 kHz linear-interpolation fix), resonance control, the Output strip and Auto level, the lean convolution plugin mode, and any change to delays (the uniquify lock stands).

## Report back (short)
- A gate table with numbers.
- Files changed.
- The correction method used.
- Render time at Movement > 0.
- Four loudness-matched default-room guitar renders for Idle, placed in `handoff_build_support_2\roadmap\eq_plan\eq1_out\`:
  - Smooth off / on at Movement 0
  - Smooth on at Movement 50 % and at 100 %
