# R01 · T1 Knobs and typed values (U1, U5, B2, B8)

**Key finding:** today the 13 desk knobs are transparent `<input type=range>` controls under a drawn needle (index.html 227–229, 246–248, 265–267, 284, 292, 305, 313; CSS app.css 1271–1302). So a click jumps the value to the pointer, there is no fine mode, no detent and no typing. The Width needle never moves because `paintDesk()` only paints trim and pan (626–628, 640–643): that is B2. **VERIFIED**

**Norms (sources):**
- WAI-ARIA APG slider pattern: arrows = one step, PageUp/PageDown = big step, Home/End, `aria-valuetext` for words such as "L30". https://www.w3.org/WAI/ARIA/apg/patterns/slider/ **VERIFIED**
- JUCE `Slider`: relative drag with `setMouseDragSensitivity` (pixels for the full range), velocity mode, and `setDoubleClickReturnValue` (reset). https://docs.juce.com/master/classSlider.html **VERIFIED**
- Pro Tools: Cmd/Ctrl-drag = fine, Option/Alt-click = reset to default. Logic Pro: Option-click reset, Shift-drag finer. Ableton: Shift fine, Delete = default. **ASSUMED** (from manuals' summaries, not re-read today)

**Recommended design (built and proven):** relative vertical/horizontal drag (180–240 px full range), Shift = 10× fine, a sticky 6 px detent at 0 dB / centre, double-click reset, wheel step, PageUp/Down, and click-the-readout-to-type with units. One helper also gives typing to every slider with an `<output id="X_out">` (21 found). Code: `roadmap/prebuild/t1_knob/`. Proof: real Mix tab, Playwright (`prebuild/shots/t1_*.png`).

**Touch points:** see `prebuild/t1_knob/README.md` (index.html after 901; app.js `syncUINow()` after 2414; optional removal of 626–628 / 640–643).

**Risks:** knobs inside `<label>` steal focus on click (handled: typing stops propagation). Touch devices need `touch-action: none` (in the css). Alt-click is not used, because Alt is also the Windows menu key in some browsers.

**Tests / goldens:** UI only, so **no golden change**. 8 node tests plus the Playwright proof.

**Decisions for Idle:** none required. Optional: the reset target is the HTML default (pan L = −1, C = 0, R = +1). A preset-aware reset would need a small extra.
