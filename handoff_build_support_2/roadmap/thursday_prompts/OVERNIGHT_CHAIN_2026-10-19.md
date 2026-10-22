# OVERNIGHT CHAIN (2026-10-19 -> 20) - PERROOMK then BLOOM, unattended

Idle is asleep. Nobody can answer questions. **Never ask. When in doubt, STOP, restore, and write it up in the morning report.** Run at high effort, edits allowed, in a NEW Build chat. Root = `C:\Users\IdleHanz\Desktop\2011 Room Reverb` (call it ROOT). Roadmap = `ROOT\handoff_build_support_2\roadmap`. Overnight folder = `roadmap\overnight\` (create it). Keep a running log in `roadmap\overnight\CHAIN_LOG.md`: one timestamped line (BST) per phase start, gate result, stop or restore.

First reads: `ROOT\.grok\skills\2011-room-reverb\SKILL.md`, `ROOT\HANDOVER.md` (the newest Current pin wins over every number here), `roadmap\BUILD_RUN_LOG.md`, then the prompts named below in full. Every gate, stop rule and expected-mover list in those prompts applies unchanged. This file only adds the chaining, the self-accept rule and restore-on-stop. Where this file and a prompt disagree, the stricter one wins.

## Global rules (binding for the whole chain)
1. Never touch a locked decision (SKILL "Durable locks", HANDOVER, D-BLOOM, D-OFFAXIS, makeup freeze, 1/r, per-room k decision, Idle's hard-clip pre approval as written in the BLOOM ROUND 3 block).
2. Never weaken a tolerance or test limit. The ONLY limit changes allowed are the ones each prompt already lists (PERROOMK: line-0 comb 0.20 -> 0.23 physics-on, no-runaway as a slope check; nothing else).
3. No deletion except your own scratch dirs under `%TEMP%` and `roadmap\overnight\_scratch\`. Never delete backups, listen files, goldens or reports. A restore overwrites from the backup zip; it never deletes outside `software\` and the harness golden dir.
4. CPU ceiling 2.40 ms (2.133 ms where pinned), wasm bench, measured, not estimated. Timing misses are re-run alone on an idle PC before calling a STOP (the prompts' flake rules).
5. Defaults bit-exact wherever the prompts say (boot room, off paths, explicit-false MD5s, `d18`/`d4`, GOLDEN_META, EMPTY/CENTRE MD5).
6. Do not open the app UI for Idle, do not post or send anything, do not touch `2011-Room-Reverb-publish\`, Desktop zips or `.ens` files.
7. There is no `.git`. Every "unchanged" check is SHA1 before/after.
8. Tag claims VERIFIED / LIKELY / ASSUMED / UNKNOWN in every report.

## Self-accept rule (for Step 0 findings, both runs)
Apply a Step 0 finding yourself ONLY if it is a pure factual correction: a line number, path, hash, test name, function name, or harness plumbing detail, that changes **no sound, no default, no locked decision, no tolerance**, and moves **no golden/MD5/pin outside that prompt's listed expected movers**. Append accepted findings to the END of that prompt file as a block headed `## ROUND 1 REVIEW ACCEPTED (overnight, self-applied, 2026-10-20)`, each numbered, with the original finding, the correction, and why it is factual-only. That block overrides earlier sections only for the items it lists.
Any finding that touches sound, a decision, a golden outside the expected movers, a tolerance, a CPU risk, a version plan change (for example the worklet must change after all in PERROOMK), or anything you are unsure how to classify = **STOP** (no Step 1 for that run, no later runs). Write it up for Idle with options.

