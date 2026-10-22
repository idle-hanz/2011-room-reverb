# S-UI2 fix-up 2: per-mic graphs always visible, Source plane below (paste into the same S-UI2 Build window · effort: high)

Idle, 3 Oct 14:15 BST: "the 3 mic diagrams should always be visible and the 3d polar should be below them". This **supersedes** D-UI22's "no capsule graphs in Bypass" and the fix-up A2 rule that hides the graphs in Measured. It is UI only, with no sound change. The mock is `research_ui_wishlist\sui2_fixup\mock\m10_mic_each_always.png`, composited from your 09:56 shots. Line numbers are from the 14:15 tree; the UI files are unchanged since 09:55.

> Hi Build. One more S-UI2 fix-up, in the same window. **UI only: don't change the sound.** Every golden must stay byte-identical; print the golden SHA1s before and after. Idle (14:15): the three per-mic graphs are always visible, and the 3D polar (Source plane) sits directly below them. This supersedes D-UI22's "no capsule graphs in Bypass" and fix-up A2's "hide the Each-capsule graphs in Measured/Bypass". Mock: `research_ui_wishlist\sui2_fixup\mock\m10_mic_each_always.png`.
>
> 1. **Layout** (`index.html:759-808`, `#stageWide`).
>    - Move the trio out of the Source plane panel into its own panel, `<div class="panel mic-each-panel" id="micEach">`, titled "Each mic · one mic each, not the combined pattern".
>    - Place it **first** in `#stageWide`, with the Source plane panel (`.mic-polar-panel`) directly below it and nothing in between.
>    - Make it a plain panel, not a `<details>`, so it can't be collapsed away.
>    - Keep the IDs `micPolarTrio`, `micPolarL/C/R` and `micCapSlotL/C/R`, so `mic_desk.js` and `placePolarTrio` (`app.js:909-921`) keep working. After a visit to the Polar tab's "Each mic" page, the trio must return to `#micEach`.
>    - Full width at 1600 and 1920, three equal columns.
> 2. **Visibility** (`syncMicEach`, `app.js:1199-1205`).
>    - Show `#micEach` in **every Colour mode** (Measured, User defined, Bypass), for every setup except Binaural. Binaural has no capsules, so keep the panel hidden there, as the pattern blocks are.
>    - Mono centre: show the C column, and dim L and R with "not used".
> 3. **Editable vs read-only.**
>    - User defined: as today, the amber front drag aims and the rim drag sets `polar_*`.
>    - Measured and Bypass: the pattern is **read-only**. `polarWritable` already returns false (`mic_desk.js:1087-1094`), so the rim never writes. The amber front still aims, as on the Top view, because aim is geometry, not pattern.
>    - Add a small lock note in the panel header: "read-only · preset pattern". Below the trio, add one line built from the preset:
>      - Measured: "Measured: the preset owns the pattern (Shure SM57 = cardioid). Drag the amber front to aim. Switch Colour to User defined to shape the pattern."
>      - Bypass: "Bypass: preset pattern, no measured colour. …"
>      - Reuse `sideLockText` (`app.js:1190-1197`).
>    - The canvas caption (`mic_desk.js:779`, today "· drag front or the rim") reads "· preset law · drag front to aim" when locked, and "· drag front or the rim" in User defined.
>    - Replace the static foot hint (`index.html:806`, "Shown in User defined…") with the mode-dependent line above.
> 4. **The graphs must draw what the engine uses.**
>    - Measured and Bypass: draw the preset law. `applyPresetLaw` (`app.js:1117-1130`) already writes `family_*` and `polar_*`; redraw the desk when the mode or preset changes.
>    - **MS classic (`ms_decode`) is the exception.** The engine's S is a hard-wired figure-8 at the mid's yaw ± 90° (`engine/early_field.py:1650, 1683-1696`: `family="bi"`, whatever `family_l/r` say). M uses `family_c/polar_c`.
>      - Draw L and R as that figure-8 in every mode, with the note "M/S: S is a fixed figure-8 (S-MIX makes it a real mic)".
>      - Draw C as the mid.
>      - Today, Measured + MS classic would otherwise draw the SM57 cardioid on L/R, which is not what is heard.
> 5. **Tests** (extend your fix-up visibility-matrix test; the A2 rule for `#micEach` changes).
>    - For {ORTF, MS classic, AB omni, Mono, Binaural} × {Measured, User defined, Bypass}:
>      - `#micEach` is visible (hidden only in Binaural);
>      - its bottom edge is above the Source plane panel's top edge, with no other panel between them;
>      - the lock note is visible exactly when the pattern is preset-owned.
>    - Rim drag: in Measured and Bypass, a 40 px rim drag leaves `polar_l/c/r` unchanged; in User defined it changes them; the front drag aims in all three modes.
>    - In Measured, the drawn family/polar equals `capsule_law(preset)` for ORTF, and MS classic draws a figure-8 on L/R.
>    - Polar tab → Each mic → back to Mic: the trio is back in `#micEach`.
>    - `research_ui_wishlist\scripts\hidden_audit.py http://127.0.0.1:7860/` → 0 leaks; the S-UI2 baseline is 0 over 96 states.
>    - Your Playwright tab tour: every tab shows only its own panels, with 7 tabs.
>    - Goldens byte-identical (SHA1 before = after); phase suite green. No WORKLET_VER bump: you don't touch the worklet or wasm.
> 6. **Screenshots** at 1600 into `research_ui_wishlist\sui2_fixup\shots\`: `mic_each_measured_1600.png`, `mic_each_user_1600.png`, `mic_each_bypass_1600.png`, `mic_each_ms_classic_measured_1600.png`.
>
> Report the golden SHA1s, the test results and the screenshot paths.

## Mock check against Build's 09:56 shots (VERIFIED from the shots and the 14:15 code)
- **User defined** (`shots/mic_user_1600.png`): the trio is **below** the Source plane, inside its panel. Idle wants it above. The order is the bug.
- **Measured / Bypass** (`mic_measured_1600.png`, `mic_bypass_1600.png`): there is no trio, because `syncMicEach` shows it only for `ASSUMED_TOYS` (`app.js:1201`). That was the old D-UI22 / A2 rule, now superseded.
- **The foot hint says "Shown in User defined…"** (`index.html:806`) and appears in Measured and Bypass, where it points at graphs that aren't there. Item 3 replaces it.
- **Read-only already works in code:** `polarWritable` is false in Measured and Bypass, and for a figure-8 (`mic_desk.js:1087-1094`). When locked, `polarHitMode` maps every press to aim (`:1104-1107`). So item 3 is captions and notes only.
- **MS classic mismatch (found while checking):** in Measured, `applyPresetLaw` would write the SM57 law into `family_l/r`. The engine ignores those keys for S, which is always a figure-8 (`early_field.py:1694-1696`). Item 4 makes the graphs honest.
- **Not changed, flagged only:** the Source plane badge reads "MEASURED" in every Colour mode, including User defined and Bypass. It is the preset's data honesty (`paintMicModel`, `app.js:1510-1520`), not the mode, which can read as a contradiction in Bypass. Possible wording: "preset data: measured". This is Idle's call and is not in the prompt.
