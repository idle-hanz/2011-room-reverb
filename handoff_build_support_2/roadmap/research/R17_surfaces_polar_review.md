# R17 · Deep design review: Surfaces and Polar

## Surfaces
**Today (VERIFIED, `ui_audit_1004/shots/1600_surfaces.png` and crops):** one 2574 px page stacks:
- a room net with curves
- a material chip row (illegal ones greyed)
- solo/mute cards
- a "Surface A" panel with 7 absorption sliders and face EQ sliders (shelves + peak)
- a Room Colour analyser ("Render to see Colour")
- Air (humidity, climate, ISO depth)

There are many ASSUMED badges and a repeated Room size sidebar. The 15 materials (`/api/surface_materials`) are 12 textbook tables plus 3 modelled panels (Miki 1990), with role rules (no carpet on a ceiling).

**Problems:**
1. Colour (face EQ) and absorption are two separate ideas on two screens, but both act on the same reflections before the FDN.
2. Air sits apart, although it acts on every path.
3. Free absorption sliders allow non-physical rooms.
4. The net does not scale to angled rooms (N faces are coming, R16 / NONRECT).

**Recommended design (mockup `prebuild/app_copy_files/mockups/surfaces.html`, shot `prebuild/shots/mock_surfaces.png`):**
- A signal-flow strip: Source → Surfaces (material + face tone) → Early + FDN → Air → Mics.
- A **Faces table** as the main control: one row per face, which scales to 5–10 faces. Each row has area, material, a 7-band absorption bar, face tone summary and S/M.
- A **Map**: unfolded box now, plan for angled rooms later.
- A **Selected face** panel: real materials only, grouped Hard / Wood / Soft / Absorber, illegal ones greyed with the reason, a data-source tag on each, and **Face tone** (the old Colour EQ, per face, before the FDN) with a one-bounce curve (material × tone).
- **Room result**: decay per band (Eyring from the faces, faces vs faces + air), with **Air moved here**.
- Free absorption sliders go to Advanced ("custom material").

**Touch points:** colour_surfaces.js (per-face sliders built at 434/472; materials `_loadMaterials` 1111; chips ~1100). The face EQ fields already exist (`low_shelf_db` … `high_shelf_hz`, 458–464). Air controls: index.html Air panel (ids humidity, air_shelf, air_lp). render_pipeline.py applies measured colour per FDN line (~981).

**Decisions for Idle:**
- **D-SURF1** Face tone = the old Colour, per face (recommend yes).
- **D-SURF2** Real materials only, with sliders in Advanced (recommend yes).
- **D-SURF3** Air moves into Surfaces (recommend yes).
- **D-SURF4** Should the faces drive the decay time, or does the decay dial keep the tail with faces shaping colour and early field only (today)? Recommend: keep the dial; show the Eyring estimate as a hint, plus a "match dial to room" button.

## Polar
**Today (VERIFIED, `1600_polar.png`):**
- a 3-D stacked tube of rings with L/C/R/Sum ticks (C unticked)
- a jargon banner ("Radius = |capsule gain| × 10^(H_db/20)…")
- Combined / Each mic / At speakers chips
- a footer that claims "same field as the Mic source plane" (B13: not true for all views)

**What it should show:** how loud each mic hears each direction, per band, plus the result at the speakers (mics × desk routing).
- **C:** draw C whenever the desk sends it (MS Mid, Decca, mono); draw it faint when muted. No manual tick.
- **Relation to Mic:** the Mic tab draws the same 1 kHz curve on the room plan; Polar is the per-band detail. Use the same colours and the same data (`/api/polar`).

**Recommended design (mockup `polar.html`, shot `mock_polar.png`):**
- 2-D small multiples (L, C, R) and "At the speakers" (L, R) instead of the 3-D stack.
- Bands red (125 Hz) → violet (8 kHz), rings every 6 dB to −24.
- A plain-words header and a short reading guide.
- Negative lobes (MS, polarity) dashed.
- Spacing/time is not shown, and the page says so.

**Touch points:** polar_field.js (renderer), app.js `/api/polar` fetch 2097 and toggles ~1815–1818, index.html Polar panel. B12 (jagged 3-D stack) goes away with the 2-D view.

**Decisions for Idle:**
- **D-POLAR1** 2-D small multiples replace the 3-D stack (recommend yes).
- **D-POLAR2** C follows the desk automatically (recommend yes).

**Tests / goldens:** none (UI). Playwright shots.
