# Non-rectangular studio rooms: research (no engine code)

4 Oct 2026, 15:40 BST, on the box. This answers Idle's 15:17 idea: preset studio-style room shapes that scale like today's box, with image sources computed as a tree, one branch per face. It extends `roadmap/NONRECT_ROOMS_BRIEF.md` (kept as the one-page summary). Earlier notes: `/workspace/non-cubic-rooms.md` (9 Sep).

**Tags:**
- **VERIFIED** = read in the cited source, measured with the prototype here, or read in the app code.
- **ASSUMED** = my judgement, a source seen only as a search summary, or a citation not re-read.

**Folder:**
- `proto/ism_proto.py`: a 3D polygon image-source prototype (Borish-style). It is not engine code.
- `proto/brute_check.py`: checks the pruning rule.
- `proto/results.json`: the measured counts.
- `proto/ism2d.py` and `proto/make_diagrams.py`: the 2D helper and the figure script.
- `diagrams/D1_branch_tree.png`, `diagrams/D2_backward_check.png`, `diagrams/D3_counts.png`.

---

## 0. Is Idle's idea right?

| Idle's claim | Verdict | Tag |
|---|---|---|
| Image sources as a tree, one branch per face | **Right.** This is Borish's extension of the image model to arbitrary polyhedra (Borish 1984). | VERIFIED |
| Count = faces^order + 1 | **Not quite.** A face can't reflect twice in a row (the second mirror puts the image back on the parent), so each node has N−1 children. Order k has **N(N−1)^(k−1)** candidates, and the **total up to order K is 1 + Σₖ N(N−1)^(k−1) = 1 + N[(N−1)^K − 1]/(N−2)**. Example: a box (N = 6) at order 4 gives 1 + 6 + 30 + 150 + 750 = **937**, not 6⁴ + 1 = 1297. Savioja & Svensson (2015) give the same sum. Kuttruff's shoebox figure (about 1.46×10⁷ candidates up to order 10, of which 1560 are valid, quoted by Wayverb) matches it exactly: 6(5¹⁰ − 1)/4 = 14,648,436. | VERIFIED |
| Each image needs a straight line from the image through to the mic, passing through every face in its chain, else it's occluded | **Right in the unfolded picture**, where the line must pass through the *mirrored copies* of the faces. In practice it is done **backwards without building mirrored rooms**: mic → deepest image; the crossing point must lie inside the last face's outline; from that point to the parent image through the previous face; and so on down to the source. | VERIFIED |
| (My quick answer) plus blocking tests for non-convex rooms | **Right.** Borish names three tests: validity (the reflection happens on the room side of the face), visibility (it hits the real face, not its infinite extension) and obstruction (nothing blocks the path). | VERIFIED (via a secondary summary of Borish and Savioja & Svensson) |
| Missing from both answers | (1) The **parent-side test** (the parent image must be in front of the face) is independent of the receiver and prunes a whole branch (see §3). (2) Even in convex rooms, **first-order images can be invisible** when a face is small; the prototype hexagon has 7.8 of 8. | VERIFIED (prototype) |

---

## 1. How many images are valid? (prototype, VERIFIED)

**Method:**
- `ism_proto.py` builds 3D rooms from face polygons and runs the tree up to order 4.
- It counts the formula's candidates, what is left after the parent-side prune, and the images audible at the mic.
- Each figure is the mean of **30 random source/mic pairs** per room, at 1.1–1.8 m high and ≥ 0.4 m from walls.
- **Check:** the box gives 6, 18, 38, 66 valid images, which is exactly the shoebox lattice count 4k² + 2. So the code agrees with Allen & Berkley's lattice.

