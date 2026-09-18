# Panel controls — Idle Hanz 2011 room reverb

Source: Structure/panel screenshots batch 6 (355–399) + prior Structure batches. Ensemble `20 October 2011 room reverb.ens`.

Tags: **VERIFIED** (on-screen) · **LIKELY** · **ASSUMED** · **UNKNOWN**.

---

## Navigation

| Control | Meaning | Tag |
|---------|---------|-----|
| Category **Switch** (ID 138, 4 ports) | Selects Surfaces / Room Dimension / Sound Position / Microphone | **VERIFIED** (394–399) |
| Shared bottom strip | Always visible across categories | **VERIFIED** |

---

## Shared (all tabs)

| Control | Meaning | Verified / assumed |
|---------|---------|-------------------|
| **GainF** | FDN / feedback gain factor (label GainF) | **VERIFIED** name; range UNKNOWN (seen ~0–1) |
| **Clip Diffusion** | Clipper enable / status for diffusion path | **VERIFIED** green On indicator; maps to Structure Clipper (prior Absorb path) — **LIKELY** |
| **AGC** On/Off + **dB** (±20) | Auto gain control + makeup/trim meter field | **VERIFIED** UI; law UNKNOWN |
| **Volume trim** | Master output trim | **VERIFIED** name; seen ~0.89–0.99; range UNKNOWN |

---

## Surfaces tab (394)

| Control | Meaning | Verified / assumed |
|---------|---------|-------------------|
| **Sides / Ahead / Behind** columns: Freq, BW, dB, Diffusion | Per-surface absorb EQ + diffusion (A–D style Peak) | **VERIFIED** labels; maps to Surface Absor+Diffu / Diffusion Matrix — **LIKELY** |
| **Floor / Ceiling** columns: Freq, Low, dB, Diffusion | Floor/ceiling use High+Low (E–F FrH/FrL style) | **VERIFIED** Low instead of BW; matches prior E–F FrH/FrL — **LIKELY** |
| **Diffusion Master** | Global diffusion multiply (→ MDiff / Clipper path) | **VERIFIED** fader; prior Structure MDiff — **LIKELY** |
| **Humidity** | Air absorption / HF damping control | **VERIFIED** knob + Diffusion Matrix Humidity port; DSP law UNKNOWN |
| **Stacked Macro** Sides/Front/Rear/Floor/Ceiling/All | Surface on/off / focus for A–F bus | **VERIFIED** buttons; Structure On/Off gates — **LIKELY** |

Example live values only (not defaults): see batch-6 §6.

Ahead **BW** Structure fader range **0…0.4** def **0.2** step **0.004** — **VERIFIED** (362 properties). Other Surfaces ranges: UNKNOWN from panel properties.

---

## Room Dimension tab (395–397)

| Control | Meaning | Verified / assumed |
|---------|---------|-------------------|
| **Width X** | Room width W (metres ASSUMED) | **VERIFIED** label |
| **Ceiling Y** | Room height H | **VERIFIED** label |
| **Lenth Z** | Room length L (UI typo “Lenth”) | **VERIFIED** typo; range **Min 2 Max 100 Default 51 Step 0.5** (396) |
| Orange **3D wireframe** | Multi Display of room box | **VERIFIED**; driven by Room Dimensions Core / Iteration N=12 |

Controls Structure outs W/H/L → terminals 20–22 — **VERIFIED** (358).

---

## Sound Position tab (398)

| Control | Meaning | Verified / assumed |
|---------|---------|-------------------|
| Category entry | Source XY (and Z via Structure SX/SZ) | **VERIFIED** tab exists |
| Mouse Area / XY pad | Source position in room plan | **VERIFIED** in Structure (377); panel pad contents **UNKNOWN** this crop |
| Structure outs | SX→23, SZ→24 | **VERIFIED** (358) |

Prior Structure: Mouse Area X,Y → Snap / Value 0.75 & 0.5 — **VERIFIED** (batch-1 + 377).

---

## Microphone tab (399)

| Control | Meaning | Verified / assumed |
|---------|---------|-------------------|
| **Mic Response** (top, e.g. 10000) | HF / Res upper limit (Hz-scale) | **VERIFIED** UI + prior MiF/Res notes — **LIKELY** Hz |
| **Angle** | Mic stand / toe angle | **VERIFIED** knob; ties to Mic Stand Angle / Diverg paths — split audio vs display |
| **Height** | Mic height (→ MY / Height terminal) | **VERIFIED** |
| **Depth** | Mic Z / depth into room | **VERIFIED**; Structure Depth / Mic Z |
| **Car/Omni** | Cardioid↔Omni blend (C/O) | **VERIFIED**; prior Microphone C/O4 — **LIKELY** |
| **Space** | L–R mic separation | **VERIFIED**; → Space/MSS family |
| Red vertical line display | Mic placement / response visualizer | **VERIFIED** graphic; exact metric UNKNOWN |

Structure Mic Stand terminals: MSS, MRa, MY, HZ, Car, HF, HpF, Hp — **VERIFIED** (358). HP Freq / HP In exist on Structure side; not clearly labeled on 399 crop (may be off-tab or unlabeled).

---

## Mic Stand Multi Display (Structure-backed graphics)

| Element | Meaning | Tag |
|---------|---------|-----|
| Room wireframe (orange) | Room Dimensions Multi Display | **VERIFIED** |
| Color G≈0.431372 B≈0.0980392 | Shared draw color consts | **VERIFIED** (366, 378) |
| Mic L/C/R addresses 17/21/25 | Array slots for capsule XY pairs | **VERIFIED** |
| Iteration N=8 (Mic) / N=12 (Room) | Draw object counts | **VERIFIED** |

---

## Do not confuse (audio Prepare vs panel Mic Stand)

| Path | Lock | Tag |
|------|------|-----|
| Prepare Macro (audio) | MCZ=`L−MZ`; MCX=`W×0.5`; ML/MR X = MCX∓Space/2; MLALR/MRALR = Diverg×0.3×±0.25 | **VERIFIED** prior |
| Mic Stand Microphones Macro (panel geom) | dX/dY via sin/cos −π..π; Space/Width half algebra | **OCR soft** — do not override Prepare |

---

## Still need properties screenshots

- Defaults/ranges: Surfaces Freq/BW/dB/Diff, Humidity, Diffusion Master, GainF, Volume trim, Mic Response/Angle/Height/Depth/Car/Omni/Space
- Sound Position pad min/max and any Z control on panel
- HP Freq / HP In panel locations
