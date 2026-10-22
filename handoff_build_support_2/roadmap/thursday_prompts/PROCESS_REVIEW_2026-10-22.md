# PROCESS REVIEW (Idle, 2026-10-22). Read-only. Plan mode, high effort. One session.

## The problem (Idle's words, plain)
Runs take hours, get bogged down in rabbit holes that never end, go backwards (stop, restore, redo), and ideas get forgotten. About 40-60 sessions of work are queued (roadmap\IDEAS_BACKLOG_2026-10-19.md). At this pace it never ends. Idle wants it faster without losing sound quality.

## What exists today
- Rules: thursday_prompts\RUN_RULES.md (new today: one goal, ~60 min box, no rabbit holes, quick tests per step, full suite once, short reports).
- Prompts are written by Grok Bot, each gets a Step 0 review then Step 1.
- Gates on most runs: sound pins/MD5s, goldens, selfcheck 45/45, pytest ~145, node 38, harness t01-t19, acceptance (6 known red), CPU 2.40 ms bench, RT-2, alias.
- Standing quality rule: Play = reasonable, lean on CPU. Render = perfect, no CPU limit.
- Backups: full zip + manifest before each run; on a fail, full restore.

## Recent examples to learn from
BLOOM_RETRY2_STOP, BLOOM_ALIAS_DIAG, BLOOM_RETRY3_STOP (roadmap\overnight\, 2026-10-22): three runs, each hours, each ended in restore. Gates were set before anyone checked they were reachable (UAD alias gate failed even for the approved prototype). CPU bench numbers moved 0.6 ms between days with no known cause.

## Your task
1. From BUILD_RUN_LOG.md and the overnight reports of the last ~2 weeks, estimate where run time goes (reading/orientation, edits, builds, tests, benches, diagnosis, restore). Rough minutes are fine; say which are guesses.
2. Review RUN_RULES.md and this process. What would you change? Consider: smaller prompts, Step 0 merged or skipped for small runs, checking a gate is reachable before using it, git branches/commits instead of zip restore, a fast test tier, a stable CPU bench (baseline re-run in the same session, tolerance), a short project brief so each new chat orients in minutes, what Grok Bot should put in or leave out of prompts.
3. Name anything slowing you down that we haven't seen.
4. Give a top-5 list of changes, each with expected time saved and any risk to sound quality.

No product edits, no fixes, no investigations of faults. Side issues: one line in IDEAS_BACKLOG. Write roadmap\overnight\PROCESS_REVIEW_2026-10-22.md, under 80 lines, plain words.
