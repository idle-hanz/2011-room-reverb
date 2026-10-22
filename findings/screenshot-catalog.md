# Screenshot catalog

All files: `C:\Users\IdleHanz\Pictures\Screenshots\Screenshot (N).png`  
Range on disk: **(138)–(486)** as of 2026-09-20. None of these PNGs are copied into the project.

Tags: **Structure** = Reaktor graph · **Panel** = Reaktor front panel · **App** = Desktop tweak UI · **Skip** = other software.

## 138–190 — mixed / other work

Mostly other Idle Hanz tools (EQ Ear Trainer, etc.). Not the 2011 ensemble. Do not mine for reverb algebra.

## 191–315 — Structure dump 1 (`2011-room-reverb.ens`)

Mined in `structure-screenshots-batch.md` … `batch-4-full.md`.

| Range | Dominant content |
|-------|------------------|
| 191–195 | Prepare / Direct Field / Absorb shell |
| **196–201** | A–F Code **0\|1 To V 18–52** — re-read 2026-09-19 in `af-bit-tables-reverified.md` |
| 202–204 | Surface Absor+Diffu |
| 205–209 | Reflection X/Y/Z Code + To V |
| 207 | **`2W-X` leaf** `(2·W)−X` |
| 210–213 | Distances and Delays, `aL`, `1/x` on 340 |
| 214–218 | Sound Processing / FDN / Gain `In×(1/32)×Gain` |
| 219–254 | Hadamard Voice 1–32 rows (`−x` signs) |
| 224 | Voice 1 all+ |
| 225 | Voice 2 even `−x` |
| 256–260 | Air Absorption / AGC. **256 amp = 1/r²** (Dis×Dis then 1/x). 258–260 AGC |
| 266–315 | Controls / Room Dimensions / Mic Stand **display** |

## 316–354 — Structure dump 2 (leaves)

Mined in `structure-screenshots-batch-5.md` + findings delta 351–354.

| Shot | Content |
|------|---------|
| 316 | Desktop / skip |
| 317–321 | Y Code leaves (`2H-Y`, `2H+Y`, `-Y`, `Y`, `-2H+Y`) |
| 322–328 | Z Code leaves (`-2L+Z`, `2L+Z`, `2L-Z`, `Z`, `4L-Z`) |
| 329–330 | X `2W-X` / `2W+X` |
| 331–333 | Prepare `MCZ=L−MZ`, Direct Field |
| 334–347 | Y/Z To V — re-read 2026-09-19 in `yz-to-v-reverified.md` (count macro→To V inputs only) |
| 348–350 | FDN Hadamard shell |
| 351–354 | `-X` invert; Prepare reconfirm; **`-2W+X` still not opened** |

## 355–357 — skip

Excel / Sals Mafia / duty-book. Not Reaktor.

## 358–399 — Structure dump 3 (`20 October 2011 room reverb.ens`)

**Was unmined** until 2026-09-19. Write-up: `structure-screenshots-batch-6.md`.

Mostly **Controls / Diffusion Matrix / panel**, not Reflection audio leaves.

| Shot | Path / content |
|------|----------------|
| 358 | Controls: Diffusion Matrix + Room Dimension + Source Position + Mic Stand |
| **359** | Diffusion Matrix named **Sides / Ahead / Behind / Floor / Ceiling** |
| **360** | On/Off: Sides, Front, Rear, Floor, Ceiling × A–F |
| 361–363 | Sides / Ahead / Behind peak macros (Freq, Bw, Mid, Diffusion) |
| 364–365 | Floor / Ceiling High/Low + Diffuse |
| 366–376 | Room Dimensions display Core (largest, Scaling, Multi Display) |
| 377 | Source Position Mouse Area (GUI) |
| 378–393 | Mic Stand display, Microphones addresses 17/21/25, stem `dX/dY` **(389)** |
| **394** | **Panel Surfaces** snapshot (knob values) |
| 395–398 | Room Dimension panel (Width / Ceiling / Lenth faders) |
| **399** | Microphone panel + **Voices 32** locked |

## 402–419 — Structure dump 4 (2026-09-19 evening)

Write-up: `structure-screenshots-batch-7.md`.

| Shot | Content |
|------|---------|
| **402** | **`-2W+X` leaf HIT** — `X − (2·W)` |
| **403** | Prepare **−0.25 is Add** (Info = sum) |
| 404–409 | Y Code `-Y` / `Y` / `-2H+Y` two pans each |
| 410–411 | Microphone 1-pole + **Power (x^y)** Gain leaf |
| 412–419 | Distances and Delays **debug** (32-voice ms / aL / angles) |
| **420–433** | Distances debug: SX clusters, ΔX, squares, **1/340**, delay ms. Write-up `structure-screenshots-batch-8.md` |
| **434–465** | SY/SZ/mic ports; Sound Processing **Dly = TL**. **461–465 Dffs = Dis×Dff×(1/Diffusion)**. Write-up `structure-screenshots-batch-9.md` + `dffs-allpass.md` |
| **466–476** | Power `X^Y` + \|x\| on Dir; Fr.V voice picker; Diffuser Delay built-in Info + **Max Delay 1000 ms** (476). Write-up `structure-screenshots-batch-10.md` |
| **477** | Mixer: L+0.5·C, R+0.5·C; no Delay. Write-up `instrument-path-map.md` |
| **478–482** | Mixer Receive **RMS Volume**; Audio Voice Combiner. Write-up `mixer-agc.md` |
| **483–484** | AGC Macro: Multiply (wiring bus to Fr.V 34–52). Write-up `mixer-agc.md` |
| **485** | Diffusion Master Function: Min 0, Max −0.5, Default −0.25 |
| **486** | Humidity Function: Min 100, Max 700, Default 400, Step 6 |

## 400–401 — old Gradio tweak app

Click-to-place matplotlib UI at `:7860`. **Not** the current Canvas / Three.js app. Historical only.
