# S-UI2 fix-up 3: badge wording and small visual fixes (pointer, not started)

**Status 3 Oct 18:45: FOLDED into S-MIX item 8** (`research_ui_wishlist/REPORT.md` §7). Do not run this on its own. Item 3 is adapted there to S-MIX's single S strip: +/− lobes, with the route shown as "→ +L, −S on R".

3 Oct 2026, 17:10 BST, build_support_2.
- **When to run:** after the S5 fix-up (`roadmap/s5_surf_1010/S5_CPU_DECISION.md` §6). If it is simpler, fold it into S-MIX as an extra item, since S-MIX touches the same Mic tab files.
- **Evidence:** the PC shots from S-UI2 fix-up 2, in `sui2_fixup/shots/` on the Desktop (box copy: `sui2_fixup/shots_pc/`): `mic_each_measured_1600.png`, `mic_each_user_1600.png`, `mic_each_bypass_1600.png`, `mic_each_ms_classic_measured_1600.png`. Mock: `mock/m10_mic_each_always.png`.

## What the shots already get right (VERIFIED by looking at the four shots)

- **Each mic:**
  - The three per-mic graphs (L / C / R) are shown in every Colour mode.
  - Measured and Bypass carry the "read-only · preset pattern" badge, and their captions say "preset law · drag front to aim".
  - User defined has no read-only badge, and its caption says "drag front or the rim".
- **Source plane** sits directly below Each mic, in all four shots.
- **Frequency colours** run red at low frequencies to violet at high:
  - per-mic rings: red outer at 20 Hz, violet inner at 16 kHz;
  - Source plane stack: red at the base to violet at the top;
  - legend: 20 red, 63 orange, 125 yellow, 250 green, 1k cyan, 4k blue, 8k indigo, 16k violet.
- **Bypass** draws one violet curve per mic, with no frequency rings.
- **MS classic Measured** draws the L and R strips as filled figure-8s (S, +90°), with C as the measured SM57 cardioid. The note reads "M/S: S is a fixed figure-8 (S-MIX makes it a real mic)".

## Items

**1. Source plane badge wording (Idle's ASSUMED default from 15:57).**
- Today the badge reads "MEASURED" in every Colour mode (VERIFIED in all four shots).
- In Measured and Bypass it should read **"preset data: measured"**.
- In User defined the plane visibly follows the user pattern: the stack bulges at the mid rings in `mic_each_user_1600.png`, VERIFIED. So there it should read **"user defined"** (ASSUMED wording, in line with Idle's default).
- Keep the tooltip that explains the badge is about the data source, not the sound mode.

**2. Source plane top clutter (VERIFIED in the Measured, User and Bypass shots).**
- At the top of the stack (the 8k–16k rings), translucent violet quads stick out up and to the left, like flags. Make the stack end cleanly: no stray fill quads, and close or cap the top ring.
- In Measured there is also one bright cyan vertical seam line down the side of the stack. Draw it like the other mesh lines, or remove it.

**3. MS classic figure-8 polarity (VERIFIED: L and R both show "Fig-8 · +90°", identical drawings with the same lobe colour fill).**
- Mark the lobes "+" (front) and "−" (rear).
- On the R strip, show that R takes −S (R = M − S): label it "−S", or swap the lobe marks.
- The strips should not look like two identical mics.
- If S is fixed in MS classic, drop "drag front to aim" from those two captions, or make sure dragging does nothing (ASSUMED: not checkable from a still).

**4. Small polish (optional, no layout change).**
- The per-mic graphs have no legend of their own; the only legend is under the Source plane. Add one thin shared legend row under Each mic, drawn by the same palette function.
- In User defined, only 4 of the 8 colours are visible because the low rings overlap. This is expected and needs no fix.

**Palette note:**
- The shots already run red → violet. Earlier today I VERIFIED that the code palettes in `mic_desk.js:27` and `source_desk.js:7-12` ran the other way, so fix-up 2 may have changed them (ASSUMED).
- S-MIX item 9 still applies: one shared `SpectrumColors.forHz`, used by every graph.

## Gates

- UI only. Goldens unchanged, and `WORKLET_VER` stays 46, or whatever the S5 fix-up set.
- The hidden-state audit stays at 0 leaks.
- `fixup2_mic_each.py` passes.
- New shots of the same four states, with:
  - the badge text per mode as in item 1;
  - no stray quads at the top of the stack;
  - +/− on the MS classic lobes and "−S" on R.
- No other UI change. No sound change. Do not start S-MIX items from this pointer, unless it is being folded into S-MIX.

## Pointer to paste

```
S-UI2 fix-up 3 (small, UI only; run after the S5 fix-up, or fold into S-MIX as an extra item).
Do handoff_build_support_2\research_ui_wishlist\sui2_fixup\FIXUP3_POINTER_badge_visual.md items 1-4 and its gates:
Source plane badge "preset data: measured" (Measured/Bypass) / "user defined" (User); clean top of the Source plane
stack (no stray violet quads, no bright seam); MS classic figure-8 lobes marked +/- with R shown as -S; optional
shared legend under Each mic. Goldens unchanged, 0 hidden leaks, new shots of the four states. Nothing else.
```
