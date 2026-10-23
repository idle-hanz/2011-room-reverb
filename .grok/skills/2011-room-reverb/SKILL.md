---
name: 2011-room-reverb
description: >
  Continue Idle Hanz’s 2011 Reaktor room-reverb rebuild (Diffuser Delay +
  Hadamard feedback + Desktop tweak app). Use when the workspace is the
  2011 Room Reverb folder, or the user says read handover, continue the
  reverb, Reaktor ensemble, Structure screenshots, FDN, image source,
  handover, A–F surfaces, or /2011-room-reverb.
---

# 2011 Room Reverb

Canonical root: the folder that contains `HANDOVER.md`, `ensemble\`, `software\`, `findings\`.

## First reads (in order)

A Thursday prompt (it names `RUN_RULES.md` or `CURRENT_BRIEF.md`) starts at `CURRENT_BRIEF.md` and the prompt. Do not open `HANDOVER.md` for that run.

1. `HANDOVER.md` — the **Current pin** is the live tree. Stop there if the user said continue / UI / mics / walls. A later section’s `WORKLET_VER` is that landing.
2. `findings/INDEX.md` — only if they asked Structure or audio
3. `findings/instrument-path-map.md` — 2011 wet spine (Structure only)
4. `docs/HOW_IT_WORKS.md` — DSP only

Version, wasm, goldens, loop gain, direct-line index, air mix, t19 ceilings, and what is already landed live in the HANDOVER Current pin. When this skill and a later HANDOVER section disagree with that pin, the pin wins.

Durable locks: `c = 340`. Delay `(d/340)×1000`. Structure Air Abs graph `1/r²` (shot 256). Software geometric level `1/r` (Idle 2026-10-10). Prepare Diverg is Add `0.5·d ± 0.25` (403), never `×0.3`. `-2W+X` = `X − (2·W)` (402). `MCZ = L − MZ`. Live geometry is metres. Room 3D and Lattice/Paths: `threeZ = L − z`. Do not flip floor X. Do not reopen L/R. Mirror is `W−sx` only. Do not fold B’s tail into A’s tank. Do not treat a post-Hadamard line as Direct. Do not omit FDN inject. Do not cap loop `g` at `0.68/√N`. Do not IR-RMS the Render FDN. Do not put a 32×32 multiply back on the audio thread. Do not fetch wasm from the worklet. The page passes the bytes in. Measured mic colour is on the way out and is not written back. Early left and right use the FDN line’s filter. The Structure microphone one-pole stays unwired (`apply_mic` false). The air one-pole stays in the code. Two sources (`TWO_SOURCES.md`) is built and off by default. Phases 1–3 of the mic brief are in the tree. Do not start Phase 4 on a bare continue.

Screenshots are **not** in the repo:

`C:\Users\IdleHanz\Pictures\Screenshots\Screenshot (NNN).png`

Catalog: `findings/screenshot-catalog.md`.

## Rules

- Do not invent A–F wall letters beyond what HANDOVER lists as VERIFIED.
- A and C share the Reaktor **Sides** panel; Left vs Right split in code is ASSUMED.
- Do not import `software/engine/absorb_masks.py` or `software/engine/to_v_tables.py` into the renderer. Data only.
- FDN matrix stays unscaled ±1 **Sylvester**. Delay is built-in **Diffuser Delay** (allpass; Max Delay 1000 ms). **Fr.V** is a voice picker. Hadamard is mix + feedback into the same delay. Mixer fold is `L+0.5·C`, `R+0.5·C`, then Voice Combiner. Makeup is running Mixer level from inject energy on Play and the same AGC on Render. Three L/C/R loops. Inject t=0 including n=(0,0,0). No delay uniquify. Do not reshoot Voice 1–32 or ask to open Diffuser Delay.
- Loop gain, page defaults, and the render-length law are the HANDOVER Current pin. `Out = In × (1/32) × Gain` is the `reaktor_parity` / lock-off law. Mix Direct is the feedforward first arrival, not FDN line output. The software distance law is 1/r. Do not retune it, the 0.55 Direct fold, or the desk on a bare continue. The Structure Air Abs graph remains 1/r².
- Work signal-path order (HANDOVER). Do not dump 200 screenshots.
- Image To V indices ~17–52 and FDN voices 1–32 are separate buses. Mapping UNKNOWN.
- `-2W+X` = `X − (2·W)` VERIFIED (shot 402). Engine uses `S − (2·R)`. Do not invent a half-W form.
- `MCZ = L − MZ`. `c = 340`. Delay `(d/340)×1000`. Structure Air Abs graph `1/r²`. Software geometric amp `1/r` (Idle 2026-10-10). No `1/√N` on the Hadamard.
- GUI macros (Mic Stand Scaling, stem `dX/dY` shot 389, Multi Display addresses) are **display**, not Prepare audio.
- Do not edit `2011-Room-Reverb-publish\`, Desktop zips, or the original `.ens` files unless the user asks to ship or archive.
- Tag every claim VERIFIED / LIKELY / ASSUMED / PROPOSAL / UNKNOWN.

## Run

- App: `software/Launch Tweak App.bat` → `http://127.0.0.1:7860`
- Engine: `software/engine/selfcheck.py` (venv + numpy)

## When mining Structure

Read the PNG as a picture. Do not trust prior OCR if a glyph is `+` `*` or `−`. Record breadcrumb path, leaf pin order, and whether the graph is audio or Controls/display.
