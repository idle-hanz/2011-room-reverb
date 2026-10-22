# Open faults pinned 2026-10-10 (after TLAW listen, Idle)

F4. Hall (preset chip) still jumps in level when clicked. Idle thinks it is just the sudden change when the preset loads. NOT investigated. Check: is it the makeup scalar changing at once (no ramp), or a real level step? Report only first.

F5. Mics do not keep their position when a preset chip is clicked (room-spot / stand positions are reset or overwritten by the preset). Idle expects mic positions to stay put. NOT investigated. Needs a read-only look at what the chip writes (mic_x/y/z, room_<cap>_*, pin_m) and a decision on what a chip should and should not touch.

Open decision: should a source approaching stand mics get louder (makeup currently cancels it; peak only drifts ~2 dB over 0.5-8 m). Idle to decide.

Queue after these: T9b (B10, B11, P2, P4, P10), T8b (wall/corner/ceiling drag, canvas scaling), T5, P-D7 (reviews failed, redo), book chapters 6-8 and PDF rebuild.

F6 (2026-10-11). 3_phase_acceptance_tests\tests\test_locks.py test_lock_geometric_level_inverse_square still asserts 1/r^2 (d*d product == 1); live law is 1/r since TLAW. Update the test to 1/r in a small cleanup session. Also HANDOVER hard-lock table and DECISIONS_LOCKED D22 wording are stale.
F7 (2026-10-11). Harness pytest does not collect: its --sw option clashes. Small fix.
F8 (2026-10-12). T14 FDN was already -24.78 dB on the pre-SRCDIST tree against the old -27.18 dB pin. Pre-existing drift, cause unknown. D-SRC-DIST-LEVEL then moved that posted source by +0.23 dB, and T14_REF fdn_rms_db is now -24.55. The gap from -27.18 to -24.78 is not this decision.
T11 status 2026-10-11: code landed, WORKLET_VER 53, live_stereo.c sha1 73a5a339..., Movement forced off after a stop rule; G3, G4 and guitar files not measured. Waiting on the top of Build's report for the stop reason.

T11b PARKED (2026-10-11, bot suggestion, Idle did not object): Movement is in the tree but forced off (G2 miss: 2.718 ms vs locked 2.40 ms shared-off; allpass runs on 3 tanks, 96 calls; shared-on passes). Revisit later as a small benched session: coefficient hold (16-25 samples) plus 8 modulated lines or skip muted centre tank, in Play and Render, then G3, G4, G2. Ceilings stay locked. See roadmap\thursday_prompts\INVESTIGATE_MOVEMENT_CPU_RUN_2026-10-11.md findings (in chat). Next: T10 refresh and Build review.

2026-10-18: newer list in OPEN_FAULTS_2026-10-18.md (F9-F12). F6 and F7 were closed by CLEANUP 2026-10-17. F9 closed 2026-10-19.
