# REVIEW REQUEST — the run plan from T4c onward (review only, NO code edits)

You are reviewing a plan, not building. Do not edit any file in software\ or the harness. Plan mode / read-only. Write your findings to handoff_build_support_2\roadmap\REVIEW_RUN_PLAN_findings.md (this is the only file you may create).

Context: Idle runs Build sessions from handoff_build_support_2\roadmap\thursday_prompts\ and NEXT_SESSION_PLAN.md. Done and in the tree (HANDOVER Current pin): T1 knobs, T2 mixer L/R, T3 MS presets, T3b MS sound (D18/D19, WORKLET_VER 52), T4 EQ-1a Smooth (shipped default OFF, switch on Room panel), T4b ORTF C off (D20, five goldens regenerated). D-SMOOTH-ON (Idle 8 Oct 21:22, roadmap\DECISION_SMOOTH_ON_2026-10-08.md): Smooth default ON, no decay correction.

## Plan to check

1. T4c — Smooth default ON (thursday_prompts\T04c_smooth_default_on_RUN_2026-10-08.md). Golden change.
2. T5 — U87 A/B render (box job, low effort).
3. P-D7 — Play vs Render re-measure on the PC (no code, report first).
4. T7 (split part 1), T8 (wall/mic drag, high), T9 (Mic tab), T10 (other tabs), T11 (EQ-1b Movement, high; new Movement refs only).
5. SL1–SL6 (Surfaces in the loop; opt-in mode, default stays bit-exact), SL7a (final A/B prep), then SL7b only on Idle's written OK.
6. Rules: every prompt is checked by Build in a review-only pass before code is written; golden-changing sessions zip software\ + harness\golden first (no git); stop on any failed gate; at most one small fix-up session before waiting for Idle; sound-changing choices go to Idle as decisions.

## Please check, against the real code and the locked decisions

a) Order and dependencies: is each session's "needs" in PROMPTS_INDEX.md still true after what actually landed (T3b wasm change, WORKLET_VER 52, Smooth switch, ORTF C off)? Anything that must move earlier or later?
b) Stale facts in the remaining prompts (T4c, T5, P_D7, T7–T11, SL1–SL7b): line numbers, file names, golden sha1s, the "box baseline 1/45 selfcheck fail" note (PC is 45/45), the t18 −71.8 target (now −71.9 after T4b), old WORKLET_VER numbers, anything referring to the ORTF default having C.
c) Golden handling: which later sessions regenerate goldens, and do their prompts say to regenerate from the post-T4b/T4c hashes? Is T11's "new Movement refs only" still true now that Smooth is default on?
d) Interactions: does Smooth default ON change what T5 (U87 A/B), P-D7 (Play vs Render at small_lock08), T11 or the SL sessions assume? Does ORTF C-off change T5, T9 or the SL calibration scenes?
e) Anything in the plan that would change the default sound without a decision from Idle.
f) Any risk, missing step, or wrong assumption you can see. Be specific: file, line, what is wrong, what to do instead.

## Report

Write REVIEW_RUN_PLAN_findings.md with: a numbered list of findings (each marked MUST FIX / SHOULD FIX / NOTE), the session each affects, and a one-line corrected order if you'd change it. If you find nothing, say so explicitly. Do not fix the prompts yourself; just report.
