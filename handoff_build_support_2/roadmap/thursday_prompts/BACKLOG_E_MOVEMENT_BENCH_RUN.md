# Backlog E — Movement bench only

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md` rules 17–22. One goal. Do not open `HANDOVER.md`. Routing preamps and compressors stay shelved.

Measure only. `MOVEMENT_FORCED_OFF` in `software\render_pipeline.py` stays true. Do not edit that flag, the curve under it, `software\engine\live_stereo.c`, the wasm, or `WORKLET_VER`. Do not un-force the knob. Un-forcing changes the tail and is a later listen run.

History, not a restore target. The 2026-10-10 G2 wasm is not today's `555414f1`. Shared-off Movement 100 was 2.718 ms (max 2.735) against 2.40 ms. Movement 0 shared-off was 2.258 ms. Shared-on at 100 was 1.893 ms against 2.133 ms. The decay-8 cube after the centre-tank skip was 1.717 ms keys off. Do not re-bench that cube, and do not bench shared-on.

One bench: harness scene `std_lock18` plus the t19 body (`source_radiation` `talking_head`, `source_radiation_b` `trumpet_byu`, yaw 35 and −25, `two_sources` true, shared tail off). Knob 0, then knob 100. Twelve `bench` calls each, burst 4, total 10, one Python process, back to back, nothing else rendering. Gate is the median of the twelve `play_median_ms` values at 100 minus the median at 0. Expect about 0: the flag returns 0 before the curve. Also quote each median, the max, and the gap from the 0 median up to 2.40. Each median must stay at or under 2.40. If 0 is not 2.258, say the bench moved and do not restore. If the delta is not about 0, stop. Name the gate, the amount, and one cause. Do not flip the flag to make them differ.

This named bench replaces t09, t15, and the two t19 lines. No audio file changes, so pytest, t03, and t04 stay off.

Write `handoff_build_support_2\roadmap\overnight\BACKLOG_E_MOVEMENT_BENCH\score.json`.

QUICK once, from `software\`, before the bench:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test tests\*.mjs
```

From the repo root, the bench:

```
software\.venv\Scripts\python.exe handoff_build_support_2\roadmap\overnight\BACKLOG_E_MOVEMENT_BENCH\bench.py
```

`bench.py` dumps the two bodies through `harness\lib\dump_params.py` into `%TEMP%`, then runs `node harness\lib\wasm_run.js` `bench 4 10` twelve times per body. `score.json` is the only file it writes under `overnight\`. Report under 20 lines.
