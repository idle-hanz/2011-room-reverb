# Process review (2026-10-22)

Read-only. No product file was changed. Minutes come from `BUILD_RUN_LOG.md`, `overnight\CHAIN_LOG.md`, and file stamps. A figure with no stamp is marked guess.

## Where the time goes

PERROOMK, a clean landing, 22:54–02:02, 188 min, measured.

- Pin check and the zip: 14 min (22:54–23:08).
- Step 0: 12 min. No stop.
- Edits and the proofs in that window: 35 min (23:20–23:55). That window includes golden checks and the hall plays.
- Pytest 37 min. Harness 8 min. Known-red acceptance 13 min. Acceptance `--slow` 50 min.
- CPU 5 min. Listens 4 min. Docs 4 min.
- Node is under 1 s. Selfcheck was about 18 s on the F9 run.

Those four test blocks are 108 min.

Bloom on 20 Oct, then a restore, 02:02–04:10, 128 min, measured.

- Step 0: 7 min, and it passed. The first zip missed the 86 MB render stamp and was retaken.
- Wiring and wasm up to the first harness file: about 36 min (02:12–02:48).
- CPU cluster: about 6 min. Neve 16x median 2.934 ms. Neve 8x median 2.209 ms, repeat 2.196 ms.
- Pytest: 37 min, finished before the alias gate.
- Alias table, restore, and the morning report: 19 min (03:51–04:10).

22 Oct stamps only.

- RETRY2 pre-zip 12:40, stop report 13:49. About 70 min. Alias failed 79 of 112. Full pytest did not run. Tree restored.
- Alias diag report 16:49. The gap after RETRY2 is 3 hours. Timed compute in that report is the prototype rescore, 343 s. The rest of the 3 hours is a guess.
- RETRY3 pre-zip 18:02, report 18:20. 18 min. Idle median about 2.79 ms, against 2.21 ms on 20 Oct. The 0.6 ms is left unknown. An overlapped first pass was discarded (p90 4.662 ms).

A cold start has no stamp. `HANDOVER.md` is 707 lines. `BLOOM_RUN_2026-10-19.md` is 270 lines. Guess 20–40 min when the chat is new. Step 0 inside a chain that had already checked the pin was 7–12 min.

Zips are 96–102 MB because `software\renders\out_20261013_115900.wav` is 86 MB. The 19 Oct pack took about 7 min (22:58–23:05).

## What I would change

The new run rules match this log: one goal, the suite once at the end, known-red is not a dig, a short stop. Six gaps are still open.

Score a new gate on the approved reference before any edit. Bloom Step 0 passed in 7 min and did not do this. The alias diag scored the prototype at 82 of 112 fail and the build at 79 of 112. Room Crush at 2x was the only preset with a finite pass. If the reference fails, leave the tree alone and hand the gate back. The pass number stays as written.

Keep a separate Step 0 only for a new numeric gate, or for an edit in `live_stereo.c`, `render_pipeline.py`, `surf_loop.py`, or the bloom files. UI, notes, and test-only work can land in the same session. On 9 Oct, plan mode blocked the review from writing its own file, so the review became a second session.

