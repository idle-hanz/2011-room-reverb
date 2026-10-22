# Structure screenshots batch 7 — shots 402–419 (2026-09-19 ~22:23–22:44)

Ensemble: `2011-room-reverb.ens`. PNGs stay in Pictures. Not copied into the repo.

Tags: **VERIFIED** = Info pane / numbered debug / pin-visible leaf · **LIKELY** = strong wiring · **UNKNOWN** = still not a table.

---

## 402 — `-2W+X` leaf **HIT**

Path: `Instrument > Reflection Code > X Code > -2W+X`

- Const **2** on **W** → Mul
- Sub: plus = **SX**, minus = **2W**
- Out **X** = **`SX − (2·W)`** ≡ **`-2W + X`**

Same layout as `-2H+Y` (321). Engine already uses `S−(2·R)`.

---

## 403 — Prepare ±0.25 is **Add** **HIT**

Path: `Instrument > Prepare > Macro`

Selected: **−0.25** on **Mic Left Angle Left / Right**.

Info (verbatim): *“Sends out the **sum** of the input values in response to an event arriving at either or both of the inputs.”*

Path still: **Diverg Parallel Converge → Mul 0.5** → fork:

- Add **−0.25** → MLALR
- Add **+0.25** → MRALR

**VERIFIED:**

```
MLALR = Diverg×0.5 − 0.25
MRALR = Diverg×0.5 + 0.25
```

Included L−R is always **0.5 rad**. At Diverg=0: ±0.25 rad (inward). An earlier Mul reading (`×0.5×±0.25`) is **overturned**.

Also visible on this shot: Mic Right X = Mic Centre X + Space/2 (Add, top-right of crop). Left X is off-crop here; engine still uses MLX = MCX − Space/2.

---

## 404–409 — Y Code remainder (one macro selected, two pans)

Method: cyan = selected-macro connections. Count **macro → To V inputs** only, not To V → M.

Already VERIFIED (earlier pass): `2H+Y` → 13–18, 24; `2H-Y` → 19–23, 27–28.

| Shot | Selected | Pan | Clear To V **input** landings (LIKELY until a third pass) |
|------|----------|-----|----------------------------------------------------------|
| **404** | **`-Y`** | 13–52 | 25–26, 33; 38–39; 47–48, 51. Also cyan up the 13–18 column (may be SY in, not all destinations). |
| **405** | **`-Y`** | 1–18 | cyan on **6, 12, 16** (and neighbors). 1–16 is extra Y bus (X Code does not write it). |
| **406** | **`Y`** | 13–52 | 29–32; 42, 47, 52; some 35–36 / 44 / 48. |
| **407** | **`Y`** | 1–18 | cyan on **5, 14, 16**. |
| **408** | **`-2H+Y`** | 13–52 | 29–32 region + upward (SY/H in). Right-column hits weaker than 406. |
| **409** | **`-2H+Y`** | 1–18 | cyan around **6–7, 16**. |

**Do not publish a full VERIFIED 25–33 / 34–52 Y table from this batch** — 406 and 408 both light 29–32, so some of that cyan is still collector/input mix. First-column 13–24 from the previous pass stands.

---

## 410–411 — Microphone / the unnamed Gain leaf

### 410 — Microphone shell **VERIFIED**

Path: `Instrument > Sound Processing > Microphone`

- Audio **In** → **1-Pole Filter** (HP/LP terminals) → **Out**
- **Dir** + **C/O** → nested **Gain** macro → filter **P** (cutoff) together with **Res**
- **Res** → **Log** → Mul → 1-Pole **P**

Res is the “upper frequency limit” via **log-scaled 1-pole cutoff**. Not a peaking Q. Engine peaking Q stays ASSUMED until someone maps this 1-pole into the colour path on purpose.

### 411 — inside Gain (the old `0x7e`) **HIT / graph VERIFIED, formula not wired**

Path: `Microphone > Macro`

Visible left-to-right:

1. **Dir**
2. Trig-style module (same family as prior `0x7a` Sine — **LIKELY** Sin/Cos, not labeled on this crop)
3. **Mul × Const 2**
4. **C/O** into **Power (x^y)** — this is the unnamed module
5. **Const 1 −** that → **Gain**

So **0x7e = Primary Power (x^y)**. Pin order (whether C/O is base or exponent) is **not** claimed from this crop. **Do not replace** the engine’s `(1+cosθ)/2` blend with a Power law until X vs Y is pixel-certain.

---

## 412–419 — Distances and Delays, debug on

Path: `Instrument > Distances and Delays` (+ nested **Macro** / **aL**).

Graph reconfirm **VERIFIED** (matches batch-2/4):

- Per-mic ΔX/ΔY/ΔZ → squares → sum → **Square Root** = 3D distance
- **1/x** on **340**, then **× 1000** → delay ms (**TL / TC / TR**)
- **ArcTan** / **Sine/Cosine** for MLALR-style angles
- **aL** Relay (415–416): Compare/Equal vs **0.25**, then **0.5** / **2** into Relay

### 412 / 413 — 32-voice debug on the delay (×1000) path

Probe text `Note: Off, <value>`. **LIKELY delay_ms** at the current panel geometry (not a stored FDN table). Transcription from 413 (soft on some digits):

| V | ms (LIKELY) | V | ms | V | ms | V | ms |
|--:|------------:|--:|---:|--:|---:|--:|---:|
| 1 | 245.912 | 9 | 287.448 | 17 | 296.282 | 25 | 384.416 |
| 2 | 236.939 | 10 | 287.448 | 18 | 227.011 | 26 | 378.739 |
| 3 | 141.078 | 11 | 387.326 | 19 | 227.28 | 27 | 327.424 |
| 4 | 141.511 | 12 | 387.326 | 20 | 303.068 | 28 | 327.61 |
| 5 | 245.9 | 13 | 338.02 | 21 | 291.638 | 29 | 384.416 |
| 6 | 350.993 | 14 | 338.201 | 22 | 288.112 | 30 | 736.362 |
| 7 | 344.765 | 15 | 393.48 | 23 | 210.91 | 31 | 711.352 |
| 8 | 354.705 | 16 | 393.48 | 24 | 291.638 | 32 | 711.352 |

Several adjacent pairs match (3–4, 9–10, 11–12, …) — LIKELY two capsules or two nearby images, not 32 unique FDN primes.

**Do not** paste this list into `propose_fdn_delays_samples`. These are **image Distances** at one panel snapshot. FDN still mixes ±1 Hadamard of delayed lines (user + shots 224–225). A Structure wire from TL/TC/TR **into** the FDN delay inputs is **not** in this batch.

### 414 / 415 — aL / 1/r-ish debug (0.03–0.22)

Same 32-voice list as 414/415 (~0.156, 0.152, 0.00387, …). **LIKELY** geometric `1/r` or the **aL** Relay output, not milliseconds.

### 416 — Compare/Equal **input** (can be negative)

Voices 21–25 ≈ **−0.058**; 1–5 ≈ **0.00388**. Not a distance.

### 417–419 — angle path (ArcTan / Sine/Cosine / 0-1-Degrees)

419 probe on ArcTan: values ~ **±0.01…0.14 rad** (MLALR-scale). 418 similar on a later trig. Display lamps **0-1-Degrees** on the right are GUI, not Prepare audio.

---

## What this does *not* unlock

- FDN line lengths as a stored table (still PROPOSAL unless Distances outs are shown feeding FDN).
- Power (x^y) pin order for Mic Gain.
- Full Y To V 34–52.
- A vs C Left/Right.
