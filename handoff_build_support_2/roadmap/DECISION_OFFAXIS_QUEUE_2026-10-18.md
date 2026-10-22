# QUEUE NOTE D-OFFAXIS (2026-10-18) - mic tail colour after Bloom, then an optional Colour module

Status: QUEUED, NOT built, no run prompt yet. It runs AFTER BLOOM (`thursday_prompts\BLOOM_RUN_2026-10-18.md`) has landed. The run prompt gets written then, with the usual Step 0 review. The scope below is the research recommendation; Idle confirms it (or changes it) when the prompt is written.

Source: `roadmap\mic_character\MIC_CHARACTER_RESEARCH.md` (sections 2.5, 2.6, 3.5, 8, 9), data in `mic_character\mic_character_params.json` and `measured_third_octave.csv`.

## Item 1 (research rank 1): diffuse-field tail colour + restore the on-axis response
What it is, in plain words: a room mic's character on a reverb is mostly how it hears the whole room from every direction at once. Big-diaphragm mics give a darker tail (at 16 kHz the tail drops 8-14 dB against 1 kHz, U87 Ai about -14 dB); small-diaphragm mics lose only 2-4.5 dB; double-diaphragm mics pick up more bass in the tail. Today the engine flattens the on-axis response, so presence peaks are lost, and the tail colour is a coarse per-line sum over a few seed angles.
- **Tail:** per mic preset, G_tail(f) = -DI(f) from the measured polar set (diffuse average, w(theta) proportional to sin theta), fitted with the existing K=3 SOS fitter, applied once per mic FDN output bus, instead of the per-line seed-angle colour on the tail. Outside the Hadamard loop and off `inject` (`software/mic_colour/HOOKS.md`).
- **On-axis:** a small K=3 SOS on direct and early that puts back the measured on-axis response (presence, air, LF roll-off). Off-axis colour stays relative to on-axis, as now.
- **Early:** keep the per-tap measured colour (`MEASURED_SHELF`). Resolve the R05 check that a tap's level comes from |H| or `pattern_gain`, not both. Crossfade per-tap (early) to diffuse (tail) over the existing early-to-late transition so nothing jumps.
- Unmeasured presets: first-order DI fallback plus a capsule-size HF shelf (research 2.6; marked estimate).
- `early_field.py` `apply_capsule_colour` (line 1706, no callers, marked ASSUMED): its step 2 becomes the measured diffuse EQ, its step 3 (proximity shelf on the tail) is removed from the tail, step 1 (HP) stays. D-PROX on near/direct sound is unaffected.

## Rules for the eventual run
- **Behind a switch, default OFF.** It changes every render, so: build with the key off and prove bit-exact first (five goldens, GOLDEN_META, both live MD5s, d18/d4, t03/t04), then render listens with it on. Flipping the default and re-pinning is a later, separate step after Idle listens (the SMALLDECAY / AMBIENCE pattern).
- Play and Render use one shared filter design; same coefficients in both.
- CPU stays under the 2.40 ms decay-8 cube ceiling (shared off) with the key on. Moving the tail colour from one filter per line to one per bus should cost less, not more; measure it.
- **Bloom interaction:** Bloom's return gain sits on the tank output before the colour (BLOOM Step 0 item 1 / 4). If the tail colour moves to one filter per bus, the Bloom gain must stay before it in both engines, so Play and Render still match. Check this in that run's Step 0.
- Reliability: middle frequencies solid; 16 kHz about +-3 dB (one unit, one plane per model); below 125 Hz indicative only (window-limited).
- Listens: the AMBIENCE clean guitar, boot and one small room, key off/on per mic family (LDC, SDC, double-diaphragm, ribbon).

## Item 2 (research rank 2, after item 1): optional Colour module
Transformer saturation (flux-domain model A) plus a valve or solid-state stage (asymmetric waveshaper model C), one level-matched **Drive** knob and a **Type** selector (Clean / Valve / Solid-state). On the wet returns only, after the mic colour and before the mix bus and limiter. Off by default; Drive 0 or Type Clean is bit-exact bypass. Audible only when pushed (valve leans to H2, solid-state to H3). Gain-compensated, so Drive changes texture, not level.

## Not queued
Elevation-aware colour (rank 3, needs 3-D data such as DirPat), Jiles-Atherton hysteresis, self-noise, a separate diaphragm transient model.

## Order
BLOOM -> D-OFFAXIS item 1 (switch, default off) -> Idle listens -> default flip run if he likes it -> item 2 Colour module (optional).