# Backlog D — hear the off-axis tail

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md` rules 17–22. One goal. Do not open `HANDOVER.md`. Routing preamps and compressors stay shelved.

`offaxis_tail` is built and off. Absent or false is today's filters. This run is the listen. Do not flip the default. Not the on-axis restore. Not the Colour module. Not return-EQ (backlog row 98).

One checkbox on the Mix page, default unchecked. It posts `offaxis_tail`. A missing or false key still adds no live-dict field. Bump `app.js` in `software\static\index.html` only. Do not bump `WORKLET_VER` unless `live_stereo.c` changes.

Listen set, from `DECISION_OFFAXIS_QUEUE_2026-10-18.md` item 1. Guitar file `handoff_build_support_2\roadmap\robotic_1240\test_guitar_dualmono_clean.wav`. Boot room and the small room `3x4x2.5`. Key off and on. One family at a time on L, C, and R:

- LDC: `NeumannU87AiCardioid`
- SDC: `SchoepsCMC5UCardioid`
- double-diaphragm: `RodeNT2ACardioid`
- ribbon: `RoyerR121`

Write the wavs under `handoff_build_support_2\roadmap\offaxis_listen\`. Do not commit them. Do not retune 1/r, makeup, the decay lock, 610-A, or the 2.40 ms ceiling. Do not bench the on key as a gate.

QUICK, from `software\`, after the checkbox:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_offaxis_tail.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test tests\*.mjs
```

Empty MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`. No FULL unless the off path moves. Report under 20 lines. Commit the checkbox only.
