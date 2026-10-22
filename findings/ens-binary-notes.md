# Ensemble binary notes (2026-09-19)

Read-only mine of `ensemble/2011-room-reverb.ens`.  
All four copies on this PC (Desktop + `ensemble\`, both filenames) are **byte-identical** SHA256 `20A405C84808AB9570A38D171F234159342496653AD886801EE73CEDD9F5D893`, 887330 bytes.

Do not edit the `.ens`. This file is notes only.

## Format

- Size field at byte 0 equals file length (887330).
- Tag `hsin` (nish) then `DSIN` / `RTKR` / `NRKT` — Native Instruments Reaktor container.
- UTF-16 versions in file: **5.6.1.0** and **6.5.0.0**. Saved from Reaktor 6; built from Reaktor 5 macros.
- Last-loaded audio (paths inside file):
  - `F:/Songs/Plague on both your houses/Mixdown/Plague on both your houses (guitar only).wav`
  - `C:/Users/IdleHanz/Documents/Native Instruments/Reaktor 6/reverb test.wav`
- Self path: `C:/Users/IdleHanz/Desktop/20 October 2011 room reverb.ens`

## Author comment (instrument)

> This version September 16 2011 I reduced the voices to 32 to implement a square feedback delay network initialy based on the pucket model

Stored twice. **Pucket** = Miller **Puckette** FDN (typo). Square 32×32 is intentional, not a screenshot guess.

Original Mac author path still in the file:

`/Users/jonsykes/Documents/Reaktor 5/Macros/Drum Sequencer/Ray tracing reverb/Add Voices .mdl`

Started from Reaktor 5 stock `_New - 2in2out.ism`.

## Named macros present as ASCII (counts)

| Name | Count | Note |
|------|------:|------|
| X/Y/Z Code | 1 each | |
| `2W-X` | 1 | |
| `2W+X` | 2 | |
| **`-2W+X`** | **1** | Leaf **exists in the file**; Structure screenshots never opened it |
| `2H-Y` / `2H+Y` / `-2H+Y` | 1 / 2 / 1 | |
| `2L-Z` / `2L+Z` / `-2L+Z` / `4L-Z` | 1 / 2 / 1 / 1 | |
| A–F Code | 1 each | |
| Hadamard | 3 | |
| Prepare | 1 | |
| `Direct Field` as that spelling | 0 | panel uses Direct Distance / DD |

## Author / Info strings (verbatim)

- Surface Absor+Diffu: *Calculates each surface Absorbtion and Diffusion*
- Surface A: *This is a section that emulates the reflection from a surfaace. There is firstly absorbtion that is filtered. Then there is signal inversion which happens in a reflection. It would be nice to have a difuser section in here.*
- Mic `Dir+`: *Direction in radians of the incident sound*
- Mic `Res`: *The upper frequency limit of the microphone*
- FDN gain: `0 > In < 1`
- Panel typos baked in: **Cieling**, **Lenth**, **Controlls**, **Proccessing**, **Cardiode**, **Absorbtion**, **Mic Lenth**

## Panel port names vs A–F

Under Controlls / Diffusion Matrix the file lists **DffA, DffB, DffD, DffE, DffF** and **AWidth**. **`DffC` and `CWidth` do not occur.** Surface C module exists, but C has no own panel diffusion/width ports. Matches Sides = A+C shared knobs.

## Exact IEEE floats (byte match, not random decode)

| Value | f32 count | f64 | Meaning |
|------:|----------:|----:|---------|
| **340.0** | **1** | 0 | Distances Const. Nearby u32 **1000** (`e803`). No 343. |
| 1000.0 | 5 | 0 | delay ms scale |
| 0.25 | 3 | | Prepare/GUI ±0.25 family |
| 0.001 | 2 | | StpFltr Tol |
| 1/32 | 35 | | FDN Gain `In×(1/32)×Gain` |
| **1/√32** | **0** | 0 | **no `1/√N` in the file** |
| 44100 | 0 | 0 | sample rate not stored as that float |
| 360.0 | 4 | | 0-1-Degrees / *360 |
| 22.0 / 7.0 | 13 / 15 | | GUI stem `22/7` as π (shot 389) |

zlib Core blobs for Hadamard are huge (~1.6 MB inflated ×2) and contain Voice 1…32 + Chain Add 4/8 labels, not readable ±1 coefficient tables.

## Delta — leaf-body compare (2026-09-19)

Read-only. Length-prefixed ASCII names (u32 length immediately before the label).

| Macro | File offset | KSModul in first ~2.8 KB |
|-------|------------:|--------------------------:|
| `2W-X` | 513342 | 10 |
| `2W+X` | 515247 | 10 |
| **`-2W+X`** | **517096** | **12** |
| `2H-Y` | 547112 | 10 |
| `2H+Y` | 549025 | 10 |
| **`-2H+Y`** | **550874** | **12** |
| `2L-Z` | 580898 | 10 |
| `2L+Z` | 582867 | 11 |
| **`-2L+Z`** | **584740** | **12** |
| `4L-Z` | 597729 | 10 |
| `-X` | 529023 | 11 |
| `-Y` | 562809 | 11 |
| `-Z` | 596675 | 11 |

Same-family bodies (first KSModul … +1800 bytes):

| Pair | Identical bytes |
|------|----------------:|
| **`-2W+X` vs `-2H+Y`** | **1767 / 1800 (98.2%)** |
| `-2W+X` vs `-2L+Z` | 1760 / 1800 (97.8%) |
| `-2H+Y` vs `-2L+Z` | 1781 / 1800 (98.9%) |
| `2W-X` vs `2H-Y` / `2L-Z` | ~98% |
| `2W+X` vs `2H+Y` / `2L+Z` | ~98% |
| `-2W+X` vs `2W-X` | 82.1% |
| `-2W+X` vs `2W+X` | 81.7% |

The 44 differing bytes vs `-2H+Y` in the first 2200 are **W/H, X/Y labels** plus canvas position fields — not a different Mul/Sub graph. `-2H+Y` was Structure-opened (shot 321) as **`Y − (2·H)`**. Shot **402** opened `-2W+X` and confirms **`X − (2·W)`** (plus=`SX`, minus=`2W`). Tag: **VERIFIED**.

`4L-Z` is the odd one out (Const **4** family; notable f32 4.0, no 2.0 in the short window).

### 0.3 / 0.25 floats

| Value | f32 count | Where |
|------:|----------:|-------|
| **0.3** | **3** | Offsets 1011, 1027, 1921 — **file header / `Reaktor New`**, not Prepare |
| **0.25** | **3** | Offsets 842664, 845364, 860304 — next to **KSModul** (Prepare ±0.25 family) |

Supports the 0.3→0.5 Prepare correction: the 0.3 glyphs in the file are not the Diverg path.

### Still not in the bytes (as a readable table)

- FDN line delay times (Feedback Delay Network region is voice-index-like 1…32 and 4/8/32, not a prime-ms table in the clear).
- Primary type id for mic `0x7e` (Dir+/C/O/Gain graph is present; type bytes not a public map).
- A vs C wall split (`DffC` / `CWidth` still **zero** occurrences).
- To V 17–52 ↔ FDN V1–32 map.

## Header / NI chunks

Human-readable graph names sit in the clear. Core cells are zlib (`bilz` = zlib reversed, `atad` = data reversed). Same as prior `/workspace/ens-mining-notes.md` which was never copied here.
