# ROOMTONE RUN 2026-10-15 (D-SMALLROOM part 1)
Read DECISION_SMALLROOM_2026-10-15.md and INVESTIGATE_SMALLROOM_DRONE_2026-10-13.md. Locked, do not retune: 1/r, SRCDIST, D-PROX, Smooth, the limiter, 0.7, the 0.55 fold, Surfaces SL1-3, PLACE, Movement off. The decay lock is untouched in THIS run (that is SMALLDECAY).

## Step 0: REVIEW ONLY (plan mode, no edits). Answer against the real code:
1. What room-tone / mode-cut code exists today (fdn.py axial_mode_hz, PEAKING_Q, DEFAULT_DEPTH, the "first axial only" cuts, the D-SL3 30 Hz keep, the boot-room 160 Hz peak). Where does it sit: before the ER/FDN or after? Both engines?
2. A plan to extend the cuts to the axial harmonics (n*c/2L, n = 1..N, up to about 500 Hz or a mode-density limit), shallow (per-bounce depth so it builds over trips), placed on the source feed BEFORE the early reflections and the FDN inject. Same coefficients in Play and Render. Is a wasm change and a WORKLET_VER bump needed?
3. Can the boot room stay bit-exact (e.g. new harmonics only where they are not in the boot set, or gated by room size)? If not, how big is the change (dB per octave on the boot render)? That would be a STOP for Idle to hear.
4. Its interaction with Surfaces (does the per-face EQ already cut at these frequencies? avoid double cutting), with SL2's octave calibration, and with the CPU (2.40 ms ceiling).
5. The test plan: on the 3x4x2.5 and 2x2.5x2.2 m guitar scenes, the top 5 tail peaks and their T60 before/after, the peak and the limiter. Listen files for Idle.
6. Any conflict with a locked decision: STOP.

## Step 1: BUILD (fresh session, after the corrections). Backup software_backup_2026-10-15_preROOMTONE.zip. Build the step 0 plan, measure, write listens to roadmap\roomtone\listen\, run the full suite, pin the goldens (bit-exact or STOP), and write the HANDOVER pin + build log.

## LOCATION NOTE (2026-10-16): axial_mode_hz and PEAKING_Q are in engine\early_field.py, DEFAULT_DEPTH is in render_pipeline.py (not fdn.py). Find the real names by search.

## ROUND 1 CORRECTIONS + IDLE DECISION (2026-10-16)
Idle chose IN-LOOP (2011 style): the cuts build up every bounce. This OVERRIDES Step 0's pre-feed plan and its "STOP if inside the loop" line. Changing the heard decay at those harmonics is intended (Idle approved). The decay lock itself is still not edited (that is SMALLDECAY).
Keep from Step 0: the 30 Hz all-axis size gate (boot and 4.5x6x2.8 have the gate OFF, so they are identity and bit-exact); the old three first-axial banks, axial_mode_hz, PEAKING_Q, DEFAULT_DEPTH, KEEP_CUT_BELOW_HZ and the three-bank blob untouched; c = 340; the harmonics n>=2 up to min(500 Hz, Schroeder); the new coefficients through a side pointer; WORKLET_VER 55 -> 56 and the two test strings; direct stays dry.
In-loop design:
- Each FDN line gets only ITS axis's harmonics (axis_for_line, i % 3), on the delay read next to the existing peak (both engines, the same coefficients; with Surfaces on, beside apply_kept_peak and outside design_bus).
- NARROW and SHALLOW per pass: start at Q 8, -0.3 dB per stage per pass (it compounds per trip). Report the effective per-harmonic T60 change and the stacked one-pass dB; no stacked scoop more than about 3 dB per pass.
- CPU: measure the worst case against the 2.40 ms ceiling. If it is over, STOP and report the options (fewer harmonics, the Schroeder cap only, skip the muted centre tank, a coefficient hold). Do NOT raise the ceiling.
- Expose the depth and Q as constants Idle tunes by ear (not UI knobs yet).
- Listens: the two small rooms before/after, plus the after at depth x0.5 and x2, to roadmap\roomtone\listen\.
Because the plan changed, run Step 0 AGAIN (Round 2 review, plan mode) on this in-loop design before building: the insertion points, the CPU estimate, the bit-exact gate and any conflict.

## ROUND 2 REVIEW ACCEPTED (2026-10-16). Step 0 DONE (both rounds); run Step 1 only, following the Round 2 review exactly:
- Insertion: one helper on the FDN delay read after the existing peak, at the 8 Play sites (bus_sample: one/two source x Surfaces on/off x the mix1/non-mix1 sites), after the early returns of read_peaked/apply_kept_peak; Render in process_block_poly after the Surfaces and peaking blocks (NOT inside "if peaking"). Each line on its own axis (i % 3). Direct/early unchanged.
- One Python designer (rbj_peaking + normalize_biquad, Float64) through a side pointer like live_surf_ptr; C applies DF1 only; the state is zeroed in scrub. HARM_Q = 8, HARM_DB = -0.3 as constants beside PEAKING_Q. Harmonics n>=2 of axial_mode_hz (c=340) up to min(500, schroeder_hz(decay_s, V)); not modes(). MAX_H 16.
- Gate ON only when all three first axials are >= 30 Hz; the key is omitted when off (MD5s af2b154a.../f30665f4... and the five TLAW goldens / GOLDEN_META 883cc732... bit-exact; any move = STOP). small_lock08 must pass unchanged (do not widen T60_TOL; a fail = STOP).
- WORKLET_VER 55 -> 56; update the four strings in test_live_stereo.py and test_mic_colour_relative.py and index.html; rebuild the wasm and the DLL together.
- CPU: wasm shared-off on both listen rooms, then the decay-8 cube, two sources, colour on, Surfaces on. Over 2.40 ms = STOP and report the options; do not raise the ceiling.
- Listens at the PLACE positions given in the review: before, -0.3, -0.15, -0.6 dB; report the top 5 tail peaks + T60, the peak, the limiter.
