# SRCDIST: makeup must not cancel source distance (D-SRC-DIST-LEVEL, Idle 2026-10-11)

Read roadmap\DECISION_SOURCE_DISTANCE_LEVEL_2026-10-11.md, DECISION_MAKEUP_FREEZE_2026-10-10.md, TLAW decision, HANDOVER Current pin.

STEP 0 REVIEW ONLY (plan mode, no edits, no builds). From the real code answer, tagged VERIFIED or ASSUMED:
1. In makeup_at_stand and ir_rms_makeup_from_inject (render_pipeline.py, app_server.py /api/colour, live_fdn_params, combined_ir), which inputs depend on the SOURCE position (makeup_source=prep.source, tap levels, first arrival)? Show exactly why makeup rises as the source moves away (stand mics: -8.5 dB at 0.5 m to +14.5 dB at 8 m in measure_tlaw.json).
2. How should makeup be frozen against source distance so that: (a) the default scene is bit-exact (five goldens, live MD5s unchanged); (b) makeup still tracks decay/feedback (the FDN gain g, decay-lock) so more reverberant rooms do not get louder; (c) a moved source follows 1/r through the injects? Propose the smallest change (for example computing makeup with the source placed at the default/reference source position, as the stand freeze does for mics). Say what the reference position is and where it is stored.
3. Does a SECOND source (two-source scenes), source preset/radiation, Flat vs Surfaces (SL2) or the Space/colour preview (/api/colour) need the same treatment? List every caller.
4. What would the limiter do at a source 0.3 m from a stand mic (source close to the stand)? Report from measure_tlaw.json; do not run new benches that write files. Flag whether a minimum-distance floor is needed (report only; that is a separate sound decision).
5. Which tests, goldens and pins would change (test_smix_desk nulls, measure_tlaw)? Is Play and Render change identical in both engines (no wasm change expected: makeup is a posted scalar)? Is WORKLET_VER affected?
6. Cut lines. Say whether this needs a sound decision beyond D-SRC-DIST-LEVEL.
Report findings only. Max 3 rounds; stop on a repeated finding. Do not code.

STEP 1 BUILD (fresh session, high effort) only after Idle's bot has folded the findings in. Backup first: software_backup_2026-10-11_preSRCDIST.zip (software\ and 3_phase_acceptance_tests\harness\golden\). Do not retune Smooth, 1/r, the limiter or the 0.7 target. Default goldens bit-exact. Finish: full suite, landing in the HANDOVER Current pin and BUILD_RUN_LOG.md, re-measure the source-moved table (0.5 to 8 m, stand mics) and the 0.3 m case, and report the peak per doubling (expect about 6 dB) and limiter amounts.

## ROUND 1 REVIEW CORRECTIONS (2026-10-12). Step 0 is DONE; run Step 1 only.

CAUSE (verified): makeup_at_stand rebuilds taps from the LIVE source; ir_rms_makeup_from_inject sets the scalar to 0.7 / peak0 times the decay term, so a farther source (lower 1/r inject) raises makeup. Early and FDN take that scalar; Direct does not.

THE CHANGE (one edit inside makeup_at_stand): compute makeup with the source placed at the REFERENCE offset from the placed stand centre = boot source minus boot stand = (-0.4, -0.3, +3.25) m (DEFAULTS sx 2.6, sy 1.2, sz 4.75 minus stand 3.0, 1.5, 1.5). Keep each caller's own decay g. Leave the audio injects on the LIVE source. That one helper covers Play, Render, the moving path, two-source (one shared scalar; source B never entered makeup), /api/colour, radiation and Surfaces. direct_makeup stays unwired. No wasm change; WORKLET_VER stays 54.

MUST HOLD: the five TLAW goldens, GOLDEN_META and both live MD5s (empty af2b154a..., stored centre f30665f4...) unchanged (on the boot stand the reference IS the boot source). If any of them moves, STOP.

RECHECK (scenes post their own source; these may move and are NOT goldens): selfcheck fold*makeup window (scene sx 3.0, sz 4.1); test_any_strip_route nulls -39.00 / -47.52 dB (scene sx 2.2); harness small_lock08, hall_lock40, T14_PIN. Re-measure each, confirm the only cause is the source freeze, re-pin with the reason "D-SRC-DIST-LEVEL". Any other pin moving is a STOP.

MEASURE AND REPORT: the stand-mic source-move table (24 x 6 x 32 m room, 0.5 to 8 m): expect makeup constant and the peak falling about 6 dB per doubling; limiter amounts. Add a row with the source 0.3 m from the stand centre and report the limiter. A minimum-distance floor is a SEPARATE sound decision: report only, do not add one.
Do not retune Smooth, 1/r, the limiter or 0.7. Backup first (software\ and handoff_build_support_2\3_phase_acceptance_tests\harness\golden\).
