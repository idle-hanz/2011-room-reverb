# Non-rectangular rooms: research brief (no implementation)

4 Oct 2026, 14:55 BST, on the box. For Idle's "let's discuss non-rectangular rooms" (THURSDAY_LIST U10). Longer notes from 9 Sep: `/workspace/non-cubic-rooms.md`; toy code: `engine/polygonal_stub.py` (not wired in).

**Where the engine is today (VERIFIED):** early reflections are shoebox images indexed by integers (nx, ny, nz) (`image_position*`, engine/early_field.py 83–181; fixed table `LIVE_32` at 257). The 32 FDN line delays are those 32 image distances (engine/fdn.py 785–814). Surfaces A–F assume six faces. All of this depends on the room being a box.

**1. Image sources beyond the shoebox (literature, VERIFIED)**
- Shoebox images form a regular lattice and every one is a valid path, with no visibility test needed (Allen & Berkley 1979, JASA 65:943).
- For any polyhedron, mirror through each face's plane, then test each image: validity (front side of the face), visibility (the path actually hits the finite face, not its extension) and obstruction (Borish 1984, JASA 75:1827).
- Candidates grow as F^order (F = number of faces) while most fail. Non-convex rooms (L-shape, alcove) also need obstruction checks, and images appear or vanish as the mic or source moves: audible pops unless crossfaded.
- Practical limit for live use: order 2–3 with 5–10 faces (for example 8 faces, order 2 = 64 candidates), redone on each parameter push like `compute_taps` now. ASSUMED: CPU is fine in Python for that size.

**2. Hybrids (literature)**
- Exact image sources for the early part plus stochastic ray tracing (or a statistical tail) for the late part is the standard hybrid (Vorländer 1989, JASA 86:172; citation from memory, ASSUMED).
- Beam tracing finds the same specular paths while pruning hidden branches early, and suits interactive use (Funkhouser et al., SIGGRAPH 1998; ASSUMED citation).
- The Scattering Delay Network (De Sena et al., IEEE/ACM TASLP 23(9), 2015, VERIFIED) puts one node on each wall at its first-order reflection point, wires the nodes together with delay lines and gets first-order reflections exact plus an FDN-like tail at FDN cost. The authors say it extends to arbitrary polyhedra; the published examples and implementations are shoeboxes.
- For this engine, the FDN already makes the tail, so geometry only has to supply (a) the early taps and (b) the line delays and per-line absorption.

**3. What the FDN delay choice would need**
- Today line i = image i distance. For a non-box room, three options:
  - (A) Use the first N valid images from a Borish/beam search, ordered by delay. This is closest to today, but the set changes with positions, so it needs smoothing and crossfades.
  - (B) Use statistics: spread the delays around the mean free path 4V/S (Kosten), made mutually prime. Stable and cheap, but loses the "this room's geometry" link.
  - (C) Use SDN-style wall-to-wall path lengths (one line per face pair).
- The matrix can stay Hadamard N (32/64/128) whichever way the delays are chosen. Per-line colour needs each path's list of faces hit, which Borish gives directly.

**4. Costs and risks**
- The UI needs a polygon editor (floor polygon plus flat ceiling, a "2.5D" room, is the easiest first step), and the Surfaces tab needs N faces instead of A–F.
- Keep the shoebox path bit-exact, so the reaktor_parity goldens and `test_mirror_exact` are untouched. Non-box rooms would be a new mode with their own goldens. They change the sound by design, so they need a decision from Idle.

**Suggested order (proposal):** (1) a Render-only 2.5D polygon room, Borish order 2 early taps and option (B) delays; (2) A/B against shoebox; (3) only then consider live Play and option (A) or (C).
