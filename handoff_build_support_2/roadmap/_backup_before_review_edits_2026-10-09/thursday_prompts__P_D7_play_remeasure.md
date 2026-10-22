# P-D7 · Play small-room re-measure on the PC (D21). Effort: low. Not a code session. After T4 (EQ-1a moves the tail).
On the PC, post-T4 tree: `python handoff_build_support_2\3_phase_acceptance_tests\run_phase_tests.py --sw software --slow -k small_lock08 --out handoff_build_support_2\roadmap\d7_play_<time>.json` (the `test_p0_engine` small_lock08 row: Play T30 per band vs the 0.8 s dial).
- **Record:** Play T30 at 250 Hz / 500 Hz / 1 kHz next to Render (box: −12 % / – / −4 %, `roadmap/research/R13_D5_D7.md`).
- **Rule (D21):** Play ≈ Render (1 kHz within ±5 % of the dial): propose accepting and widening the small-room tolerance. Play still ≈ −8 %: a live-tank bug, an M session later.
- **Golden impact:** none. No code change; do not edit `software\`.
- **Stop if:** the run is not on the post-T4 tree. Report the numbers to Idle before anything changes.
