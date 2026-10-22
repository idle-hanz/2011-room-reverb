# S-UI2 fix-up prompt (paste into the same S-UI2 Build window · effort: high)

> Hi Build. This is a fix-up in the same S-UI2 session. **Part A is UI only: don't change the sound.** Every golden must stay byte-identical. **Part B is approved** (Idle locked D-UI21 and D-UI22 at 09:06 BST, 3 Oct). Do it after Part A. It changes the sound only in Measured/Bypass with non-law patterns, and your report must give before/after nulls.
>
> **Design notes:**
> - `research_ui_wishlist\sui2_fixup\REPORT.md` (findings, all tagged VERIFIED/ASSUMED, with file:line).
> - Mocks: `research_ui_wishlist\mock\m3_mic.png` (v3, Measured and User defined states) and `research_ui_wishlist\mock\m9_surfaces_colour_merge.png`.
> - Line numbers below are from the 2 Oct 21:45 BST tree.
>
> **Before you start:** copy the harness `golden` folder somewhere safe and print the SHA1 of every file in it.
>
> ## Part A: UI only
>
> **A1. Colour dropdown order** (`index.html:208-212`)
> - Order the options **Measured · User defined · Bypass**.
> - Keep the values `MEASURED_SHELF` / `ASSUMED_TOYS` / `BYPASS`.
>
> **A2. Show only what acts in each Colour mode** (`syncPatternChrome` `app.js:1161-1221`, `syncMicEach` `:1142-1149`). Use `hidden`, not `disabled`.
>
> - **Measured:**
>   - Show the Side/Centre **preset** dropdowns and the **high-pass** row. Keep today's "No high-pass · This microphone has none" for SM57.
>   - **Hide** Family, Polar and the Each-capsule graphs. **Keep the Split L/R tick** (D-UI25 = no).
>   - Hide the "User defined capsule" panel.
>   - Show one line: "Pattern comes from the preset (SM57 = cardioid). Switch Colour to User defined to shape it."
>   - No mismatch line: Part B1 makes Measured always use the preset law.
> - **User defined:**
>   - **Hide** the preset dropdowns and the high-pass row (measured colour is off in this mode).
>   - Show Family + Polar for Side and Centre, the Split L/R tick (splits the pattern), the Each-capsule graphs and the User defined capsule panel.
>   - Don't change `preset_owns_pattern` in Part A.
> - **Bypass (D-UI22, locked):** show it as Measured, but without the high-pass row: preset shown, Split shown, pattern rows and graphs hidden, note "Bypass: preset pattern, no measured colour". The sound side is B2.
> - **Split L/R in Measured and Bypass (D-UI25 = no, locked 09:09):** keep the tick. Ticked, it shows a **preset picker per side** (`mic_preset_l` / `mic_preset_r` via `applyCapsulePreset(["l"])` / `(["r"])`) and no pattern rows. The high-pass stays one shared "Side high-pass" row: the only key today is `mic_hpf_sides` (`app_server.py:507`, VERIFIED). Per-side HPF needs new keys, so it goes to S-MIX.
>   - L and R may be different measured mics, or the same mic doing different jobs.
>   - Idle's case: L = side mic, R = room mic, C = the M/S mid. Positions and routing for that arrive in S-MIX (link chip Independent, per-strip routing).
>   - Keep today's MS-classic block on the tick ("M/S uses one figure-8") until S-MIX lifts it. Change the hint to "Per-side jobs in M/S arrive with the S-MIX desk".
> - **Fix `sideLockText`** (`app.js:1129-1140`): word the text from the preset (`capsule_law` / preset label), not from `state.family_l`. Today MS classic in Measured says "Shure SM57 is a fixed fig-8".
> - **Clean up "User defined capsule"** (`index.html:697`, `#capsuleColour`):
>   - Remove "Panel high-pass", "High-pass Hz" and "Proximity". Render never reads `mic_hp_on`, `mic_hp_hz` or `mic_proximity` (`render_pipeline.py:1012-1015` are their only uses). Keep the keys in the state and API for old saves.
>   - Keep Mic response and Capsule size.
> - **`#micPlayNote`** (`index.html:214`; no JS uses it, so it shows in every mode):
>   - Null Play against Render in Measured on the default body (your S7 method).
>   - If they null below −60 dB, delete the note.
>   - Otherwise show it in Measured only.
>   - Report the number.
>
> **A3. Mic tab layout (mock `m3_mic.png` v3).** Today at 1600×1000: Top and Combined panels are 553×409, the Source plane is 1117 wide, the hero is 847×522 and the tools column is 228 px. The sidebar is only 584 px tall, leaving about 980 px of it empty.
> 1. Move `<aside class="mic-polar-tools">` (`index.html:205-332`) out of the Source plane into a new sidebar panel **`#panelMics` "Mics"**, under Listen, shown on the Mic tab only. Order inside it:
>    - Colour;
>    - the 3 alignment ticks;
>    - Side mics;
>    - Centre mic;
>    - the User defined capsule details (moved from Listen; User defined only).
> 2. On the Mic tab, give `main.layout` the class `mic-wide`, with `grid-template-areas: "stage side" "wide wide"`. Add a `<section class="stage-wide">` after the sidebar and move the Source plane panel into it, so it spans the full main width (1564 px at 1600). Hero about 1536×600. In User defined, put the 3 Each-capsule graphs in a row under the hero.
> 3. Top and Combined stretch to the sidebar's height:
>    - panels `align-items: stretch`, `display: flex; flex-direction: column`;
>    - canvas wrap `flex: 1; min-height: 560px`, replacing `aspect-ratio: 900/480` (`app.css` `.mic-floor-wrap, .mic-3d-wrap`).
> 4. Add one `ResizeObserver` on the Mic grid that redraws Top, Combined, hero and each. Today `mic_desk.js` and `polar_field.js` have none.
> 5. Keep the existing 1100 px and 900 px single-column breakpoints working.
>
> **A4. Space tab camera** (`static\js\image_views.js`)
> - **Controls:**
>   - **left-drag orbits** (today `onPointerDown` `:417-429` only orbits on right, middle or Alt);
>   - right-drag or Shift+left pans;
>   - middle-drag orbits;
>   - the wheel zooms;
>   - **double-click resets** to the fit (there is no handler today).
> - **Fit once:** `buildLattice`, `buildPaths` and `buildLegs` call `fitCamera` on every rebuild (`:312/355/394`), so every sidebar change snaps the view back. Fit only on the first data, on Reset, or when the room size changes by more than 2×. Keep the user camera across `setData` and chip changes.
> - **Room-scaled clamps** in `updateCamera` (`:268`; today 2.5–120):
>   - `minR = 0.2·diag`;
>   - `maxR = 8·max(W,H,L)` (Lattice: 3·the fit radius);
>   - `camera.far = 4·radius`;
>   - fog from 0.9·radius to 3·radius (today fixed at 28–90 with far 400).
> - Add a small `+ / − / Fit` button cluster in the panel head.
> - Hint on all 3 chips (`index.html:458`, `app.js:887-895`): "Drag to orbit · right-drag or Shift to pan · scroll to zoom · double-click to reset".
> - The camera only looks around: it never moves objects. Path hover tips stay.
>
> **A5. Colour merges into Surfaces (D-UI23; mock `m9_surfaces_colour_merge.png`).** Today Colour holds only the analyser, 0 dB ref, Hold A/B, Clear, the face badge and the "This face · absorb×EQ" strip (`index.html:474-517`). The face EQ is already on Surfaces.
> 1. Remove the Colour tab button. That leaves **7 tabs**: Room · Source · Mic · Mix · Space · Surfaces · Polar.
> 2. Move the `#colourViews` panel into the Surfaces view as **"Room colour · analyser of the wet sound"**, under the selected-face detail and above Air. Keep its toolbar, face badge, analyser and strip.
>    - Wording: it is a **measurement of the rendered wet IR, not an EQ**. Head hint: "What the faces above do to the wet sound · 1/3 octave · updates after Render".
>    - Never call it an EQ, "post", or "Colour EQ". The EQ is the per-face Surface EQ above it.
> 3. Put the Absorption and Surface EQ graphs side by side.
> 4. Fold `isColour` / `setMode("colour")` (`app.js:988-1042`, `colour_surfaces.js:1219-1221`) into the Surfaces view. A saved `view: "colour"` opens Surfaces.
> 5. **After Render (D-UI23b):** don't jump tabs (`app.js:2351-2357` today jumps to Colour). Just update the analyser.
> 6. Sidebar on Surfaces is unchanged: Room size, Preview, Advanced.
> 7. Don't build the D-UI17 post-EQ here. D-UI24 is locked as A: a Mix-tab Output strip next to Auto level, built in S-OUT.
>
> **A6. Tests** (add them to your Playwright tour; Chrome headless at 1600×1000 and 1920×1080):
> 1. The Colour options read exactly ["Measured", "User defined", "Bypass"].
> 2. Visibility matrix, for {ORTF, MS classic, AB omni, Mono} × {Measured, User defined, Bypass}. Assert visible/hidden for: preset side/centre, high-pass rows, `family_side`, `polar_side`, `family_c`, `polar_c`, `side_split`, `#micEach`, `#capsuleColour` and the lock line, following A2.
>    - `side_split` is visible in Measured, Bypass and User defined.
>    - In Measured with Split ticked: per-side presets and the shared Side high-pass are visible, per-side family/polar are hidden.
>    - Picking a different preset for R leaves `mic_preset_l` unchanged.
> 3. `sideLockText`: MS classic + Measured mentions the preset's cardioid, not "fig-8".
> 4. Layout at 1600:
>    - `#panelMics` is inside `.sidebar`;
>    - the Source plane panel is at least 1500 px wide;
>    - the hero is at least 1400×560;
>    - Top and Combined canvases are each at least 520 wide and 540 tall;
>    - `.mic-polar-tools` no longer sits inside the Source plane.
> 5. Space, on each of Lattice, Paths and Last legs:
>    - a plain left-drag changes the canvas pixels (hash);
>    - after an orbit, changing a sidebar control (e.g. Stand X) keeps the camera, i.e. the hash differs from a fresh fit;
>    - double-click restores the fitted hash;
>    - Hall lattice: 60 wheel-out steps keep changing the picture until `maxR`.
> 6. Tabs: 7 `.view-tab`, with no `colour`. The Room colour card (`#colourCanvas`) is visible on Surfaces. A Render does not change the active tab.
> 7. All 11 Mic setups load in each Colour mode without console errors.
> 8. `research_ui_wishlist\scripts\hidden_audit.py http://127.0.0.1:7860/` (v2: finds the tabs itself and visits every mode) exits 0. The S-UI2 baseline is 0 leaks over 96 states.
> 9. **Goldens:** the SHA1 of every golden is unchanged vs your copy, the phase suite passes, and `git diff` touches only `static\` (plus tests).
>
> ## Part B: sound (APPROVED, Idle 09:06 BST 3 Oct: D-UI21 yes, D-UI22 yes)
>
> **B1. D-UI21, Measured = the preset owns the pattern.** Today, after any Mic setup load (`applyMicPreset` `app.js` ~1328/1371) or a User defined edit, `preset_owns_pattern=false`. Measured then renders the setup's own family/polar with SM57 colour on top. Measured null vs the law: bi −20.1/−15.2 dB, omni −22.6/−18.3 dB (L/R); Play the same.
> - Entering Measured re-applies the preset law to `family_*/polar_*` and sets `preset_owns_pattern=true`.
> - Server: in `_mic_colour_fields` (`app_server.py:460-500`), when `colour_mode == MEASURED_SHELF`, always use `capsule_law`.
> - Loading `ab_omni`, `ms` or `ms_classic` while in Measured switches Colour to User defined, with a toast.
>
> **B2. D-UI22, Bypass = "Measured without colour".** Pattern = preset law, the same as B1, but no measured colour and no HPF.
>
> **B3. Tests:**
> - Measured + MS classic renders the SM57 law: null against an explicit cardioid render at or below −100 dB.
> - Loading AB omni in Measured lands in User defined and renders as today's User defined AB omni (null at or below −100 dB).
> - Default ORTF goldens are byte-identical: all 11 setups except those 3 already match the law.
> - Record any golden you had to touch, with the reason, in `GOLDEN_META.json`. Expected: none.
> - **Before/after nulls in your report** (L/R, Render and Play), for these cases:
>   - Measured + MS classic;
>   - Measured + AB omni (it should land in User defined);
>   - Measured + ORTF after a User defined edit to bi then back to Measured (before: about −20/−15 dB vs the law; after: ≤ −100 dB vs the law);
>   - Bypass + MS classic;
>   - default ORTF in all 3 modes (before = after, ≤ −100 dB).
>
>   The baseline method and today's numbers are in `sui2_fixup\scripts\pattern_sound_probe.py` and `data\pattern_sound_probe.json`.
>
> **Report:**
> - Part A test results.
> - The `#micPlayNote` null number.
> - The Part B before/after null table.
> - Golden SHA1s (before = after).
> - Screenshots of the Mic tab in each of the 3 modes at 1600, the Space tab after an orbit plus a sidebar change, and Surfaces with Room colour.
> - Anything you could not do and why.
