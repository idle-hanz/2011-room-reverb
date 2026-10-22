# T1 prebuild: knobs and typed values (U1, U5, B2, part of B8)

**Files:** `rr_controls.js` (logic + DOM), `rr_controls.css`, `rr_controls_boot.js` (which knob gets which settings), `test_rr_controls.mjs`, `prove_t1.py`.

## Behaviour (all proven in the real Mix tab, `shots/t1_results.json`)
- Drag up or right to raise the value (relative, no jump to the pointer). Full range = 180 px for Trim, 240 px for Width, 200 px for Pan. 45 px up on Trim gave exactly +6.0 dB.
- Shift while dragging = 10× finer (45 px gave +0.6 → 0.5 dB at step 0.5). Shift can be pressed mid-drag without a jump.
- Detent at 0 dB / centre: holds within 6 px of travel. A drag from +6 dB ending 0.4 dB short landed on 0.
- Double-click resets to the default (the input's HTML `value`). Wheel = one step (Shift = a tenth). PageUp/PageDown = 10 steps. Arrow keys, Home and End stay native.
- Click the readout under a knob, or any slider's `<output id="X_out">`, to type: units and words work ("-4.5 dB", "L30", "C", "50 cm", "120 ms", unicode minus, comma decimals). Enter applies, Esc cancels, bad text flashes pink. 13 knobs and 21 sliders got typing in the copy.
- The value goes through the input's own `input`/`change` events, so app.js handlers, undo and recall run unchanged. The proof shows the app's weights line updating (C +0.689 +0.371 after typing L30).
- **B2 fixed for free:** the needle is painted from the value for every knob, including Width (+12 dB → 70°).

## Integration (exact points, current app copy)
1. Copy `rr_controls.js`, `rr_controls_boot.js` to `software/static/js/`, `rr_controls.css` to `software/static/css/` (or append it to app.css).
2. `index.html` after line 901 (`app.js?v=44`): add the css link and two script tags (cache-bust `?v=1`).
3. `app.js` `syncUINow()` (starts 2277): after `schedulePolar();` at **line 2414** add `if (window.RRControls) window.RRControls.refreshAll();`. This repaints readouts and needles after presets and recall.
4. Optional clean-up once green: delete the needle code in `paintDesk()` at **626–628** (trim) and **640–643** (pan). `refreshAll` paints both. Keep `pan.disabled` at 635–636.
5. CSS: `.knob` (app.css **1271**) grows to 40 px through `.rr-knob`. `.desk-strip.is-pan-locked .knob input` (**1302**) still blocks the pointer on locked pans; `.rr-knob` dims them.
6. B8 (Pan live on non-pan routes) is T2's job: when T2 marks the pot "none", set `pan.disabled = true` in `paintDesk()` at 635.

## Tests
`node --test test_rr_controls.mjs` (8 pass): drag maths, fine mode, snap/clamp, detent zone, wheel, parsing, formatting, needle. The UI proof is `prove_t1.py` (Playwright). It runs against any served copy and gave no page errors.

## Stop conditions for Build
Stop and report if any `input` handler in `bindDesk()` (747–848) stops firing (the weights line stops updating), if undo/recall misses a typed value, or if a golden changes (none should: this is UI only).
