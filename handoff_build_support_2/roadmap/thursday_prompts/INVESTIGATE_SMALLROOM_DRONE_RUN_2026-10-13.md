# INVESTIGATE: small-room low-mid drone + clipping on guitar (2026-10-13). READ-ONLY. No edits to software\, no re-pins.
Idle's report: a full mix sounds good. Guitar through it with the room made SMALLER gives a terrible low-mid bass drone, and it clips. Current pin: WORKLET_VER 55, PROX landed.

Reproduce in Render (and in Play if you can) on the default scene, then shrink the room in steps (e.g. 6x8x3 m down to about 3x4x2.5 m and 2x2.5x2.2 m). Guitar DI or the PROX listen guitar as the input. For each size, report:
1. Peak, limiter dB and samples, and the T60 per octave (63 to 2k). Which band rings longest?
2. The tail spectrum: the frequencies of the top 5 narrow peaks, and their decay times. Do they match the room's axial modes (c/2L)? Do they match the FDN delay lengths or their sums (a metallic/feedback ring)?
3. Isolate the cause by toggling one at a time, report-only: the Proximity boxes off; Surfaces Decay Flat vs shaped (SL2/SL3); Smooth; the makeup (does makeup_at_stand rise as the room shrinks? decay-lock g near 1?); the distances from the source to each mic (is any < 0.5 m after shrinking, so PROX is active?); whether the mics/stand end up outside or on a wall.
4. Does the FDN feedback g at the low/low-mid bands approach or exceed 1 in small rooms (instability)? Check the decay-lock and the per-band gains.
5. Say which cause(s) it is, with numbers, and propose fix options (do not build): e.g. the room-tone resonance cuts before ER/FDN (Idle's 2011 idea), a makeup ceiling, a per-band g clamp. Flag any that touch sound or a locked decision.
Write the results to roadmap\INVESTIGATE_SMALLROOM_DRONE_2026-10-13.md and a short summary in chat.
