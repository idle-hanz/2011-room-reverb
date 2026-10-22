# Current brief (2026-10-22)

Read this instead of `HANDOVER.md`. The Current pin in `HANDOVER.md` still wins if this page and that pin disagree. Prompts live in `handoff_build_support_2\roadmap\thursday_prompts\`. One goal per run. `RUN_RULES.md` in that folder.

## Pins

BLOOM landed 2026-10-22. `WORKLET_VER` 60. `live_fdn.js?v=60`. `app.js?v=65`. `pack_room.js?v=53`. `app.css?v=36`. `bloom_scene.js?v=1`. Wasm sha1 `e0692ef3ac8dcf0193dd463ea0695e67cfa3df46` (370549 bytes). `live_stereo.c` sha1 `b367464f82c37e7a17d217588e906f00ff5a47e7`. `bloom_live.inc` sha1 `57052071b6bdd2d72f1eae7204a2232afa4cd733`.

Off path held: empty MD5 `b6c55d429fa63d6d0d3cd1fcc7d23e88`, centre MD5 `b3e6bcd9dfa13ad737d2b15d561f7d30`, `GOLDEN_META` `a362cf5e490089807b39346ba207633b88511548`. Five golden sha1s are in `software\tests\test_quick_pins.py`.

Play / Render oversampling: Natural 2/2, Glue ADAA 1/1, Room Crush 1/2, Nuke ADAA 1/1, Swell 2/2, Neve 1/8, 610-A 8/8. Bloom panel is on the Mix page and defaults off. Python is `software\.venv\Scripts\python.exe`.

## Play lean, Render perfect

Play is a rough preview and must fit 2.40 ms. It may use lower Bloom and preamp oversampling. Render is the high-quality path and has no CPU ceiling. Shared-on Play ceiling stays 2.133 ms. Do not raise either ceiling.

## Do not touch

Do not retune 1/r, the 0.55 Direct fold, the desk, makeup freeze, source-distance makeup, Smooth, the limiter, or the decay lock. Do not force Play and Render onto one decay-lock `g`. Do not retune 610-A or chase its 9 kHz spike. Do not re-pin the five goldens on a bare continue. Do not start Phase 4, SL4, T9b, S-OUT, scatter, smear, or CPU fallbacks (c) and (d). Movement stays forced off. `c` stays 340. Do not flip L/R or floor X. Do not fold B into A's tank. Do not edit the original `.ens` files. Do not wire A–F bit tables into the audio path.

## Where files live

Canonical root is this folder (`HANDOVER.md`, `ensemble\`, `software\`, `findings\`). Live app: `software\Launch Tweak App.bat` at `http://127.0.0.1:7860`. Goldens: `handoff_build_support_2\3_phase_acceptance_tests\harness\golden\`. Backlog: `handoff_build_support_2\roadmap\IDEAS_BACKLOG_2026-10-19.md`. Pinned listen wav: `software\renders\out_20261013_115900.wav`. Screenshots stay in `C:\Users\IdleHanz\Pictures\Screenshots\`. Do not treat `2011-Room-Reverb-publish\`, Desktop zips, or `docs-*-tmp\` as the live tree.

## QUICK (after each step)

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test *.mjs
```

Add `pytest` for the test file you touched. Leave `test_b2_render_length.py` out.

## FULL (once, at the end)

Acceptance pytest, `--slow`, harness t05, and extra CPU benches stay off.

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_b2_render_length.py
```

From the repo root, after that pytest:

```
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t03,t04
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t19
software\.venv\Scripts\python.exe handoff_build_support_2\3_phase_acceptance_tests\harness\run_all.py --sw software --only t19
```

The two `t19` lines are the CPU delta: same boot, back to back, nothing else rendering. Each must pass the 2.40 ms Play ceiling. The delta is the second median minus the first.
