# R09 · T9/T10 Layout, 1280 px Mix, Room size panel placement (U6, P14, B5)

**Key findings (VERIFIED, UI audit screenshots, build 51):**
- At 1280 px the Mix tab hides the Host strip (B5), because the bus strips sit in a fixed row.
- The Room size panel is repeated in the Source sidebar (and was in others). The Source floor canvas is only 472 px wide.
- Surfaces is a 2574 px page with the room net, materials, face EQ, Colour analyser and Air stacked vertically.

**Norms:** one control in one place (a value edited in two places drifts; this is the app's own D-UI rules). WCAG 2.2 reflow (1.4.10) says content should reflow without loss at 320 CSS px. We only need 1280, but the same idea applies: wrap the strips, never hide them. https://www.w3.org/WAI/WCAG22/Understanding/reflow.html **ASSUMED** (not re-read today)

**Recommended design:**
- Mix: buses wrap under the mic strips below ~1400 px (CSS grid `auto-fit, minmax(150px, 1fr)`). Never hide a strip.
- Room size lives **only on the Room tab** (W/L/H sliders + wall drag from T8). Other tabs show a read-only "6.0 × 8.0 × 3.0 m · edit" chip that jumps to Room. **Recommend this over a global header bar**, because the header is already full (Upload, Play, Render).
- Source: drop Room size and move Preview/status into the header, so the canvas can grow to about 700 px.
- Advanced: one place (L9), not per tab.

**Touch points:** index.html `#roomFields` (app.js 715–738 paints it), the Source sidebar panels, the Mix `.desk-strips`/buses CSS (app.css ~1240–1330). Mockups in `prebuild/mockups/` show the Surfaces/Polar/Space versions.

**Tests / goldens:** none (UI). Playwright screenshots at 1280 / 1600 / 1920 should replace the audit's.

**Decisions for Idle:** **D-ROOMSIZE**, where Room size lives: Room tab only + read-only chip elsewhere (recommended), or a global header bar.
