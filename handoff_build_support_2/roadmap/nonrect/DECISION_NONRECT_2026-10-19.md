# DECISION: Non-rectangular rooms (Idle, 2026-10-19 08:24-08:35)

Answers to the 8 pending decisions from NONRECT_RESEARCH.md. These are binding for Stage 1.

1. **First shapes:** splayed control room, LEDE (dead front, live back), and a non-parallel live room. The hexagon is not in the first set.
2. **Early echoes:** the 32 early taps take a fixed number from each bounce order, chosen by geometry only, not the 32 loudest. That keeps them stable while the user tweaks, and gives an even build-up into the tail.
3. **Tank delays:** fixed for each shape and source position, derived from the mic stand. Dragging a mic never retunes the tail, which avoids pitch wobble and clicks and keeps the Hadamard character.
4. **Render first:** Stage 1 is Render only. Play follows once Render is proven.
5. **Echo visibility fades:** 15 ms fade in and out whenever an image becomes visible or hidden as a mic moves.
6. **Surfaces:** every real wall is represented on the Surfaces page, with LEFT-RIGHT MIRROR SYMMETRY only.
   - Each left wall is paired with its mirrored right wall and they share one material.
   - Front/back and floor/ceiling are NOT mirrored; they stay independent.
   - Symmetry applies to materials. A non-parallel live room's geometry may be slightly asymmetric to kill flutter. Ask Idle before mirroring geometry.
7. **L-shape:** parked. Note the "coupled room" idea for the backlog: the far arm adds a later, darker second decay. If wanted later, there may be cheaper ways to get it.
8. **Scattering delay network tank:** research note only. The Hadamard tail stays.

Existing rule kept: the shoebox (box) rooms stay bit-exact. The shapes scale with size settings the way rooms do now.