## Restore-on-stop procedure (used by Phase 3 and 4)
1. Stop editing at once. 2. Extract the run's backup zip over `software\` and the harness golden dir (overwrite). 3. Restore any other file that run edited (prompt-listed docs, HANDOVER, tests, static files) from the copies you saved in `roadmap\overnight\_pre_<RUN>\` before editing (save a copy of every non-`software\` file before you first edit it). 4. Re-hash every file in the backup's SHA1 manifest; all must match. Also re-check WORKLET_VER, every `?v=`, wasm, `live_stereo.c` and Temp DLL sha1s against the pin. 5. Log a BUILD_RUN_LOG row "STOPPED + restored (pins verified / NOT verified)". 6. Leave the run's listen and report files that were already written but mark them invalid in the report. 7. Go straight to Phase 5. If the restore cannot be verified, say so first and in bold in the morning report.

## Phase 0 - Precondition: F9 has landed
F9 Step 1 (`thursday_prompts\F9_NOTES_RUN_2026-10-19.md`) is running in another Build chat. Landed means BOTH: `roadmap\BUILD_RUN_LOG.md` has an F9 / F9_NOTES row dated 2026-10-19 or later, AND `roadmap\f9_notes\f9_remeasure.json` exists. If not, wait and poll every 10 minutes (log each poll) for up to 2 hours. Still not landed = STOP: write the morning report (Phase 5) saying so, change nothing.
If the F9 row says STOPPED or failed: STOP the chain, change nothing, report.
F9 must leave the product untouched; confirm the F13 pin (WORKLET_VER 59, `app.js?v=62`, `live_fdn.js?v=59`, `pack_room.js?v=52`, wasm `843a6eb8...`, `live_stereo.c` `bbdf5799...`, Temp DLL `dcde61df...`, GOLDEN_META, live MD5s) still holds against HANDOVER. Any mismatch = STOP.
Also confirm no other Build session is still writing (F9 row closed, no newer temp scratch than 15 minutes in `%TEMP%\f9*`). If unsure, wait one more poll.

