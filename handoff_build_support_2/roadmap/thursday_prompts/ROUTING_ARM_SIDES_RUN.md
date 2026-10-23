# Arm Array and Room the way Master already arms

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`. One goal. Do not open `HANDOVER.md`. Do not touch 610-A, Bloom coefficients, oversampling, makeup, the decay lock, or the 2.40 ms ceiling.

Review: `handoff_build_support_2\roadmap\CODE_REVIEW_2026-10-23.md`, finding 1.

`armMaster` in `software\static\js\routing_scene.js` sets Master Amount to 100 when the compressor menu moves from Off onto a preset and Amount is 0. Array and Room do not. `onRoute` in `software\static\js\app.js` only calls it for `route_master_comp`. Amount 0 means that strip posts nothing (`live()` in `routing_scene.js`). Play then has no section 13. Render has no array or room insert.

Do the same arm for `route_array_comp` and `route_room_comp`. A stored Amount 0 that is already on a preset stays 0, same as Master. Preamp menus stay as they are. A chosen preamp already posts at drive 0.

Update `software\tests\test_routing.mjs`. The line that requires array Amount to stay 0 after an Off-to-Glue menu change becomes 100, and the scene then posts. Remove `route_array_*`, `route_room_*`, and `route_master_*` from `_UI_ONLY_IDS` in `software\tests\test_s_audit_ui.py`. The R1 comment there is wrong after R2. Do not lengthen the `test_a12` settle in this run.

Bump the `app.js` and `routing_scene.js` cache query in `software\static\index.html` if those files change. Empty live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`.

QUICK, from `software\`:

```
node --test tests\test_routing.mjs
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py tests\test_routing.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
```

`test_a12` is not in QUICK. It is slow and it flakes under a full suite. Report under 20 lines. No FULL.
