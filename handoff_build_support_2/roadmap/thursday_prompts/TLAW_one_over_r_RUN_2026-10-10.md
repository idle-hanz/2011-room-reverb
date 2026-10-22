# TLAW: change the distance law from 1/r^2 to 1/r (Idle decision, 2026-10-10)

STEP 0 (REVIEW ONLY, plan mode, no edits): check this whole prompt against the real code and the locked decisions. Report findings only. If a finding touches sound beyond what is stated here, or a locked decision other than the ones overridden below, STOP and report. Do not code in this pass. Max 3 review rounds; stop on any repeated finding.

STEP 1 (build, fresh session, high effort). First make software_backup_2026-10-10_preTLAW.zip. Read HANDOVER.md Current pin. FIX-B must be finished and pinned first; if it is not, stop.

DECISION (Idle, 2026-10-10, locked): the distance gain becomes amplitude 1/r (about 6 dB per doubling) for the whole software, Play and Render. This overrides: HANDOVER "Do not replace 1/r^2 with 1/r", the Current-pin "do not retune 1/r^2", the durable-lock note on Air Abs 1/r^2, D22 (the later opt-in "Physical" 1/r option) the 1/r^2 wording in D-MAKEUP-FREEZE, and the 30 Sep 2026 binaural level decision (1/r^2 from the head centre): binaural keeps geometric_level(r_h) from the head centre with both ears equal, only the exponent changes to 1/r. D-MAKEUP-FREEZE itself (makeup frozen at stand distance) stays. Direct sound stays exactly as is (no distance law, 0.55 fold, delays follow distance).

WHAT TO DO
1. In software/engine/early_field.py change geometric_level to 1.0/distance (keep the <=1e-9 -> 0 guard). Update its docstring: say Air Abs graph is 1/r^2, and Idle chose 1/r on 2026-10-10 with the reason (AGC balance, close mics too loud, physical pressure law).
2. Find every other place that assumes 1/r^2 using rg (selfcheck test_air_abs_one_over_r_squared, comments in build_inject_from_taps, any docs strings, app.js display text). Change only what is needed. Do not use line numbers.
3. selfcheck: replace the 1/r^2 test with a 1/r test pinning 1 m -> 1, 2 m -> 0.5, 4 m -> 0.25.
4. Do NOT touch live_stereo.c, the wasm, direct sound, the limiter, the makeup target (0.7), or makeup_at_stand logic. WORKLET_VER stays 52 unless a cache-bust is truly needed; say if so.
5. Goldens: the five T4c goldens will move on purpose. Before regenerating, confirm the ONLY cause is the distance law: for each golden report the old and new sha1 and peak/RMS change. Also expected to move on purpose, same single cause: the d18.f32 and d4.f32 prefixes in test_b2_render_length.py, the post-freeze null residuals -33.30 dB and -42.50 dB in test_smix_desk.py test_any_strip_route, and render_std_unlocked_byp.f32 pins in test_b2/test_b6_heights. Re-measure the new values, confirm each moved only because of the distance law, re-pin them with the reason. Any OTHER pin that moves is a STOP. Regenerate the goldens, update GOLDEN_META.json with the reason "TLAW 1/r, Idle decision 2026-10-10", and update every test that pins the old sha1 (test_smix_desk.py, test_b2_render_length.py, test_b6_heights.py, others found with rg).
6. Re-measure with fix_b/measure_fix_b.py: solo C at 0.5, 1, 2, 4, 8 m; screenshot 554/555 cases; 0.3 m above the source; source moved 0.5 to 8 m with stand mics. Report pre-limiter peak steps per doubling (expect about 6 dB for room-spot mics), makeup, limiter amount.
7. Check that a stand-mic scene with the source moved is reported only; do not change makeup behaviour. Report the result.
8. Run the full suite (pytest, node --test, selfcheck; test_a12 and test_a5 flakes rerun alone), harness t03/t04. Update the HANDOVER Current pin with the decision, the new golden sha1s and the counts. Write DECISION_DISTANCE_LAW_2026-10-10.md in roadmap.

STOP RULES: stop and report if anything other than the five goldens and their pins changes, if the limiter engages in default scenes, if Play and Render makeup gap grows beyond the known 0.8 dB, or if a test fails for a reason not listed here. Do not chase diminishing returns.

REPORT: what changed, old/new golden sha1s, the measurement tables, test counts, anything left open. Idle will listen before accepting.


REVIEW LOG (2026-10-10): round 1 findings folded in: binaural decision added to override list; d18/d4 prefixes and the two null residuals added to expected moves. FIX-B must be finished and pinned before Step 1 (stop rule stays).

