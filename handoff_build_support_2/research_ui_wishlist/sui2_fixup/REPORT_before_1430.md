# S-UI2 fix-up: Mic tab, Space camera, Colour → Surfaces, face EQ vs tail (3 Oct 2026, 08:18–09:20 BST; decisions locked 09:06/09:09)

Tree: PC snapshot `snapshot_2026-10-03_0818` (zip MD5 E3CC1C205CDE074E4B0516F0CC44D277). Latest PC edits: 2 Oct, 21:05–21:45 BST.
Method: I ran that tree headless on the box (Chrome at 1600×1000 and 1920×1080) and probed it with Playwright. For sound I rendered and played the default body through the harness. Nothing on the PC was changed.
Every claim is tagged **VERIFIED** (measured or read in code) or **ASSUMED**.
Idle's screenshots are `idle_shots/screenshot_534.png` (08:11 BST) and `screenshot_535.png` (08:12 BST).

Files:
- `FIXUP_PROMPT.md`: the paste-ready prompt for Build.
- `..\mock\m3_mic.png` (v3; v2 kept in `..\mock\old\`); source `..\scripts\m3_mic_gen.py`.
- `..\mock\m9_surfaces_colour_merge.png` (source `..\mock\src\m9_surfaces_colour_merge.html`).
- `scripts/`, `data/`, `shots/`.

---

## 1. Colour dropdown order
**VERIFIED.** `index.html:208-212` lists the options as Measured, Bypass, User defined (`ASSUMED_TOYS`).

**Fix:** reorder the options to **Measured · User defined · Bypass**. This is a markup change only. The values stay the same (`MEASURED_SHELF`, `ASSUMED_TOYS`, `BYPASS`), so saved states and the API are unchanged.

## 2. What each mode shows today, and what it should show

### Today (VERIFIED, probe `data/mic_probe.json`)

| Control | Measured | User defined | Bypass |
|---|---|---|---|
| Side/Centre **preset** dropdown | shown | shown | shown |
| High-pass row | shown, disabled for SM57 ("No high-pass · This microphone has none") | same | same |
| **Family / Polar** (Side and Centre) | **shown but greyed** (disabled), with lock text | enabled | enabled |
| Split L/R tick | shown and enabled (disabled only for MS classic) | same | same |
| Each capsule graphs (`#micEach`) | hidden | shown | shown |
| Sidebar "User defined capsule" (`#capsuleColour`, `index.html:697`) | **shown** ("not used in Measured") | shown | shown |
| "Play still uses the old shelf. Render uses this colour." (`#micPlayNote`, `index.html:214`) | shown | shown | shown. No JS reads this id, so it is static in every mode |

### Bugs found

1. **Lock text names the wrong pattern (VERIFIED).** `sideLockText` (`app.js:1129-1140`) words the side lock from `state.family_l`. With MS classic in Measured it says "Shure SM57 is a fixed fig-8". The SM57 is a cardioid; fig-8 is the setup's own value.
2. **Dead controls in "User defined capsule" (VERIFIED, by grep).** `render_pipeline.py` takes `mic_hp_on`, `mic_hp_hz` and `mic_proximity` (`:1012-1015`) but never reads them afterwards, so "Panel high-pass", "High-pass Hz" and "Proximity" do nothing in Render. Play's packed parameters come from the same taps.
   - ASSUMED: they do nothing in Play either. I did not test Play directly.
   - `mic_response_hz` and `capsule_mm` **are** used.

### Proposed (UI only)

| Control | Measured | User defined | Bypass (D-UI22, locked) |
|---|---|---|---|
| Preset dropdown | **shown** | **hidden** | shown |
| High-pass row | **shown** (enabled when the preset has one) | hidden | hidden (Bypass has no measured colour, so there is no HPF; VERIFIED below) |
| Family / Polar | **hidden** (not greyed) | **shown** | hidden |
| Split L/R | **shown** (D-UI25 = no, 09:09). Ticked: a **preset picker per side** (one shared Side high-pass row, since `mic_preset_l/r` exist but only `mic_hpf_sides` does; per-side HPF goes to S-MIX). L and R can be different measured mics, or the same mic doing different jobs. No pattern rows | shown (splits the pattern) | shown, splits presets (as Measured) |
| Each capsule graphs | hidden | shown | **hidden** (supersedes the D-UI19 "also in Bypass") |
| User defined capsule panel | hidden | shown, moved into the Mics panel, keeping only Response Hz and Capsule mm | hidden |
| Lock text | one line: "Pattern comes from the preset (SM57 = cardioid). Switch Colour to User defined to shape it." | none | "Bypass: preset pattern, no measured colour" |
| `#micPlayNote` | only if it is still true (see below) | hidden | hidden |
| Pattern-mismatch line | not needed: D-UI21 is locked, so Part B makes Measured always use the preset law | — | — |

`#micPlayNote`: Build should check it. ASSUMED: S5/S7 brought Play onto the same taps, so the note may now be wrong. If Play in Measured nulls against Render (the S7 path, −72 dB at 1140), delete the note. Otherwise show it in Measured only.

## 3. Screenshot 535, and whether hidden pattern controls change the sound in Measured

**Screenshot 535 (VERIFIED from the image):**
- Side mics show Family **Bidirectional** and Polar **Fig-8** with the slider enabled.
- There is no lock text, the Centre mic is Cardioid-family / **Supercardioid**, and "Each capsule" is open below.
- In this build Measured greys Family/Polar and hides Each capsule. So 535 **was not taken in Measured**.
- It also lacks the "M/S uses one figure-8" hint, so it was not MS classic either.
- ASSUMED: it was taken in User defined or Bypass, after Family was set to Bidirectional by hand.

**Engine use of the pattern (VERIFIED, code):**
- Render's early taps and FDN inject use the `MicStand` family/polar in **every** colour mode (`render_pipeline.py` ~1100-1150 → `compute_taps` → `_inject_levels`). Play's packed parameters come from the same taps.
- Measured colour (`mic_colour/colour.py`) is a frequency shelf relative to on-axis, applied **on top of** that analytic pattern gain.
- HPF and measured colour apply only in `MEASURED_SHELF`.

**Who owns the pattern (VERIFIED, code):**
- The server (`app_server.py:460-500`) replaces family/polar with the preset's `capsule_law` only when the preset id is explicit **and** `preset_owns_pattern` is true.
- The client sets `preset_owns_pattern=false` on **every Mic setup load** (`applyMicPreset`, `app.js` ~1371 and 1328) and on any family/polar write (`app.js` 1104/1124, `mic_desk.js:1145`).
- It sets it true only in `applyCapsulePreset` (~1442-1456) and in the default state (`app.js:93`).

**Measured (VERIFIED, `scripts/pattern_sound_probe.py`, default body, SM57 ×3):** with `owns=false`, changing family from cardioid to bi or omni **changes the sound in every colour mode**:

| Mode, owns=false | Render null L/R, bi vs card | Render null, omni vs card | Play null, bi vs card |
|---|---|---|---|
| Measured | −20.1 / −15.2 dB | −22.6 / −18.3 dB | −20.3 / −16.1 dB |
| Bypass | −17.8 / −13.5 dB | −20.7 / −17.3 dB | −17.5 / −13.4 dB |
| User defined | −19.4 / −14.9 dB | −22.0 / −18.1 dB | −19.0 / −14.7 dB |

With `owns=true` every null is below −2990 dB, i.e. no difference.

**So:** in Measured, the greyed (or, after this fix, hidden) Family/Polar **do** change the sound whenever a Mic setup was loaded or the user edited them in User defined. Those values carry over into Measured. That is a sound bug, not a UI one, so it is **decision D-UI21**.

**Mic setups in Measured (VERIFIED, setup table plus probe):**
- Three setups have a pattern different from the SM57 law (cardioid, polar 0.5):
  - `ab_omni` (L/R omni, polar 0);
  - `ms` (C omni);
  - `ms_classic` (L/R bi).
- In Measured these play their own pattern with SM57 colour on top. Binaural is separate.
- The other setups match the law, so the default ORTF and the goldens are not affected.
- **Split L/R in Measured:** the split box offers per-side preset + family + polar. With one catalogue mic only the (greyed) pattern can differ.
  - **Idle (09:09): keep it.** Use case: L is a side mic and R a room mic, while C stays the mid of the M/S. In Measured, Split gives a preset picker per side.
  - Full use needs S-MIX: the link chip set to Independent (own position and aim) and per-strip routing. That case is now an S-MIX acceptance scenario (`..\REPORT.md` S-MIX prompt).
  - Today MS classic disables the tick ("M/S uses one figure-8", VERIFIED in the probe). The fix-up keeps that block only until S-MIX, which removes it.

## 4. Mic tab layout (VERIFIED sizes at 1600×1000; at 1920 in brackets)

**Measured today:**
- `main` is 1564 px wide.
- Top panel 553×409 (586×426); Combined 553×409 (553×426). The canvases are 523×279.
- The Source plane panel is 1117×1099. Its hero canvas wrap is 847×522 (880×522) and the tools column beside it is only **228 px** wide (`.mic-polar-body` `grid-template-columns: minmax(0,1fr) 228px`, `app.css:893`).
- The sidebar is 458 wide but only **584 tall** (Listen 519 + Advanced 43). That leaves about 458×980 px empty below it, next to the Source plane.

**Proposal (mock `mock/m3_mic.png` v3, two states):**
- The tools column (`<aside class="mic-polar-tools">`, `index.html:205-332`) becomes a new sidebar panel **"Mics"** under Listen, holding:
  - Colour;
  - the three alignment ticks;
  - Side mics;
  - Centre mic;
  - in User defined only, the User defined capsule details.
- On the Mic tab, `main.layout` gets grid areas `"stage side" "wide wide"`:
  - Top and Combined stretch to the sidebar's height (panels use `align-items: stretch`; canvases `flex: 1; min-height: 560px`, replacing `aspect-ratio: 900/480`).
  - The Source plane panel moves to the `wide` row and spans the **full 1564 px**. Hero ≈1536×600; in User defined the Each-capsule row of 3 sits below it.
- Canvas sizing:
  - `mic_desk.js` reads `getBoundingClientRect` on every draw and `polar_field.js` has `resize()` (`:356`). Neither has a `ResizeObserver` (VERIFIED, grep).
  - Add one ResizeObserver on the Mic tab grid that redraws Top/Combined/hero/each.

## 5. Space tab camera (VERIFIED, `static/js/image_views.js`; probes `data/space_probe.json`, `data/space_reset_probe.json`)

Root causes:
1. **Left-drag does nothing.**
   - `onPointerDown` (`:417-429`) orbits only on right, middle or Alt+left, and pans only on Shift+left.
   - Probe: `left_drag_changes = false` on Lattice, Paths and Last legs. Right, Alt and Shift drags and the wheel all work.
   - The hints still say "orbit Alt/RMB" (`index.html:458`, `app.js:887-895`).
2. **Every app state change resets the camera.** `syncUINow` and the chip clicks → `scheduleImagesFetch` → `fetchImages` → `applyImageView` → `setData` → `rebuild` → `buildLattice`/`buildPaths`/`buildLegs` each call `fitCamera` (`:312/355/394`).
   - Probe: an orbit holds for 6 s while idle, but any sidebar change snaps back to the fitted view.
   - Idle experiences this as "doesn't orbit".
3. **Zoom is clamped and fog is fixed.**
   - `updateCamera` clamps the radius to 2.5–120 (`:268`); the far plane is 400 and the fog is 28–90 (`:30-33`).
   - Probe: wheel-out stops after about 40 steps. The Hall lattice fit wants max(14, 3.2·max·1.05), so Hall cannot be zoomed out and far images fade into the fog.
4. **No reset.**
   - There is no dblclick handler (VERIFIED, grep).
   - The probe's "dblclick changes the picture" is ASSUMED to be the pointer events of the two clicks, not a reset.
5. No overlay blocks the canvas: the element at the canvas centre is `#imageCanvas` (VERIFIED).

**Conclusion:** the S-UI1 item 7 camera fix was not carried out.

**Fix spec:**
- **Controls:**
  - left-drag orbits;
  - right-drag or Shift+left-drag pans;
  - middle-drag orbits;
  - the wheel zooms;
  - double-click resets to the fit.
- **Zoom limits:** zoom to the cursor is optional. Clamps scale with the room:
  - `minR = 0.2·diag`;
  - `maxR = 8·max(W,H,L)` (Lattice: 3·the fit radius);
  - `camera.far = 4·radius`;
  - fog from `0.9·radius` to `3·radius`.
- **Fit once:** `fitCamera` runs only on the first data and on Reset. When `setData` and the chips change and the room box still fits, the camera is kept. Changing the room size by more than 2× may refit.
- **Buttons:** a small `+ / − / Fit` cluster in the panel head.
- **Hint:** "Drag to orbit · right-drag or Shift to pan · scroll to zoom · double-click to reset", on all three chips.
- The 3D views orbit to look around and never move objects (Idle's rule). Path hover tips stay.

## 6. Colour belongs with Surfaces (item 7, added 08:20 BST)

Idle: "colour should be tied in with surfaces as it is an eq tied to the surface".

**Today after S-UI2 (VERIFIED, `data/colour_probe.json`, `shots/tab_colour.png`, `shots/tab_surfaces.png`, `index.html:474-604`):**

| Tab | Stage | Sidebar | Own controls |
|---|---|---|---|
| **Colour** | One panel, 1094×696: the wet-IR 1/3-octave analyser "updates after Render" (`#colourCanvas`), a legend (Now/Last/Hold A/Hold B), a face badge for the selected surface, and a read-only **"This face · absorb×EQ"** sparkline (`#colourSparkCanvas`) | Preview, Advanced | 4 only: 0 dB ref (Peak band / 1 kHz), Hold A, Hold B, Clear. **No EQ controls** |
| **Surfaces** | Surfaces panel, 1094×2105: banner, room net A–F, 16 material chips plus "All legal faces", Solo/Mute, face cards. Selected-face detail: Absorption vs frequency (1046×322) and **Surface EQ** (1046×322) with **7 sliders**: Low shelf dB/Hz, Peak dB/Hz/Q, High shelf dB/Hz (`colour_surfaces.js:434-441`), then Advanced (Smear, Tail diffusion, seed, λ_ref). Air card, 1094×271 | Room size, Preview, Advanced | all face and material controls |

So the per-face EQ already lives on Surfaces. The Colour tab only **shows the result** of that EQ plus absorption, and its face badge and sparkline follow the Surfaces selection.
- After every Render the app **jumps to the Colour tab** unless Colour or Surfaces is already open (`app.js:2351-2357`, VERIFIED).
- No post-EQ exists yet (VERIFIED; D-UI17 planned it for the Colour tab in S-OUT).

**Proposal D-UI23 (UI only, no sound change), mock `mock/m9_surfaces_colour_merge.png`:**
- Delete the Colour tab button. That leaves **7 tabs**: Room · Source · Mic · Mix · Space · Surfaces · Polar.
- Move the `#colourViews` panel into the Surfaces view as a **"Room colour · analyser of the wet sound"** card. It is a measurement of the rendered wet IR, **not an EQ**: the face EQ is the per-face control above it (Idle, 09:02: "colour is not a post EQ, it is an EQ applied to a surface"). Place it directly under the selected-face detail and above Air. It keeps its toolbar (ref, Hold A/B, Clear), face badge, analyser and the "This face · absorb×EQ" strip.
- Put the Absorption and Surface EQ graphs side by side (2 × ~520 wide instead of stacked 1046 wide), so the analyser sits right under the EQ sliders.
- Workflow hint: "Hold A → change the face EQ or material → Render → compare".
- `setView("colour")` / `isColour` / `colourSurfaces.setMode("colour")` (`app.js:988-1042`) fold into the Surfaces view. Any saved `view: "colour"` maps to `"surfaces"`.
- **D-UI23b, after Render:** recommend **no tab jump**. The analyser just updates. The alternative is to jump to Surfaces and scroll to Room colour.

**D-UI24: the new home for the D-UI17 post-mixer EQ. Locked 09:06 = A.**

| Option | Where | Note |
|---|---|---|
| **A (recommended)** | **Mix tab, a new "Output" strip** after the buses: Auto level (D-UI11) + Post-EQ low shelf / peak / high shelf with a small curve, flat = bit-exact bypass | It shapes the whole mix, so it sits with the faders. The Surfaces analyser can overlay its curve later |
| B | A "Master EQ" card under the Room colour analyser on Surfaces | One place to see the EQ and its effect, but it mixes per-face and whole-mix EQ |
| C | Drop D-UI17 | The per-face EQ may be enough |

Neither D-UI23 nor D-UI24 changes the sound. D-UI17 itself (S-OUT) changes it only when moved off flat.

---

## 7. Decisions (Idle, locked 3 Oct 2026 09:06 BST; D-UI25 corrected 09:09)

| ID | Question | Decision |
|---|---|---|
| **D-UI21** | In **Measured**, does the preset always own the pattern? | **YES.** Entering Measured re-applies the preset law (`preset_owns_pattern=true`), and the server enforces `capsule_law` whenever `MEASURED_SHELF`. Loading AB omni, MS or MS classic switches Colour to User defined, with a toast. Before (VERIFIED): with a non-law pattern, Measured nulls −15…−23 dB against the law. FIXUP_PROMPT Part B1. |
| **D-UI22** | What is **Bypass**? | **YES = preset pattern, no measured colour, no capsule graphs**, and no Family/Polar/HPF. Supersedes the D-UI19 "graphs also in Bypass". Part B2. |
| **D-UI23** | Merge Colour into Surfaces (7 tabs), no tab jump after Render? | **YES.** The card is called an analyser of the wet sound, not an EQ. Part A5. |
| **D-UI24** | Home of the D-UI17 post-mixer EQ | **A:** a Mix tab Output strip next to Auto level, built in S-OUT. |
| **D-UI25** | Hide Split L/R in Measured? | **NO (09:09).** Keep it. In Measured, Split = a preset picker per side (per-side HPF keys come in S-MIX). Use case: L = side mic, R = room mic, C = mid. This needs S-MIX (link Independent plus per-strip routing) and is an S-MIX acceptance scenario. |
| **D-UI26** | Should the face EQ and absorption shape reach the tail (before the FDN)? | **A, LOCKED (Idle 09:22).** Per-line face colour (absorption shape relative to the card mean, plus face EQ) on the FDN inject in both engines and on Play early. It is session S5: `roadmap/s5_surf_1010/S5_PROMPT_D-UI26.md`. See §8.4. |

Hidden audit: `scripts\hidden_audit.py` v2 finds the tabs itself and visits every Colour mode. On the S-UI2 tree it finds 0 visible `[hidden]` elements over 96 states (4 setups × 3 modes × 8 tabs; VERIFIED).

The UI-only parts (sections 1, 2, 4, 5, 6 and the bug fixes) are `FIXUP_PROMPT.md` Part A. D-UI21/D-UI22 are Part B, **approved 09:06**, with before/after nulls in Build's report. D-UI26 = A (locked 09:22) is not in the fix-up. It is engine session S5 (`roadmap/s5_surf_1010/S5_PROMPT_D-UI26.md`).

---

## 8. Face EQ and the tail (Idle, 09:02: "colour is not a post EQ, it is an EQ applied to a surface, so it should be somehow before FDN")

Tree: the 08:18 snapshot, read-only. Measured on the box with `scripts/face_eq_probe.py` and `scripts/face_mean_probe.py` (data in `data/face_eq_probe.json` and `data/face_mean_probe.json`).
- Body: the default client body, with `direct_wet = early_wet = fdn_wet = 1`.
- IR length 1.5 s, at 48 kHz.
- Windows: 0–80 ms and 80 ms+.
- Bands: third-octave, mean of L and R.
- Test move: face A (Left wall) high shelf +6 dB at 5 kHz.

### 8.1 Where the face colour is applied (VERIFIED, code)

| Path | Render (Python) | Play (wasm `live_stereo.c`) |
|---|---|---|
| **Early reflections** | Full per-face cascade on each image tap, for every face that tap hits: absorption as one RBJ peaking filter per band, gain √(1−α(f)), Q 0.9, plus face EQ low shelf / peak / high shelf (`render_pipeline.py:503-506` → `surface_colour.py:648-692`). | **None.** The early lane reads the same per-line write as the FDN lane (`live_stereo.c:1634-1646`). The only per-line terms are inject × air shelves × source tint. The SURF section is just a per-line early gate for Solo/Mute (`:44-46`, `:1000-1011`, `:1579-1581`). |
| **FDN input (inject)** | Broadband only: `tap_reflect_gain` = Π over hit faces of √(1 − mean α) (`render_pipeline.py:531-567`, applied at `:648`). **No EQ and no frequency shape.** | The same broadband `tap_reflect_gain` is packed into `inject` (`render_pipeline.py:1711`). No EQ, no shape. |
| **Inside the loop** (per-line colour, `line_t60`) | Room-depth peaking banks plus `line_t60 = decay_s` (decay lock). No surface input (`FDN(...)`, `:650-664`). The mic colour is applied per line after the loop and is not a surface term. | Same design (`live_peaking_banks(room…)`, `line_t60`). No surface input. |
| **Solo/Mute** (D11/D12) | Early only (`image_in_early`, `:419`). `effective_surfaces()` is never called (grep), so the FDN inject ignores Solo/Mute. | Early only (SURF early gate). "xin and the FDN lane stay open." |

### 8.2 Measured: face A high shelf +6 dB (VERIFIED)

| Engine · bus | 0–80 ms third-octave Δ | 80 ms+ Δ | Null (new vs old) |
|---|---|---|---|
| Render · early only | 4k +0.20, 5k +0.45, 6.3k +0.72, 8k +0.87, 10k +1.09, 12.5k +1.20, 16k +1.20 dB; ≤ 2 kHz ≈ 0 | −0.02 dB flat | 0–80 ms: L −9.7, R −27.2 dB |
| Render · FDN only | 0.00 | 0.00 | −2986 dB (bit-identical) |
| Render · full mix | max +0.08 dB (16k) | 0.00 | 0–80 ms −22.6 / −42.4 dB; tail −126 / −133 dB |
| **Play** · early / FDN / mix | **0.00** | **0.00** | ≈ −2990 dB (bit-identical) |

Two more measurements:
- **Absorption shape, same mean** (face A bands reversed): Render early changes by up to +0.24 dB. The Render FDN and all of Play are bit-identical (VERIFIED).
- **Mean absorption** (face A +0.30 in every band, FDN bus only): the tail energy moves only −0.13 / −0.04 dB (L/R), identically in Render and Play (null −24.8 / −29.6 dB) (VERIFIED). The mean does reach the inject, but the decay lock and the RMS makeup hold the tail's T60 and level.

**Answers:**
1. **Render:** the face EQ shapes **only the early reflections**. The tail ignores it, and gets only each face's broadband mean absorption on the inject.
2. **Play:** the face EQ and the absorption shape do **nothing at all, not even early**. This is a Render/Play parity gap in the early field. Play hears a face's broadband mean absorption only through the inject, which also scales the early read.
3. **Can you hear a face EQ move the tail?** No, in either engine. In the default full mix, a +6 dB face shelf moves the 0–80 ms window by at most 0.08 dB (Render) and 0 dB (Play).

### 8.3 D-UI26 (new sound decision): feed the surface colour into the tail

Physically, every reflection off face X is filtered by R_X(f) = √(1−α_X(f)) · EQ_X(f). The late field is made of those same reflections. So the tail should carry the faces' colour: statically (the spectrum of what seeds the tail), and, more completely, per band in the decay.

| Option | What | Physics | Cost and risk |
|---|---|---|---|
| **A (recommended)** | **Per-line inject colour.** Each FDN line i is seeded by tap i (`taps[i % n]`), whose hit faces are known (`surfaces_hit_by_n`). Filter line i's inject with H_i(f) = Π over hit faces of EQ_X(f) · √(1−α_X(f)) / √(1−ᾱ_X). The mean is already in `tap_reflect_gain`, so it isn't counted twice. In Play, put the filter on the shared per-line write, before the early and diffuse tints: one place colours both the early reflections and the FDN input, which also closes the Play early gap. The server fits each line's cascade to ≤ 3–4 biquads (packed like the shelf section). In Render, filter `inj[:, i]` with the same fitted stages so Play = Render. | The tail spectrum takes the colour of the reflections that seed it, weighted by how many lines hit each face. T60 stays the user's Decay (lock respected). The filter sits **outside the loop**, so passivity is untouched and EQ boosts are safe. | M. Play CPU: 32 lines × 2 sources × ≤ 4 biquads (ASSUMED affordable; must pass t15/t19 by median). `reaktor_parity` → off (bit-exact). **Flat EQ: bit-exact** if the stages are skipped. The absorption shape is not flat at defaults (0.05 → 0.22), so including it changes the default early field in Play and the default tail colour in both engines. That means regenerating the goldens, with the reason recorded. |
| A-EQ only | As A, but the EQ only, without the absorption shape | Half-physical: Play early still lacks the absorption shape | Defaults are bit-exact and goldens unchanged |
| B (later) | **Per-band decay from the surfaces.** Area-weighted α(f)·|EQ|² (Eyring) sets the relative T60 per band inside the loop's per-line absorption filters, with Decay as the 1 kHz anchor. EQ gain is clamped to |R| ≤ 1 inside the loop. | The most physical: bright walls ring longer at HF | L. Changes the decay shape and overlaps D4 (frequency-dependent decay). Boosts can't be honoured inside the loop. |
| C | Keep it early-only, and label the face EQ "early reflections only" | None | None |

**Recommendation:** **A, with both the EQ and the absorption shape.** Alternatively A-EQ-only, if Idle wants the defaults to stay bit-identical. Then B later, together with D4. Option A also fixes the Play-early gap (VERIFIED: Play has no face colour today).

**Solo/Mute (D11/D12):**
- Keep them **early-only**. The inject colour uses the ungated face cards, so Mute X does not take X's colour out of the tail. D12 already makes Solo listen to Early only.
- In Play the early gate multiplies the early **read**, after the shared write filter, so gating still works unchanged.
- `tap_reflect_gain`'s `muted → 0` branch is unreachable today (no caller of `effective_surfaces`). Keep it that way, or delete it, so a Mute never silences a line's tail.

**Expected size (ASSUMED, by formula, not measured):** the tail change at HF ≈ 10·log10(1 + p·(10^(G/10) − 1)), where p is the share of tail energy injected by lines that hit the face, and G is the face's shelf gain in dB.

**Acceptance for A:**
- Flat EQ plus parity: bit-exact.
- Face A +6 dB HS: the Render and Play 80 ms+ deltas agree within 0.3 dB per band ≥ 2 kHz, and are > 0 dB.
- Play early 0–80 ms matches Render early within 0.5 dB per band.
- t13/t18 parity holds, t15/t19 CPU by median holds, and the goldens are regenerated only if the absorption shape is included, with the reason recorded.

### 8.4 D-UI26 = A LOCKED (Idle 09:22), folded into S5 (box, 3 Oct 10:10–11:05 BST, `snapshot_2026-10-03_1010`, wasm a80209d2e69c)

Prompt: `roadmap/s5_surf_1010/S5_PROMPT_D-UI26.md`, which also replaces S5 item 1 in the roadmap §5. Evidence is in `roadmap/s5_surf_1010/`. Unmarked numbers are VERIFIED box measurements.

**Render prototype A** (box-only copy of the software: `protoA_root/software/render_pipeline.py`). In `_scale_inject_reflect`, each line gets the exact relative-absorb peaks plus the face EQ of its hit faces.
- The early field is unchanged (max-abs 0.0).
- Flat-shaped cards: the FDN output is bit-identical to the shipped tree (max-abs 0.0).

**Expected default change** (third-octave dB, L/R mean; `expect/expect_default.json`):
- **Tail (80 ms+), FDN bus and full mix:**

  | Hz | 125 | 250 | 500 | 1k | 2k | 4k | 5k | 6.3k | 8k | 10k | 16k |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | Δ dB | +0.39 | 0.00 | +0.19 | +0.05 | +0.02 | −0.21 | −0.27 | −0.33 | −0.37 | −0.28 | −0.07 |

  There is LF modal ripple of up to ±0.5 dB, and the FDN-bus null is −24.0 dB. Play is ASSUMED to follow, since Play − Render tail is 0.00 dB after S7.
- **Play early (0–80 ms):** this is Render early with per-band absorb against absorb flattened to the card mean, which is what Play does today.

  | Hz | 125 | 250 | 500 | 1k | 2k | 4k | 6.3k | 8k | 16k |
  |---|---|---|---|---|---|---|---|---|---|
  | Δ dB | +0.26 | +0.15 | +0.23 | +0.03 | −0.10 | −0.33 | −0.40 | −0.39 | −0.07 |

  ASSUMED: this equals the Play early change, within the fit error.
- **Face A HS +6 dB now moves the tail.** At 6.3/8/10/12.5/16 kHz it is +0.26/+0.41/+0.53/+0.48/+0.52 dB (today 0.00). All faces at +6 give up to +6.0 dB at 12.5 kHz. This replaces the §8.3 formula estimate.
- **Guitar** (`guitar/`, before level matching): the tail is +0.74 dB louder and the mix +0.18 dB. With a carpet floor, the tail is +2.0 dB and the mix +0.53 dB, because the LF is no longer absorbed at the card mean.

**Play fit** (`fit/fit_k.json`, 92 hit sets, max error in dB, K = 2/3/4/6):

| Case | K = 2 | K = 3 | K = 4 | K = 6 |
|---|---|---|---|---|
| Default | 1.57 | 1.08 | 0.24 | 0.08 |
| Carpet | 4.11 | 2.47 | 0.77 | 0.48 |
| Extreme EQ | 13.1 | 6.6 | 6.5 | 1.3 |

This changes §8.3. Render uses the **exact** stages (it is the reference), and Play uses a per-line fit with K adaptive up to 6. The fit is not "≤ 3–4 biquads in both".

**CPU:** see the prompt. The box t19 paired median is +6 % at K = 4 and +9 % at K = 6. The PC is marginal against the 2.133 ms gate (ASSUMED, PC 5–10 % slower), so the prompt has a stop rule.

**Parity tests use per-engine Δ:** the box shows Play early about +6 dB broadband against Render early before S5. That offset predates S5; its cause was not checked (ASSUMED a bus-definition difference).

