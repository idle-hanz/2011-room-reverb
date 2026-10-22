# R14 · Play CPU 2.17 ms with the FDN fader at 0: tank gating (N17)

**Today (VERIFIED, engine/live_stereo.c):**
- When the FDN is muted, the tank keeps running and only the output gain ramps. See the params block near 1187 (`nowFdn = fdn_wet > 1e-4`, and the comment "Mute does not: the tank keeps running"); `fdnWas` 269; `bus_sample` 1946 sets `runFdn = 1` always.
- Result: 2.17 ms at FDN 0, against 1.18 ms before S-AUDIT, under the 2.40 ms ceiling.

**Norm (VERIFIED):** VST3 plug-ins report their tail (`getTailSamples`; `kInfiniteTail` keeps processing) and use silence flags. They skip work only when the output is truly silent, and `setProcessing(false)` resets state.
- https://steinbergmedia.github.io/vst3_dev_portal/pages/Tutorials/How+to+use+the+silence+flags.html
- https://steinbergmedia.github.io/vst3_doc/vstinterfaces/classSteinberg_1_1Vst_1_1IAudioProcessor.html

So the accepted rule is: keep the tail ringing out after mute, then stop once it is below a threshold, and restart cleanly.

**Recommended rule:**
1. While the FDN is muted, keep running until the tank's state energy has stayed below −96 dBFS for 50 ms (or 1.5 × T60, whichever is first).
2. Then skip the tank (`runFdn = 0`) and zero its state.
3. On unmute, start from zero state with the existing output ramp. The tail builds from new input only, which is what a muted send does on a real desk.

Saving ≈ the tank's share of 2.17 ms whenever the FDN is muted and silent (ASSUMED ≈ 0.8–0.9 ms, from the 1.18 ms pre-S-AUDIT figure). No change while the FDN is up, so **no CPU gain in normal use**.

**Risks:** a click on unmute if the ramp is too short (keep ≥ 10 ms). Tests that mute and unmute expecting the old tail back would change.

**Touch points:** live_stereo.c 269, ~1187, 1946 (energy check per block), plus the ramp code at 2490/2500/2601/2712.

**Tests / goldens:** NO for the default (FDN up). Live mute/unmute tests need a new expectation.

**Decision for Idle:** **N17**, keep as now (simplest, under budget), or gate after the tail dies (recommend gate, but it is not urgent: it only helps with FDN at 0).
