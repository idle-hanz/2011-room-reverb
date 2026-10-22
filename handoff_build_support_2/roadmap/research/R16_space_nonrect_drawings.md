# R16 · Space tab drawings for non-rectangular rooms

**Today (VERIFIED, audit shot `ui_audit_1004/shots/1600_space.png`):**
- The Space tab draws the mirrored-room lattice (wireframe boxes), with view chips Lattice / Paths / Last legs and a "32 images · 32 FDN lines · mics C" line.
- A Hadamard size sidebar (8–128) sits beside it.
- The lattice only makes sense for boxes: in an angled room the mirror rooms do not tile, and most mirror sources are not heard. The prototype in `roadmap/nonrect/` found 2–9 % valid at order 4.

**Recommended design (mockup `prebuild/app_copy_files/mockups/space.html`, live 2-D image-source with validity back-trace):**
1. **Rectangle** (`#lattice`, shot `prebuild/shots/mock_space_lattice.png`): keep the lattice; every mirror source is heard. Hadamard size moves to Advanced.
2. **Angled room, mirror sources** (`#nonrect`, `mock_space_nonrect.png`): plan view, with first-order mirror rooms dashed. Heard sources are solid, blocked ones hollow. A side panel shows the counts (5 of 6 first order, 10 of 30 second order in the RFZ example) and the N(N−1)^(k−1) rule.
3. **Angled room, paths + arrivals** (`#paths`, `mock_space_paths.png`): each heard source drawn as its real bounce path, plus an arrivals strip (time vs level, coloured by order). This answers "what does the early field consist of" for any shape.

All three images were checked by eye and fixed: framing, label clashes, and the rectangle second-order count, which is now labelled as "4 repeat corner images".

**Touch points:** image_views.js (Space renderer; `/api/images` fetch app.js 1193). The non-rect engine work is the NONRECT brief (`roadmap/NONRECT_ROOMS_BRIEF.md`). The drawings need `/api/images` to return validity and the path points per image: two new fields, no change for rectangles.

**Tests / goldens:** none (view only). Add a Playwright shot per state.

**Decision for Idle:** **D-SPACE**: adopt the plan + paths view for angled rooms, keeping the lattice for boxes (recommend yes). Optional: show order 3+ only as counts (recommend yes; drawing them is noise).