| Room (faces) | Order 1 | Order 2 | Order 3 | Order 4 | Valid, orders 0–3 / 0–4 |
|---|---|---|---|---|---|
| Box 6×4.5×3 m (6) | 6 of 6 (100 %) | 18 of 30 (60 %) | 38 of 150 (25 %) | 66 of 750 (9 %) | 63 / 129 |
| Hexagon booth, R 1.6 m (8) | 7.8 of 8 (97 %) | 24 of 56 (42 %) | 48 of 392 (12 %) | 81 of 2744 (3 %) | 81 / 162 |
| Splayed control room, 4→6 m, sloped ceiling (6) | 6 of 6 | 18 of 30 (60 %) | 38 of 150 (25 %) | 63 of 750 (8 %) | 63 / 126 |
| LEDE-style, splayed front (8) | 6.6 of 8 (83 %) | 21 of 56 (37 %) | 45 of 392 (12 %) | 79 of 2744 (3 %) | 74 / 153 |
| Gable-ceiling vocal booth (7) | 6.6 of 7 (94 %) | 19 of 42 (46 %) | 40 of 252 (16 %) | 68 of 1512 (4 %) | 67 / 135 |
| L-shaped live room, non-convex (8) | 5.1 of 8 (63 %) | 15 of 56 (27 %) | 31 of 392 (8 %) | 53 of 2744 (2 %) | 52 / 105 |

**What this means:**
- Valid images grow roughly like the box's 4k² + 2, while candidates grow like 7^k. **At order 4 only 2–9 % of candidates are real.**
- Every shape still has **more than 32 valid images by order 3**. Today's `LIVE_32` uses orders 0–4 as 1 / 6 / 11 / 10 / 4 (VERIFIED, `engine/early_field.py:257`), so an order-3 or order-4 search is enough to fill 32 taps.
- The L-shape loses the most because of blocking. Its direct path is blocked in some pairs.
- See `diagrams/D3_counts.png`.

---

## 2. The visibility and occlusion algorithm, step by step

**Room model:** a closed set of planar face polygons with normals pointing into the room. The prototype extrudes a floor polygon to a flat or sloped ceiling; the gable booth is built face by face.

