# T8 · Split part 2 + wall drag (U2, U4). Effort: high. Needs T1, T7. Decisions: **D-UI37 locked**: wall drag uses "stop" (no push).
Read `handoff_build_support_2\roadmap\prebuild\t7_t8_drag\README.md`; integrate `drag_model.js` into room_editor.js (pointerdown 741 before the pickFloorKind fallback, pointermove 780, elevation 830/864, endDrag 974–978; freeze the layout from 136–157 during drag) and mic_desk.js 1040–1065 for Split/Linked. P1 canvas scaling first.
- **Cut line:** mic drag (R and room mics) first; wall/corner drag next; ceiling drag and double-click typing only if green.
- **Golden impact:** none (sound changes only as the sliders do).
- **Done when:** `test_drag_model.mjs` passes in `software\tests` and a Playwright run on the real Room tab repeats `prebuild/shots/t8_results.json`-style checks.
- **Stop if:** a drag reaches a value the slider cannot, or an empty click no longer selects as before inside the room.

**Idle 9 Oct (D-ROOMMIC):** drag the room mic FIRST (floor x/z, side-view height, aim handle, own icon, stops 10 cm short of walls), before walls and corners. See roadmap\DECISION_ROOM_MIC_2026-10-09.md.
