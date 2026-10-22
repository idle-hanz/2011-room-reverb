# Structure screenshots batch 8 — shots 420–433 (2026-09-19 ~22:56)

Path: `Instrument > Distances and Delays > Macro`. Debug on. Same graph as 412–419.

These shots **do not** open Feedback Delay Network. They **do** lock the per-voice image-distance chain.

---

## Graph (VERIFIED)

Left column ins: **SX, SY, SZ** (image coords, poly 32) and **MLX/MLY/MLZ**, **MRX/MRY/MRZ**.

For each axis:

1. **Sub** (“Subtracter for 2 signals”, 422) → Δ = image − mic
2. **Order** then **Value** (Trig samples the Δ; 423 Info is the Value/S&H text)
3. **Mul** Δ×Δ → square
4. **Add** the three squares (428 “Adder for multiple signals”)
5. **Square Root** → 3D distance (metres)
6. **1/x** on Const **340** (431: **0.00294118** on every voice = 1/340)
7. **× 1000** → delay ms **TL / TC / TR**

That is the same law already in the engine: `delay_ms = (d/340)×1000`.

---

## 420 — SX (image X) per voice **LIKELY**

Debug on InPort **SX**. Three clusters (digits soft):

| Voices (approx) | SX | LIKELY X-macro | Fits if W≈57, source≈24.93, MLX≈28.27 |
|----------------:|---:|----------------|----------------------------------------|
| 1–10, 31–32 | **24.925** | `X` | 24.925 − 28.274 = **−3.349** (matches 424) |
| 11–20 | **89.075** | `2W−X` | 2×57 − 24.925 = 89.075; ΔX = **60.801** |
| 21–30 | **−24.925** | `−X` | −24.925 − 28.274 = **−53.199** |

`2W+X` (~139) and `-2W+X` (~−89) **do not appear** in this snapshot. Tag **LIKELY** (room size not panel-confirmed; 57 m is large vs the Desktop default 6 m — could be the live Reaktor fader, or a display unit). Do **not** shrink the live-32 table from this alone.

421: a single live readout **26.2743** on a nearby wire (not the 32-list).

---

## 424 — ΔX after Sub **VERIFIED** (matches 420)

| Voices | ΔX |
|-------:|---:|
| 1–10, 31–32 | **−3.34929** |
| 11–20 | **60.8008** |
| 21–30 | **−53.1992** |

## 425 — ΔX² **VERIFIED**

`(−3.34929)² = 11.2177`; `(60.8008)² = 3696.74`; `(−53.1992)² = 2830.16`. Same voice groups.

## 426 / 427 — another axis squared (Y or Z)

Clusters **2288.01**, **9538.82**, **58403.3** (voices 31–32). sqrt ≈ 47.83 / 97.67 / 241.7. The 241 m pair is the long path (matches delay ~711 ms).

## 429 — sum of squares (before √)

Voice 1 **6689.06** → √ = **81.79** m. Close to 430’s 83.60 (different mic L vs C, or rounding).

## 430 — distance (Square Root) **LIKELY metres**

Voice 1 **83.6006**. `83.6006 / 340 × 1000 = 245.88` ms.

## 431 — 1/340 **VERIFIED**

All 32 voices **0.00294118**.

## 432 — d/340 (seconds)

Voice 1 **0.245884** s.

## 433 — delay ms after ×1000 **LIKELY** (cleaner than 413)

| V | ms | V | ms | V | ms | V | ms |
|--:|---:|--:|---:|--:|---:|--:|---:|
| 1 | 245.88 | 9 | 287.42 | 17 | 296.66 | 25 | 384.15 |
| 2 | 236.91 | 10 | 287.42 | 18 | 227.53 | 26 | 378.46 |
| 3 | 141.03 | 11 | 387.8 | 19 | 227.80 | 27 | 327.11 |
| 4 | 141.48 | 12 | 338.4 | 20 | 303.68 | 28 | 327.29 |
| 5 | 245.88 | 13 | 338.55 | 21 | 291.28 | 29 | 384.15 |
| 6 | 350.97 | 14 | 338.4 | 22 | 288. | 30 | 736.37 |
| 7 | 344.75 | 15 | 393.78 | 23 | 210.42 | 31 | 711.35 |
| 8 | 354.7 | 16 | 303.68 | 24 | 291.28 | 32 | 711.35 |

Digits after the point are OCR-soft. Law `ms = d/340×1000` is **VERIFIED**; this list is a **snapshot** at the current panel, not a stored FDN table.

---

## What this is *not*

- Not a wire into the Hadamard / FDN delay lines.
- Not SY/SZ lists (so no full `(nx,ny,nz)` per voice yet).
- Not Power (x^y) pin order.

## Useful next click

Same debug overlay on **SY** and **SZ** InPorts (like 420 on SX). Three 32-lists would invert the live image macros per voice.
