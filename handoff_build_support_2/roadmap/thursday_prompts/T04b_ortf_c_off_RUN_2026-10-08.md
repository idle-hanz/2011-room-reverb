# T4b — ORTF without C by default + "ORTF + C" preset (D20). Effort: medium. D20 locked by Idle 4 Oct 16:43. GOLDEN CHANGE: this is the only change in the session.

Start: read HANDOVER.md (root, Current pin wins). T1, T2, T3, T3b and T4 are in the tree. T4 shipped Smooth as a switch, default OFF; goldens unchanged. WORKLET_VER 52. Suite green after T4: pytest 112, node 20, selfcheck 45/45. Then read the skill.

## What D20 says (verbatim from DECISIONS_LOCKED_2026-10-04.md)

ORTF = C off by default; new preset "ORTF + C" = today's sound (C at 0 dB, 477 fold). Old scenes keep their stored C.

## Step 0 — before any edit

a) No git. Zip software\ AND harness\golden\ (handoff_build_support_2\3_phase_acceptance_tests\harness\golden) to "C:\Users\IdleHanz\Desktop\2011 Room Reverb\software_backup_2026-10-08_preT4b.zip". This is the pre-session tree and the revert point.
b) Record the six current sha1s (they should match the pin):
- GOLDEN_META.json d332b67fd31923280762700a0f2f8e1ec3a43368
- play_std_lock18_byp.f32 ca052f3f1f9af7c30a30b62139370b3468cb54a7
- play_std_lock18_col.f32 3774b7d5f284ca445306db153ba9bae35d637651
- play_std_unlocked_byp.f32 07dc23c3a35c5752f0d4f2a3b767a61f03fa9876
- play_std_unlocked_col.f32 53024c874192c4e0276be7fea4b1c2ec201f1a19
- render_std_unlocked_byp.f32 ebd77c3b599e80a037f4a3c552c93f6e37343d1b
Do not rerun the full suite before the edit.

## Build

Read handoff_build_support_2\roadmap\prebuild\t4b_ortf_c\README.md. Its line numbers are from before T1-T4, which all changed app.js, index.html and app_server.py, so find every anchor with rg and match on code:
- app.js MIC_PRESETS `ortf`: add an `ortf_c` copy (today's ORTF with C).
- state `third_mic`; `loadDeskPreset`: `ortf` -> "off", `ortf_c` -> "centre"; `matchPresetId`.
- index.html: add `<option value="ortf_c">ORTF + C</option>` in the preset select.
- app_server.py: an empty body, or ORTF without `third_mic` or `mic_gain_c`, -> C at 0 (off).
- Must play nicely with T2's L/R buttons and T3's MS presets: selecting ORTF / ORTF + C sets the centre strip the way T2 maps it; MS presets unchanged.
Copy tests_py\test_t4b_ortf_c_off_draft.py into software\tests; flip its strict xfail and remove the marker once it passes.

## Goldens

- Regenerate only the goldens whose scene is the ORTF default and that move because C is now off. Use GOLDEN_META reason "D20 ORTF C off (Idle 4 Oct 16:43)". Keep Smooth OFF in every render (T4 default).
- Each regenerated golden rendered with the new "ORTF + C" preset (or third_mic "centre") must match its OLD bytes, max-abs 0 for Play, null <= -120 dB for Render.
- Any golden for a non-ORTF setup that moves = fail.
- Update test pins (e.g. test_smix_desk render SHA1) only where they pin a regenerated golden, and say which.

## Done when

- The t4b draft passes with the xfail flipped.
- "ORTF + C" nulls against today's ORTF (<= -120 dB).
- Old saved scenes with `third_mic: "centre"` recall unchanged.
- T2 null rows, T3/T3b MS tests, the early-lane test, mirror and t18 still pass.
- Full suite at the end: pytest, node --test, selfcheck 45/45. Known flake test_a12: pass alone = note it.
- WORKLET_VER stays 52 unless a wasm change is truly needed (it should not be: this is preset and server default logic).

## Stop rule

Whole session or nothing. If any non-ORTF reference moves, or the regeneration cannot finish this session, restore software\ and harness\golden\ from the preT4b zip and report. Leave a clean, working tree.

## Report back

Files changed, which goldens were regenerated (old and new sha1s), the "ORTF + C" null numbers, the old-scene recall check, full-suite counts, WORKLET_VER, and one line on how loud the new default is versus before (direct-only and full IR, in dB) so Idle knows what to expect when he listens.
