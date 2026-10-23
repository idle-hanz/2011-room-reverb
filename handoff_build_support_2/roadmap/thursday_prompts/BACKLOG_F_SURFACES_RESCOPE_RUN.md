# Backlog F — Surfaces re-scope

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md` rules 17–22. One goal. Do not open `HANDOVER.md`. Routing preamps and compressors stay shelved. Do not start SL4.

Write the re-scope. Do not build a mode, flip a default, re-pin a golden, or render an A/B.

The old plan is one re-record: Surfaces + natural air decay + U87 (`DECISIONS_LOCKED_2026-10-04.md` D-SL10, ST-1, N11, D-UI38). That bundle does not match the tree. `phys_ceiling` is already the default (`app_server.py`, absent key is on). `decay_mode` absent stays `flat`. `DECAY_MODES` is still `("flat", "surfaces")`. Natural is the comment on that line, not a mode. U87 is not the default. SL1–SL3 are in. SL4, SL5, SL6, SL7a, and SL7b have not run. Movement stays forced off.

Read only: `handoff_build_support_2\roadmap\IDEAS_BACKLOG_2026-10-19.md` rows 2.1–2.4 and section 9 item 6, `handoff_build_support_2\roadmap\DECISIONS_LOCKED_2026-10-04.md` D-SL1 through D-SL10, and the five prompts `SL4_directional_calibration.md`, `SL5_treatment_rows.md`, `SL6_auto_treat.md`, `SL7a_default_switch_prep.md`, `SL7b_default_switch.md`.

Write `handoff_build_support_2\roadmap\BACKLOG_F_SURFACES_RESCOPE.md`. For SL4, SL5, SL6, SL7a, and SL7b, one line each: still do it, drop it, or wait for Idle, and whether that line changes the default golden. Name what PHYSDEFAULT already covered. Name the one remaining default change that still needs Idle's written OK. Do not list other options. If that remaining change is an audio law, stop after the note. Do not edit `software\`.

No audio file changes, so pytest, t03, and t04 stay off.

QUICK once, from `software\`, after the note:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test tests\*.mjs
```

Report under 20 lines. `software\` must have no diff.
