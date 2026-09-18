# How the 2011 Room Reverb works

> **Illustrated edition:** see [`HOW_IT_WORKS_ILLUSTRATED.md`](HOW_IT_WORKS_ILLUSTRATED.md) (diagrams in [`diagrams/`](diagrams/)).


Text-first notes for Idle Hanz. No diagrams — numbered prose and tables only.
Tags: **VERIFIED** (Structure / ens), **ASSUMED** (prototype choice), **PROPOSAL** (not from file).

---

## 1. What the 2011 ensemble is trying to do

The Reaktor ensemble models a rectangular room two ways at once:

1. **Early field (image sources).** For each reflection order, mirror the source across walls, measure distance to a stereo mic pair, delay by distance / speed of sound, and scale by geometric `1/r`. That builds the first clear echoes and the L/R balance of the room.
2. **Late field (Hadamard FDN).** A 32-line feedback delay network mixes energy with an **unscaled ±1 Hadamard** matrix and a single loop gain `g` in `(0, 1)`. Early taps excite the FDN; the early field itself stays a separate wet path.

The rebuild on this Desktop pack copies the **verified leaf algebra** and Prepare mic/source math into Python. It does **not** invent an A–F surface dictionary or a full Structure Hadamard sign table from soft OCR.

---

## 2. Signal flow (in order)

1. **Prepare / Direct Field**  
   Panel knobs become metres: room `W, H, L`; mic `MZ, MY, Space, Diverg`; source `SoX, SoZ` (0–1).  
   Mic centre: `MCX = W × 0.5`, `MCZ = L − MZ` (VERIFIED). Left/right mics share Y/Z; X = `MCX ∓ Space/2`.  
   Source: `SX = W × SoX`, `SY = MY`, `SZ = MCZ + (L − MCZ) × SoZ` (VERIFIED).  
   Direct Field path uses **2D XZ** distances for its own `DD` readout (VERIFIED); image distances later use **3D** Euclidean (VERIFIED).

2. **Reflection Codes (X / Y / Z)**  
   Named mirror macros produce image coordinates per axis (`2W−X`, `−X`, `2H−Y`, `4L−Z`, …).  
   Outputs fan into **To V** collectors (indices roughly 17–52) so each voice is an `(X, Y, Z)` triple.

3. **Distances and Delays**  
   For each image vs left / centre / right listener:  
   `d = √(Δx² + Δy² + Δz²)`, `delay_ms = (d / 340) × 1000` (VERIFIED).  
   Geometric level uses reciprocal `1/r` (VERIFIED).

4. **Absorb Diffus / A–F masks**  
   Serial A→F codes write **0|1** into To V slots. That is a **surface → voice mask** bus (VERIFIED that the mask writers exist).  
   Letter → physical wall dictionary is **not wired in this prototype** (ASSUMED omitted / not invented).

5. **Sound Processing**  
   Per-voice delay, level, mic pattern (cardioid↔omni lerp is LIKELY), optional peaking / humidity shelves (ASSUMED filter details).  
   Stereo L/R from the mic pair.

6. **FDN**  
   32 delay lines, feedback through unscaled ±1 Hadamard, multiply by `g ∈ (0, 1)`. **No `1/√N`**.  
   Delay stagger from `W, H, L` is a **PROPOSAL**, not measured from the ensemble.

7. **Mix**  
   Dry + early wet + FDN wet → out. The tweak app writes `software/renders/out.wav`.

---

## 3. Verified leaf algebra (table)

Corner origin, full room size `R` (no half-W). Sub pin order as opened in Structure.

| Macro / law | Formula | Tag |
|-------------|---------|-----|
| Pass-through `X` / `Y` / `Z` | `S` | VERIFIED |
| `−X` / `−Y` | `−S` | VERIFIED |
| `2W−X` / `2H−Y` / `2L−Z` | `(2·R) − S` | VERIFIED |
| `2W+X` / `2H+Y` / `2L+Z` | `(2·R) + S` | VERIFIED |
| `−2H+Y` / `−2L+Z` | `S − (2·R)` | VERIFIED |
| `−2W+X` | same family as Y/Z form | leaf not opened; engine uses same Sub shape |
| `4L−Z` | `(4·L) − Z` | VERIFIED (Z only) |
| `MCZ` | `L − MZ` | VERIFIED / LOCKED |
| `MCX` | `W × 0.5` | VERIFIED |
| `MLX` / `MRX` | `MCX − Space/2` / `MCX + Space/2` | VERIFIED |
| `MLALR` / `MRALR` | `Diverg × 0.3 × (−0.25)` / `(+0.25)` | VERIFIED |
| `SX` / `SY` / `SZ` | `W×SoX` / `MY` / `MCZ+(L−MCZ)×SoZ` | VERIFIED |
| Speed of sound `c` | `340` m/s | VERIFIED Const |
| Delay | `(d/340)×1000` ms | VERIFIED |
| Geometric level | `1/r` | VERIFIED |
| Image distance | 3D Euclidean | VERIFIED |
| Direct Field `DD` | 2D XZ | VERIFIED |

