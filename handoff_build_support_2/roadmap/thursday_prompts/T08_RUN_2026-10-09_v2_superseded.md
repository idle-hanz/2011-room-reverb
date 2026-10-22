# T8 - Source-page ROOM MIC drag only (D-ROOMMIC, D-UI37 stop rule). Effort: high. Needs T1, T7 (in the tree). Golden impact: NONE.

Start: read HANDOVER.md (root, Current pin wins; T1-T4c and T7 in the tree, WORKLET_VER 52, app.js?v=51), then the skill, then roadmap\DECISION_ROOM_MIC_2026-10-09.md. Build's read-only review of the first version of this prompt (roadmap\REVIEW_T8_findings.md, if present) found it unsafe; this version replaces it.

SCOPE. This session is the Source-page room mic only. Do NOT drag walls, corners or the ceiling (that is T8b). Do NOT do P1 (canvas scaling). Do NOT change applyTopDrag or the on-stand Mirror / Linked drag in mic_desk.js: on-stand L/R drag keeps setting space only. Do NOT route anything through micDragTo's Split branch.

Step 0: no git. Zip software\ to "C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-09_preT8.zip". Do not run the full suite first (green after T7: pytest 125, node 24, selfcheck 45/45).

Facts to rely on (verified by the review; re-check each with rg, line numbers may drift):
- Live software\static\js\drag_model.js already has roomSpot and exports it. Read the live file. Do NOT replace it with prebuild\t7_t8_drag\drag_model.js (it lacks roomSpot; test_t7_room_spots.mjs needs it).
- micDragTo writes only room_<cap>_x/z, clamps onto the wall, and its Split branch sets place_r = "room" without copying the stand pose. There is no height or aim function yet: add them in the live file. Do not use micDragTo's Split branch.
- A strip is Room only if place_<cap> === "room" or (cap C and third_mic === "room"); use the existing tests (stripIsRoom in app.js, roomPlaced in mic_desk.js). RRDrag.micPositions ignores the centre third_mic case: do not rely on it.
- A strip moves its room spot only when it is already Room. On the gesture that first sets Room, copy the stand pose with exactly the numbers snapRoomSpotToStand uses in app.js (stand X/Y/Z and toe) BEFORE applying the pointer delta, so the aim does not jump.
- room_editor.js has no room-mic drawing today: drawFloor draws L, C, R from geo.mic_left / mic_centre / mic_right; hitFloor returns only "source", "sourceB", "mic" or null; RoomMath.compute never reads room_<cap>_*. Keep today's bitmap pixels.
- Sync path is real: typing stores state["room_"+cap+"_"+k], syncUI paints #room_<cap>_x/z/y/yaw, RoomEditor onChange calls syncUI, heardMix posts mic_x/y/z_<cap> and the yaw only while that strip is Room. A drag must write only the four room_<cap>_* state keys, then call the existing setState and onChange. Never write mic_x_* directly.
- Leave the script order in index.html (room_editor.js, drag_model.js, app.js). Do not add a second script tag.

BUILD, in order:
1. For each strip that is Room, draw one object on the floor view and the side view in room_editor.js, from RRDrag.roomSpot (floor: x, z; side: z, y), NOT from geo.mic_left / look_l. Own handle and label, not on the L-R bar. Colours: L #a78bfa, C #2dd4bf, R #34d399 (stand handles stay COLORS.mic #60a5fa). A faint line to geo.source. That strip's pattern drawn along the room yaw. A small aim handle.
2. Hit-test the room-mic handles BEFORE the stand mic (hitFloor) and before any wall hit, so grabbing one never moves the stand.
3. Floor drag writes only room_<cap>_x and _z, stopping 0.10 m short of each wall. Side-view drag writes only room_<cap>_y (do not clamp it to the Mic height slider; keep it between 0.1 m and the room height minus 0.1 m). The aim handle writes only room_<cap>_yaw.
4. An empty click inside the room selects as it does today. Mirror, ORTF default and old scenes stay bit-exact.
5. Add node tests for the new height and aim maths in software\tests (point any copied test at ../static/js/drag_model.js, as test_t7_room_spots.mjs does) and keep test_t7_room_spots.mjs green.

PROOF. Do NOT run prove_t8.py and do not require prebuild\shots\t8_results.json (that proves a mock-up in Linux Chrome, not this tree). Instead write a Playwright script against http://127.0.0.1:7860 on the real #floorCanvas and #elevCanvas that shows: one floor drag, one height drag, one aim drag, each producing the same four-field values as typing the same numbers; the 10 cm stop at a wall; an empty click inside the room still selecting as before; no page errors. Save screenshots under handoff_build_support_2\roadmap\t8_room_mic\. The server on port 7860 may be an old process: restart it before the run, but only if you started it yourself; if Idle's is running, tell Idle to restart it and use another port for your tests.

Golden impact: none. The five goldens, wasm (65949a98c1212a29d252b8c075e7ff5946c7f8d2), live_stereo.c (3e3007f3586af26224470f6d207a2e7310d5a70f) and WORKLET_VER 52 unchanged. T7 nulls (all inside -120 dB) must still pass. Known flake test_a12_visible_controls_post_or_are_ui_only: rerun alone; pass alone = note it.

Stop and report (do not redesign) if: a drag reaches a value the matching field cannot, an empty click no longer selects as before, Mirror or an old scene is no longer bit-exact, any golden moves, or room_editor.js cannot draw a per-strip object without moving the stand mic hit-test.

Finish: update the HANDOVER Current pin, run the full suite (pytest, node --test, selfcheck 45/45), then report: files changed, test counts, Playwright results, anything skipped.
