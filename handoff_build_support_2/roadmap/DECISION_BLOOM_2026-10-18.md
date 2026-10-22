# DECISION D-BLOOM (Idle, 2026-10-18) - "virtual compressor" for ambience

Status: DECIDED in principle, NOT built. Queued AFTER AMBIENCE (AMBIENCE_RUN_2026-10-18.md) lands. A run prompt gets written then, with the usual Step 0 review.

## Idea (Idle's words)
"although rooms arent as reverberant as we want, we use compressors and things to turn it up. ... A 'virtual' compressor that does not turn the gain up like the analogue version, but rather delivers more ambience cleanly by tweaking the algorithm. ... familiar controls ... attack, release, predelay."

## What it is
A compressed room mic brings the ambience up between notes. Bloom gets that musical effect inside the reverb instead of by gain on the whole signal, so noise, rumble and clipping are not raised.
- A level follower on the dry input steers the tail only: how much reaches the FDN input, and how loud the tank output comes back. All of it happens before the limiter.
- Direct and early sound are never touched, so transients keep their character.
- The Puckette/Hadamard tank, the unscaled Hadamard mix and the 1/sqrt(N) decay-lock loop are NOT changed. Bloom steers what goes in and how loud it comes out (plus the optional Sustain below).

## Controls - in the MIX window (Idle, 2026-10-18)
One panel, working name "Bloom":
- **Amount** - how much the tail comes up when the input is quiet (the ratio-like control). 0 = off, bit-exact.
- **Threshold** - input level above which the tail is held back.
- **Attack** - how fast the tail ducks when a note hits.
- **Release** - how fast the ambience blooms back after the note stops.
- **Predelay** - delay before the tail input (tank inject). It does not delay direct or early sound.
- **Sustain** (optional, last to be built) - while the input is quiet, the per-octave decay (the phys_ceiling / wall-hardness path from AMBIENCE) is lengthened temporarily, then settles back. Hard cap so the loop gain can never reach 1. Smoothed coefficient changes so there is no zipper noise or click.

## Rules for the eventual run
- Amount 0 (default) and Predelay 0: bit-exact against the pins current at that time. The live dict grows no key while off.
- Play and Render use one shared function. Same envelope maths in Python and wasm.
- CPU stays under the shared-off ceiling (2.40 ms on the decay-8 cube) with Bloom on.
- No gain applied after the limiter. No change to makeup, g_decay, 1/r, SRCDIST, D-PROX, Smooth, 0.7, the 0.55 fold, Surfaces or PLACE.
- Listens: guitar (the clean file from AMBIENCE) in a small and a mid room, Bloom off and three settings (gentle, medium, heavy), plus attack/release extremes. Report tail level vs time, the limiter, true peak.
- Build order: Predelay, then Amount/Threshold/Attack/Release on the tail level, then Sustain as a separate later step.

## Fits with
Wall hardness (AMBIENCE Part 4) sets the room. Bloom is how you play it.
