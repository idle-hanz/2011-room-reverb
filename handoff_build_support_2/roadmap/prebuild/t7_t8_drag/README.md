# T7/T8 prebuild: drag walls, ceiling and mics; per-strip room spots (U2, U4)

**Files:** `drag_model.js` (pure maths, no DOM), `test_drag_model.mjs` (12 pass), demo `../app_copy_files/mockups/t7_t8_drag_demo.html`, `prove_t8.py`, Python draft `../tests_py/test_t7_room_spots_draft.py`.

## Behaviour (proven in the demo, `shots/t8_*.png`)
- Hit band 8 px on each wall, 12 px corners (only after the object hit-test misses). The cursor follows the wall direction.
- The opposite wall stays put. Dragging the left or back wall shifts every x or z (source, B, stand, room spots), so objects stay put on screen.
- Grab offset is kept: no jump on pointer-down.
- Shift = 0.1 m snap, otherwise 0.01 m. Limits come from the sliders: W 1–80, L 2–120, H 1–40.
- "stop" mode (default): a wall stops 10 cm short of any object, and the label says "(stopped at an object)". "push" mode clamps objects instead. **Small decision D-DRAG (recommend stop):** stop never moves a mic or source silently.
- The ceiling is dragged on the side view and stops 10 cm above the highest mic or source.
- Live label: "Width 7.49 m · Length 9.00 m". Double-click a wall → `fieldForWall()` names W/L/H for typing (use T1 typing).
- Mic drag: **Mirror** (L/R symmetric, space = 2|x − mcx|, as mic_desk.js 1056–1062), **Linked** (moves the stand), **Split** (R becomes a room mic with its own spot). A strip set to Room always moves its own spot.
- The layout is frozen while dragging and refits on release, so the pointer maths stays stable. While growing, the room may draw past the canvas edge until release.

## Key finding (VERIFIED)
The server already accepts per-strip mic positions: app_server.py **637-648** (line fix 2026-10-09) (`mic_x_/mic_y_/mic_z_/mic_pos_<cap>`), desk_matrix.py **51–54, 330–333**. app.js `heardMix()` (starts line **509**; room-spot copy **541-549**) copies the one shared `room_x/y/z/yaw` into them. **So per-strip room spots (T7) are a client-only change:** migrate `room_*` → `room_<cap>_*` (`migrateRoomSpots`, bit-exact) and read the per-strip fields at 541-549 (491-503 is the pan law; leave it alone). No server or engine change, so the T7 cut line can be smaller.

## Integration (current app copy)
1. Copy `drag_model.js` to `static/js/`, script tag before room_editor.js (index.html 893).
2. room_editor.js floor `pointerdown` (**741**): if `hitFloor()` (673) returns null, call `RRDrag.hitWall(px, py, floorLayout(geo))`. On a hit, start a wall drag with `beginWallDrag(state, hit, lay, px, py)` **before** `pickFloorKind()` (684) falls back to the nearest object. Today an empty click moves the last-dragged object (FAR = 90 px, line 99).
3. Floor `pointermove` (**780**): during a wall drag, `Object.assign(state, ctx.s0, wallDragTo(ctx, px, py, {shift}).patch)`, then the existing `onRoomDim`-style clamp (`RoomMath.clampRoom`) and redraw. Draw `label` near the wall. On hover set `canvas.style.cursor = RRDrag.cursorFor(hit)`.
4. Elevation `pointerdown` / `pointermove` (**830 / 864**): `hitCeiling()` / `ceilingDragTo()` the same way. `endDrag` stays at 974–978.
5. Freeze the layout: keep `lay` from pointer-down in the drag context (floorLayout 136–145, elevLayout 147–157). Refit on `endDrag`.
6. T8 mic drag in the Mic top view: mic_desk.js 1040–1065 already does Mirror. Route Split/Linked through `RRDrag.micDragTo` and keep `RoomMath.maxSpace`.
7. T7 state: add `room_<cap>_x/y/z/yaw` to state defaults (app.js ~92). Run `migrateRoomSpots` on load and recall. In `heardMix()` 491–503 read `src["room_" + cap + "_x"]` etc., falling back to `room_x`.

## Stop conditions
Stop if Mirror renders are not bit-exact before and after (D-UI25 acceptance), if any golden changes, or if dragging changes a value the matching slider could not reach.