**A. Build the tree (depends on the source and room only):**
1. The root is the source S.
2. For each node P whose last face is f, and each face g ≠ f: if P is **not strictly in front of g's plane**, skip g and its whole branch (parent-side test, §3). Otherwise the child is I = mirror(P, g), with face chain (…, g).
3. Stop at order K, or when the image is further from the room than the longest wanted delay allows (distance cut; such an image's children are further still).

**B. Backward check for each node (depends on the mic):** see `diagrams/D2_backward_check.png`.
1. Set p = mic. Take the deepest image I_k and its last face f_k.
2. The mic must be in front of f_k and I_k behind it. Intersect the segment p → I_k with f_k's plane to get the crossing point q.
3. **Outline test:** q must lie strictly inside f_k's polygon (point-in-polygon in the face plane). Otherwise the path is invalid (it would hit only the extension).
4. **Direction test:** q must be in front of the previous face in the backward walk; otherwise the path would leave through the back of a wall.
5. **Blocking test (non-convex rooms only):** the segment p → q must not cross any other face.
6. Set p = q and move to the parent image I_(k−1) and face f_(k−1). Repeat steps 2–6.
7. Finally the segment p → S must be clear (blocking test in non-convex rooms). If every step passes, the reflection is real.

**Output:** the path length (delay), the hit points (the arrival direction at the mic for polar patterns), and the face chain (gives the per-face material and colour product for D-UI26).

---

## 3. Speedups, and when a branch can be pruned

**Parent-side prune: safe for the whole branch, in any room (VERIFIED).**
- If the parent P is behind or on face g, no path that reflects off g right after P can exist. The real segment arriving at g comes from the room side, and P lies further back on that same line, so P would have to be in front of g.
- Every descendant contains that same step, so the whole subtree is dead for every mic position.
- **Brute-force check (`brute_check.py`):** with no pruning, 3088 audible paths over 48 source/mic pairs across all six rooms. Pruning removed 0 of them.

**Visibility failure: can't prune (VERIFIED).**
- A node that is hidden at this mic (outline miss or blocked) can still have audible children, because the path takes a different route through other faces.
- Prototype: **16–36 % of hidden nodes below order 4 had at least one audible descendant** (box 36 %, splayed 35 %, gable 30 %, hexagon 23 %, LEDE 21 %, L-shape 16 %). `D1_branch_tree.png` shows an example: Front → Left is hidden, but one of its children is heard.
- Wayverb and Savioja & Svensson describe audibility as checked per path at the receiver (VERIFIED).

**Beam tracing (Funkhouser et al. 1998; Laine et al. 2009) (VERIFIED):**
- Keep, with each node, the "beam": the region reachable from the image through the chain of face outlines.
- Only spawn children for faces that overlap the beam. A branch whose beam is empty, or misses every face, can never be valid for **any** mic position, so it is pruned before the per-mic check.
- The results are identical to the image-source method, with far fewer nodes. The precomputed beam tree then serves a moving listener quickly.
- This is the "stop around the corner" rule from the 9 Sep notes.

**Caching:**
- The tree depends only on the room and the source, so a **mic move only re-runs step B**.
- A source move rebuilds the tree. A room size or shape change rebuilds both.
- Prototype cost per source/mic pair at order 4, in pure Python: tree 2–6 ms, backward checks 19–63 ms (VERIFIED, `results.json`).
- With numpy vectorisation, an order-3 cap or the distance cut, this should fall to a few ms (ASSUMED); compiled code is likely below 1 ms (ASSUMED).

**Hybrid sieving (Vorländer 1989) (VERIFIED):** ray tracing finds which images are visible, then image sources give exact timing. This is useful only for high orders; not needed for 32 taps.

---

## 4. Studio shapes worth having as presets

All presets scale with the existing W / L / H sliders: vertices are stored as fractions of W and L, and heights as fractions of H. The Box stays the default.

| Preset | Geometry (proposal) | Why studios use it | Source |
|---|---|---|---|
| **Splayed control room (RFZ-style)** | Side walls splayed 120° to the front wall (30° each side) over the front half; ceiling rising toward the rear | Sends early reflections away from the mix position. D'Antonio & Konnert: "side walls are splayed 120° with respect to the front wall… we have reduced the number of sources from 8 to 6"; trapezoidal baffle and rising ceiling; the reflection-free zone extends about 4 ft above and 6 ft behind the listener | VERIFIED (D'Antonio & Konnert 1984, AES preprint, RFZ.pdf) |
| **LEDE** | Splayed/dead front, parallel rear with diffusers (the diffusers are not modelled: geometry only) | Davis & Davis: "an effectively anechoic path between the monitor loudspeakers and the mixer's ears which extends for at least 2 to 5 ms beyond the studio's initial time delay gap" | VERIFIED (JAES 28(9), 1980, quoted in Audio, Aug 1987). The exact preset geometry is ASSUMED |
| **Non-parallel live room** | Box with one side wall and the ceiling tilted 6° each (≥ 12° total between opposite surfaces) | Breaks flutter echo between parallel walls; it does **not** remove low-frequency modes | ASSUMED (Everest, *Master Handbook of Acoustics*; Adrian James flutter study; seen as search summaries only) |
| **Hexagon drum/vocal booth** | Regular hexagon prism, 120° inner angles | Commercial six-sided booths exist (KUBE polygon booths, 120° internal angles) | ASSUMED (vendor page via search summary) |
| **Gable / "cathedral" ceiling booth** | Box floor, two sloped ceiling planes | No parallel floor and ceiling, so no vertical flutter | ASSUMED (no primary source found) |
| **L-shaped live room** | Non-convex; one leg can be an alcove | Gives a live room with a "round the corner" spot; the hardest case (blocking) | ASSUMED (common room type); geometry VERIFIED in the prototype |

**Recommended first presets:** Splayed control room, LEDE-style and the Non-parallel live room. They are convex, so there are no blocking tests or extra CPU, and they are studio-relevant. Then Hexagon booth and Gable booth. The L-shape comes last (non-convex, more glitches).

---

## 5. What the engine would need

