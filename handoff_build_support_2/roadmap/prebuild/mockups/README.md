# T10 / design mockups: Surfaces, Polar, Space (non-rect)

Static HTML that links the real `app.css`. Serve from `software/static/mockups/` and open `/static/mockups/<name>.html`. The numbers are computed in the page, so the layout reacts to real values. Screenshots: `../shots/mock_*.png`. Each one was checked by eye and fixed (overlaps, wrong claims, framing).

- **surfaces.html:** Faces table (scales to N faces), Map (unfolded box), selected-face panel (real materials only, grouped, illegal ones greyed with the reason, data-source tag on each), Face tone (the old Colour EQ, now per face and before the FDN), and Room result (Eyring per band, faces vs faces + air) with **Air moved here**. The signal-flow strip at the top says where each part acts.
- **polar.html:** plain-words header, 2-D small multiples instead of the 3-D stack, bands red → violet, C drawn faint when muted on the desk, "At the speakers" row = mics × desk routing, and a reading guide. Curves are first-order stand-ins; the real page uses `/api/polar`.
- **space.html:** three states (`#lattice`, `#nonrect`, `#paths`). Rectangles keep the mirrored-room lattice. Angled rooms switch to a plan with heard (solid) and blocked (hollow) mirror sources, reflection paths, and an arrivals strip. The geometry is a real 2-D image-source with validity back-trace.

Integration is T10 (and the non-rect project later): rebuild the three tabs to these layouts, keeping the element ids that app.js, colour_surfaces.js (434/472 build the per-face sliders) and polar_field.js read.
