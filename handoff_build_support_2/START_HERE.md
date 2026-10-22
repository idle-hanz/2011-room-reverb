# START HERE: 2011 Room Reverb handoff (`handoff_build_support_2\`), 4 Oct 2026 22:05 BST

## STATUS as of Sat 17 Oct 2026 07:05 BST (this block wins over the table below)
- **Done and in the tree:** T1, T2, T3, T3b, T4, T4b, T4c, T7, T8, T9, T10, T11 (Movement forced off), FIX-A, FIX-B, TLAW, SL1, SL2, SL3, SRCDIST, PROX, PLACE. ROOMTONE is in the tree and stopped on the CPU gate (decay-8 cube 2.582 ms, ceiling 2.40 ms).
- **Live pin:** `WORKLET_VER` 56, `live_fdn.js?v=56`, `app.js?v=59`. Wasm and `live_stereo.c` hashes are the root `HANDOVER.md` Current pin. Five TLAW goldens. `GOLDEN_META` `883cc732…`. Empty-body MD5 `af2b154a…`. Stored-centre MD5 `f30665f4…`.
- **Queue, each one only when Idle starts it:** SMALLDECAY, SL4–SL7, F4, F5, F8, T8b, T9b, Movement revisit, D-UI32–34, T5, P-D7.
- **Leave as they are:** 1/r, SRCDIST, D-PROX, PLACE, Surfaces, the decay lock, and Movement off.
- **Do not** paste T01. **Do not** create `software\docs\HANDOVER.md`.
- **Rules:** every prompt is reviewed by Build (read-only) against the real code before it is built; golden-changing sessions zip software\ and harness\golden\ first (no git); long prompts are RUN_*.md files with a one-line paste.
- **Review findings:** `roadmap\REVIEW_RUN_PLAN_findings.md`. Build log: `roadmap\BUILD_RUN_LOG.md`.


## What to paste first
1. Open a new Build window on the job Idle named. The status block above is the queue. Do not paste `roadmap\thursday_prompts\T01_knobs.md`. Do not create `software\docs\HANDOVER.md`.
2. **`NEXT_SESSION_PLAN.md`** (this folder) keeps the 4 Oct run order. The status block wins over that table.
3. Each prompt names its prebuild folder. Read that README before editing; it has the exact integration points.

## Map
| Path | What |
|---|---|
| `NEXT_SESSION_PLAN.md` | The run order (the one plan) |
| `roadmap\thursday_prompts\` | Paste prompts + `PROMPTS_INDEX.md` |
| `roadmap\prebuild\` | Tested pre-built code: `README.md` (T1–T10) and `sl\README.md` (SL1–SL6) |
| `roadmap\DECISIONS_LOCKED_2026-10-04.md` | Every locked decision + the HANDOVER block |
| `roadmap\THURSDAY_LIST.md` | The full fix list and background |
| `roadmap\sound_tricks\` | SURFACES_IN_LOOP + SOUND_TRICKS research, prototypes, A/B audio |
| `roadmap\eq_plan\`, `roadmap\research\`, `roadmap\nonrect\` | EQ plan, research briefs, non-rect rooms |
| `ui_audit_1004\UI_AUDIT.md` | UI audit (4 Oct) |
| `book\` | Living technical book (draft 5 Oct): start at `book\HOW_TO_READ.md` (non-engineers) or `book\README.md` |
| `_archive\` | Superseded files; see `_archive\README.md` |
| `MD5SUMS_SYNC_2026-10-04.txt` | MD5 of every file in the 4 Oct 22:15 sync (box → PC) |
| older folders (`1_…` to `7_…`, `research_*`, `_runs`, `BIG_JOBS_ROADMAP_2026-10-01.md`, `DECISIONS_LOCKED_2026-09-28.md`, mirror briefs) | Earlier phases, kept for reference |

## Cleanup done 2026-10-05
With Idle's OK (5 Oct 06:47 BST), these temp items were deleted from the PC handoff folder: `ui_audit_1004\_stage\`, `ui_audit_1004\app_copy_1354.zip`, `roadmap\prompts\` (old prompts, replaced by `roadmap\thursday_prompts\`), `roadmap_sync_1004.zip` / `1004b` / `1004c` with their `_md5.txt` files, and `handoff_sync_1004d.zip`. Nothing is waiting to be deleted.

Never touch `software\` from these docs: Build sessions change it, one prompt at a time.