**Where the box is baked in today (VERIFIED):**
- Images are integer lattice indices (`image_position*`, `early_field.py:83–181`).
- The 32 taps are a fixed index table (`LIVE_32`, :257).
- FDN line i delay = tap i distance (`engine/fdn.py:785–814`).
- Surfaces assume six faces A–F.
- Polar patterns only scale tap gains, never change which images are chosen (see THURSDAY_LIST U9).

**Choosing the 32 early taps and FDN delays when the set isn't regular (decision D-NR2/3):**

| Option | How | Pros | Cons |
|---|---|---|---|
| (a) Per-order quota like `LIVE_32` | Take the nearest valid images per order: 1 / 6 / 11 / 10 / 4 | Same tail structure as today; independent of pattern (keeps the U9 rule) | Some orders may run short in small or odd rooms (fill from the next order) |
| (b) First 32 by delay | Sort valid images by path length | Simple, geometric | Biased to low orders in big rooms |
| (c) Loudest 32 at the mic | Weight by pattern | Most energy | Changes with yaw and pattern; the same issues as U9 |

- **Recommendation: (a)**, with taps chosen by geometry only.
- **FDN delays:** either (i) from those 32 taps as today, or (ii) **frozen per preset and source**, computed at the stand (not at each capsule) so a mic drag doesn't move the line lengths.
  - **Recommendation: (ii)**, so the tank stays stable while early taps update. The mean-free-path option 4V/S (Kosten) is kept as a fallback (ASSUMED).

**CPU (VERIFIED for where the work happens, ASSUMED for the numbers):**
- The geometry runs where `compute_taps` runs now: in Python on a parameter push (`live_fdn_params`, render_pipeline.py:1936).
- The worklet DSP cost does not change: still 32 taps plus an N-line Hadamard.
- At 20–70 ms per push in pure Python (order 4), drags would update at about 15 Hz. That needs caching (§3), an order-3 cap for Play, or numpy.
- Render can afford order 4 or more.

**Glitches when reflections appear or vanish (VERIFIED by measurement):**
- A mic walk in 1 cm steps (2 m; 0.7 m in the two small booths), counting set changes (orders ≤ 3): box 0, L-shape 2.5 per m, splayed 7 per m, LEDE 11.5 per m, hexagon about 30 per m, gable about 39 per m.
- Each event switches a tap on or off, which clicks if done hard.
- **Fix:** fade a tap's gain to or from 0 over about 10–20 ms instead of switching (ASSUMED value). DIVA updated image-source parameters at 20–30 Hz with smooth interpolation (Savioja et al. 1999, VERIFIED).
- A physically smoother option for Render only is edge diffraction (UTD, Tsingos et al. 2001, VERIFIED), which fills the shadow edge.
- Keep the tap *slot* stable: a tap that vanishes keeps its slot at gain 0 until a new image takes it after the fade.

**Box parity (VERIFIED as a requirement):**
- The Box keeps today's code path untouched, so the `ebd77c3b…` golden, `test_mirror_exact` and reaktor_parity are unaffected.
- The polygon engine is a separate path used only when shape ≠ Box.
- **Cross-check test:** run the polygon engine on a box and assert it finds the same image positions as the lattice (the prototype already gives 4k² + 2).

**Surfaces:** N faces instead of A–F. Map each new face to its nearest A–F group by default, so the existing material cards and the D-UI26 per-line colour still work.

**Scattering delay network alternative (De Sena et al. 2015, VERIFIED):**
- One scattering node per face, at its first-order reflection point, fully connected by delay lines.
- First-order reflections are exact; higher orders are approximate. CPU is FDN-like.
- The authors say it extends to arbitrary polyhedra, though the published examples are shoeboxes.
- It would **replace** the Hadamard FDN topology, so no parity with the 2011 engine is possible. Keep it as research, not the main plan (ASSUMED judgement).

---

## 6. Staged plan