## Phase 1 - Backup preOVERNIGHT
Zip `ROOT\software\` (excluding `.venv`, `__pycache__`) plus `ROOT\handoff_build_support_2\3_phase_acceptance_tests\harness\golden\` (and any other golden dirs HANDOVER names) into `ROOT\software_backup_2026-10-19_preOVERNIGHT.zip`. Write a manifest `roadmap\overnight\PIN_MANIFEST_preOVERNIGHT.txt`: SHA1 of every file in the zip, the zip's own SHA1 and size, plus WORKLET_VER, every `?v=`, wasm, `live_stereo.c`, Temp DLL sha1s and the live MD5s. Test-open the zip and verify the count and a sample of hashes. Failure = STOP.

## Phase 2 - PERROOMK Step 0 (read-only)
Prompt: `thursday_prompts\PERROOMK_RUN_2026-10-19.md`. Do its Step 0 items 0-N exactly, read-only (scratch probes in `%TEMP%` allowed, as the prompt says, e.g. the loop-gain probe). Write every finding, tagged, to `roadmap\overnight\PERROOMK_STEP0.md`. Its Step 0 STOP items (for example any scene's per-bank loop gain at or above 0 dB, boot k not reproducible, a worklet/C change needed) are STOPS here. Apply the self-accept rule. Then, and only then, append the accepted block to the PERROOMK prompt.

## Phase 3 - PERROOMK Step 1
Follow the PERROOMK Step 1, gates, STOP rules, expected movers, listen files and docs sections exactly (its own backup `software_backup_<date>_prePERROOMK.zip` too, in addition to preOVERNIGHT). Prove rule 1 and rule 2 before test edits. Full suite: pytest `software\tests`, node, selfcheck, harness `run_all.py`, and acceptance pytest **with `--slow`**, compared against the F13 row (expected after: the 6 known failures only, per the prompt). CPU via wasm bench. Write the listen files to `roadmap\perroomk\listen\`. HANDOVER Current pin block "PERROOMK". Add a BUILD_RUN_LOG row (time BST, prompt, high, overnight chain, build, result with counts).
Any STOP = Restore-on-stop using `software_backup_2026-10-19_preOVERNIGHT.zip`, then the whole chain stops (no BLOOM).
"Passed cleanly" = every gate passed, no STOP, no unexplained new failure, CPU under ceiling, only listed movers moved.

## Phase 4 - BLOOM (only if Phase 3 passed cleanly)
1. Re-pin: write `roadmap\overnight\PIN_MANIFEST_postPERROOMK.txt` (same content as Phase 1) and confirm HANDOVER's new PERROOMK pin matches the tree.
2. Backup `ROOT\software_backup_2026-10-19_preBLOOM.zip` (same scope as Phase 1, the name BLOOM's own Backup section asks for), with manifest `PIN_MANIFEST_preBLOOM.txt`.
3. BLOOM Step 0: prompt `thursday_prompts\BLOOM_RUN_2026-10-19.md` **including the `ROUND 3 RESULTS FOLDED IN` block (from about line 215), which overrides the sections it names**. Start from the PERROOMK pins (the R3 baseline notes say so). Findings to `roadmap\overnight\BLOOM_STEP0.md`. Same self-accept rule. Its item 14 conflicts with locked decisions = STOP. The listed "known, for Idle to confirm, not a stop" items and the "R3 open items for Idle" stay open: do not decide them, use the prompt's stated defaults, and list them in the morning report. Fit results that the prompt calls "reported outcomes, not stops" (colour-off for a preset that fails the null rule, Neve fallback to nclip_flux 8x under R3-D, Swell rel63 +35/+31 %, Room Crush creep not built) are not stops.
4. BLOOM Step 1: every part, gate and STOP rule of the prompt and R3-E, including off-path bit-exact proven first, Play vs Render, alias gate, delay compensation, clicks, CPU at or under 2.40 ms worst case fully on. Version bumps as the prompt says from the live pin (expected WORKLET_VER 59 -> 60, `app.js?v=62 -> 63`, `pack_room.js?v=53` only if changed); rebuild wasm and every compiled copy. Full suite including acceptance `--slow`.
5. Listens: Set 1 (B2 files via `mk_listen_b2.py`, with the B3 prototype column in `B2_report.json`, A/B/C sha1s unchanged) and Set 2 (guitar, boot room) exactly as the prompt describes.
6. HANDOVER "Current pin ... - BLOOM", BUILD_RUN_LOG row, delete only your Temp scratch.
Any STOP = Restore-on-stop using `software_backup_2026-10-19_preBLOOM.zip` (PERROOMK stays landed). Verify against `PIN_MANIFEST_preBLOOM.txt`.

## Phase 5 - Morning report (always, even after a stop)
Write `roadmap\overnight\MORNING_REPORT_2026-10-20.md` in plain language for Idle (short sentences, no jargon without a one-line explanation). Cover:
- One-paragraph summary: what landed, what did not, where it stopped.
- Per run (F9 check, PERROOMK, BLOOM): Step 0 findings count, which were self-applied and which stopped the chain.
- Test counts: pytest, node, selfcheck, harness, acceptance `--slow` (passed / failed / xfailed / skipped), compared with the F13 row; any flakes with both runs.
- CPU: medians and worst case for each gated scene vs 2.40 ms.
- Versions: WORKLET_VER, `app.js?v=`, `live_fdn.js?v=`, `pack_room.js?v=`, before and after.
- New pins: wasm, `live_stereo.c`, Temp DLL sha1s, moved MD5s old -> new, room k and mid T60 table (hall, cube, small room, boot).
- Listening files to play, full paths, in order, with what to listen for (PERROOMK hall before/after and boost in dB; BLOOM B2 order: Nuke bass, Room Crush drums, Swell mix, Natural vocal, 610-A and Neve vocals, Glue mix; then Set 2).
- Any stop: the exact rule number and file, the exact numbers, and options for Idle.
- Restore status: which backup, pins verified yes/no.
- Open questions left for Idle (PERROOMK open questions, BLOOM R3 open items, the Step 0 "for Idle to confirm" items).
- Backups and manifests created, with sizes.
Then end the session. Do not start any other prompt.
