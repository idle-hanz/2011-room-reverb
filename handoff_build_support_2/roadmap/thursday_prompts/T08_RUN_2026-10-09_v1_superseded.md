# T8 - Room mic drag first, then wall drag (U2, U4, D-ROOMMIC, D-UI37). Effort: high. Needs T1, T7 (in the tree). Golden impact: NONE.

Start: read HANDOVER.md (root, Current pin wins; T1-T4c and T7 in the tree, WORKLET_VER 52, app.js?v=51, drag_model.js already added by T7), then the skill, then roadmap\DECISION_ROOM_MIC_2026-10-09.md.

Base prompt: roadmap\thursday_prompts\T08_split_part2_drag.md and prebuild\t7_t8_drag\README.md (integrate drag_model.js into room_editor.js: floor pointerdown before the pickFloorKind fallback, pointermove, elevation pointerdown/move, endDrag; freeze the layout during a drag; mic_desk.js Mirror/Linked/Split drag routing). T7 changed app.js, mic_desk.js and index.html, and drag_model.js may differ from the prebuild copy: read what is actually in the tree, find every anchor with rg and match on code, not line numbers. If Build's review pass found corrections, they win.

Step 0: no git. Zip software\ to "C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-09_preT8.zip". Do not run the full suite first (green after T7: pytest 125, node 24, selfcheck 45/45). Do P1 (canvas scaling) first as the base prompt says.

Cut line, in order, committing mentally after each:
1. D-ROOMMIC on the Source page: each strip that is on Room mic is its own object in room_editor.js (floor and side views), with its own icon and label coloured to match the strip, never attached to the stand. Drag it on the floor (x, z), drag its height on the side view, and turn its aim with a small handle. It stops 10 cm short of walls ("stop", D-UI37). A faint line shows distance to the source. Pattern and aim are drawn on the icon. Dragging writes the same room_<cap>_x/y/z/yaw fields the T7 typed fields use, so typing and dragging stay in sync. An empty click inside the room selects as before.
2. Mic drag in Mirror, Linked and Split through RRDrag.micDragTo (mic_desk.js), keeping RoomMath.maxSpace. A strip on Room always moves its own spot.
3. Wall and corner drag (hit band 8 px walls, 12 px corners, opposite wall stays put, "stop" mode, live label).
4. Ceiling drag and double-click typing only if everything is green with time left.

Golden impact: none (sound changes only as the sliders do). Mirror, ORTF default and old scenes stay bit-exact. The five goldens, wasm (65949a98...), live_stereo.c and WORKLET_VER 52 unchanged. T7 nulls must still pass.
Known flake: test_a12_visible_controls_post_or_are_ui_only: rerun alone; pass alone = note it.

Done when: test_drag_model.mjs passes in software\tests; a Playwright run on the real Room tab repeats prebuild\shots\t8_results.json-style checks AND includes a room-mic drag (floor, height, aim) that moves the same fields as typing; no page errors; full suite green.

Stop and report (do not redesign) if: a drag reaches a value the matching slider cannot, an empty click no longer selects as before inside the room, Mirror/old scene is no longer bit-exact, or any golden moves.

Finish: update the HANDOVER Current pin, full suite (pytest, node --test, selfcheck 45/45), then report: files changed, test counts, which cut-line steps landed, Playwright results, anything skipped.