| Stage | What | Size | Goldens |
|---|---|---|---|
| 0 | This research + prototype (done) | — | — |
| 1 | **Render-only prototype in the engine:** a `room_shape` parameter (Box default) with 3 convex presets scaled by W/L/H. Polygon image sources to order 4 with parent-side pruning and distance cut. Taps by per-order quota; FDN delays frozen from the stand. Faces mapped to A–F. Box path bit-exact; the polygon-on-box cross-check test | M | NO (Box untouched) |
| 2 | A/B renders for Idle: each preset vs a box of the same volume | S (box job) | NO |
| 3 | Play support: the cached tree, per-tap gain fades in the worklet, order-3 cap or numpy, mic/source clamped inside the polygon | M | NO (Box untouched; new shape references) |
| 4 | UI: shape picker; polygon outline on the Room/Source/Mic floor plans; Surfaces with N faces (works with U4 wall drag) | M | NO |
| 5 | Optional: beam tree, the L-shape and other non-convex presets with blocking tests, edge diffraction in Render, a C port, or SDN research | L | new references only |

**Decisions for Idle:**
- **D-NR1:** which presets first. Recommendation: Splayed control, LEDE-style, Non-parallel live room.
- **D-NR2:** how taps are picked. Recommendation: per-order quota, geometry only.
- **D-NR3:** FDN delays. Recommendation: frozen per preset and source, from the stand.
- **D-NR4:** Render-only first, Play later? Recommendation: yes.
- **D-NR5:** tap fade time. Proposal: 15 ms (ASSUMED).
- **D-NR6:** default face-to-A–F mapping, or a full N-face Surfaces UI at once?
- **D-NR7:** is a non-convex L-shape wanted at all (extra CPU, more glitches)?
- **D-NR8:** park SDN as research only? Recommendation: yes.

All of these change the sound only when a non-box shape is picked. The Box default stays bit-exact.

---

## Sources
- Allen, J. B. & Berkley, D. A. (1979). Image method for efficiently simulating small-room acoustics. JASA 65(4), 943–950 (VERIFIED, read 9 Sep).
- Borish, J. (1984). Extension of the image model to arbitrary polyhedra. JASA 75(6), 1827–1836, doi:10.1121/1.390983. Validity, visibility and obstruction tests (VERIFIED via abstract and a secondary summary).
- Savioja, L. & Svensson, U. P. (2015). Overview of geometrical room acoustic modeling techniques. JASA 138(2), 708–730, doi:10.1121/1.4926438. Count sum, receiver-dependent validity (VERIFIED, snippet).
- Vorländer, M. (1989). Combined ray-tracing/image-source algorithm. JASA 86(1), 172–178, doi:10.1121/1.398336 (VERIFIED, abstract).
- Funkhouser, T. et al. (1998). A beam tracing approach to acoustic modeling for interactive virtual environments. SIGGRAPH 98, 21–32 (VERIFIED, abstract).
- Laine, S. et al. (2009). Accelerated beam tracing algorithm. Applied Acoustics (VERIFIED, text excerpt).
- Savioja, Huopaniemi, Lokki & Väänänen (1999). Creating interactive virtual acoustic environments. JAES 47(9) (VERIFIED, summary).
- Tsingos, N., Funkhouser, T., Ngan, A. & Carlbom, I. (2001). Modeling acoustics in virtual environments using the uniform theory of diffraction. SIGGRAPH 2001, 545–552 (VERIFIED, summary).
- De Sena, E. et al. (2015). Efficient synthesis of room acoustics via scattering delay networks. IEEE/ACM TASLP 23(9), 1478–1492 (VERIFIED, arXiv 1502.05751).
- Wayverb, image-source chapter (reuk.github.io/wayverb/image_source.html): Kuttruff's 1.46×10⁷ / 1560 figure, backward path check (VERIFIED).
- Davis, D. & Davis, C. (1980). The LEDE concept… JAES 28(9), 585–595 (VERIFIED via the 1987 Audio article quote).
- D'Antonio, P. & Konnert, J. H. (1984). The RFZ/RPG approach to control room monitoring. AES 76th Convention preprint (VERIFIED, PDF read).
- Everest, F. A. & Pohlmann, K. *Master Handbook of Acoustics*: splaying to stop flutter (ASSUMED, not re-read). KUBE polygon booths (ASSUMED, vendor summary).
