# Structure screenshots batch 6 — shots 358–399 (2026-09-19)

Ensemble: `20 October 2011 room reverb.ens` (Reaktor 6).  
Vision read of every PNG 358–399. 355–357 and 400–401 noted as skip / other UI.

Tags: **VERIFIED** = visible labels / wiring · **LIKELY** · **UNKNOWN** · **GUI** = Controls/display, not Prepare audio.

## Priority outcomes

| Target | Status |
|--------|--------|
| A–F → physical surface **names** | **HIT** — Diffusion Matrix (359) + On/Off (360) + panel (394) |
| A vs C Left vs Right | **MISS** — both sit under one **Sides** panel |
| `-2W+X` leaf | **MISS** — this dump never entered Reflection Code |
| Mic stem angle formula | **HIT / GUI only** (389) |
| Live voice count | **HIT** — Instrument Voices **32** locked (399) |
| Panel Surfaces snapshot knobs | **HIT** as *this snapshot’s numbers*, not DSP law |

---

## 1. A–F wall dictionary (the missing piece)

### VERIFIED — Diffusion Matrix (358, 359)

Path: `Instrument > Controls > Diffusion Matrix`

Five named surface macros + two globals:

| Panel name | Ports (suffix) | Out indices (358/359) |
|------------|----------------|------------------------|
| **Sides** | FrR, BmR, RsR/RsB, DffR | 1–4 |
| **Ahead** | FrB, BmB, RsB, DffB | 5–8 |
| **Behind** | FrD, BmD, RsD, DffD | 9–12 |
| **Floor** | FrEH, FrEL, DffE | 13–15 |
| **Ceiling** | FrFH, FrFL, DffF | 16–18 |
| Diffusion Mix | | 19 |
| Humidity | | 20 |

Letter suffixes: **B** = Ahead, **D** = Behind, **E** = Floor, **F** = Ceiling. Sides uses **R** on the panel ports (not A/C). Audio Absorb codes remain A–F.

Floor / Ceiling have **High/Low** freq only (364, 365). Sides / Ahead / Behind have Freq + Bw + Mid + Diffusion (361–363). Matches Surface Absor+Diffu: A–D peak, E–F FrH/FrL.

### VERIFIED — On/Off (360)

Path: `Controls > Diffusion Matrix > Stacked Macro > On/Off`

Rows labelled **Sides, Front, Rear, Floor, Ceiling**. Inputs and outputs **A–F**. Const 1 and IR also gated.

### VERIFIED — Surfaces panel (394)

Front-panel columns: **Sides · Ahead · Behind · Floor · Ceiling**.  
Stacked Macro buttons: **Sides, Front, Rear, Floor, Ceiling, All**.

Category switch: Surfaces / Room Dimension / Sound Position / Microphone.

### How this maps to letters

| Letter | Panel name | Tag |
|--------|------------|-----|
| **B** | Ahead / Front | VERIFIED name |
| **D** | Behind / Rear | VERIFIED name |
| **E** | Floor | VERIFIED name |
| **F** | Ceiling | VERIFIED name |
| **A** and **C** | **Sides** (shared knobs) | VERIFIED that Sides is the pair; **which letter is Left vs Right is ASSUMED** |

The Desktop app still colours A = Left (−X) and C = Right (+X) so each card is audible. That split is **ASSUMED**, not Structure-opened.

### Snapshot knob values (394) — this snapshot only

Do **not** treat as the DSP default law. Recorded so a later session can match a Reaktor recall if wanted:

| Column | Freq / High | Bw or Low | Diffusion |
|--------|-------------|-----------|-----------|
| Sides | 100 | Bw 0.044 | 0.16 |
| Ahead | 428 | Bw 0.024 | 0.25 |
| Behind | 6667 | Bw 0.308 | 0.33 |
| Floor | High 517.8 | Low 100 | 0.27 |
| Ceiling | High 20030 | Low 145 | 0.65 |

Also visible: **Diffusion Master = −0.5** (tall fader; old −35.9 misread **REJECTED**). **Humidity** is a rotary under it, no readout. GainF = 1, Clip Diffusion on, AGC Off, Volume trim ≈ 0.0921.

