# PLACE_SCALE RUN 2026-10-13: keep the source and mics inside a shrinking room (bug fix)
Evidence: roadmap\INVESTIGATE_SMALLROOM_DRONE_2026-10-13.md. Shrinking the room pins the source and stand to the walls/corner, Space falls to 0 (ORTF collapses to one point), five FDN lines share 3.06 ms, and the limiter takes 10 dB. A scaled interior scene does not drone or clip.
Locked, do NOT retune: 1/r, SRCDIST makeup_at_stand reference, D-PROX, Smooth, the limiter, 0.7, the 0.55 fold, the decay lock, Surfaces, Movement off. This run is placement only.

## Step 0: REVIEW ONLY (plan mode, no edits). Answer against the real code:
1. Every place a room-size change moves or clamps the source, the stand, the mic positions and Space (room_math.js clampRoom/clampInside, app.js applySize/applyPlace, the server clamp_inside_room, the T10 size chip). Which one pins to the wall and which one drives Space to 0?
2. The proposal: on a size change, scale the source and the stand positions proportionally with the room (relative position kept), then clamp to a wall margin (e.g. max(0.3 m, 10% of that axis)); never reduce Space or the mic spacing because of the room size; mics are never on or outside a wall. Does this conflict with any locked decision or with F5 (chips resetting mic positions)?
3. Are boot and all pinned scenes unaffected (no size change, so bit-exact)? List any test that posts a small room and would move.
4. Does Play and Render use the same clamp? A wasm change is not expected (WORKLET_VER 55 stays); confirm.
5. Check that with the fix, the 2 x 2.5 x 2.2 m guitar scene has no duplicate FDN delays and a limiter well below the 10 dB. Report-only plan.

## Step 1: BUILD (fresh session, after the corrections)
Backup software_backup_2026-10-13_prePLACE.zip. Implement the step 0 plan. The five TLAW goldens, GOLDEN_META, both live MD5s and all pins hold bit-exact (any move = STOP). Re-measure the investigation's three small rooms: peak, limiter, duplicate delays, T60 per octave; and write 2 guitar listens (before/after at 2 x 2.5 x 2.2 m) to roadmap\place\listen\. Full pytest, node, selfcheck; cache pins bumped only where changed; the HANDOVER Current pin and the BUILD_RUN_LOG landing. Report whether any drone remains, which would be a separate sound decision (the decay lock or room-tone cuts).

## ROUND 1 REVIEW CORRECTIONS (2026-10-13). Step 0 DONE; run Step 1 only. Follow the Step 0 "Step 1 plan" exactly:
- Scale ONLY inside onRoomDim (app.js), from the previous value of the axis that changed: sx, sz, sy, mcx, mcz, my, unmirrored source B, room_x/y/z, each room_<cap>_*, finite my_l/my_c/my_r. Then inset to max(0.3 m, 10% of that axis).
- Leave clampRoom, clamp_body, clamp_inside_room, applyPlace, drag_model.js (T8b) and the wasm untouched. test_a7 must stay unchanged.
- After clampRoom, restore Space if the capsules still sit inside (0, W); only if the pair is wider than the room, slide the stand, then shorten Space. Leave centre_dz alone. Parity on keeps mcx = W/2.
- WORKLET_VER 55 stays; only app.js?v=58 -> 59 (+ its test pin).
- Expected: the goldens, GOLDEN_META, both live MD5s, harness small_lock08/hall_lock40 and all pins bit-exact. The 4.5x6x2.8 page result moves (expected, not a golden).
- The "no duplicate delays" claim is dropped: print all 32 delay values per small room instead. Report any remaining 1.8 s ring as a later decay-lock decision.
