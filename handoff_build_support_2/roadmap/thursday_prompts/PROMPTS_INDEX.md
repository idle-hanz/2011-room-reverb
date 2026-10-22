# Thursday paste prompts (pointer prompts), updated 4 Oct 2026 16:55 BST; Surfaces-in-the-loop SL1–SL7 added 20:45 BST; one default switch (SL7a/SL7b, T6 merged) 20:50 BST; SL1–SL6 prebuild pointers + stubs archived 22:05 BST

All 14 decisions were locked by Idle at 16:43 (`../DECISIONS_LOCKED_2026-10-04.md`: D18–D24, D-UI32–38). Nothing is blocked by an open decision any more.

**2026-10-09 review:** T4, T4b and T4c have all landed. Every later prompt runs on the post-T4c tree (Smooth ON, ORTF C off, WORKLET_VER 52). Findings and the edits made from them: `../REVIEW_RUN_PLAN_findings.md`. **T6 is merged into SL7b** (20:40–20:41, Idle): Surfaces, natural decay (ST-1 + ST-2) and the U87 default switch together in **one** re-record. SL7b is gated on Idle's written OK on the SL7a final A/B (D-UI38 amended).

Sizing: each prompt is one Build session at high usage. Work above the cut line first and commit; below it only if the suite is green with time left. Stop conditions end the session cleanly with a report, never a half-merge. A golden-changing session changes nothing else.

| Run | Prompt | Effort | Goldens | Decisions | Gate |
|---|---|---|---|---|---|
| 1 | T01_knobs.md (+ paste HANDOVER block) | medium | NO | — | — |
| 2 | T02_mixer_lr.md | high | NO | D-UI31, D-UI36 | — |
| 3 | T03_ms_presets.md | medium | NO (new MS tests; `MS_LEVEL = "legacy"`) | D-UI29 | — |
| 4 | T03b_ms_sound.md | medium | **MS references only** (main NO) | D18, D19 | needs T3 |
| 5 | T04_eq1a.md | high | **YES** (main) | locked prompt | — |
| 6 | T04b_ortf_c_off.md | medium | **YES** (main) | D20 | needs T4 |
| 6b | T04c_smooth_default_on_RUN_2026-10-08.md | medium | **YES** (main) | D-SMOOTH-ON | **DONE 2026-10-09, do not paste again** |
| 7 | T05_u87_ab_render.md (box job) | low | NO | early U87 listen (the gate is now the SL7a A/B) | needs T4c (done) |
| 8 | P_D7_play_remeasure.md (PC step, no code) | low | NO | D21 | needs T4c (done) |
| 9 | T07_split_part1.md | medium | NO | D-UI37 | needs T2, T3 |
| 10 | T08_split_part2_drag.md | high | NO | D-UI37 ("stop") | needs T1, T7 |
| 11 | T09_mic_tab.md | medium | NO | — | needs T7 |
| 12 | T10_other_tabs.md | medium | NO | D-UI35 | needs T8 |
| 13 | T11_eq1b.md | high | NO for the default; new Movement refs | locked prompt | needs T4c (done) |
| 14 | SL1_surfaces_target_readout.md | medium | NO (read-only model) | D-SL1–9 | needs T11 (order), T10 |
| 15 | SL2_surfaces_loop_render.md | high | NO (Flat default bit-exact; new Surfaces refs) | D-SL1, D-SL3, D-SL7 | needs SL1 |
| 16 | SL3_surfaces_loop_play.md | high | NO (Flat Play bit-exact) | D-SL3, D-SL7 | needs SL2 |
| 17 | SL4_directional_calibration.md | medium | NO (Surfaces mode only) | D-SL2, D-SL4 | needs SL2 (SL3 for Play) |
| 18 | SL5_treatment_rows.md | high | NO (Surfaces mode only) | D-SL6, D-SL8 | needs SL4 |
| 19 | SL6_auto_treat.md | medium | NO (suggestions only) | D-SL5, D-SL9 | needs SL5 |
| 20 | SL7a_default_switch_prep.md | high | NO (flags not flipped; adds the frozen Flat (2011) parity suite) | ST-1, ST-2, N11, D-SL10, D-UI30 | needs SL6 |
| when OK | SL7b_default_switch.md ("Default switch") | high | **YES** (everything default, one re-record; Flat parity stays bit-exact) | D-SL10, ST-1/2, N11, D-UI30/38, D-SL1/6/8 | **Idle's written OK on the SL7a final A/B**; whole session or nothing |

**Surfaces in the loop (SL1–SL7), added 20:45 BST:** D-SL1–9 locked by Idle at 20:37 BST, 4 Oct (`../DECISIONS_LOCKED_2026-10-04.md`). Source: `../sound_tricks/SURFACES_IN_LOOP.md` + `proto2/`. They run after T11. The UI follows the T10/D-UI32 Surfaces mockup (`../prebuild/app_copy_files/mockups/surfaces.html`, Room result panel). Surfaces is an opt-in Decay mode, so the default golden stays bit-exact through SL1–SL6. Only gated SL7b changes it, and it switches Surfaces, natural decay and U87 in one re-record. `T06_u87_default.md` and `SL7_surfaces_default_goldens.md` are "do not run" stubs, moved to `../../_archive/roadmap/thursday_prompts/` (22:05 BST).

**SL1–SL6 are pre-built and tested (22:00 BST):** `../prebuild/sl/README.md` (engine modules, patches, Play C core, UI, tests, proof). Each SL prompt now says "integrate + test" and names its README block. The run order with gates is in `../../NEXT_SESSION_PLAN.md`.

Later (locked, not Thursday): D22 Physical realism, D23 tank gating, D24 velvet smear, D-UI32–34 Surfaces/Polar/Space redesigns (mockups in `../prebuild/mockups/`).
