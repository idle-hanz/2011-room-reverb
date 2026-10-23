# Backlog C — off-axis tail colour, default off

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`. One goal. Do not open `HANDOVER.md`.

Source: `handoff_build_support_2\roadmap\DECISION_OFFAXIS_QUEUE_2026-10-18.md` item 1, the tail only. Not the on-axis restore. Not item 2 (the Colour module). Not return-EQ (backlog row 98). Those wait until Idle has heard this switch.

One new key. Absent or false on every scene that exists today. Off means today's filters, unchanged. Build the on path and leave it off: one K=3 SOS per mic bus, G_tail(f) = −DI(f) from the measured polar set, on the FDN output, outside the Hadamard loop, off inject. Same coefficients in Play and Render. Bloom's return gain stays before that filter. `software\mic_colour\HOOKS.md` and `software\engine\early_field.py` `apply_capsule_colour` are the notes. Do not call the dead function as it stands.

Step 0 is on, in this session: the edit is in `software\render_pipeline.py` and `software\engine` live C (`live_stereo.c`). Name the files and the key. Then build. Do not open a second plan-mode session.

Gate, scored on the current build before the edit: empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`, centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`, and the five golden sha1s in `software\tests\test_quick_pins.py`. If that score already matches, add the switch. If any of them move while the key is off, stop. Do not flip the default. Do not render a listen. Do not bench the on key.

Do not touch routing preamps, routing compressors, 610-A, makeup, 1/r, the decay lock, or the 2.40 ms ceiling.

QUICK after the off path is green, from `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test *.mjs
```

Add the test file this run touches. FULL once, at the end, only if that off path held: pytest without `test_b2_render_length.py`, then harness t03, t04, and the two t19 lines in `CURRENT_BRIEF.md`. Report under 20 lines.
