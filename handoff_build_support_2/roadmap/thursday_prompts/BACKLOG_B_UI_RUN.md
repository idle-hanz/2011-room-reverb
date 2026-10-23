# Backlog B — wall and ceiling drag (UI only)

Start at `CURRENT_BRIEF.md`. Follow `handoff_build_support_2\roadmap\thursday_prompts\RUN_RULES.md` rules 17–22. One goal. Do not open `HANDOVER.md`. No audio change. Empty live MD5 stays `b6c55d429fa63d6d0d3cd1fcc7d23e88`. QUICK only. Commit at the end.

Save and load already landed (`#saveSetupBtn`, `localStorage` in `software\static\js\app.js`). Do not redo them. Mic-tab B10/B11 is T9b. Do not start it. Routing preamps and compressors stay shelved.

`wallDragTo` and `ceilingDragTo` in `software\static\js\drag_model.js` have no caller. On `#floorCanvas`, a pointer that misses a source, mic, or room-mic handle and hits `RRDrag.hitWall` starts `beginWallDrag` / `wallDragTo` (mode `stop`; Shift snaps to 0.1 m). On `#elevCanvas`, the same miss plus `hitCeiling` starts `ceilingDragTo`. Handles still win. A click inside the room, off the 8 px band, still moves the selected object. Do not edit `drag_model.js`, the snap law, wasm, `live_stereo.c`, `render_pipeline.py`, `surf_loop.py`, or bloom DSP.

Merge the returned `patch` with `Object.assign` and `RoomMath.clampRoom`. Bump `room_editor.js` in `software\static\index.html`. Name the new pin in `CURRENT_BRIEF.md`.

QUICK, from `software\`:

```
node --test tests\test_wall_drag.mjs
.\.venv\Scripts\python.exe -m pytest tests\test_quick_pins.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe engine\selfcheck.py
node --test *.mjs
```

No FULL. Report under 20 lines.
