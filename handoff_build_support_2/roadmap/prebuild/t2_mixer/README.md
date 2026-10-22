# T2 prebuild: L/R buttons with polarity (D-UI31, U7)

**Files:** `lr_buttons.js` (pure, no DOM), `test_lr_buttons.mjs`, demo page `../app_copy_files/mockups/t2_mixer_demo.html`, `prove_t2.py`. The Python cross-check is `../tests_py/test_t2_lr_null_draft.py`: it runs the JS mapping in node, then checks the real `desk_matrix.fold_for` weights are identical for 6 routes × 2 phases × MS/non-MS × 5 pans.

## Model
Each strip has an L and an R button with three states: 0 off, 1 on, −1 on with Ø. A click cycles off → on → Ø → off. The buttons map onto routes that exist today (app.js `pair()` 442–457), so there is **no engine change**:

| L | R | route | phase | pot |
|---|---|---|---|---|
| on | off | l | +1 | none |
| off | on | r | +1 | none |
| on | on | pan (Mid of an MS pair: **both**) | +1 | Pan (none for both) |
| on | Ø | s | +1 | Width |
| Ø | on | s | −1 | Width |
| Ø | off / off, Ø | l / r | −1 | none |
| Ø | Ø | pan / both | −1 | Pan / none |
| off | off | muted (`mute_<cap>` = true) | — | none |

Edge cases found while testing (all handled and tested):
- **pan at exactly ±1 shows as L-only / R-only** (ORTF L and R strips light one button). Going from one side to both lands on the centre detent (`pan = 0`), so the click is always audible.
- **"centre" migrates to pan at 0**. The weights are identical under the locked linear law (D-UI4). They would not be under constant power.
- **A Mid strip that is on pan/centre today stays pan (`forcePan`).** Without this, L+R would become "both" and jump +6 dB. This is the only failure the null test caught.
- **Legacy "both" on a non-Mid strip is kept as both (`legacyBoth`)**, so there is no level jump on old scenes.

## Integration (current app copy)
1. Copy `lr_buttons.js` to `static/js/`. Add a script tag after index.html line 900 (before app.js).
2. index.html: replace each strip's route row (`<div class="route-row">` **219–226** L, the matching rows for C ~238–245 and R ~257–264) with two buttons, `<button class="lr-btn" data-lr="l" data-side="l">L</button>` + R. Remove the Ø buttons **230 / 249 / 268**. Keep `ms_s` (212) for now.
3. app.js `bindDesk()`: replace the `[data-route]` click handler at **850–861** with `Object.assign(state, RRLR.clickPatch(state, cap, side).patch); state.desk_touched = true; syncUI();`. Remove the phase click handler at **830–837**.
4. app.js `paintDesk()` (610): for each cap, call `RRLR.fromRoute(route, phase, mute, {msMid: RRLR.isMsMid(state, cap), pan: state["pan_"+cap]})`. Paint `data-v` on the two buttons and set the pot label and `pan.disabled` from `toRoute(...).pot` (this closes **B8**). The Width box toggle at 682–687 already follows route s.
5. Mic-strip Solo: add a `data-solo="l|c|r"` button per strip. Extend `SOLO_BUSES` (281–284) or add `solo_l/c/r` that zero the other mic gains in `heardMix()` (464, mic gains at 488–490). Solo-in-place (audible, destructive), as on the bus solos.
6. CSS: the `.lr-btn` rules in the demo page `<style>` are ready to move to app.css.

## Stop conditions
Stop if any golden or the S-MIX desk tests (`tests/test_smix_desk.py`) change, if an old scene loads with a different weights line, or if MS classic stops reading L+R = both on C.
