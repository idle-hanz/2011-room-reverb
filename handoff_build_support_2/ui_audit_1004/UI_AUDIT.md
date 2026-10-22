# UI_AUDIT 1004: hands-on UI audit of the 2011 Room Reverb tweak app

Written 4 Oct 2026, 14:20 BST, on the box. **Read-only.** Nothing in `software\` was changed, and the app on the PC was not started or stopped.

## What was audited
- **Build:** the PC's `software\` copied at 13:54 BST: `WORKLET_VER` 51, wasm sha1 `6ebecc333b50…` (S-AUDIT), `app.js?v=44`, `mic_desk.js?v=16`, `app.css?v=31`.
  - Copy: `app_copy_1354.zip`, MD5 `6ae2fe57bd4235b71d88da6425da4634` (matches the PC). It excludes `.venv`, caches and `renders`.
  - `3_phase_acceptance_tests\` doesn't exist at the PC root, so there was nothing to copy.
- **How it ran:**
  - `uvicorn app_server:app` on 127.0.0.1:7871 on the box. Wasm was served as `application/wasm`; no COOP/COEP was needed.
  - Browser: headless Chrome with Playwright and SwiftShader WebGL.
  - Scripts in `scripts/`:
    - `tour.py`: 7 tabs at 1600×1000 and 1280×800, then all 12 Mic setups × 3 Colour modes × Split L/R. It also covers Mix and Polar for each setup, every Route chip including "S → +L, −R", Solo/Mute and the Surfaces faces.
    - `knob_probe.py`: tests the knobs with clicks, drags, wheel, double-click, Shift and arrow keys.
    - `setup_probe.py`: selects each setup on a fresh page and reads the desk state.
    - `misc_probe.py`: layout overflow, needles, tooltips and chip styles.
    - `capture_annot.py` and `annotate.py`: element boxes and the annotated shots.
- **Data and shots:** data is in `data/`. The 93 shots are in `shots/`, with crops in `crops/`. **I looked at every shot cited below myself.**
- **Tags:**
  - **VERIFIED** = seen in a screenshot, the DOM, a probe or the code.
  - **ASSUMED** = inferred and not reproduced.
  - **Queue** = new, or already in `roadmap/THURSDAY_LIST.md` (item id).
- **Size:** S ≤ ½ session, M ≈ 1 session, L = several.
- None of the fixes below changes the sound. Anything that would is under Questions.

---

## A. Bugs

| # | Tab | What's wrong | Why it matters | Suggested fix | Size | Tag | Shot | Queue |
|---|---|---|---|---|---|---|---|---|
| B1 | Mix | **Pan and trim knobs are very hard to control (Idle's note).** Each knob is an invisible native horizontal `<input type=range>` stretched over a 32 px circle (`app.css` `.knob input`, opacity 0). Measured by probe: <br>• The whole range sits in about **16 px**: trim **1.5 dB per px**, pan **0.125 per px** (12.5 %). <br>• Clicking jumps straight to the click point. Clicks on the hidden thumb (half the knob) do nothing. <br>• Vertical drag does nothing. <br>• No wheel, no double-click reset, no Shift fine mode, no centre/0 dB detent. <br>• No number readout for trim or pan (only "TRIM"/"PAN"). <br>• Keyboard arrows work (0.5 dB / 0.01). <br>The needle turns 280° for that 16 px. Same for Width, trim_direct, trim_fdn, trim_early and trim_dry. | Every desk knob is affected. You can't set 0 dB or centre by hand, and one click can throw a trim to ±12 dB. | See **Fix F-KNOB** below | S–M | VERIFIED (`data/knob_probe.json`, code `app.js` 760–846, css 1271–1302) | A1_mix_knobs.png | **New** (Idle's note; overlaps the "numeric pan readouts" part of L8) |
| B2 | Mix | **Width knob needle never moves.** `paintDesk()` sets `--needle` for trim and pan but not width, so the needle stays at the CSS default −140° (the minimum) while the value is 0 dB (the centre). | It shows −24 dB when the value is 0 dB. | Paint the width needle in `paintDesk()`, as for trim (−24…+24 → −140…+140°) | S | VERIFIED (probe `width_needle`, shot) | A1_mix_knobs.png | New |
| B3 | Mic | **"MS classic" can't stay selected.** It flips to **Custom** within 300 ms. `matchPresetId()` requires `state.ms_decode`, but nothing ever sets it true (S-MIX moved M/S to the desk). Picking **Custom** snaps back to the matched preset (e.g. ORTF), so that menu item does nothing. | The setup name is wrong. Code that checks `mic_setup === "ms_classic"` (`app.js` 1539) stops treating it as M/S after the first sync. | In `matchPresetId()`, treat `pair_mode === "ms"` with `mic_route_* === "s"` as MS classic. Make Custom a real "keep my tweaks" state, or show it as a read-only label | S | VERIFIED (`data/setup_probe.json`) | A2_ms_classic_measured.png | New |
| B4 | Mic | **MS classic in Measured: the S strip is a cardioid but is drawn and labelled as S.** The side preset falls back to SM57 cardioid, so the L plot draws a cardioid aimed +90° under "S → +L, −R". The only warning is a small hint, "S wants a figure-8 preset". Switching back to User defined does not restore Bidirectional (`family_side` stays cardioid). The R plot is still drawn as a live cardioid although R is muted, whereas Mono centre shows "NOT USED". | It looks like M/S but the S capsule isn't a figure-8. You lose the preset by toggling Colour. | **UI part (safe):** make the hint a visible warning on the S plot. Restore `family_l = bi` when leaving Measured. Grey out the R plot with "NOT USED". **Sound part:** which measured fig-8 to use is **Q1** | S | VERIFIED (shots `mic_ms_classic_meas.png`, `mic_ms_classic_assu.png`, `setup_probe.json`) | A2_ms_classic_measured.png | New |
| B5 | Mix | **At 1280 px the Host bus strip is fully hidden and Early is clipped.** The desk is 962 px wide in an 842 px scroller with no visible scrollbar (Host 886–982 px vs a scroller edge of 873 px). At 1440 px it's 7 px short. | You can't see that a bus exists. Very common laptop width. | Wrap Buses under Mics below about 1500 px, or narrow the strips (78 → 64 px). Always show the horizontal scrollbar | S | VERIFIED (`misc_probe.json`, shot) | A3_mix_1280_cutoff.png | New |
| B6 | Mic | **Binaural still shows dead mic controls:** <br>• Off/Centre/Room third-mic chips (Centre highlighted) <br>• Link heights <br>• a C capsule with an aim handle on the Top view <br>• "C 0 cm" in the readout <br>• Combined caption "Three capsules… stay apart in the speakers" <br>• the source-plane badge "preset data: measured" | Idle's only-relevant-controls rule. They do nothing, because binaural mutes C. | Hide the `#thirdMicRow`, Link heights and the C capsule in binaural. Use a binaural caption and badge ("Head: SADIE II KU100") | S | VERIFIED (shot, DOM) | A5_binaural_dead_controls.png | **Partly queued**: head views and HRTF polar are in R4 (S6). The dead chips and badge are new (left over from AUDIT_1852 A6) |
| B7 | Mic | **Mono centre still shows L/R controls:** Horizontally aligned, Mirror/Linked/Independent, and Off/Centre/Room (Off would remove the only mic), plus Capsule space 0.00. | Clutter. "Off" probably silences the output. | Hide the link and third-mic rows when `mic_setup === mono_c`. Disable "Off" | S | VERIFIED visible; the silence is ASSUMED | `crops/side_binaural_monoc.png` | New |
| B8 | Mix | **The Pan knob is live but ignored on strips not routed to Pan.** `pair()` only reads pan when the route is `pan`. Centre, Both, L, R and S ignore it, but the knob stays enabled and turns. | It's a control that does nothing. | Disable and dim Pan when the route isn't Pan (as Trim already swaps to Width for S) | S | VERIFIED (code `app.js` 442–457) | A1_mix_knobs.png | New |
| B9 | Room, Source | **The L and R capsule labels print on top of each other** ("MR"/"LIR") on both floor plans at ORTF spacing. On the Source tab, "Left" sits at the top-left corner while "Right" is centred on its wall. | Unreadable. You can't tell which capsule is which. | One "L·C·R" stand label, or offset the labels outward along each capsule's aim | S | VERIFIED | A6_floor_labels.png | New |
| B10 | Mic | **The Top-view drag targets overlap at ORTF/XY:** the C capsule circle sits on top of L and R (17 cm spacing). | It's hard to grab L or R. "Clear drag targets" was one of Idle's wishes. | When the spacing is under 2 × the radius, shrink the circles. Put grab handles on the rim or the aim line. Show a hover ring and cursor on the target that will be picked | S–M | VERIFIED visually; which capsule a click actually picks is ASSUMED | A4_mic_targets_labels.png | Related to **L14** (drag issues, "check with Idle") |
| B11 | Mic | **Combined pattern:** the big L/R label sprites cover the capsules, the lobes clip at the right edge, and the overlapped labels read "LR". | You can't see the capsules. Known since AUDIT_1852 A14, but it isn't in S-AUDIT A1–A12 or the Thursday list. | Scale or hide the labels in focus mode, and fit the camera to the lobes' bounding sphere | S | VERIFIED | A4_mic_targets_labels.png | New (unqueued AUDIT_1852 A14) |
| B12 | Mic | **The top of the source-plane 3D stack (8k/16k) renders as jagged, spiky sheets.** | It looks broken. The S-MIX "violet patches / cyan seam" item was meant to clean the stack. | Check the high-band mesh: winding order and the clamp on noisy measured lobes | S–M | VERIFIED (shot); the cause is ASSUMED | `crops/mic_plane.png` | Probably left over from an S-MIX item |
| B13 | Polar | **The footer says "Combined uses the same polar field as the Mic source plane",** but Polar defaults to L + R (C unticked) while the Mic source plane includes C. The two plots look different (near-cylinder vs cardioid stack). | The legend contradicts the plot. | Default the Polar ticks to match the Mic setup (C on when it's used), or reword the footer | S | VERIFIED (shots `1600_polar.png`, `1600_mic.png`) | — | New |

### Fix F-KNOB (B1): plain JS/CSS, no sound change, goldens untouched
1. **Drag:** replace the stretched native range with a pointer-drag handler. Keep the `<input type=range>` (hidden, focusable) for keyboard and ARIA.
   - On `pointerdown`, capture the pointer and store the start value. Don't jump.
   - Value change = (−dy + dx) × scale.
   - **Full range = 200 px:** trim 24 dB → 0.12 dB/px; pan 2 → 0.01/px; width 48 dB → 0.24 dB/px.
   - Round to the input's `step`.
2. **Fine:** Shift (or Ctrl/Alt) while dragging = ×0.1 (trim 0.012 dB/px, pan 0.001/px). Keep 0.1 dB display precision.
3. **Reset:** double-click, or Alt-click, resets to the default: trim 0 dB, pan the strip default (L −1, C 0, R +1 in Independent; 0 otherwise), width 0 dB.
4. **Wheel:** one notch = one step (trim 0.5 dB, pan 0.02, width 0.5 dB). Shift = fine (0.1 dB / 0.005). Only while hovering, with `preventDefault` so the page doesn't scroll.
5. **Detent:** at pan centre and 0 dB, a sticky zone of ±6 px of drag (about ±0.06 pan / ±0.7 dB) that snaps to exactly 0. Shift-drag bypasses it.
6. **Readout:**
   - A small value under each knob, always visible:
     - trim: "+1.5 dB" or "0.0 dB";
     - pan: "L 35", "C" or "R 100" (percent);
     - width: "+3.0 dB".
   - Show the same in a tooltip while dragging.
   - Set `aria-valuetext`.
   - Click the readout to type a value, as the faders already do (`read_*` handler, `app.js` 776).
7. **Bigger target:** 40 px knob with a 4 px hit pad. Cursor `ns-resize` on hover. Dim (not just `pointer-events:none`) when locked.
8. **Test:** Playwright. Drag 100 px and expect half range. Shift-drag 100 px and expect 1/20 of the range. Double-click resets. A wheel notch moves one step. No posted parameter changes on hover.

---

## B. Feels off / polish (no sound change)

| # | Tab | What | Fix | Size | Tag | Shot | Queue |
|---|---|---|---|---|---|---|---|
| P1 | Room | The floor-plan canvas is 900×640 drawn into a 512×364 box, so all labels show at about 57 % (about 5 px). The Source tab's same view is 1:1 | Size the backing store to the CSS box × DPR and draw text in CSS px | S | VERIFIED (`annot_boxes.json` canvas_edit) | A6_floor_labels.png | New |
| P2 | Mic | The chip rows Mirror/Linked/Independent and Off/Centre/Room have no visible label (only `aria-label`) | Add "L/R link" and "Third mic" labels | S | VERIFIED | `crops/mic_side.png` | New |
| P3 | Mic, Mix | **Split L/R** is a separate tick under Side mics, away from the L/R link chips. Two "Independent" chips (Mix pair mode and Mic link mode) mean different things | See **Q5** | S | VERIFIED | `crops/side_assu_vs_meassplit.png` | New |
| P4 | Mic | Section headings change by mode. In User defined the Centre section is just "Pattern". With Split on, the "Side mics" heading disappears and one "No high-pass" sits above Split for both sides. There's an empty gap of about 60 px under the chip rows | Keep "Side mic" and "Centre mic" headings in every mode. Collapse the empty hint row | S | VERIFIED | `crops/side_assu_vs_meassplit.png` | New |
| P5 | Mix | No tooltips: 72 of 72 desk controls have no `title`. Fader readouts lack "dB". The matrix shows raw linear gains ("C +0.500 +0.500") | Add titles, "dB" units and the matrix in dB ("C −6.0 / −6.0 dB") | S | VERIFIED (`misc_probe.json`) | A1_mix_knobs.png | New (L8 covers meters and pan readouts only) |
| P6 | Mix | The 6 route chips wrap onto two lines with "R" orphaned. The FDN strip's Decay slider pushes its readout and Mute lower than the other buses | Two rows of 3 chips (Pan/Centre/Both · L/R/S), or a compact select. Pin the readout and Mute rows to the bottom | S | VERIFIED | A1_mix_knobs.png | New |
| P7 | Mix, Surfaces | Native white `<select>`s (Mix S/M pickers, Air "Climate") break the dark theme. The S/M letters are oversized | Use the shared dark select style | S | VERIFIED | `crops/mix_msc.png`, `crops/surf_air.png` | New |
| P8 | Space, Polar | The active chip ("Lattice", "Combined") has a **transparent** border while inactive chips have borders, so the selected one looks unselected. Mix chips do the opposite (teal = on) | One active-chip style everywhere | S | VERIFIED (computed style) | `crops/space_head.png` | New |
| P9 | All | **Frequency colours:** red→violet order is correct everywhere and comes from the shared stops. But there are two palette files (`spectrum_colors.js` and `freq_palette.js`), and 4 modules colour by band index while `mic_desk` and `source_desk` colour by Hz. The same frequency shifts hue between views: 250 Hz is 96° in the legend vs 120° on the 3D stack, and 4 kHz is 239° vs 220° | Keep one palette file and always use `forHz` | S | VERIFIED (node check) | — | New |
| P10 | Mic, Polar | The ring set 20/63/125/250/1k/4k/8k/16k skips 500 Hz and 2 kHz. The three per-mic plots have no frequency legend (only the source plane does) | Add a mini legend to the trio. Consider octave rings | S | VERIFIED | `crops/mic_each.png` | New |
| P11 | Surfaces | Badge clutter (4+ "ASSUMED" badges). "All legal faces" sits among the material chips. Absorber names use inches. "Solo off" is styled like an active button. EQ labels wrap ("Low shelf / dB"). Absorption sliders have no Hz unit and no colour dot to tie them to the plot. The flat EQ line is drawn as a rainbow | One ASSUMED note per panel. Move "All legal faces" next to the help text. Use mm. Neutral Solo-off style. Wider label column. Colour dots on the band sliders | S | VERIFIED | `crops/surf_net.png`, `crops/surf_cards.png` | New (material defaults are N7; face EQ reset is N8) |
| P12 | Surfaces | Face identity colours (D red, C violet, E amber) reuse frequency hues | Use neutral greys or letters only for face identity | S | VERIFIED | `crops/surf_net.png` | New |
| P13 | Surfaces | Air: the "Air amount (humidity)" readout says 50 % RH at slider value 0.35, while the hint says "Right is drier air". The direction and the readout are confusing | Label the ends ("Off ··· Dry") and show RH and dB/s at 8 kHz | S | VERIFIED readout and hint; mapping ASSUMED | `crops/surf_air.png` | Air is on Surfaces: L15 confirmed done. This part is new |
| P14 | Room, Source, Space, Surfaces | The Room size panel repeats on 4 sidebars. Advanced / Structure locks is on every tab | Room size on Room only (with a link elsewhere) | S | VERIFIED (`tour.json` heads) | — | Advanced on every tab is **already queued L9**. Room size is new |
| P15 | Space | MICS L/C/R ticks appear in the tab bar on Space only (layout shift). For ORTF only C is ticked by default | Move them into the Space panel head. Default to the setup's live mics | S | VERIFIED | `1600_space.png` | New |
| P16 | Room | 3D room: the "Back" label floats mid-floor in front of the mic. The position readout is duplicated (floor plan and 3D, in different colours), and so is the Mic Top readout (header and canvas) | Pin wall labels to the wall planes. Show one readout | S | VERIFIED | `crops/edit_3d.png` | New |
| P17 | Source | The elevation readout "Mic 1.50 m / Src 1.20 m" overlaps the room box edge | Move it outside the box | S | VERIFIED | A6_floor_labels.png | New |
| P18 | Surfaces | The Room Colour face card says "West", a compass word used nowhere else | Use Left/Right/Front/Back | S | VERIFIED | `crops/surf_colour.png` | New |
| P19 | Polar | The banner is still jargon ("Radius = \|capsule gain\| × 10^(H_db/20)…") | — | S | VERIFIED | `1600_polar.png` | **Already queued L10** |
| P20 | Mix | No master meter, clip LED or Output strip | — | M | VERIFIED absent | — | **Already queued N2/N3 (S-OUT), L8** |
| P21 | All | Console: the only message is the three.js r150 deprecation warning. No errors and no failed requests at either width (the favicon is fixed) | Optional: move to the ES-module three.js | S | VERIFIED | — | Known (AUDIT_1852 A16) |

---

## C. Questions for Idle (would change the sound, or touch a locked decision)

1. **Q1 (sound):** In MS classic + Measured, which measured figure-8 should S auto-pick? Options: U87 Ai Bidirect, AKG C414 Bidirect, Rode NT2-A Bidirect or Coles 4038. Today it silently stays an SM57 cardioid (B4).
2. **Q2 (sound):** The MS classic preset sets M (C) to `gain_exact_c = 1.5` (+3.5 dB) to both sides, with S at 0 dB (desk matrix L +1/−1, C +1.5/+1.5). Is that the intended 2011 fold? ASSUMED intended. Compare B6 in the Thursday list (N18: ORTF C at 0 dB).
3. **Q3 (sound):** Picking AB omni or MS (omni mid) switches Colour to **User defined** with a toast, although measured omnis exist (DPA 4006, C414 Omni, U87 Ai Omni, NT2-A Omni). Should these setups stay Measured with an omni preset? VERIFIED (`app.js` 1956).
4. **Q4 (sound, materials):** "Heavy curtain" (Sengpiel heavy velour, wall-only) is the only curtain-type material. It's a textbook value, not a made-up one. Keep it, given "no curtain-type fantasy materials"?
5. **Q5 (locked D-UI3 layout, no sound):** Merge the "Split L/R" tick into the L/R link chips (Mirror / Linked / Independent / Split), as wished ("one shared side mic with a small Split tick merged with L/R link")? Today they're separate controls (P3).
6. **Q6 (UI conflict):** Idle's wishes say both "pattern + yaw controls under each polar plot" and "pattern controls only inside the Side/Centre mic sections". Today the plots only have captions ("Cardioid · −55° · drag front to aim"), and the pattern lives in the sidebar. Should a numeric yaw box (and a read-only pattern name) go under each plot?

---

## D. Checked and fine (VERIFIED)
- 7 tabs (Room, Source, Mic, Mix, Space, Surfaces, Polar).
- No `#micPlayNote`, and no Colour tab. The old `colour` view maps to Surfaces (`app.js` 1440).
- The Hadamard panel is on Space only. Room, Source and Mic sidebars carry no Mix or engine controls.
- The three per-mic diagrams are always shown. They're read-only with a badge in Measured, editable in User defined, and "NOT USED" for unused mics in Mono centre.
- Split L/R is visible in Measured with per-side preset pickers.
- "S → +L, −R" is on every strip and swaps Trim for Width.
- Mono centre locks L/R (D-AUD-1).
- Frequency order is red (low) → violet (high) in every plot and legend.
- No `[hidden]` leaks, and no page-level horizontal overflow at 1600 or 1280 (apart from B5 inside the desk).

## E. Not testable headlessly
- Audio playback and listening (Play live, Render A/B).
- Real drag feel and latency on the canvases. Only the knob mechanics were probed numerically.
- WebGL look on a real GPU (this used SwiftShader).
- Hover states on canvas targets.
- Drag-and-drop WAV upload.
