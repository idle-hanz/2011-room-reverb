# Idle's UI/engine wishlist (20 items): research report

**Written:** 2 Oct 2026, 18:13–19:50 BST. **Updated** about 19:30 BST with items 19 and 20 (Mic tab, from Idle), checked against `snapshot_2026-10-02_1905` (UI files are identical to 1815).
**Tree tested:** `snapshot_2026-10-02_1815`. This is a read-only robocopy of the PC `software\` folder, zip MD5 0295B7C4B9925BC426E2A3F3847418E2. The PC was not touched and the app was not restarted.
**How it was tested:** the app ran headless on the box (port 7875) and was click-tested with Playwright and headless Chrome (SwiftShader). Levels come from the harness Render (`render_ir.py`) and Play (`wasm_run.js`, the shipped wasm).

Every claim carries a tag:
- **VERIFIED:** reproduced or measured here.
- **ASSUMED:** inferred, not measured.

**Note.** Build's shared-tail edits (17:53–17:57: WORKLET_VER 44, the "Shared tail (lighter CPU)" checkbox) are in this tree. They have **not** been verified here; that is out of scope.

Folder: `shots/` holds the screenshots, `mock/` the before/after mocks (PNG, HTML in `mock/src`), `data/` the JSON and measurements, and `scripts/` everything that can be re-run.

---

## 1. Per-item table

Size key: S = under half a day, M = about one Build session, L = a full session or more.

| # | Item | Verdict | Root cause (file:line) | Fix | Size | Changes the sound? | Decision and recommendation |
|---|---|---|---|---|---|---|---|
| 1 | Radiation colours inverted | **BUG, VERIFIED** (code and screenshot `shots/b1_source_violin.png`) | `static/js/source_desk.js:7-12`: 250 Hz `#3b82f6` blue … 8 kHz `#f87171` red. `static/js/mic_desk.js:27` `RING_COLORS` has the same cool-to-warm order (used at lines 653, 690, 734). | One shared spectral map, `static/js/spectrum_colors.js`: low = red → orange → yellow → green → blue → high = violet. Use it for Source radiation, Mic rings, Polar and all legends. | S | No | Just do it (Idle asked for exactly this). |
| 2a | The 3 hidden mic graphs move the wrong way | **BUG, VERIFIED** (XY 90°: the L lobe points right while its front dot is at −45° left; `shots/b2_eachcapsule_xy90_*.png`) | `mic_desk.js:730` (measured grid) and `:744` (analytic) draw `sx = cx − r·sin(…)`. The front dot (`polarFrontPx`, `:561`) and the pointer (`:866-888`) use `cx + S·r·sin`, with `S = RoomMath.YAW_X_SIGN = +1` (`room_math.js:101`, flipped from −1). The plot was never flipped with it. | Use `cx + S·…sin` in both branches. **Also check:** the Top-view halo at `mic_desk.js:417` and the side view at `:498` use the same `−sin` (ASSUMED that they may be mirrored too; test with XY ±45). | S | No | Just do it. |
| 2b | Cardioid slider and family dropdown don't work | **VERIFIED: disabled by design, with no explanation** | In the default colour mode (Measured) `app.js:1576-1578` and `:1717-1718` set `family_*`/`polar_*` to `disabled`, because the measured preset owns the pattern. The only preset is the Shure SM57 (`index.html:232, 245`). In Bypass the controls work: `polar_l` 0.5→0.9 updates the canvas, posts `/api/polar` with `pattern_l: supercardioid`, and moves `polar_r` too (Link). VERIFIED. | (a) Explain the lock where the control is: "Shure SM57 is a fixed cardioid. Pick a multi-pattern mic or set Colour to Bypass." (b) ~~Open "Each capsule" by default.~~ Superseded by item 19: the Each-capsule graphs show only in User defined (and Bypass). (c) Later, add multi-pattern measured presets so the pattern can be dialled in Measured mode. | S (a, b), M (c) | No (a, b) | Do a and b now. c needs mic data. |
| 3 | Link/mirror L and R, or 3 independent mics (an MS pair plus a room mic) | **FEATURE** | Today there is a single stand: L and R at ±space/2, and C at `centre_dz`. `link_lr_yaw` mirrors the yaw only. | Mic tab: an **L/R link** chip (Mirror · Linked · Independent; **geometry only**, the pattern split is item 20's tick) and a **3rd mic** chip (Off · Centre (array) · Room (own X/Z/height/yaw/preset)). The engine needs a position per mic: early taps per mic and FDN inject per mic. Mock: `mock/m3_mic.png`. | L | Only in the new modes; the defaults stay bit-identical | **D-UI3:** recommend yes. Ship with the mixer (S-MIX). |
| 4 | Mixer to match (MS decode, routing per mic) | **FEATURE** | `engine/fdn.py:380-408`: linear balance pan (`pan_lr`: 1−t, t; centre 0.5/0.5 = −6 dB, the "477 fold"), plus one polarity per strip. Each strip can only reach L/R with one sign. MS classic is decoded **inside** the capsule model (`engine/early_field.py:1643-1700`, `ms_decode`), so the desk can't set the width. | Per-strip **Route** chips: Pan · Centre · Both · L · R · **M/S decode** (S → +L, −R). Pair header: Stereo pair · M/S pair (with **Width**) · Independent. Pan-law chip: 2011 linear (default) · constant power. Show a read-only matrix. The Mic setup dropdown loads the desk preset (§4). Move the MS decode from the capsule model into the desk matrix. Mock: `mock/m2_mix.png`. | L | Only in the new modes. MS classic at width 0 dB must null against today (acceptance test). | **D-UI4:** recommend yes, with linear as the default pan law (constant power would make today's C fold 3 dB louder). |
| 5 | Pan and trim move badly | **BUG, VERIFIED** (Playwright) | `static/css/app.css:1221-1250`: the "knob" is an invisible **horizontal** `<input type=range>` stretched over a 32 px dial. Measured: vertical drag 60 px = no change. A click on the left edge jumps to the minimum (−12 dB / pan −1). A 5 px drag right takes trim 0 → +7.5 dB and pan 0 → +0.63. 17 px = full range. Wheel and double-click do nothing. (`data/probe_bugs.json` `b5`) | A shared `knob.js` rotary: pointer-capture vertical drag (200 px = full range), Shift = ×0.1, wheel = one step, double-click = reset (0 dB / centre), arrow keys, no jump on click, 44 px hit area, value shown while dragging. Keep the `<input>` as the value store so state and tests are unchanged. | S | No | Just do it. |
| 6 | Polar tab: the Mic graph plus each mic, or what arrives at each speaker | **FEATURE + layout BUG, VERIFIED** | The Polar 3D tab is the same `cs-split` page as Colour and Surfaces (`app.js` setView `isCS`). The polar field sits about 2000 px down, under Colour and Surfaces (`shots/tour_ortf_polar.png`). | Give Polar its own page with chips: **Combined** (the same component as the Mic tab) · **Each mic** · **At speakers**. At speakers: P_L/R(θ, f) = Σᵢ w_iL/R · gᵢ(θ, f) · e^{−jωτᵢ(θ)}, using the desk matrix. The server already computes "Sum" with the centre delay (`polar_field.py`), so extend it to per-speaker sums. Mock: `mock/m7_polar.png`. | M | No | Do it with S-UI2 (own page) and S-MIX (At speakers, which needs the matrix). |
| 7 | Head control hidden unless binaural | **BUG, VERIFIED** | The JS is right (`app.js` `syncBinauralChrome` about line 1683 sets `hidden = !on`), but `app.css:295` `.ctrl{display:grid}` and `:318` `.ctrl-select{display:flex}` beat the UA `[hidden]` rule. The hidden audit (`scripts/hidden_audit.py`, `data/hidden_audit.json`) finds 4 leaks: `headPresetRow` and `headYawRow` (ORTF and Mono, on Mic/Lattice/Paths/Polar), an empty `capsuleStackListen` (Mic), and `pathsModeRow` (shown on Lattice). | Add `[hidden]{display:none!important}` near the top of `app.css`, then re-run the audit (expect 0 on every tab × setup). | S | No | Just do it. |
| 8 | 3D polar graph leans when mic height changes | **VERIFIED: by design, but misleading** | The stack is drawn in the plane through L, R and the **source** (`polar_field.py:256-289` `_mic_source_plane`, used at `:514`, stacked along the normal at `:583`; the Polar field uses `_lr_source_plane` at `:625`). Src height stays at 1.20 m (Link heights is off by default). Measured: mic 1.5 m → tilt 5.3°, mic 3.0 m → **29.0°** (`shots/crop_b8_my*.png`). The capsules have no pitch control, so the lean says nothing about the mics. | Default plane = **horizontal at mic height**, with source elevation drawn as a marker ("source −29°"). Keep "Tilt to source" as a chip. | S | No | Recommend a horizontal default. |
| 9 | Source page: bigger place/face diagrams | **VERIFIED** (layout) | The Place & face floor (720×420 canvas) and elevation (180 px) sit in a short card with an empty page below (`shots/b1_source_violin.png`). | Three columns: a narrow controls column, Place & face filling the column height, Elevation 300 px below it, Radiation on the right. Mock: `mock/m6_source.png`. | S | No | Do it in S-UI2. |
| 10 | Feedback vs Decay | **VERIFIED** (code and measurement) | See §2. With Decay armed (the default), Feedback is ignored. With it off, Feedback is the 2011 law g = Gain/N: at the default room it gives only **0.12 s** (Gain 1) or 0.11 s (Gain 0.85). | Make one **Decay (s)** the tail control. Move Feedback to Advanced as "2011 law: Structure Gain", active only under Reaktor parity and the Hall snapshot. Remove the dead `fdn_g` from the Studio/Club chips (`app.js:2141, 2146`). | S | No at defaults (Decay is armed). The 2011 snapshot keeps its law. | **D-UI10:** recommend **merge**: Decay main, Feedback under Advanced/parity. |
| 11 | Overall level low; wants auto level | **VERIFIED** (measured, §3) | At defaults you hear **only the FDN bus**: the Direct and Early faders default to −∞ (`fader_direct = 0`, `fader_early = 0`). Energy gain: Render **−8.1 dB**, Play **−11.4 dB** (impulse peak −19.3 / −22.6 dBFS). SM57 Measured colour alone costs 4.3–4.8 dB. Play sits about 3.2 dB under Render on the tail (the known gap, roadmap §0.F; S7 closes it). | **Auto level** (§3): one fixed output gain worked out from the per-bus energy for the current parameters. It does not follow the signal and is not a compressor. Faders become a balance. Target 0 dB K-weighted. Off under parity. | M | **Yes** (level only, no spectrum change) | **D-UI11:** recommend option A, after S7 and S5. |
| 12 | Is Air 1-pole still needed? | **VERIFIED** (engine code, §4) | The 1-pole cut-off is fc = Wet/d (`early_field.py:1944`): 94 Hz at 3.3 m. At mix 1 that is −20.6 dB at 1 kHz, which is not air. At mix 0.25 (2011) it is a flat −2.5 dB step above about 200 Hz. The default is already 0. ISO 9613 and panels cover the physics. | Remove it from the UI. Keep it under Advanced as "2011 Air 1-pole", which the Hall snapshot sets (`app.js:220`, `air_lp 0.25`). | S | No (default 0) | **D-UI12:** recommend hiding it (parity-only). |
| 13 | Lattice: more 3D control and zoom; Hall can't zoom out | **BUG, VERIFIED** (Hall: 40 wheel-outs change nothing; `shots/b13_hall_lattice_pair.png`) | `static/js/image_views.js:224` clamps the camera radius to 2.5–120 m. The Hall lattice wants max(14, 97·3.2·1.05) = 326 m (`:204-213`), so the camera sits inside the lattice. Far plane is 400 (`:33`). Orbit needs right/middle/Alt-drag (`:384`); left-drag does nothing. | Scale the clamps with the room (min 0.2·diag, max 8·max(W,H,L)); far plane = 4 × radius. Left-drag orbits, right/Shift-drag pans. Add +/−/Fit/Reset buttons. | S | No | Just do it. |
| 14 | Paths doesn't look like the room; no 3D rotate | **VERIFIED** (code and screenshot) | `buildPaths` (`image_views.js:289-321`) draws edge lines (`homeBox`), a near-black floor (`0x12141a`) and a near-horizontal front camera (phi 1.12, theta 0). Orbit is hidden as in item 13. | Shade the floor, draw faint walls with A–F labels (as on the Floor tab), use a ¾ default view, and left-drag orbit. Mock: `mock/m4_space.png`. | S–M | No | Do it in S-UI1 (orbit and zoom) and S-UI2 (looks). |
| 15 | Merge Lattice and Paths with view chips; sidebar = room size + Hadamard | **FEATURE** | They are already one viewer (`image_views.js` `mode` lattice/paths/legs), shown under two tabs. | One **Space** tab with chips Lattice · Paths · Last legs. Sidebar: Room size plus Hadamard (moved out of the Mix box). Mock `m4_space.png`. | S | No | Do it in S-UI2. |
| 16 | The Mix box controls belong elsewhere | **VERIFIED** inventory | The sidebar "Mix" box (`index.html:633-673`) is shown on Mix, Lattice, Paths, Colour, Surfaces and Polar. It holds Hadamard, IR length, Air amount, Air 1-pole, Air shelf, Air climate, the 2011 snapshot, "Also bake an IR", Shared tail and Diffusion seed. The seed is a **duplicate** of `diffusion_seed` on Surfaces (`index.html:509` vs `:672`). | Delete the Mix box. Hadamard → Space. Air ×3 → Surfaces/Air. 1-pole, IR length, shared tail, snapshot, bake IR and one seed → Advanced. Map in §5, mock `m1_tabmap.png`. | S | No | Do it in S-UI2. |
| 17 | Colour tab should be just post-EQ | **VERIFIED** inventory | Today the "Colour" page holds: the wet-IR 1/3-octave **analyser** (Now/Last/Hold A/Hold B/Clear, 0 dB ref Peak band / 1 kHz), a "This face · absorb×EQ" strip, and **below it the whole Surfaces panel** (room net, 16 materials, Solo/Mute, 7-band absorption, face EQ low/peak/high, Smear, Structure dif, seed, λ_ref) and the Polar field. No post-EQ exists. | Colour = **one post-mixer EQ** (low shelf, peak, high shelf), flat by default and bypassed bit-exact, drawn over the analyser. It goes after the mixer, so the locked stage order (source → air → surfaces → mic colour) is unchanged. Mock `m5_surfaces_colour.png`. | M (both engines and wasm) | Only when moved off flat | **D-UI17:** recommend yes, in S-OUT with auto level. |
| 18 | Air belongs with Surfaces | **AGREED** | The air controls sit in the Mix box (item 16). | Surfaces tab gains an **Air** card: amount, climate, ISO depth. The Smear/Structure-dif/seed/λ_ref sliders fold into "Advanced" on Surfaces. | S | No | Do it in S-UI2. |
| 19 | Rename the colour option "Assumed toys" to **User defined**; in User defined the 3 Each-capsule pattern graphs become visible and editable, and stay hidden/locked for measured presets | **VERIFIED** (labels and lock code, 1905 tree) | Exact labels: `static/index.html:212` `<option value="ASSUMED_TOYS">Assumed toys</option>` in `#colour_mode` (options: Measured · Bypass · Assumed toys); `index.html:620` `<summary>Assumed toys <em>not used in Measured</em></summary>` of `<details id="capsuleColour">`; hint `index.html:626` ("Assumed toys mode still uses capsule size on the early path"); `static/js/polar_field.js:156` meta text "Assumed toys · low rings toward omni". Engine value `mic_colour/modes.py:7` `ASSUMED_TOYS` (aliases ASSUMED/TOYS/LEGACY, `:11-19`). The 3 graphs are `<details class="mic-each" id="micEach">` (`index.html:256-284`, canvases `micPolarL/C/R`), collapsed by default; `app.js:903-918` `placeCapsuleControls` moves the family/polar rows into them on the Mic tab. The pattern lock already keys on the mode: `app.js:1578` and `:1717-1718` disable family/polar only when `colour_mode === "MEASURED_SHELF"`, so ASSUMED_TOYS and Bypass are already editable. No test matches the label text (rg over `software/tests` and the phase harness: 0 hits). | Change the **labels only**; keep the value `ASSUMED_TOYS` so saved states, API and tests are unchanged: option text "User defined", `capsuleColour` summary "User defined capsule <em>not used in Measured</em>", hint "User defined still uses capsule size on the early path", polar meta "User defined · low rings toward omni". Visibility: `micEach.hidden = colour_mode === "MEASURED_SHELF"` (open, not just un-hidden, when User defined is picked; Bypass behaves like User defined, see D-UI19). Editable = drag the amber front to aim (exists) plus drag the lobe rim to set `polar_*` (new; writes the same value as the section slider, item 20). Measured keeps aiming on the Top view. Note the mode is not only a pattern unlock: it also turns on the early-path capsule toys and the −6 dB inject shelf (`modes.py:32-39`), so the new name must not imply "Measured but unlocked". Mock `mock/m3_mic.png` (v2). | S | No (labels and visibility only; ASSUMED_TOYS sound unchanged) | **D-UI19:** recommend yes, with Bypass also showing the graphs. Do it in S-UI2. |
| 20 | Pattern controls only inside the per-mic sections (Side mics, Centre mic); Side shows ONE shared side-mic pattern, with a small **Split L/R** tick for two independent side mics | **VERIFIED** (layout and presets) | Today the family/polar rows live in `#capsuleStackListen` (`index.html:592-616`, the Listen sidebar on other tabs) and are moved under the Each-capsule graphs on the Mic tab (`app.js:903-918`). The preset pickers are separate `.mic-choice` blocks (`index.html:228-252`: `mic_preset_side` and `mic_preset_centre`). The state already has **separate** `mic_preset_l/c/r` (`app.js:89`); the side picker writes both via `applyCapsulePreset(["l","r"], …)` (`app.js:1872-1876`), and the server resolves each slot on its own (`app_server.py:473`). So a per-side preset needs no new key. All 11 Mic setups set `family_l = family_r` and `polar_l = polar_r` (`app.js:6-63` setup table; VERIFIED by script), so one shared side control loads every setup unchanged. | Move family + polar into the **Side mics** and **Centre mic** sections (next to preset and high-pass); delete the rows from the Each-capsule slots and the Listen stack. Side, unsplit (default): one Family + Polar that writes both `family_l/r` and `polar_l/r`. **Split L/R** ticked: Left and Right rows, each writing its own key. Unticking copies L to R (toast "Right now matches Left"). The tick is UI state (`side_split`), derived on load as `family_l != family_r or polar_l != polar_r or mic_preset_l != mic_preset_r`, so old saves open correctly. Split also shows a preset picker per side (`applyCapsulePreset(["l"])` / `(["r"])`). **How it combines with the link chip (item 3):** the chip is geometry only (position, height, yaw; Mirror = today's Link angles), the tick is capsule only (preset, high-pass label, pattern). They are orthogonal and nothing is set twice; all 6 combinations are valid (e.g. Independent + unsplit = two identical mics aimed freely; Mirror + split = mismatched pair). MS classic: the Side section is the S figure-8 pair; keep it unsplit and disable the tick with "M/S uses one figure-8". Mono centre hides Side; Binaural hides both pattern blocks. Measured locks the section controls with the S-UI1 reason; User defined unlocks them and shows the graphs (item 19). Mock `mock/m3_mic.png` (v2). | S | No (uses the existing per-capsule keys `family_*`, `polar_*`, `mic_preset_*`; with one preset in the list, split presets only matter once more mics are added) | **D-UI20:** recommend yes, all in S-UI2. |

**Extra findings, all VERIFIED:**
- **X1.** The Studio and Club chips set `fdn_g` 0.85/0.9 but leave Decay armed, so those values do nothing (`app.js:2137-2160`; `applyPlace` never touches `decay_lock`).
- **X2.** There are two seed controls for one parameter (item 16).
- **X3.** The default mic list has only the SM57, so Measured mode always locks the pattern (item 2b).
- **X4.** All 11 Mic setups have identical L and R family/polar (item 20), so a shared side control is lossless for every preset.

---

## 2. Item 10: what Feedback does that Decay doesn't

Code references: `render_pipeline.py:1091-1092, 1178-1185` (Render), `:1610-1612, 1728-1736` (Play params), `engine/fdn.py:581` (`structure_gain_for_rt60`), `app.js:1639-1657`, `app_server.py:413-414` (defaults `decay_s` 1.8, `decay_lock` true).

**Decay armed (`decay_lock` true, the default):**
- Moving the Decay slider sets the lock. Moving Feedback clears it (`app.js:1646, 1654`).
- The loop runs lossless at g = 1/√N (the ±1 Hadamard lock holds).
- Each line gets its own loss, 10^(−3·dᵢ/(sr·T60)) (`line_t60`). That is Jot's rule: every line decays at the same rate per second, so T60 is exact and even across delays.
- Feedback (`fdn_g`) is ignored. The makeup uses `structure_gain_for_rt60(…)/N`.

**Feedback in charge (`decay_lock` false):**
- The loop scale is uniform, g = Gain/N. With the unscaled Hadamard (row norm √N), one trip scales by Gain/√N, which is −15 dB per trip at Gain 1 and N = 32.
- Short lines decay faster per second than long ones, so the tail is uneven. This is the 2011 Reaktor law.
- **Measured (`data/levels/params_*.log`):** at the default room (mean delay 29.2 ms), Gain 1 → **0.117 s**, Gain 0.85 → **0.107 s**. Only in the 57×34×97 Hall (mean delay 415 ms) does Gain 1 give a usable 1.65 s.
- The FDN energy stays almost the same (Render −7.95 vs −7.97 dB), because `ir_rms_makeup_from_inject` renormalises it.

**What Feedback gives that Decay can't:** (a) bit-parity with the 2011 snapshot, and (b) the 2011 uneven-decay character in very large rooms. In normal rooms it is effectively a 0–0.12 s slap control.

**Recommendation (D-UI10): merge.**
- Decay (s) is the only tail control. It moves onto the FDN strip on the Mix desk.
- Feedback goes under Advanced as "2011 law (Structure Gain)". It is shown and active only when Reaktor parity is on or the Hall snapshot is loaded; the snapshot sets `decay_lock` false (`app.js:214-215`). Rename the hint.
- Remove `fdn_g` from the Studio/Club presets (X1).
- No sound change at defaults: VERIFIED that Decay is armed by default, so `fdn_g` is unused.

---

## 3. Item 11: levels at defaults and an auto-level design

**Measured (VERIFIED, `scripts/levels.sh`, `levels_render1500.sh`, `levels_an.py` → `data/levels/levels_summary.json`).**

Setup: the 18:15 client state (captured from the page, `data/client_state_1815.json`), one unit impulse, 48 kHz.
- E = stereo IR energy, the mean of L and R, in dB. This equals the output/input RMS ratio for white noise.
- K = the same after BS.1770 K-weighting.
- Peak = impulse-response peak in dBFS.

| Scene | Render E / K / peak | Play E / K / peak |
|---|---|---|
| **Defaults as heard** (FDN only; Direct and Early faders −∞) | **−8.14 / −4.53 / −19.3** | **−11.38 / −7.91 / −22.6** |
| Direct only, 0 dB | −8.06 / −4.51 / −10.0 | −8.06 / −4.51 / −10.0 |
| Early only, 0 dB | −19.43 / −15.82 / −20.4 | −14.21 / −10.65 / −18.3 |
| Direct + FDN + Early, all 0 dB | −3.01 / +0.55 / −5.7 | −3.15 / +0.37 / −6.4 |
| FDN, Decay 0.6 / 1.8 / 4.0 s | −8.32 / −8.14 / −8.36 | −11.74 / −11.38 / −11.54 |
| FDN, Bypass colour (no SM57) | −3.38 | −7.05 |

**What this means:**
1. The default output is about 8–11 dB below the input in energy. ASSUMED: a −18 dBFS RMS programme comes out near −26 (Render) / −29 (Play) dBFS RMS.
2. The tail is **already energy-normalised against Decay** (±0.2 dB Render, ±0.4 dB Play), so "Decay changes loudness" isn't the problem. Fader defaults and mic colour are.
3. Measured SM57 colour costs 4.3–4.8 dB.
4. Play's FDN is a constant 3.2 dB under Render. This is the same in every window from 0 to 1.5 s, and the same on the 16:30 tree. It is the gap roadmap §0.F already pins on the Play-only −1.70 dB trim, and **S7 (D3/D3b) closes it**.
5. Early differs between the paths (Play +5.2 dB). ASSUMED cause: Play's 32 images and old shelf versus Render's full set; S5 changes Play early.

**Design: fixed-energy wet normalisation ("Auto level"). It is not dynamic and not a compressor.**
- **Option A (recommended): one output gain from the per-bus energies.**
  - G = 10^(T/20) / √(Σ_b w_b²·E_b), over b ∈ {Direct, Early, FDN, Dry}.
  - w_b is the bus fader×trim gain after the mic matrix.
  - E_b is the K-weighted energy of bus b at 0 dB for the current parameters.
  - G is recomputed only when parameters change, and ramped over about 50 ms. It never follows the signal.
  - Faders then act as a balance: raising FDN makes Direct quieter so the total stays at T. That is what Idle asked for.
  - The 1/r² direct/reverb ratio inside the scene is kept, which matters for the 1/r² lock.
  - Target T = 0 dB K, so output loudness ≈ input loudness for broadband material.
  - Off under `reaktor_parity`, with a readout "Applied +x dB".
- **How to get E_b cheaply.** Rendering the IR on every edit is too slow: a 1.5 s IR took 14.3 s on the box (`render1500_default.log`). Instead:
  - Direct: an analytic Σ over capsules of (gain·1/r·pattern)², times a per-preset K-weighted mic-colour energy factor (precomputed once per preset).
  - Early: Σ tap amp² × per-tap broadband reflect, air and colour factors.
  - FDN: already makeup-normalised (VERIFIED to within about 0.4 dB), so use a constant per colour mode and N, calibrated once.
  - Acceptance: the analytic E_b is within ±0.5 dB of the measured IR energy on 8 or more scenes in both paths.
- **Option B: unit energy per bus, then faders.** Each bus is normalised on its own. This loses the distance cue (moving the mic no longer changes direct/reverb). Not recommended.
- **Option C: a fixed calibration constant** (for example +4.5 dB so the default scene is 0 dB K). Trivial, but the faders stay absolute. A stop-gap at most.
- **Option D: normalise the Render output file.** This depends on the input and does nothing for Play. Not what Idle asked.
- **Headroom (VERIFIED from the peaks above):**
  - Option A at T = 0 dB K puts the default impulse peak near −14.8 dBFS and the all-buses peak near −6.2 dBFS.
  - Render keeps `clip_guard`. Play gets a clip LED, not a limiter (a limiter would be dynamic).
- **Sound-changing: YES (level only).** Default on or off is Idle's call; recommend **on**, with an Off chip.
- **Order:** after S7 (Play = Render tail) and S5 (Play early changes), otherwise the calibration is wrong. Ideally after S-MIX too, since the matrix changes w_b.

---

## 4. Item 12: Air 1-pole vs ISO air vs panel darkening

VERIFIED with the snapshot's engine functions (`scripts/air_compare.py` → `data/air_compare.json`). Humidity slider 0.35, studio climate. dB at 1k / 4k / 8k / 16k Hz.

| Path length | 1-pole, mix 1 (fc) | 1-pole, mix 0.25 | ISO 9613 shelf (default) |
|---|---|---|---|
| 3.3 m (direct distance; air-free by lock) | −20.6 / −32.5 / −38.2 / −43.0 (94 Hz) | −2.45 / −2.48 / −2.48 / −2.48 | 0 / −0.07 / −0.37 / −1.23 |
| 7 m (1st-order image) | −27.1 / −39.0 / −44.7 / −49.5 (44 Hz) | −2.5 flat | 0 / −0.15 / −0.78 / −2.62 |
| 17 m (3rd order) | −34.8 / −46.7 / −52.4 / −57.2 (18 Hz) | −2.5 flat | 0 / −0.36 / −1.91 / −6.33 |
| 30 m | −39.7 / −51.7 / −57.4 / −62.2 (10 Hz) | −2.5 flat | −0.04 / −0.64 / −3.41 / −11.0 |

Panel darkening with the default card (α 0.10 at 1k, 0.18 at 4k, 0.22 at 8k), in dB at 1k / 4k / 8k:
- per bounce: −0.46 / −0.86 / −1.08;
- three bounces: −1.37 / −2.59 / −3.24.

**Reading:**
- The 1-pole (fc = Wet/d, `early_field.py:1944`) is not a physical air model. At mix 1 it removes nearly everything above 100 Hz. At the 2011 mix of 0.25 it is a −2.5 dB level step plus a slight LF tilt.
- ISO air grows with **distance**; panels grow with **bounce count**. The two are physically independent and both are needed. ISO is what keeps big rooms dark at long paths (30 m: −11 dB at 16 kHz), where the panels alone give about 1 dB per bounce.

**Recommendation (D-UI12):** take the Air 1-pole off the main UI. Keep it under Advanced as "2011 Air 1-pole", set by parity and the Hall snapshot. Default 0 means no sound change. Keep ISO and panels. The panels do not replace air.

---

## 5. Inventory now, and the proposed tab and control map

**Now (VERIFIED, `data/tour.json`, `shots/tour_*`). Visible controls per tab (ORTF):**

| Tab | Count | Contents |
|---|---|---|
| Room | 20 | Room size; Preview (1 or 2 sources); Advanced (`reaktor_parity`, `colour_impl`) |
| Source | 39 | Source chips, link, radiation preset, yaw/pitch/size (slider + number), Face mic/away/Omni, 6 band chips, Horizontal/Vertical |
| Mic | 52 | Top/Side, 4 Enlarge, colour mode, align, link angles, link heights, side/centre preset + HPF, family/polar ×3. Listen: setup, **head preset/yaw (leak)**, space, stand X/Z, mic/src height, HP, response, proximity, capsule mm |
| Mix | 75 | 3 mic strips (trim/pan/Ø/fader/read/mute), Stereo mic, 4 buses (trim/solo/fader/read/mute), Natural, Feedback, Decay, plus the whole Mix box |
| Lattice / Paths | 58 each | mic checkboxes, All, mode chips, plus **Listen and the Mix box** (neither is relevant here) |
| Colour / Surfaces | 95 each | analyser, net, 16 materials, Solo/Mute, 14 sliders, Smear, Structure dif, 2 seeds, λ_ref, 4 polar toggles, refresh, plus the Mix box |
| Polar 3D | 114 | the same page plus Listen |

**Proposed (`mock/m1_tabmap.png`).** Eight tabs, each with its own sidebar:

| Tab | Main | Sidebar |
|---|---|---|
| Room | Floor and 3D room | Room size, Preview |
| Source | Bigger Place & face and Elevation; Radiation (spectral colours) | Room size, Preview |
| Mic | Top/Side, Combined, Each mic open with a live pattern | Listen: setup, L/R link, 3rd mic; Head only in binaural |
| Mix | Mic strips with Route; buses; Decay on the FDN strip | Output: Auto level; Preview |
| Space | Lattice · Paths · Last legs | Room size + **Hadamard** (Hadamard stays off Room/Floor and Mic, per Idle's memory) |
| Surfaces | Net, materials, faces, plus an **Air** card; Smear/Structure dif/seed/λ_ref folded | Room size, Preview |
| Colour | Post-EQ over the analyser | Preview |
| Polar | Combined · Each mic · At speakers | Listen |

**Advanced** (one global fold, Structure jargon only): Reaktor parity and the 2011 snapshot, Feedback (2011 law), 2011 Air 1-pole, IR length, Shared tail, Diffusion seed (one copy), Colour impl, "Also bake an IR".

**Design language:** the mocks reuse the app's own tokens (`app.css:2-27`: `--bg #0b0c10`, `--accent #2dd4bf`, pills, 12 px radius). ASSUMED that these match Idle's site. No site URL is in `HANDOVER.md` or the roadmap, so Idle should confirm or send the URL.

---

## 6. Mixer and routing design (items 3, 4, 6)

**Standard practice (sources: Sound On Sound "This Is Stereo! Part 4" and Q&A on M-S decoding; Universal Audio MS basics; Decca tree panning/gains, ebrary/"Panning and gains for three- and five-microphone trees"; Mix "The Decca Tree"):**
- **MS:** L = M + S, R = M − S. On a desk: M centred; S hard left; a duplicate of S, polarity-inverted, hard right; the two S faders linked. The S level is the **width**. Check by muting M: the S pair should cancel in mono. The optional −3 dB matrix compensation is L = (M+S)−3 dB.
- **Blumlein / XY:** coincident, panned hard L/R. Blumlein is crossed figure-8s at 90° (the XY setups with the fig-8 family).
- **Decca tree:** L/R hard (or pulled slightly in), C centred about 3 dB below L/R (−3 dB pan law: the faders stay level), or −4.5 to −6 dB by taste. Outriggers hard L/R. Often a high-pass of about 110 Hz on C.
- **AB, ORTF, NOS, DIN:** pairs panned hard L/R.

**Proposal (`mock/m2_mix.png`):**
- **Engine model.** The engine still produces one signal per mic (image taps → per-mic FDN inject → per-mic output). The desk becomes a signed 3×2 matrix:

  ```
  w = route(strip) · gain · polarity
  ```

  - Pan: linear (2011, default) or constant-power law.
  - Centre: the pan law at 0.
  - Both: (g, g).
  - L or R only.
  - M/S decode: (+g, −g), where g is the Width gain.

  This generalises `capsule_speaker_weights` (`engine/fdn.py:386`) and the Play `mic_gain/pan/phase` fields into `w[3][2]`. ASSUMED: the existing 9 floats can carry it with a blob field added.
- **MS classic moves its decode from `early_field.py` (capsule level) to the desk.** Acceptance test: at Width 0 dB it must null against today's MS classic (< −90 dB). ASSUMED to be exactly equivalent, because each mic has its own linear path. It is **not** equivalent with Shared tail on (one network for all mics), so make M/S decode select per-mic tails, or document the difference.
- **Pair modes.** Stereo pair (L/R faders ganged, which replaces "Stereo mic"), M/S pair (M and S strips with Width), Independent.
- **Setup dropdown → desk preset** (Idle's list):

  | Setup | Desk |
  |---|---|
  | AB / XY / ORTF / NOS / DIN | Stereo pair, hard L/R, C off (or a Room mic) |
  | MS classic | L strip = S, routed **S → +L, −R** (Width 0 dB = ±1); C strip = M, Both at +3.5 dB (= today's M weight 1.5 per side); **R strip freed** (off, or a Room mic). Updated 3 Oct 14:30 (Idle 14:15). |
  | MS 3-mic (`ms`: omni mid, cardioids inward) | Stereo pair plus C Centre |
  | Mono centre | C Centre, L/R off |
  | Binaural | locked L/R, C off |

  A Decca-style L/C/R starts from Custom with C at −3 dB. Changing the setup reloads the preset **only if** the desk hasn't been touched since; otherwise it asks.
- **3rd mic as a Room mic.** It needs its own position, yaw and preset in `MicStand`/`early_field` (taps per mic), with its own FDN inject. Size L. The defaults stay bit-identical because the 3rd mic is off or Centre, as today.
- **Polar "At speakers" (item 6).** The same `w` drives the per-speaker polar sums, so the graph always matches what the desk sends.

---

## 7. Build session prompts (paste-ready) and where they go

**Order:**
1. **Shared tail.** It appears to have landed (17:53–17:57, not verified); verify it first.
2. **S-UI1.** Quick bugs, no sound change, UI files plus a display-only Python helper. Run it now: it touches no engine, wasm or tests that S7 or S5 need.
3. **S7.**
4. **S-UI2.** Tab restructure, no sound change. It can run before or alongside S5, because S5 is engine/Play SURF.
5. **S5.**
6. **S-MIX.** Decisions D-UI3 and D-UI4. Sound changes only in the new modes.
7. **S-OUT.** Auto level and post-EQ. Decisions D-UI11 and D-UI17; this one changes the level.

S-OUT goes last because it needs final levels from S7, S5 and S-MIX.

### S-UI1: quick bug fixes (no sound change)
> Hi Build. Session S-UI1: UI bug fixes only. **Don't change the sound:** Play and Render must stay bit-identical; prove it with `harness\run_all.py` (goldens unchanged) and the phase suite. Evidence and file:line references: `handoff_build_support_2\research_ui_wishlist\REPORT.md` §1 (items 1, 2, 5, 7, 8, 13) and `mock\m8_bugs.png`. Do this, in order:
> 1. **Hidden leak (item 7):** add `[hidden]{display:none!important}` near the top of `static/css/app.css`. Run `research_ui_wishlist\scripts\hidden_audit.py` against your server; expect 0 visible `[hidden]` elements on every tab × {ORTF, Binaural, Mono}. Head preset and Head yaw show only in Binaural.
> 2. **Each-capsule lobes (item 2a):** `mic_desk.js` `drawPolar2d` lines 730 and 744 use `cx − r·sin`. Use `cx + S·r·sin` with `S = RoomMath.YAW_X_SIGN`, as `polarFrontPx` (561) and the pointer (866–888) do. Check the Top-view halo (417) and the side view (498) with the same test. Test: XY 90° and ORTF; each lobe's maximum is within 5° of its amber front dot, in Measured and in Bypass.
> 3. **Pattern controls (item 2b):** when Measured locks `family_*`/`polar_*` (`app.js` 1576–1578, 1717–1718), show the reason next to them ("Shure SM57 is a fixed cardioid. Pick a multi-pattern mic or set Colour to Bypass"). **Do not** open "Each capsule" by default (superseded by item 19: S-UI2 shows it only in User defined/Bypass).
> 4. **Spectral colours (item 1):** add `static/js/spectrum_colors.js` (low = red → orange → yellow → green → blue → high = violet; 20 Hz deep red, 16 kHz violet). Use it in `source_desk.js` (7–12), `mic_desk.js` `RING_COLORS` (27) and every legend.
> 5. **Knobs (item 5):** add a shared `static/js/knob.js` for trim, pan (and later width). Vertical pointer-capture drag (200 px = full range), Shift ×0.1, wheel = one step, double-click resets to 0 dB / centre, arrow keys, no jump on click, 44 px hit area, value tooltip while dragging. Keep the `<input type=range>` as the value store so state and tests don't change. Test with Playwright: a 60 px vertical drag changes the value; a click doesn't.
> 6. **Plane tilt (item 8):** in `polar_field.py` (`_mic_source_plane` 256–289 used at 514/583, `_lr_source_plane` at 625), make the default plane horizontal at mic height and draw the source elevation as a marker. Keep the old plane behind a "Tilt to source" chip. Test: mic height 1.5 → 3.0 m keeps the stack upright (tilt 0°).
> 7. **Space camera (item 13/14, controls only):** `image_views.js`: scale the radius clamp (224) with the room (min 0.2·diag, max 8·max(W,H,L)); far plane = 4 × radius; left-drag orbits, right/Shift-drag pans; add +/−/Fit/Reset buttons. Test: the Hall (57×34×97) lattice fits on Fit, and wheel-out works.
> 8. Bump WORKLET_VER only if you touch the worklet (you shouldn't need to). Report goldens unchanged, the suite results, and screenshots of each fix.

### S-UI2: tab and control restructure (no sound change)
> Hi Build. Session S-UI2: restructure the tabs and sidebar. **Don't change the sound** (goldens unchanged). Plan: `research_ui_wishlist\REPORT.md` §5 and §1 items 19–20, and mocks `m1_tabmap.png`, `m3_mic.png` (v2, Mic tab), `m4_space.png`, `m5_surfaces_colour.png`, `m6_source.png`, `m7_polar.png`. Idle's rules: uncluttered tabs showing only relevant controls; no Hadamard on Room/Floor or Mic; Structure jargon under Advanced; keep the app's design tokens.
> 1. **Tabs:** Room · Source · Mic · Mix · **Space** (merges Lattice and Paths; chips Lattice · Paths · Last legs; it is one viewer already) · Surfaces · Colour · Polar. Give each tab its own sidebar as in the map; update `syncSidebar`. Remove the `isCS` shared page, so Colour, Surfaces and Polar each get their own page.
> 2. **Delete the sidebar Mix box** (`index.html` 633–673). Hadamard → Space sidebar. Air amount, climate and ISO depth → a new **Air** card on Surfaces. Air 1-pole (renamed "2011 Air 1-pole"), IR length, Shared tail, 2011 snapshot, "Also bake an IR" and **one** diffusion seed (remove `diffusion_seed_mix`) → Advanced.
> 3. **Feedback vs Decay (D-UI10, if Idle accepts merge):** Decay (s) goes on the FDN strip. Feedback goes under Advanced as "2011 law (Structure Gain)", visible and active only with Reaktor parity or the Hall snapshot. Remove `fdn_g` from the Studio/Club presets (`app.js` 2137–2147; it is dead while Decay is armed). Reword `#decayHint`.
> 4. **Source layout:** Place & face fills the column; Elevation 300 px; narrower controls column.
> 5. **Space looks:** shaded floor, faint walls with A–F labels, ¾ default camera.
> 6. **Polar page:** chips Combined (reuse the Mic tab component) · Each mic. ("At speakers" comes in S-MIX.)
> 7. Surfaces: fold Smear, Structure dif, seed and λ_ref into an "Advanced" section on that tab.
> 8. **Colour "User defined" (item 19, D-UI19):** relabel only, keep the value `ASSUMED_TOYS`: `index.html:212` option text → "User defined"; `:620` summary → "User defined capsule <em>not used in Measured</em>"; `:626` hint → "User defined still uses capsule size on the early path"; `polar_field.js:156` → "User defined · low rings toward omni". Show and open `#micEach` (the 3 Each-capsule graphs) when `colour_mode` is ASSUMED_TOYS or BYPASS; hide it in MEASURED_SHELF. Editable: the amber front drag (exists) plus a rim drag that sets `polar_*` (same value as the section slider). Measured keeps aiming on the Top view. Test: switching the mode toggles `#micEach` visibility; saved states with ASSUMED_TOYS load as User defined; goldens unchanged.
> 9. **Pattern controls only in the mic sections (item 20, D-UI20):** move family + polar into the Side mics and Centre mic `.mic-choice` blocks (`index.html:228-252`); remove the rows from `#capsuleStackListen` and stop `placeCapsuleControls` (`app.js:903-918`) moving them under the graphs. Side unsplit (default): one preset + Family + Polar writing both `mic_preset_l/r`, `family_l/r` and `polar_l/r`. A small **Split L/R** tick shows Left and Right rows (preset, family, polar) with their own keys (the state already has `mic_preset_l/r`, `app.js:89`; use `applyCapsulePreset(["l"])`/`(["r"])`); unticking copies L to R. `side_split` is UI state, derived on load from any L≠R among those keys. The L/R link chip (S-MIX) is geometry only; the tick is the only pattern split, so there are no duplicate controls. MS classic: tick disabled ("M/S uses one figure-8"). Mono centre hides Side; Binaural hides both pattern blocks. Measured: locked with the S-UI1 reason. Test: every Mic setup loads unsplit with identical state to today (all 11 have L = R); split + edit R leaves L unchanged; unsplit copies L to R; goldens unchanged.
> 10. Tests: a Playwright tour where every tab shows only its own panels (assert the sidebar panel IDs per tab), the hidden audit is 0, goldens are unchanged, and the phase suite passes.

### S-MIX: mic link, 3rd mic and mixer routing (PASTE-READY: new Build window, effort high; run after S-UI2 fix-up 2. D-UI3/D-UI4/linear pan law LOCKED by Idle 3 Oct 15:57; updated 16:00)
> Hi Build. New session: **S-MIX**, at high effort. Run it after the S-UI2 fix-up 2 (`sui2_fixup\FIXUP2_PROMPT_mic_each.md`) has landed.
> - Idle locked (3 Oct 15:57):
>   - **D-UI3 yes:** three independent mics with L/R link modes;
>   - **D-UI4 yes:** the desk matrix with M/S decode, Width and Route chips, including "S → +L, −R" on any strip;
>   - **the 2011 linear pan law as the default.**
> - Design: `handoff_build_support_2\research_ui_wishlist\REPORT.md` §6 (desk) and §8 (decisions). Mocks: `mock\m2_mix.png` v2, `m3_mic.png`, `m7_polar.png`.
> - **Defaults must stay bit-identical:** ORTF and every current setup at defaults, goldens byte-identical (print the SHA1s before and after).
> - Line numbers are from the 3 Oct 14:15 tree; S5 has since touched `render_pipeline.py`, so re-find them.
> 1. Replace the desk law with a signed matrix `w[3][2]` per mic.
>    - Route chips on **every** strip (L, C and R alike): Pan · Centre · Both · L · R · **S → +L, −R**.
>    - "S → +L, −R" is M/S decode from a single side mic: the strip feeds L at +g and a polarity-inverted copy of itself to R at −g. g is that strip's **Width** knob (dB; 0 dB = ±1), which replaces Trim while the route is on.
>    - Any strip may take it, more than one at once (they sum), with no requirement that another strip is the M. With M muted, an S-routed strip cancels exactly in mono (L+R = 0).
>    - Pan-law chip: 2011 linear (default) or constant power.
>    - Generalise `engine/fdn.py` `capsule_speaker_weights` (`:375-397`) and the Play mic gain/pan/phase fields. Add a blob field and bump WORKLET_VER.
>    - The read-only matrix shows the signed weights.
> 2. Move the MS-classic decode from `engine/early_field.py` (`ms_decode`, `:1643-1715`) to the desk.
>    - Today (VERIFIED, code), M and S sit at the stand centre and the S is a hard-wired figure-8 at yaw_M + 90° (`:1650`, `:1694-1696`). The L bus is M+S, the R bus M−S and the C bus M, folded L+½C / R+½C. At default trims that gives L = 1.5·M + S and R = 1.5·M − S.
>    - New mapping:
>      - **L strip = S**: a figure-8 capsule coincident with C, aim yaw_C + 90°, routed **S → +L, −R**, with w_S = (+g_L, −g_R) from today's trims.
>      - **C strip = M**, routed Both, with w_M = (g_L + ½g_C, g_R + ½g_C). At defaults that is 1.5/1.5 = +3.5 dB.
>      - **The R strip is freed.**
>    - While the S capsule is coincident with M (the M/S pair default), its User-defined capsule toys and colour follow the M axis, as `ms_decode` does today (`th_l = th_r = th_m`). Once it is moved off the M point, they follow its own axis. This is the default (ASSUMED, Idle 15:57: "apply the minor defaults"); note it in HANDOVER.
>    - Acceptance: at Width 0 dB the new desk nulls against today's MS classic at < −90 dB in Play and Render, Shared tail off, same geometry. With Shared tail on, either use per-mic tails for M/S or document the difference.
> 3. Pair modes: Stereo pair (replaces Stereo mic), M/S pair, Independent.
>    - M/S pair has two pickers: which strip is S (L, C or R; default L) and which is M (default C). The S mic is placed coincident with the M mic, aimed M + 90°, and the remaining strip is free (Independent).
>    - The setup dropdown loads the desk preset (table in §6) only if the desk hasn't been touched since.
>    - Loading MS classic, MS or AB omni still switches Colour to User defined (D-UI21); a user ticking Split or changing routes never triggers that switch.
> 4. Mic tab: L/R link (Mirror · Linked · Independent; **geometry only**: position, height, yaw. Preset and pattern stay with the Split L/R tick from S-UI2; do not add pattern or preset to the link chip) and 3rd mic (Off · Centre · Room with its own X/Z/height/yaw/preset). Positions per mic go through `MicStand`, early taps and FDN inject.
> 5. Polar "At speakers": per-speaker sums using `w`.
> 6. Tests: default goldens unchanged; MS null; Room-mic image delays match the geometry; a Playwright test that the setup preset loads the matrix.
> 7. **Acceptance scenario (D-UI25 09:09 + Idle 14:15): M/S from one side mic plus an independent room mic.** L = figure-8 side, decoded +L/−R; C = mid, centre to both; R = independent room mic with its own position, aim and pattern, panned. Mock: `mock\m2_mix.png` v2 (Route chip on the L strip).
>    - **Setup.**
>      - Load MS classic. It switches to User defined (D-UI21), and the desk preset is L = S → +L, −R at Width 0 dB, C = M Both +3.5 dB, R off.
>      - Set the R strip to Independent / Room, give it its own X/Z/height/yaw and preset (omni), route it Pan R 30 % at −6 dB, and set Width +2 dB on L.
>      - Lift the S-UI2 "M/S uses one figure-8" block on the Split tick.
>      - Per-side HPF keys `mic_hpf_l` / `mic_hpf_r`; `mic_hpf_sides` stays the unsplit control.
>    - **Run it twice:**
>      - in User defined, L is family `bi`;
>      - in Measured, L uses a measured figure-8, i.e. `RoyerR121`, whose `capsule_law` is fig8/bi (VERIFIED, `tests/test_mic_colour_relative.py:140-141`).
>      - In Measured, the SM57 default on L would be a cardioid "S". Show a hint ("S wants a figure-8 preset"); don't block it.
>    - **Null tests (Play and Render, Shared tail off):**
>      1. **MS classic equivalence:** with R off and Width 0 dB, the new desk nulls against today's MS classic at < −90 dB, same geometry (S coincident with M at the stand, aim +90°), in User defined and in Bypass.
>      2. **Mono cancel:** with C muted and R off, (L+R)/2 of the output is exactly 0 (≤ −200 dB). With C muted, L-out = −R-out sample for sample.
>      3. **Width:** at Width +2 dB the S part of L-out minus that of R-out scales by 10^(2/20) exactly, and the M part is unchanged (null of M-only ≤ −100 dB).
>      4. **The room mic is independent:**
>         - moving or re-aiming R, or changing R's preset or pattern, leaves the L+C-only output unchanged (null ≤ −100 dB, R muted vs R moved);
>         - R's early image delays match its own geometry;
>         - changing R's preset leaves `mic_preset_l` and L's colour unchanged.
>      5. **Any-strip route:** the same scene mirrored onto the strips (C = S → +L, −R, L = M, R = room, or R = S) gives the same output to ≤ −100 dB.
>    - **Save and reload:** the setup survives. Old saves load bit-identically (every current setup at defaults; goldens unchanged).
> 8. **Source plane badge** (`paintMicModel`, `app.js:1510-1520`): the text reads **"preset data: measured"** (or "preset data: assumed"), not just "MEASURED". It describes the preset's data, not the Colour mode. UI only. ASSUMED default (Idle 15:57).
> 9. **One shared frequency palette (Idle's rule, 3 Oct 15:57).** Every frequency-coloured graph goes from **red at low frequencies through orange, yellow, green and cyan to blue/violet at high frequencies**.
>    - Use one function: `static/js/spectrum_colors.js`, `SpectrumColors.forHz(hz)` (log-frequency, 20 Hz deep red → 16 kHz violet) plus `forIndex(i, n)`. The S-UI1 item 4 file was never added (VERIFIED: it is absent from the 14:15 tree).
>    - Replace today's local palettes, which run the wrong way (VERIFIED):
>      - `mic_desk.js:27` `RING_COLORS`: grey/blue at 20–63 Hz → red at 16 kHz (the Mic tab ring legend);
>      - `source_desk.js:7-12`: 250 Hz blue → 8 kHz red;
>      - `polar_field.js:278-285`: the 3D stack is one hue with brightness by band; make it spectral, low = red.
>    - Every legend must use the same function.
>    - Test: a unit test that `forHz` is monotonic in hue from red to violet, plus a Playwright check that the Mic-tab and Source-tab legends read 20 Hz red … 16 kHz violet.
>    - UI only, goldens byte-identical.
> 10. Report:
>     - golden SHA1s before and after;
>     - the five null tests of item 7 in Play and Render;
>     - t19 (CPU, median of paired A/B; it must not rise more than 1 % against the pre-S-MIX wasm at defaults);
>     - hidden audit 0 and the tab tour;
>     - screenshots of the Mix tab (Idle's scenario) and the Mic tab legend.

### S-OUT: auto level and post-EQ (needs D-UI11 and D-UI17; changes the level)
> Hi Build. Session S-OUT, after S7, S5 and S-MIX. Design: `research_ui_wishlist\REPORT.md` §3 (option A) and §1 item 17; mock `m5_surfaces_colour.png`.
> 1. **Auto level:** a static output gain G = 10^(T/20)/√(Σ w_b² E_b). Use K-weighted per-bus energies from a cheap analytic model: Direct analytic; Early from tap amps × reflect/air/colour factors; FDN as a calibrated constant, since makeup already normalises it. Recompute only on parameter changes and ramp over 50 ms. Target 0 dB K by default; chips Auto level / Off; "Applied +x dB" readout. Off under `reaktor_parity`. Both engines.
> 2. Acceptance: the analytic E_b is within ±0.5 dB of the measured IR energy (`research_ui_wishlist\scripts\levels_an.py` method) on 8 or more scenes, in both paths. With Auto on, the default scene's output K-energy is 0 ± 0.5 dB, and moving any bus fader changes the total by < 0.5 dB.
> 3. **Post-EQ (Colour tab):** low shelf, peak and high shelf after the mixer, in both engines. Flat must be a bit-exact bypass. The locked stage order before the mixer is unchanged.
> 4. Goldens: regenerate only with Auto level on, with the reason recorded; with Auto off, the goldens are unchanged.

---

## 8. Decisions for Idle

| ID | Question | Recommendation |
|---|---|---|
| D-UI3 | 3 independent mics (MS pair + room mic) and L/R link modes? | **LOCKED yes (15:57)** |
| D-UI4 | Desk matrix with M/S decode, Width and Route chips; default pan law? | **LOCKED yes, 2011 linear default (15:57)** |
| D-UI8 | Mic-tab plane: horizontal by default, with "Tilt to source" as a chip? | Yes |
| D-UI10 | Feedback: keep, merge or remove? | Merge: Decay main, Feedback under Advanced/parity |
| D-UI11 | Auto level option A, B or C; on by default? | A, on by default, Off chip, after S7/S5 |
| D-UI12 | Air 1-pole off the main UI? | Yes, parity-only |
| D-UI17 | Colour = a new post-mixer EQ? | Yes (flat = bypass) |
| D-UI19 | Rename "Assumed toys" to "User defined" (labels only, value stays ASSUMED_TOYS); show the 3 Each-capsule graphs only in User defined; also in Bypass? | Yes; also show them in Bypass (it is not a measured preset either). Note User defined also keeps the capsule toys and the −6 dB inject shelf |
| D-UI20 | Pattern only in the Side/Centre sections, one shared side control plus a Split L/R tick; link chip = geometry only | Yes, all in S-UI2 (keys exist) |
| — | Idle's site URL for the design language | Please send it; the mocks use the app's tokens |

**Update 3 Oct 2026, 09:20 BST: S-UI2 fix-up and locked decisions.** Details are in `sui2_fixup\REPORT.md` §7–8. The prompt is `sui2_fixup\FIXUP_PROMPT.md` (Part A UI; Part B approved).

| ID | Decision (Idle, 3 Oct 09:06; D-UI25 corrected 09:09) |
|---|---|
| D-UI21 | **Yes.** In Measured the preset owns the pattern. Loading AB omni, MS or MS classic switches Colour to User defined. Before: the hidden family/polar changed the sound (−15 to −23 dB nulls). |
| D-UI22 | **Yes.** Bypass = preset pattern, no measured colour. *The "no capsule graphs" part is superseded by D-UI27 (Idle 14:15).* |
| D-UI23 | **Yes.** Colour merges into Surfaces as "Room colour · analyser of the wet sound" (a measurement, not an EQ). 7 tabs. No tab jump after Render. |
| D-UI24 | **A.** The D-UI17 post-mixer EQ goes on a Mix tab Output strip next to Auto level, built in S-OUT. |
| D-UI25 | **No.** Keep Split L/R in Measured: a preset picker per side. Use case: L = side mic, R = room mic, C = M/S mid. This is an S-MIX acceptance scenario. |
| D-UI26 | **A, LOCKED (09:22).** Per-line face colour in both engines (tail + Play early). Session S5: `roadmap\s5_surf_1010\S5_PROMPT_D-UI26.md`. |

Mocks: `m3_mic.png` v3.1 (v2 is in `mock\old\`) and `m9_surfaces_colour_merge.png`. `scripts\hidden_audit.py` v2 finds the tabs itself and visits every Colour mode; the S-UI2 tree scores 0 leaks over 96 states.

**Update 3 Oct 2026, 14:30 BST: Idle's 14:15 asks.**

| ID | Decision / status |
|---|---|
| D-UI27 | **Yes (Idle 14:15, UI only).** The three per-mic graphs (`#micEach`) are always visible: editable in User defined; read-only in Measured and Bypass, showing the preset law with a lock note (MS classic shows its hard-wired figure-8 S). The Source plane (3D polar) goes directly below them. Supersedes D-UI22's "no capsule graphs" and fix-up A2's "hide in Measured". Prompt: `sui2_fixup\FIXUP2_PROMPT_mic_each.md`. Mock: `sui2_fixup\mock\m10_mic_each_always.png`. |
| D-UI28 | **Requested (Idle 14:15); D-UI3 + D-UI4 now LOCKED.** The route **S → +L, −R** on any strip, with Width: M/S decode from a single side mic, which frees the third mic as an independent room mic. It is in the S-MIX prompt items 1–3 and 7 (5 null tests). Mock: `mock\m2_mix.png` v2. |
| D-UI3 | **YES, LOCKED (Idle 15:57).** Three independent mics with L/R link modes (S-MIX). |
| D-UI4 | **YES, LOCKED (Idle 15:57).** A desk matrix with M/S decode, Width and Route chips, including "S → +L, −R" on any strip. **The default pan law is 2011 linear (LOCKED).** |
| Minor defaults (ASSUMED, Idle 15:57 "apply them") | While S is coincident with M, its User-defined colour follows the mid's axis; once moved, it uses its own. The Source plane badge reads "preset data: measured". |
| Palette rule (Idle 15:57) | Every frequency-coloured graph runs red (low) → blue/violet (high) through one shared function (`SpectrumColors`). Today's Mic and Source palettes run the other way (VERIFIED). This is S-MIX item 9. |
| Compatibility | D-UI21: loading an MS-type setup still switches to User defined; Split/route edits never trigger it. D-UI25: Split stays in Measured; R gets its own preset; per-side HPF keys arrive in S-MIX. D-UI20: the link chip stays geometry only; the M/S-pair coincidence is part of the pair mode, not the link chip. |

