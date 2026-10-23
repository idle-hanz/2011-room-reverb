# Give test_a12 a settle that survives a loaded suite

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md`. One goal. Do not open `HANDOVER.md`. Do not change product code. Do not touch `app.js`, `routing_scene.js`, 610-A, Bloom coefficients, oversampling, makeup, the decay lock, or the 2.40 ms ceiling.

Review: `handoff_build_support_2\roadmap\CODE_REVIEW_2026-10-23.md`, finding 2, the settle only.

`test_a12_visible_controls_post_or_are_ui_only` in `software\tests\test_s_audit_ui.py` gives up inside `settle()` after 900 ms, and it may return once 80 ms have passed and three polls are quiet. `scheduleLiveParams` in `software\static\js\app.js` posts on a 45 ms timer. Under suite load that post arrives after `settle()` has already called the control quiet. The same test passed alone in 89.81 s. That red run is not a product fault.

Move the earliest wait from 80 to 200 and the deadline from 900 to 2500. Keep the three stable polls. Leave the 45 ms timer alone.

Routing ids are no longer in `_UI_ONLY_IDS`. Do not put them back. A quiet routing id means the strip did not post. Stop and report that id. Do not allowlist it, and do not edit the panel.

`test_a5` is the same kind of load flake. Do not touch it.

`app.js?v=70` and `routing_scene.js?v=3` stay. Empty live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`.

From `software\`:

```
.\.venv\Scripts\python.exe -m pytest tests\test_s_audit_ui.py::test_a12_visible_controls_post_or_are_ui_only -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
```

`test_a12` is slow. One run. No FULL. Report under 20 lines.