Ahead Bw fader (362): Max 0.4, Min 0, Default 0.2, Step 0.004.

---

## 2. Room Dimensions (GUI)

Path: `Controls > Room Dimensions` (366–376).

- Width X / Ceiling Y / Lenth Z (panel typo **Lenth**) into a Core Cell + Iteration + Multi Display.
- Nested **Output the largest** (370, 371): max of three dims via `>` + routers.
- Volume ← largest × Volume; Diffusion ← mean(dims) × Diffusion — matches batch-4 276–277.
- **Scaling** (376): fit X/Y into a display box (`82/X`, `51.25/Y`, compare, scale). **GUI only.**
- Lenth Z fader (396): Max **100**, Min **2**, Default **51**, Step **0.5**.

Panel 3D box (395–397) is the Reaktor Multi Display room, not the Desktop Three.js view.

---

## 3. Mic Stand / Microphones (GUI)

Path: `Controls > Mic Stand` (378–393).

### VERIFIED display (already in batch-4, reconfirmed)

- StpFltr Tol **0.001** on W, L, Space, Angle, Depth (379).
- Iteration N=**8**.
- Microphones array writes (384): **Left Address 17**, **Centre 21**, **Right 25**; each X1/Y1/X2/Y2 at Address+0…+3.
- Colour consts ~0.431372 / 0.0980392 on the display bus (378).
- Depth labelled Mic Z.

### VERIFIED — stem `dX/dY` (389) ⭐ GUI only

Path: `Mic Stand > Macro > Microphones > Macro`

```
u = Angle × 0.5 + (−0.25)     =  0.5·Angle − 0.25
θ = u × (22/7)                22/7 wired into a module labelled Pi
dX = Mic Lenth × sin(θ)       sin −π..π
dY = Mic Lenth × cos(θ)       cos −π..π
```

If Angle is 0–1, `u` is −0.25…+0.25 and `θ` is about ±45°.

This is the **red-line mic graphic**, not Prepare audio. Audio toe is Prepare `Diverg × 0.5 × ±0.25` (×0.5 VERIFIED 331/354; ±0.25 as Mul LIKELY). Do not replace Prepare with 389. An older 0.3 factor was a false VERIFIED.

---

## 4. Source Position (GUI)

Shot 377: Mouse Area X/Y → merge → Snap(2); Db → Value(0.75)+Value(0.5); Snap(1) → out X. Same family as batch-1. Display placement, not Prepare `SX = W×SoX`.

---

## 5. Instrument panel (399)

- **Voices 32**, Lock Voices 32, Max/Min Voices 32.
- Mic Response 10000, Height 1.9, Depth 0.1633, Car/Omni 0.764, Space 0.250.
- Black Multi Display = mic red-line graphic (the limitation the Desktop app replaced).

---

## 6. What this dump does **not** contain

- No Reflection Code leaves (`-2W+X` still unopened).
- No Absorb A–F bit tables (those are 196–201).
- No Hadamard Voice rows (those are 224–254).
- 355–357 Excel; 400–401 old Gradio tweak app.

---

## Per-shot index

| Shot | Breadcrumb / content | Tag |
|------|----------------------|-----|
| 358 | Controls shell | VERIFIED |
| 359 | Diffusion Matrix named surfaces | VERIFIED dictionary |
| 360 | On/Off Sides/Front/Rear/Floor/Ceiling | VERIFIED |
| 361 | Sides peak macro | VERIFIED |
| 362 | Ahead + Bw fader range | VERIFIED |
| 363 | Behind peak macro | VERIFIED |
| 364 | Floor High/Low/Diffuse | VERIFIED |
| 365 | Ceiling High/Low/Diffuse | VERIFIED |
| 366–376 | Room Dimensions Core / Scaling / largest | GUI |
| 377 | Source Position Mouse Area | GUI |
| 378–388 | Mic Stand / Microphones addresses | GUI |
| 389 | Stem dX/dY | VERIFIED GUI formula |
| 390–393 | Sound Source / address increment | GUI |
| 394 | Surfaces panel snapshot | VERIFIED knobs (snapshot) |
| 395–398 | Room Dimension panel | GUI |
| 399 | Microphone panel + Voices 32 | VERIFIED |
