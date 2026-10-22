# R07 · T7/T8 Free R mic, room-mic positions, wall drag and constraints (U2, U4)

**Key finding (VERIFIED):** the server already takes a separate position for every strip: `mic_x_/mic_y_/mic_z_/mic_pos_<cap>` (app_server.py 609–620, desk_matrix.py 51–54 and 330–333). Only the client shares one room spot: `heardMix()` 491–503 copies `room_x/y/z/yaw` into all of them. **So "one room spot per strip" and "R free in Split" are client-only work.** T7 shrinks from "engine and state" to state + UI, and Mirror stays bit-exact by construction.

**Recommended design (built and tested, `prebuild/t7_t8_drag/`):**
- Per-strip `room_<cap>_x/y/z/yaw`, migrated from `room_*` on load (bit-exact).
- Mic modes: Mirror (L/R symmetric about the stand), Linked (whole stand), Split (R becomes a free room mic).
- Wall drag on the floor plan: opposite wall stays put, objects stay put on screen, Shift = 0.1 m, slider limits.
- Default **stop** rule: a wall stops 10 cm short of any mic or source and says so. The alternative "push" would move objects silently, which changes the sound without the user asking.
- Ceiling drag on the side view. Grab offset kept. Layout frozen during the drag.

**Constraints:** W 1–80, L 2–120, H 1–40 (index.html 538–540). The stand space is capped by the nearer wall (`RoomMath.maxSpace`). Room mics clamp inside the room.

**Touch points:** `prebuild/t7_t8_drag/README.md`:
- room_editor.js 741 / 780 / 830 / 864 / 974–978, layouts 136–157
- mic_desk.js 1040–1065
- app.js state ~92 and 491–503

**Risks:** today an empty click moves the last-dragged object (room_editor.js FAR = 90 px, line 99). Wall hits must be tested before that fallback, or users lose the old behaviour silently. Recommend keeping the fallback only for clicks inside the room.

**Tests / goldens:** **no golden change** (Mirror bit-exact). 12 node tests plus 2 pytest drafts. The D-UI25 acceptance test (L = S, C = M, R = free room mic) becomes a client-only test.

**Decisions for Idle:** **Q5** (one Mirror/Linked/Split control replacing the Split tick + yaw chips; recommend yes). **D-DRAG** (stop vs push; recommend stop).
