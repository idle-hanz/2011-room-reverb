# REVIEW REQUEST — T5 and P-D7 prompts (review only, NO edits to anything)

You are a read-only reviewer. Do not edit any file. Print your whole report as your final answer.

Read: HANDOVER.md (root, Current pin; T1-T4c are in the tree, WORKLET_VER 52, Smooth default ON, ORTF centre OFF), roadmap\thursday_prompts\T05_u87_ab_render.md, roadmap\thursday_prompts\P_D7_play_remeasure.md, roadmap\research\R05_T5_T6_u87.md, roadmap\research\R13_D5_D7.md, roadmap\REVIEW_RUN_PLAN_findings.md, and the real code and harness they refer to.

Check each prompt against the real tree:
1. Will every command, path, script name, flag and file in the prompt actually exist and work on this PC tree (for example run_phase_tests.py with --sw, --slow, -k small_lock08, --out)? Quote what you checked.
2. Is T5 really "no Build usage / box job", or does rendering the A/B (SM57 vs U87 Ai Cardioid vs CMC5-U, ORTF with C off, Smooth on, loudness-matched, blind names plus key file) need the real software tree, which lives on the PC? Say exactly where it should run and what it needs (dry guitar file path, render entry point, how to set the mic model per scene).
3. For both: any stale fact, wrong number or step that would make the run fail, mislead, or change the default sound without Idle's decision. Does either prompt write into software\ or start/stop the app? (It must not.)
4. Does P-D7 need Smooth both on and off for reference, and does the prompt say how to set it (smooth key) for both Play and Render?
5. Give a corrected, minimal replacement prompt text for each if anything must change.

Mark each finding MUST FIX / SHOULD FIX / NOTE with file and line. If nothing is wrong, say so explicitly.
