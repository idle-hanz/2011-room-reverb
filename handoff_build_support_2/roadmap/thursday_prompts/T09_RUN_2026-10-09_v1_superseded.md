# T9 - Mic-page ROOM MIC window + dead-control fixes B6, B7 (D-ROOMMIC). Effort: high. Needs T7, T8 (in the tree). Golden impact: NONE.

Start: read HANDOVER.md (root, Current pin wins; T1-T4c, T7, T8 in the tree, WORKLET_VER 52, app.js?v=51, room_editor.js?v=17, drag_model.js?v=2), then the skill, then roadmap\DECISION_ROOM_MIC_2026-10-09.md. If Build's review findings for this prompt exist (roadmap\REVIEW_T9_findings.md) they win over this text.

SCOPE. This session is the Mic-page Room mic window, then B6 and B7 only. B10, B11, P2, P4 and P10 are the NEXT session (T9b); do not start them. Do not change the engine, the wasm, heardMix posting, the boot places, or anything on the Source page (T8 is done). Do not add any drag that sets place_*.

Step 0: no git. Zip software\ to "C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-09_preT9.zip". Do not run the full suite first (green after T8: pytest 125, node 28, selfcheck 45/45).

Facts to re-check with rg first (line numbers drift):
- A strip is Room only if place_<cap> === "room" or (cap C and third_mic === "room"): use the existing tests, stripIsRoom (app.js) and roomPlaced (mic_desk.js ~871). Typed fields for X, Z, Height, Aim already exist per Room strip (T7: #room_<cap>_x/z/y/yaw, stored in state["room_"+cap+"_"+k], painted by syncUI). The Source-page drag (T8) writes those same four state keys. "Return to stand" is the existing On stand button: reuse its handler, do not write a second path. snapRoomSpotToStand (app.js ~526-535, ~1019-1023) already copies the stand pose when a strip becomes Room.
- A Room mic's aim is its own spot (mic_desk.js ~878, ~1014).

BUILD, in order:
1. Room mic window on the Mic tab, one per strip that is Room, below the stand mic sections, hidden when no strip is Room. Contents: a heading "Room mic (L|C|R)"; a "Return to stand" button (the existing handler); the X, Z, Height and Aim fields, i.e. the SAME four inputs T7 made (move or re-home them, do not duplicate ids; typing, T8 dragging and this window must stay in sync through state and syncUI); read-only "Source: x.x m" and "Nearest wall: x.x m"; that strip's own preset, pattern, HPF and gain controls (reuse the existing per-strip controls; Split already gives R its own, T7); a small polar diagram of that mic, reusing the existing per-mic pattern drawing, aimed along its room yaw. Use T1's typing helper (rr_controls) for any number shown.
2. Distances: compute from the same geometry the Source page uses (geo.source and the room spot). Display only; never post them.
3. B6: in Binaural hide #thirdMicRow, Link heights and the C capsule, the "C 0 cm" readout, and the three-capsules Combined caption; use a binaural caption and badge "Head: SADIE II KU100".
4. B7: when mic_setup is mono_c, hide the link and third-mic rows and disable "Off" (it would remove the only mic). Leave the ORTF centre-off default and the D-AUD-1 greying (monoStripLocked, app.js ~395-397) in place.
5. Node tests for any new pure maths (distance readouts); a Playwright script on the real Mic tab (use the Windows Chrome launcher and free-port pattern in software\tests\test_s_audit_ui.py ~21-31 and ~223-237; never touch Idle's server on 7860). It must show: the window appears only for a Room strip, edits in the window move the same fields and the Source-page object, a T8-style drag updates the window, Return to stand hides it, Binaural and Mono centre hide the dead controls, no page errors, at 1280 and 390 px wide. Save shots under handoff_build_support_2\roadmap\t9_room_mic_window\.

Golden impact: none. Mirror, ORTF default (C off) and old scenes stay bit-exact. The five goldens, wasm (65949a98c1212a29d252b8c075e7ff5946c7f8d2), live_stereo.c (3e3007f3586af26224470f6d207a2e7310d5a70f) and WORKLET_VER 52 unchanged. T7 stand-pose nulls stay <= -120 dB; test_dui25_r_is_a_free_room_mic still expects the moved R spot louder than -40 dB (do NOT make it a null). Known flake test_a12_visible_controls_post_or_are_ui_only: rerun alone; pass alone = note it.

Stop and report (do not redesign) if: a fix needs an engine change, the window needs ids that clash with T7's fields, any golden moves, Mirror/old scene is no longer bit-exact, or the 390 px layout loses a control's only copy off-screen.

Finish: update the HANDOVER Current pin, bump the cache pins in tests that pin app.js/mic_desk.js/index.html versions, run the full suite (pytest, node --test, selfcheck 45/45), then report: files changed, test counts, Playwright results, anything skipped.
