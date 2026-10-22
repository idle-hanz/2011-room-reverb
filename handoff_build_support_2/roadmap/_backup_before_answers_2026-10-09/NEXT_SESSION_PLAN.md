# NEXT SESSION PLAN: Thursday Build sessions (written 4 Oct 2026, 22:05 BST)

Supersedes `_archive/NEXT_SESSION_PLAN_2026-10-01.md`. Build usage resets **Thu 8 Oct 2026, 10:28 BST**.
Sources (all synced): `roadmap/thursday_prompts/PROMPTS_INDEX.md`, `roadmap/THURSDAY_LIST.md`, `roadmap/DECISIONS_LOCKED_2026-10-04.md` (D18–D24, D-UI29–38, D-SL1–10, ST-1/ST-2, N11).

Rules:
- One prompt = one Build session (new window).
- Work above the cut line first and commit. Go below it only if the suite is green with time left.
- A stop condition ends the session cleanly with a report, never a half-merge.
- A session that changes goldens changes nothing else.
- Paths are relative to `handoff_build_support_2\`. Every prompt names its prebuild README (exact integration points; `rg` the anchor first).

| # | Session | Prompt (`roadmap/thursday_prompts/…`) | Effort | Goldens | Gate / needs | Prebuild |
|---|---|---|---|---|---|---|
| 1 | T1 Knobs + typed values | `T01_knobs.md` (first paste the HANDOVER block from `roadmap/DECISIONS_LOCKED_2026-10-04.md`) | medium | NO | — | `roadmap/prebuild/t1_knob/` |
| 2 | T2 Mixer L/R buttons | `T02_mixer_lr.md` | high | NO | — | `roadmap/prebuild/t2_mixer/` |
| 3 | T3 MS presets | `T03_ms_presets.md` | medium | NO (new MS tests) | — | `roadmap/prebuild/t3_ms/` |
| 4 | T3b MS sound (D18/D19) | `T03b_ms_sound.md` | medium | **MS references only** | T3 | `roadmap/prebuild/t3b_ms_sound/` |
| 5 | T4 EQ-1a Smooth | `T04_eq1a.md` | high | **YES (main)** | — | `roadmap/eq_plan/` |
| 6 | T4b ORTF C off (D20) | `T04b_ortf_c_off.md` | medium | **YES (main)** | T4 | `roadmap/prebuild/t4b_ortf_c/` |
| 7 | T5 U87 A/B render (box job, no Build usage) | `T05_u87_ab_render.md` | low | NO | T4, T4b. Early listen only; the switch gate is the SL7a A/B | — |
| 8 | P-D7 Play re-measure (PC step, no code) | `P_D7_play_remeasure.md` | low | NO | T4 | — |
| 9 | T7 Split, part 1 | `T07_split_part1.md` | medium | NO | T2, T3 | `roadmap/prebuild/t7_t8_drag/` |
| 10 | T8 Split, part 2 (drag) | `T08_split_part2_drag.md` | high | NO | T1, T7 | `roadmap/prebuild/t7_t8_drag/` |
| 11 | T9 Mic tab | `T09_mic_tab.md` | medium | NO | T7 | — |
| 12 | T10 Other tabs | `T10_other_tabs.md` | medium | NO | T8 | `roadmap/prebuild/mockups/` |
| 13 | T11 EQ-1b Movement | `T11_eq1b.md` | high | NO for the default (new Movement refs) | T4 | `roadmap/eq_plan/` |
| 14 | SL1 Room result readout | `SL1_surfaces_target_readout.md` | medium | NO (read-only) | T11 (order), T10 | `roadmap/prebuild/sl/` |
| 15 | SL2 Surfaces in Render | `SL2_surfaces_loop_render.md` | high | NO (Flat bit-exact; new Surfaces refs) | SL1 | `roadmap/prebuild/sl/` |
| 16 | SL3 Surfaces in Play | `SL3_surfaces_loop_play.md` | high | NO (Flat Play bit-exact) | SL2 | `roadmap/prebuild/sl/` (C core; JS glue to build) |
| 17 | SL4 Directional + calibration | `SL4_directional_calibration.md` | medium | NO | SL2 (SL3 for Play) | `roadmap/prebuild/sl/` |
| 18 | SL5 Treatment rows | `SL5_treatment_rows.md` | high | NO | SL4 | `roadmap/prebuild/sl/` |
| 19 | SL6 Auto-treat | `SL6_auto_treat.md` | medium | NO | SL5 | `roadmap/prebuild/sl/` |
| 20 | SL7a Default switch prep (Natural (air) mode, frozen `tests/refs_flat2011/`, U87 touch points, final A/B) | `SL7a_default_switch_prep.md` | high | **NO** (flags not flipped) | SL6 | `roadmap/prebuild/sl/` (Natural reuses `surf_loop`) |
| when OK | SL7b Default switch (Surfaces + Natural decay + U87 + real materials, one re-record) | `SL7b_default_switch.md` | high | **YES (all defaults; Flat parity stays bit-exact)** | **Idle's written OK on the SL7a final A/B**; whole session or nothing | — |

Do not run: `T06_u87_default.md` (merged into SL7b) and `SL7_surfaces_default_goldens.md` (split into SL7a/SL7b). Both are in `_archive/roadmap/thursday_prompts/`.

**Decisions open for Idle before SL4–SL6** (details in `roadmap/prebuild/sl/README.md`, "Findings"):
1. The Helmholtz Q: the model gives about 1.5–2, against the ASSUMED 3.
2. D-SL3: whether to keep the per-axis cuts below 30 Hz (treated plan 16/23 kept, 15/23 dropped).
3. The SL4 mild double slope in the untreated plaster room: directional or room average.
4. Treatment also colours the early reflections in Surfaces mode.
