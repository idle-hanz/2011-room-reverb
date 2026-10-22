# R02 · T2 Mixer L/R buttons, mic-strip Solo, renaming Array/Room (U7, D-UI31)

**Key finding:** every L/R/Ø button state maps onto a route that already exists in app.js `pair()` (442–457). So D-UI31 needs **no engine change**. The null test (JS mapping → real `desk_matrix.fold_for`) holds for 6 routes × 2 phases × MS/non-MS × 5 pans (`prebuild/tests_py/test_t2_lr_null_draft.py`, 12 pass). **VERIFIED**

The tests found three traps; all are handled in `prebuild/t2_mixer/lr_buttons.js`:
1. A Mid strip already on pan/centre would turn into "both" (+6 dB) when re-read.
2. Pan at exactly ±1 should light one button, not two.
3. Old "both" on a non-Mid strip must stay "both".

**Solo norms (sources):** Solo-in-place (SIP) mutes the other channels on the main mix (destructive). PFL/AFL go to a cue bus and are not destructive. Sound On Sound "Q. What do Solo, PFL and AFL do?" https://www.soundonsound.com/sound-advice/q-what-do-solo-pfl-and-afl-do, and Sweetwater "What are PFL, AFL and SIP?" https://www.sweetwater.com/sweetcare/articles/what-pfl-afl-sip/ **VERIFIED**. The app has one output, so **SIP is the only workable kind**, and that is what the bus solos already do (app.js 281–284, 567). **Recommend:** mic-strip Solo = SIP through the same logic. Several solos add together. Bus solos and mic solos are independent (solo L + solo FDN = L's FDN feed only).

**Array / Room naming (VERIFIED app.js 491–503):** "Array" = the mic stays on the stand. "Room" = the mic is unplugged and placed at its own room spot. **Recommend plain labels "On stand" / "Room mic"**, with tooltips. This is a rename only, so there is no state change.

**Touch points:** `prebuild/t2_mixer/README.md`:
- route rows index.html 219–226 / 238–245 / 257–264
- Ø buttons 230 / 249 / 268
- `bindDesk()` 830–837 and 850–861
- `paintDesk()` 610
- `heardMix()` mic gains 488–490 for solo

**Risks:** the strip mute and "both off" share `mute_<cap>`. A user who mutes and then presses L un-mutes (intended, documented).

**Tests / goldens:** **no golden change**. 11 node tests, 12 pytest null rows, and the existing `tests/test_smix_desk.py` must stay green.

**Decisions for Idle:** (a) rename Array/Room → "On stand"/"Room mic" (recommend yes); (b) mic-strip Solo as solo-in-place (recommend yes).
