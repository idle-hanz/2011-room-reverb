# T1 · Knobs + typed values. Effort: medium. Decisions: none open.
First, paste the HANDOVER block from `handoff_build_support_2\roadmap\DECISIONS_LOCKED_2026-10-04.md` into `software\docs\HANDOVER.md` (decisions D18–D24, D-UI32–38).
Read `handoff_build_support_2\roadmap\prebuild\t1_knob\README.md` and integrate `rr_controls.js/.css/_boot.js` into `software` exactly at the points listed (index.html after 901; app.js `syncUINow()` after 2414). Re-check each line with rg first.
- **Do:** the 13 Mix knobs (drag, Shift fine, detent, double-click reset, wheel, PageUp/Down, click-to-type) and typing on every slider with an `<output id="X_out">`; B2 needle.
- **Cut line:** Mix knobs + helper first. Typing on other tabs and the per-face Surfaces sliders (colour_surfaces.js 434/472) only if green with time left.
- **Golden impact:** none (UI only). Run the full suite; any audio diff = stop.
- **Done when:** `node --test` on the copied tests passes; `prove_t1.py` against the PC server gives the same numbers as `prebuild/shots/t1_results.json`; no page errors.
- **Stop if:** a bindDesk handler stops firing (weights line frozen), undo/recall misses a typed value, or any golden moves. Report and stop; do not redesign.
