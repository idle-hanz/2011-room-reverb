# CLEANUP RUN 2026-10-17: housekeeping, NO sound changes
Source: roadmap\AUDIT_2026-10-17.md. Locked and untouched: all audio code paths, 1/r, SRCDIST, D-PROX, PLACE, ROOMTONE, Surfaces, the decay lock, Movement off. The five TLAW goldens, GOLDEN_META 883cc732..., both live MD5s and WORKLET_VER 56 must stay byte-identical. Any audio change = STOP.
Do not run this at the same time as SMALLDECAY Step 1 (both touch the tests/HANDOVER). Run it before or after.

## Step 0: REVIEW ONLY (plan mode, no edits). For each item, confirm it with file:line and give the exact edit plan:
1. F7: the harness --sw option clash (3_phase_acceptance_tests\tests\conftest.py:28) that stops the acceptance tests from loading.
2. F6: test_lock_geometric_level_inverse_square (tests\test_locks.py:72) asserts 1/r^2; rewrite it to assert the locked 1/r law (D-TLAW 2026-10-10), renamed to match.
3. The stale docs: START_HERE.md and NEXT_SESSION_PLAN.md (9 Oct) brought up to date with the current pin, the done list (T10, SL1-3, TLAW, SRCDIST, PROX, PLACE, ROOMTONE built and STOPPED on CPU) and the real queue (SMALLDECAY, SL4-7, F4/F5, F8, T8b/T9b, Movement revisit, the redesigns). HANDOVER.md historical lines (about 386-528, incl. line 449 "Do not replace 1/r^2 with 1/r"): mark them as SUPERSEDED by TLAW (do not delete the history).
4. The about 40 old xfail "not landed" checks: list each one with a proposal of delete (obsolete), keep xfail (still planned, give the roadmap item) or convert to a real passing check (already landed). Show the list; do not delete anything in Step 0.
5. The two *_draft.py test files: delete, merge or keep?
6. mic_proximity: the UI slider plus the server key that render() ignores. Proposal: remove the slider from the UI and leave the key accepted-but-ignored on the server (so old posted bodies and the MD5s don't change). Confirm the MD5s are unaffected.
7. apply_capsule_colour (early_field.py:1684): dead with no callers. Delete or keep with a comment?
8. A quick test tier: propose a pytest marker / a "quick" command (target under 3 min) covering the locks, goldens, MD5s and pins, with the full suite still the gate.
9. Any conflict with a locked decision: STOP.

## Step 1: BUILD (fresh session, after the corrections)
Backup software_backup_2026-10-17_preCLEANUP.zip. Make only the Step 0-approved edits. Run the acceptance tests (now loadable) and the full pytest, node and selfcheck; re-hash the goldens and the MD5s (identical). Bump the cache pins only if a UI file changed (app.js/index.html). HANDOVER Current pin + BUILD_RUN_LOG landing. Report each item done/skipped.