Prototype grid: **32** images = 3×3×3 plus face centres, omit `(0,0,−2)` (from-them / agreed). Polarity `(−1)^(nx+ny+nz)` (from-them).

---

## 4. What To V 17–52 and A–F masks mean

**To V** collectors are indexed event writers shared across Reflection Codes (and Absorb). One shared index is one image voice: an X-macro pick + Y-macro pick + Z-macro pick.

- X Code maps macros onto repeating indices **17–52** (Structure batch-4).
- Y / Z Codes feed **19–52** (partial fan-outs documented in batch notes).
- A–F Codes write **0 or 1** into those voice slots — a **mask** that can mute or enable absorption/diffusion per voice.

What this pack does **not** claim: which letter A–F is which physical surface (floor/ceiling/walls). Tables exist in batch-4 notes; they are **not invented into the audio engine**.

---

## 5. FDN rules used here

| Rule | Value | Tag |
|------|-------|-----|
| Size | N = 32 | agreed |
| Matrix | unscaled ±1 Hadamard (Sylvester construction in code) | construction ASSUMED; no OCR rows claimed VERIFIED |
| Loop gain | `g` in `(0, 1)` | from-them / lock |
| Scaling | **no `1/√N`** | lock |
| Delays | from room `W,H,L` stagger | PROPOSAL |
| Inject | early taps → Hadamard columns | PROPOSAL pattern |

Structure shows hierarchical summers and gray `−x` for signs, plus a separate `In×(1/32)×Gain` path in one shot — the live audio FDN copy is not fully restored; this prototype keeps the agreed unscaled ±1 + `g` rule.

---

## 6. What the tweak app exposes vs what is still ASSUMED

**Exposed (you can turn these):**

- Room `W, H, L` (defaults ASSUMED musical sizes)
- Source `SoX, SoZ`, height via `MY` (Prepare VERIFIED formulas)
- Mic `MZ, MY, Space, Diverg`, `Car/Omni`
- Mix: early wet, FDN wet, dry, FDN `g`, IR length
- Motion: path on/off; presets still / ellipse / perimeter; ellipse rate / radii (path shapes ASSUMED)

**Locked in UI / engine:**

- `c = 340`
- `MCZ = L − MZ`
- Mirror leaf algebra listed above
- Unscaled ±1 FDN, no `1/√N`
- No A–F surface dictionary wired

**Still ASSUMED / open:**

- Sample rate 44100
- Peaking Q, humidity shelf coeffs, allpass ms
- Cardioid exact `0x7e` blend algebra (lerp `(1+cosθ)/2` kept as LIKELY)
- FDN delay proposal and inject mapping
- Motion hop/OLA (100 ms hop, 200 ms Hann) — same idea as `moving_room_demo.py`
- Full Hadamard sign table from Structure OCR
- A–F → wall dictionary

---

## 7. How to listen / A/B with the Reaktor `.ens`

1. Open the ensemble on your machine (pack points at `ensemble/` on Desktop — the `.ens` itself is not duplicated inside this zip’s audio path; you already have `2011-room-reverb.ens` from the project).
2. Feed the **same dry WAV** into Reaktor and into the Tweak App.
3. Match room / mic / source knobs as far as labels allow (`W,H,L`, Space, Diverg, SoX/SoZ, Car/Omni).
4. Render with **path off** first for a static A/B, then try ellipse motion vs a fixed Reaktor source.
5. Compare early clarity and L/R image first; treat long FDN tail differences as expected while delay stagger remains PROPOSAL and A–F masks are unwired.
6. Desktop demo WAVs (`moving-room-demo.wav` / short) are listening references only — not claims of bit-exact Reaktor identity.

When something disagrees, prefer Structure VERIFIED algebra over prototype ASSUMED filters. Do not “fix” by inventing coefficients.

---

## Further reading in this pack

- `docs/QUICKSTART.md` — launch and render in a few steps  
- `findings/structure-findings.md` — master Structure log  
- `findings/INDEX.md` — batch note paths  
- `software/engine/README` equivalent: engine modules + `selfcheck.py`
