# EQ-1a Build prompt: Smooth switch (paste into Build after S-AUDIT is merged)

**Session EQ-1a (one session, self-contained).** Idle locked this on 4 Oct. Work in `software\`. First re-read the current code, because line numbers in the notes may have moved. Reference: `handoff_build_support_2\roadmap\eq_plan\EQ_PLAN.md` §4e/§4f, and `proto_mod\` (box prototype: `fdn_mod_proto.diff`, metrics `analyse2.py`, sizes `proto_mod.json`; the "dcap" variant is this feature).

## Build
1. **Smooth = diffuser gain cap |Dffs| ≤ 0.7, default ON.**
   - Apply it where Dffs is made (the `tap_dff` results in `render_pipeline.py`, used by both the offline FDN and `live_fdn_params`). Play and Render then get identical values from one source.
   - Smooth off must be today's engine, bit-exact.
2. **Decay correction.** On the box, the uncorrected cap lengthened octave T30 by +4–8 % at 63–500 Hz, with HF unchanged.
   - Compute the correction; don't hand-tune it per room. The likely cause is the diffuser allpass group delay changing the effective loop time. Fold it into the existing per-line decay lock (`lg`) or another existing per-line coefficient.
   - Don't add a new in-loop filter slot unless G3 still passes.
3. **Forced off** in `reaktor_parity`, flat cards and the mirror/null test modes, whatever the UI says.
4. **UI:** a Smooth switch next to Decay on the Room tab (placement ASSUMED, so keep it easy to move). Save it in presets; old presets load with Smooth ON.

## Gates (report each with numbers)
- **G1 Bit-exact off.**
  - With Smooth off, Render and Play match the pre-session tree at max-abs 0 on the golden scenes.
  - Parity, flat and mirror modes are bit-identical to pre-session with Smooth on or off.
- **G2 Decay (Smooth on).**
  - Rooms: default, box (3 × 2.4 × 4 m, Decay 0.8 s) and one carpet room.
  - Octave T30 at 125 Hz–8 kHz is within ±5 % of Smooth off. Report 63 Hz.
  - Mid T30 (500 Hz–1 kHz) is within ±5 % of the Decay setting.
- **G3 CPU (paired t19, 12-round pair, PC).** Shared-off ≤ 2.40 ms and shared-on ≤ 2.133 ms with Smooth on. Report the deltas against pre-session.
- **G4 Effect.** Default room, Smooth on vs off: late-tail peakiness (method as `analyse2.py`) is ≥ 0.4 dB lower. The prototype gave −0.64 dB.
- **G5 Goldens.**
  - Regenerate **only** the goldens whose diff comes from the Smooth default, with the reason "EQ-1a: Smooth default ON (Dffs cap 0.7 + decay correction)".
  - Each one, rendered with Smooth off, must still match its old golden bit-exactly.
  - Any other golden change is a fail.
- **G6 Existing tests.**
  - t18 at defaults ≤ −60 dB, target the current −71.8 dB.
  - `test_mirror_exact` ≤ −120 dB.
  - All other tests pass.

## Stop rule
If G2 can't pass without breaking G3, or G1 or G5 can't be made clean, stop and don't push a half-done default:
- **Ship the switch with Smooth default OFF.** Goldens stay unchanged, and G1, G3 and G6 must pass.
- **Or revert to the pre-session tree.**
- Then report what blocked it.

Either way the software must build, run and pass the tests at the end of the session.

## Out of scope
Movement (EQ-1b), D-INT (44.1 kHz interpolation), resonance control, the Output strip, and any delay change (the uniquify lock stands).

## Report back (short)
- A gate table with numbers.
- Files changed.
- The correction method used.
- The final Smooth default.
- Two loudness-matched default-room guitar renders (Smooth off / on) in `handoff_build_support_2\roadmap\eq_plan\eq1_out\`.
