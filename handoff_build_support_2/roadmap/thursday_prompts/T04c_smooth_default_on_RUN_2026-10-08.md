# T4c — Smooth default ON (D-SMOOTH-ON, Idle 8 Oct 21:22). Effort: medium. GOLDEN CHANGE: the only change in this session. Needs T4b in the tree.

Start: read HANDOVER.md (root, Current pin wins), then the skill, then handoff_build_support_2\roadmap\DECISION_SMOOTH_ON_2026-10-08.md.

## Step 0
a) No git. Zip software\ and handoff_build_support_2\3_phase_acceptance_tests\harness\golden\ to "C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-08_preT4c.zip". This is the revert point.
b) Record the current golden sha1s from the Current pin (post-T4b). Do not rerun the full suite first.

## Build
- Flip the Smooth default to ON wherever T4 set it off: render_pipeline.py default, app_server.py posted-body default, app.js state/boot, and the Room panel checkbox (checked).
- A missing `smooth` key in a saved preset or body = ON.
- NO decay correction: lg stays on the existing decay-lock formula (T4 showed neither correction works for both rooms; Idle accepted the bass change).
- reaktor_parity, flat cards, mirror/null modes and MS direct-only checks still force Smooth OFF, whatever the UI or body says.
- Do not touch live_stereo.c or the wasm (the cap is applied where Dffs is built, shared by Render and Play). WORKLET_VER stays 52.

## Goldens
- Regenerate only the goldens that move because Smooth is now on. GOLDEN_META reason: "D-SMOOTH-ON: Smooth default ON, no decay correction (Idle 8 Oct 21:22, listened to eq1_out guitar A/B)".
- Each regenerated golden rendered with Smooth OFF must match its pre-session bytes (Play max-abs 0, Render null <= -120 dB).
- Any golden that moves for another reason = fail. Update test pins only where they pin a regenerated golden; say which.

## Done when
- Fresh boot shows Smooth ticked; posting smooth false gives the pre-session tree bit-exact.
- Parity/flat/mirror bit-identical to pre-session.
- t18 <= -60 dB (pre-T4 -71.8), test_mirror_exact <= -120 dB, T2/T3/T3b/T4b tests pass.
- Full suite: pytest, node --test, selfcheck 45/45. Known flake test_a12: pass alone = note it.
- Report default-room octave T30 Smooth on vs off once more (should match T4: 250 Hz about +8%), as a record.

## Stop rule
Whole session or nothing. If anything outside the Smooth default moves or regeneration can't finish, restore from the preT4c zip and report.

## Report back
Files changed, regenerated goldens old/new sha1s, the Smooth-off null numbers, the T30 table, full-suite counts, and the HANDOVER Current pin line.
