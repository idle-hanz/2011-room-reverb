# Run rules (Idle, 2026-10-22). Every prompt follows these.
1. One goal per run. If the prompt has two goals, do the first and stop.
2. Time box: about 60 minutes. If not done, stop, write a 10-line status, keep the work on a branch/backup, do not restore and redo.
3. No rabbit holes. Any side issue, odd number or old failure: one line in roadmap\IDEAS_BACKLOG_2026-10-19.md, then carry on. Never investigate it in this run.
4. Tests: QUICK after each step (sound pins/MD5s, goldens, tests for the touched files). FULL suite + CPU bench once, at the end only.
5. Known-red acceptance tests are not reasons to stop or to dig.
6. On a stop: say which gate, by how much, and the one-line likely cause. No extra diagnosis.
7. Report: under 20 lines, plain words.

## Added 2026-10-22 from PROCESS_REVIEW (Idle approved all five)
8. Reachable gates: before any edit, score a new gate on the approved reference (prototype or current build). If the reference fails, stop and report; do not edit.
9. Order: run the gate most likely to fail first. Full pytest + harness once, only after it passes. Acceptance --slow is off by default (only when the prompt asks).
10. CPU: bench old and new back to back in the same session; gate the difference (new - old) as well as the 2.40 ms ceiling for Play. Render has no CPU ceiling.
11. Backups: git commit before edits (C, wasm, Python, JS, goldens; render wavs excluded). On a fail, keep the work on a branch; no zip restore.
12. Brief: read CURRENT_BRIEF.md (one page, includes the do-not-touch list) instead of the full HANDOVER. Prompts give only the delta. Step 0 review only for a new gate or an audio-core change.

## Added 2026-10-22 from PROCESS_REVIEW "More suggestions" (Idle approved)
13. QUICK tier (after each step): sound pins/MD5s, quick pins test, selfcheck, node tests, tests for touched files. Node, from `software\`: `node --test (Get-ChildItem tests\*.mjs | % FullName)`. PowerShell does not expand the glob.
14. FULL tier (once, at the end): pytest WITHOUT test_b2, harness t03 + t04 (they re-render the goldens; a golden hash alone only proves the file wasn't edited), CPU delta bench. Harness t05, the acceptance pytest (and --slow) and extra CPU benches are OFF unless the prompt asks.
15. Prompts: about 40 lines, one gate, real paths under handoff_build_support_2\roadmap\, a paste-ready QUICK command, a 20-line report. If the gate is not yet scored, the run scores it and stops.
16. Never two audio laws in one run.

## Added 2026-10-23 (Idle). Heard faults were becoming a second investigation.
17. Two heard faults in one prompt is invalid. The builder replies in five lines and stops. The prompt bot splits the file before the next run. This replaces "do the first and stop" for a heard fault.
18. A listen complaint is one session when the change is wiring (a key not posted, a guard, a missing forward). Read the path, quote one number from a file that already exists, and land that fix in the same session. Stop for Idle only when the change is an audio law (a makeup formula, the 610 trim, a new gain).
19. Do not list hypotheses. One suspected cause. If a report or a wav already has the number, do not re-render to get it again.
20. Do not ask for the app, a logged request body, and a render in one prompt. Prove keys with the node test and one render() call. Open the app only after that passes and Idle still hears nothing.
21. Start from CURRENT_BRIEF.md. Do not reconcile HANDOVER.md or the long memory note at the start of a Thursday run.
22. Plan mode and Step 0 stay off for a heard fault whose cause is already a backlog line. Step 0 stays on for a new numeric gate or an edit in live_stereo.c, render_pipeline.py, surf_loop.py, or the bloom DSP.