Grok Bot prompts should carry the goal, the files, the one gate, the quick command, and the stop line. A new gate also needs its reference score, or the words "not scored yet". Leave out restated locks, old hashes, side-issue diagnosis, and a request for a full pin table. A one-page current brief holds the locks, the hashes, the commands, and the real prompt path (`handoff_build_support_2\roadmap\thursday_prompts\`). HANDOVER stays the archive.

There is no `.git` at the root or in `software`. Undo is a zip, a manifest, an unpack, and a DLL rebuild. The same `live_stereo.c` has been rebuilt as DLL hashes `dcde61df`, `970e63bb`, `181d05cd`, `6b1612c7`, and `8408f9e0`. Selfcheck does not load that DLL. One commit of `software`, without `.venv` and without the render wavs, makes undo a checkout.

The quick tier needs a named command. The 22 Oct quick pytest was 19–21 s. Selfcheck is about 18 s. `test_b2_render_length` was 381 s and was killed at 174 s, so it stays out. Quick golden work is a hash compare. A re-render waits for the single full pass. Acceptance `--slow` stays off unless the prompt names a slow test. The known-red acceptance spends 13 min reprinting the same six failures.

CPU compares off then on, same boot, one process, with no other render running. The 20 Oct repeat moved 0.013 ms. The 22 Oct idle number sat about 0.6 ms above a different day's 2.21 ms, and that boot did not re-run the off case. Gate the delta. If the off case itself has moved, say the bench moved. The 2.40 ms ceiling stays.

## What else slows a new chat

- Score files live in `%TEMP%`. A restore drops them, and the next run measures again.
- Full pytest deletes the pinned 86 MB wav. F9 and Bloom both copied it back. One pre-Bloom zip was incomplete because that wav was missing.
- The Python path and the wasm port were both built before the Python alias result existed.
- The backlog still lists PHYSDEFAULT and Bloom as not started. About 77 lines are still open, including jobs that have since landed, so a new chat can pick a finished one.
- The injected memory note is long, and older pins in it disagree with the current block.
- One heavy bench at a time. The discarded RETRY3 pass ran while an alias render was still going.

## Top 5

1. Score a new gate on the reference before the edit. If it fails, do not build. Saves the failed cycles: about 70 min after the RETRY2 zip, the RETRY3 restore, and 37 min of pytest on 20 Oct. Sound risk: none. The gate number stays. Idle still owns the rule.

2. Run that gate before any suite. Full pytest and harness once, after a pass. Leave acceptance `--slow` off the default. Saves about 37 min on a stop like 20 Oct, and about 50 min on a landing that runs `--slow`. Sound risk: low. Pin hashes, MD5s, and golden hashes still run at each step. The full suite still runs once before a landing.

3. Same-boot CPU pair, and gate the delta. A median from another day stays a note. Saves a false restore when the machine has moved by tenths of a millisecond. Sound risk: low. A real jump still shows in the delta. Same-boot noise was 0.013 ms. The 2.40 ms ceiling stays.

4. Git commit instead of the 96 MB zip. Keep render wavs out. Ignore DLL hash drift. Saves the measured 7 min pack, plus unpack, stamp repair, and the hash writeup. Guess 10–20 min a run. Sound risk: low if C, wasm, Python, JS, and the golden f32 files are in the commit.

5. One-page current brief, and prompts that are only the delta. Step 0 only for a new gate or the audio core. Saves a cold read, guess 20–40 min, and a separate review session on small jobs. Sound risk: a short prompt can drop a do-not-touch line. The brief keeps that list. Step 0 stays on for the audio core.

## More suggestions

### The six gaps

1. A new gate is never scored on the approved reference. Bloom Step 0 passed in 7 minutes and did not catch this. The alias diag then scored the prototype at 82 of 112 fail and the build at 79 of 112. Room Crush at 2x was the only preset with a finite pass. Fix: the first step of a new gate is that score, on the reference, before any edit. If the reference fails, hand the gate back and leave the tree alone. Sound risk: none. The pass number stays. Idle still owns the rule.

2. Step 0 is its own session, and plan mode blocks the write. The 9 Oct review could not save its own report. PERROOMK's Step 0, inside a chain that had already checked the pin, was 12 minutes and found no stop. Fix: a separate Step 0 only for a new numeric gate, or for an edit in `live_stereo.c`, `render_pipeline.py`, `surf_loop.py`, or the bloom files. UI, notes, and test-only work build in the same session. Sound risk: none.

3. Prompts restate locks and old hashes. `HANDOVER.md` is 707 lines. `BLOOM_RUN_2026-10-19.md` is 270. The builder re-reads both and then reconciles them with the memory note. Fix: the prompt is the goal, the files, one gate, the quick command, and the stop line. A one-page brief holds the locks, the hashes, the commands, and the real prompt path. Sound risk: a short prompt can drop a do-not-touch line. The brief keeps that list. Step 0 stays on for the audio core.

4. Undo is a 96 MB zip plus a DLL rebuild. The 19 Oct pack took about 7 minutes. The same `live_stereo.c` has been rebuilt as DLL hashes `dcde61df`, `970e63bb`, `181d05cd`, `6b1612c7`, and `8408f9e0`. Selfcheck does not load that DLL. Fix: one git commit of `software`, without `.venv` and without the render wavs. Undo is checkout. A DLL hash mismatch is not a failed restore. Sound risk: low if C, wasm, Python, JS, and the golden f32 files are in the commit.

5. Quick has no named command, so slow tests get pulled in. The 22 Oct quick pytest was 19–21 seconds. Selfcheck is about 18 seconds. Node is under a second. `test_b2_render_length` was 381 seconds and was killed at 174 seconds. The known-red acceptance is 13 minutes. Fix: the prompt pastes one command, using `software\.venv\Scripts\python.exe`, for pin hashes, live-dict MD5s, golden file hashes, selfcheck, and node. `test_b2` and the acceptance pytest stay out of that command. Sound risk: low. The full suite still runs once before a landing. A golden file hash only proves the file was not edited. It does not replace one re-render. Keep harness t03 and t04 for that.

6. CPU medians are compared across days. On 20 Oct the same boot repeated within 0.013 ms (2.209 vs 2.196). On 22 Oct the idle median was about 2.79 ms, and that boot did not re-run the off case. The first pass was discarded because an alias render was still going (p90 4.662 ms). Fix: off then on, same boot, one process, nothing else rendering. Gate the delta. If the off case itself has moved, say the bench moved and do not restore. Sound risk: low. A real jump still shows in the delta. The 2.40 ms ceiling stays.

### Ten more, largest time save first

1. Plan the open backlog as six runs, not one prompt per row. The backlog still has on the order of 70 open lines, and many of them are a decision or a parked idea, not a session. Six runs cover the work that changes what Idle hears. Anything else waits.

   A is a decision, with no code. Which Bloom gate can the reference pass? The diag found a finite pass only for Room Crush at 2x. Most other presets were stuck no matter the oversampling. Until Idle picks that rule, another retry will restore again. Sound risk: none, because nothing is built.

   B is the UI leftovers: wall drag, the Mic-tab cleanup, save/load. The prompt forbids audio files. Tests are node and the quick pin command. No wasm, no full pytest, no harness. Sound risk: none if that forbid holds.

   C is off-axis tail colour and the return-EQ shapes (the Colour-module row), one switch, default off, goldens bit-exact. It is not a Bloom retry. Sound risk: the switch has to default off. An on-by-default switch moves the goldens and is a stop.

   D is non-rectangular rooms, stage 1 only. D-NR1 through D-NR5 and D-NR8 are already answered. D-NR7 parks the L-shape. D-NR6 is a full Surfaces page, not a map onto A–F. Render only. The Box stays bit-exact. Play, echo fades, and the L-shape are not in this run. Sound risk: the Box golden. If it moves, stop.

   E is a Movement bench only. The knob is forced off because an older wasm missed 2.40 ms. The centre-tank skip later brought the cube down near 1.75 ms. Measure on the current wasm. Do not un-force the knob in the same run. Sound risk: none on a measure. Un-forcing changes the tail, so that is a later run with a listen.

   F is one Surfaces re-scope, then one build. SL4, SL5, SL6, SL7a, and SL7b are five prompts for one idea, and SL7 is partly overtaken by the physics default. The note says what is left (directional decay, the U87 default, materials). The build does not flip a new default. Sound risk: directional decay changes the tail. Flat goldens stay bit-exact, or the run stops.

   Park, and do not write a prompt for: the book, the Studio One plug-in, a C migration, scatter and smear, diffraction, and "loudest 32". Sound risk of the whole split: putting two audio laws in one run. C, D, and F each stay one law.

2. Keep one live list with three headings: Next, Waiting on Idle, Parked. The session that writes a BUILD_RUN_LOG row moves that line in the same edit. A stop copies its one-line cause into the list the same night. Delete the "looks forgotten" section, or it becomes a second queue that nobody strikes. The backlog header still shows PHYSDEFAULT as waiting on Step 0, and Bloom as not started. A new chat can pick a finished job. Sound risk: none. The time saved is a whole session, when that happens.

3. The next prompt contains only the option Idle chose. The other options become backlog lines the same night, under Waiting or Parked. Bloom's three options (keep the images and report them, raise oversampling, or move the shaper) were argued again across the 20 Oct stop, RETRY2, the diag, and RETRY3. That is how a closed question costs another day. Sound risk: none.

4. How to write the prompt. One gate. Delete later gates from the file. Do not leave them under "also". Bloom stacked the alias rule, RT-2, the CPU ceiling, clicks, Play-vs-Render, the null rule, and the full suites. The first red ended the run. The rest was still read. When a sentence is wrong, replace it. Do not stack an override under the old paragraph. The builder follows both. Cap the prompt at about 40 lines. Put the real folder in it: `handoff_build_support_2\roadmap\thursday_prompts\`. A prompt that says `thursday_prompts\` at the repo root costs a hunt at the start. `BLOOM_RUN_2026-10-19.md` is 270 lines. Guess 20–40 minutes of cold reading, and the unread half still gets reconciled. Sound risk: low. The one-page brief keeps the do-not-touch list, so the short prompt does not have to.

5. Ask for a 20-line report and nothing else: which gate, by how much, one cause. Do not ask for a hash table, a VERIFIED tour of every pin, or a diagnosis of the next fault. RETRY2's stop report and the alias diag are long enough that the writing is a large part of the 70 minutes after the RETRY2 zip, and of the 3-hour gap before the diag file (guess, apart from the 343 seconds of prototype scoring). Sound risk: none. The pins still exist. They do not need to be copied into the report unless one of them moved.

6. What to cut from the suites, and what to keep. This is the part a short list gets wrong.

   Keep, every landing, once: full software pytest, harness t03 and t04, selfcheck, node. t03 re-renders the four play goldens. t04 re-renders `render_std_unlocked_byp`. That is the sound check. `test_quick_pins` and `test_smix_desk` only hash the golden files. A matching hash means nobody edited the file. It does not mean the engine still produces it.

   Cut from the default landing:

   - The acceptance pytest. Non-slow is 13 minutes (780 s on 20 Oct). `--slow` is another 50 minutes (3017 s). Harness already covers the twins: t01 pack against `test_p1`, t10 and t12 T60 against `test_p0_2`, t13 parity against `test_p0_4`, t14 level against the headroom t14 test. The same six failures are reprinted: `test_k1` on the ms preset, `test_p0_5` server defaults, the air-tint lock, `test_s3` mirror null at −38.9 dB, `test_s3` b_pose, and `test_sh_p1`. Run this suite when a prompt touches defaults, mirror, or two-source. Do not run it on a UI landing or a notes landing.
   - `test_b2_render_length` inside the default pytest. It took 381 seconds. Its golden re-render repeats t04. Its long T30 tails repeat what `--slow` already does. Name it when the prompt changes render length or the fade.
   - A second and third CPU bench. Harness t09 (silence), t15 (colour on, one source and two), and t19 (radiation) run inside the 8-minute harness, and the prompt then benches the decay-8 cube (5 minutes on PERROOMK). One scene per landing. If the prompt names a bench, skip t09 and t15. Run t19 only when the prompt names no bench.
   - Harness t05. Default `source_radiation` is already `omni` (`app_server.py`), so t05 repeats t03's unlocked bypass play. t06 targets that same file and is already pending, because the scatter key is not in the tree. Leave t06 pending. Skip t05 unless the prompt changes radiation.

   Do not cut selfcheck or node to save time. They are about 18 seconds and under a second. Do not cut the per-step quick pin command either. The duplicate is running the slow copies at the end, on top of pytest and t03/t04.

   Sound risk of these cuts: the known mirror null and the client/server default mismatch stay invisible on runs that skip acceptance. They already do not stop a run. A render-length regression waits until a prompt names `test_b2`. A silence or colour-on CPU miss on std_lock18 waits until a prompt names that scene. The named scene still uses the 2.40 ms ceiling. t03 and t04 stay, so the five TLAW goldens are still re-rendered once per landing.

7. Store the score json under `roadmap\overnight\<run>\`. `%TEMP%` is deleted with the restore, or it simply is not there next session, so the next run measures again. The diag's prototype rescore was 343 seconds, and RETRY2 and RETRY3 had already scored the build. Guess 15–40 minutes of repeat measuring on the following run. The prompt should name that path. Sound risk: none.

8. Give every prompt the quick command as lines Idle can paste. Use `software\.venv\Scripts\python.exe`. The Windows `python` alias is missing, and a wrong launcher burns the start of the session. The command is the pin file, selfcheck, and node. It is not "run the tests for the files you touched", because there is no map from file to test, and the builder guesses. When the prompt knows the test, it names the file. Sound risk: none.

9. A landing prompt lists the files that may change and the files that may not. "While you are there" is how a second goal gets in. Python and the wasm port are both built before the Python gate has passed. For a new DSP gate, the prompt says: prove it in Python, stop if that fails, and only then touch `live_stereo.c`. RETRY2 had a scratch wasm tap before the alias rule was known to be reachable. Sound risk: low. The risk is the opposite habit, shipping a Python-only change that Play does not share. The prompt's last step is still the Play port, after the Python gate passes. One run, two steps, with a stop between them.

10. Strike landed rows when you write the prompt, not after the build. Before Grok Bot writes the next prompt, it marks the backlog row it is about to open, and it does not open a row that says Landed, Waiting, or Parked. PHYSDEFAULT, F13, PERROOMK, and UI-TIDY-1 have log rows. The queue at the top of the backlog was written on 19 Oct and still describes them as not started. One pass that retitles those rows, before any new prompt, stops the next chat from rebuilding them. Sound risk: none.

### What Grok Bot puts in a prompt, and what it leaves out

Put in: the one goal, the files that may change, the files that may not, the one gate, the reference score or the words "not scored yet", the paste-ready quick command, the stop line, and where to write the 20-line report. If the gate is not scored yet, step 1 is the score and the run ends there.

Leave out: a copy of the locks, old hashes, a second goal, later gates, options Idle has not chosen, side-issue diagnosis, a request for a pin table, and an override block sitting under a paragraph it contradicts. Point at the one-page brief for the locks.
