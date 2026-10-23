# Backlog D — non-rectangular rooms, Render only

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md` rules 17–22. One goal. Do not open `HANDOVER.md`. Routing preamps and compressors stay shelved.

Source: `handoff_build_support_2\roadmap\nonrect\NONRECT_RESEARCH.md` stage 1, and the 2026-10-22 answers in `IDEAS_BACKLOG_2026-10-19.md`. Prototype: `handoff_build_support_2\roadmap\nonrect\proto\ism_proto.py`. Do not wire `software\engine\polygonal_stub.py`.

One key, `room_shape`. Absent or `box` is today's shoebox. That path stays bit-exact. Three convex presets, scaled with W/L/H: splayed control room, LEDE, non-parallel live room. Polygon image sources to order 4, parent-side pruning, distance cut. Taps by per-order quota, geometry only. FDN delays frozen per preset and source, from the stand.

Render only. Do not edit `software\engine\live_stereo.c`, the wasm, or `WORKLET_VER`. Play stays the shoebox. No 15 ms tap fades (that is Play). No L-shape. SDN stays research. Do not map new walls onto A–F. The N-face Surfaces page is not this run.

Step 0 is on: the edit is in `software\render_pipeline.py`. Name the files and the key, then build. Plan mode stays off.

Gate, scored before the edit: empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`, centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`, and the five golden sha1s in `software\tests\test_quick_pins.py`. If any of them move while the shape is absent or `box`, stop. Name the gate, the amount, and one likely cause.

Do not retune 1/r, makeup, the decay lock, 610-A, or the 2.40 ms ceiling.

QUICK, from `software\`, after the box path is green:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test tests\*.mjs
```

Add the test file this run touches. `node --test *.mjs` from `software\` finds no files; the tests live in `tests\`. FULL once, at the end, only if the box path held: pytest without `test_b2_render_length.py`, then harness t03, t04, and the two t19 lines in `CURRENT_BRIEF.md`. Report under 20 lines.
