# How the 2011 Room Reverb works

> **Illustrated edition:** see [`HOW_IT_WORKS_ILLUSTRATED.md`](HOW_IT_WORKS_ILLUSTRATED.md) (diagrams in [`diagrams/`](diagrams/)).  
> **UI map:** [`UI_GUIDE.md`](UI_GUIDE.md) · **Launch:** [`QUICKSTART.md`](QUICKSTART.md)

Text-first notes for Idle Hanz. Tags: **VERIFIED** (Structure / ens), **ASSUMED** (prototype choice), **PROPOSAL** (not from file).

The current product is a **Desktop FastAPI** tweak app (`software/app_server.py`, `Launch Tweak App.bat`) at **http://127.0.0.1:7860** — custom Canvas / Three.js UI. It is **not** Gradio. Legacy `tweak_app.py` is reference only.

---

## 1. What the 2011 ensemble is trying to do

The Reaktor ensemble models a rectangular room two ways at once:

1. **Early field (image sources).** For each reflection order, mirror the source across walls, measure distance to the mic array, delay by distance / speed of sound, and scale by geometric `1/r`. That builds the first clear echoes and the L/R (and C) balance of the room.
2. **Late field (Hadamard FDN).** An **N**-line feedback delay network mixes energy with an **unscaled ±1 Hadamard** matrix and a single loop gain `g` in `(0, 1)`. Early taps **excite** the FDN; the early field itself stays a separate wet path into Mix.

The Desktop rebuild copies the **verified leaf algebra** and Prepare mic/source math into Python. **Hadamard N** (UI chips 8 · 16 · 32 · 64 · 128, default **32**) sizes the **image table and FDN lines together**. The pack does **not** invent a full Structure Hadamard OCR sign table. Surfaces A–F absorb/EQ/diffusion in the modern UI are **ASSUMED** (Structure mask writers exist; wall dictionary is not OCR-locked into the engine as verified truth).

---

## 2. Signal flow (in order)

1. **Prepare / geometry**  
   Room `W, H, L`. Mic stand: free `mcx` / `mcz` (or Reaktor parity `MCX = W × 0.5`), height `my`. Locked: `MCZ = L − MZ` (VERIFIED). Source: free `sx` / `sz`; height `sy` (modern UI — independent of `my` unless Link heights). Historically Prepare locked `SY = MY` (VERIFIED). Capsules L/R at `MCX ∓ Space/2`, shared Y/Z with centre.

2. **Image sources (N mirrors)**  
   Named mirror macros (`2W−X`, `−X`, `2H−Y`, `4L−Z`, …) produce image coordinates. Prototype grids for N = 8…128 (N = 32 = live / from-them table). Polarity `(−1)^(nx+ny+nz)` (from-them).

3. **Distances and Delays**  
   For each image vs L / C / R: `d = √(Δx² + Δy² + Δz²)`, `delay_ms = (d / 340) × 1000` (VERIFIED). Geometric level `1/r` (VERIFIED). Direct Field `DD` readout stays **2D XZ** (VERIFIED).

4. **Mic model + Surfaces colour**  
   Per-capsule pattern (omni / cardioid / fig‑8 ASSUMED) and yaw. Optional Surfaces A–F absorb × EQ × path-length diffusion jitter (**ASSUMED**). Structure A–F **0|1** mask writers into To V are VERIFIED to exist; letter→wall dictionary is not claimed verified here.

5. **Early wet**  
   Delayed, levelled, pattern-weighted image taps → early wet bus.

6. **FDN**  
   N delay lines, feedback through unscaled ±1 Hadamard, × `g ∈ (0, 1)`. **No `1/√N`**. Early taps inject into the FDN (PROPOSAL inject mapping). Delay stagger from `W,H,L` is PROPOSAL.

7. **Mix / Render**  
   Dry + early wet + FDN wet. Long WAVs use **FFT convolution**. Writes `software/renders/out.wav`.

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
| `MCX` | `W × 0.5` | VERIFIED (parity); modern free `mcx` is an extension |
| `MLX` / `MRX` | `MCX − Space/2` / `MCX + Space/2` | VERIFIED |
| `MLALR` / `MRALR` | `Diverg × 0.3 × (−0.25)` / `(+0.25)` | VERIFIED Reaktor; ≈±4.3° at Diverg=1 |
| `SX` / `SY` / `SZ` | `W×SoX` / `MY` / `MCZ+(L−MCZ)×SoZ` | VERIFIED Prepare; modern free sx/sz and editable `sy` |
| Speed of sound `c` | `340` m/s | VERIFIED Const |
| Delay | `(d/340)×1000` ms | VERIFIED |
| Geometric level | `1/r` | VERIFIED |
| Image distance | 3D Euclidean | VERIFIED |
| Direct Field `DD` | 2D XZ | VERIFIED |

**Live-32 image grid** (from-them / agreed): 3×3×3 plus face centres, omit `(0,0,−2)`. Other N values are ASSUMED/PROPOSAL subsets or supersets (see Mix Hadamard chips / `software/UI_NOTES.md`).

---

## 4. To V 17–52 and A–F masks

**To V** collectors are indexed event writers shared across Reflection Codes (and Absorb). One shared index is one image voice: an X-macro pick + Y-macro pick + Z-macro pick.

- X Code maps macros onto repeating indices **17–52** (Structure batch-4).
- A–F Codes write **0 or 1** into those voice slots — a **mask** bus (VERIFIED that writers exist).

What this pack does **not** claim as verified audio-engine truth: which letter A–F is which physical surface. The modern Surfaces desk uses an **ASSUMED** orientation (A Left −X · B Front +Z · C Right +X · D Back −Z · E Floor −Y · F Ceiling +Y) and geometric wall hits until an OCR voice↔tap map is locked.

---

## 5. FDN rules used here

| Rule | Value | Tag |
|------|-------|-----|
| Size | N ∈ {8,16,32,64,128}, default 32 | 32 from-them; other N ASSUMED/PROPOSAL grids |
| Matrix | unscaled ±1 Hadamard (Sylvester in code) | construction ASSUMED; no OCR rows VERIFIED |
| Loop gain | `g` in `(0, 1)` | from-them / lock |
| Scaling | **no `1/√N`** | lock |
| Stability hint | keep `g < 1/√N` | practical (UI note) |
| Delays | from room `W,H,L` stagger | PROPOSAL |
| Inject | early taps → FDN | PROPOSAL pattern |

---

## 6. Mic model (modern UI)

Not one global cardioid↔omni knob for the product story. The Listen panel and **Mic** desk expose:

| Setup | Space (approx) | Notes |
|-------|----------------|-------|
| AB omni / AB cardioid | ~0.80 m | Spaced pair |
| XY 90° / 120° | ~0.01 m | Coincident; absolute toe degrees |
| ORTF (default) | ~0.17 m | ±55° half-angle |
| NOS / DIN | ~0.30 / ~0.20 m | ±45° |
| **MS** | ~0.05 m | **Omni mid + inward cardioids** (L −90° / R +90°) — ASSUMED layout; UI label |
| MS classic | ~0.05 m | Mid cardioid + Side fig‑8 (fig‑8 ASSUMED) |
| Mono centre | 0 | C only |
| Custom | — | Free tweak after drift |

Per capsule: pattern (omni / cardioid / fig‑8 ASSUMED) and yaw (0° = room forward +Z). Cardioid gain uses a **LIKELY** `(1+cosθ)/2` style; exact Reaktor Core blend is unproven. Absolute toe / yaw is a **modern ASSUMED extension** beyond VERIFIED Diverg×0.3×±0.25.

---

## 7. Colour, Surfaces, Polar 3D

| Desk | Role | Tag |
|------|------|-----|
| **Colour** | 1/3-octave magnitude of wet IR after Render; Hold A/B compare; 0 dB = peak band or 1 kHz | ASSUMED long-term colouration view |
| **Surfaces** | Cards A–F: absorb vs freq, EQ shelves/peak, diffusion 0…1; path-length jitter `Δd` seeded | ASSUMED; seed ⇒ bit-identical IR |
| **Polar 3D** | Pattern × frequency mesh in the mic–source plane (tilts when `sy ≠ my`); not image arrivals | Pattern algebra LIKELY/VERIFIED-ish; freq morph ASSUMED |

Diffusion model (ASSUMED): `Δd = D · λ_ref · sin²(θ) · u` with seeded SHA-256 stream; default `λ_ref = 0.02` m. `D = 0` ⇒ specular delays.

---

## 8. UI mapping (tabs → engine)

| Stage tab | Engine meaning |
|-----------|----------------|
| Floor · Side · 3D | Edit `sx,sz,mcx,mcz,my,sy`; 3D orbit-only |
| Mic | Same geometry, zoomed; L/C/R polar + pattern/yaw |
| Lattice | Visualise N image cells / polarity |
| Paths | Folded in-room polylines ↔ last-leg segments (`image_geometry`) |
| Colour / Surfaces / Polar 3D | Post-render / ASSUMED colour desks |

Sidebar: **Room size**, **Listen** (setup + capsules), **Mix** (Hadamard N, early/FDN/dry, g, IR length, diffusion seed), **Preview**, **Advanced** (Reaktor parity mic-X lock).

---

## 9. Studio One vision (intended architecture)

**PROPOSAL / vision — not a shipping plugin claim.** Linked track-FX instances would each be a **source** in one shared rectangular room; a shared room editor (outside the plugins) would own W/H/L, Surfaces, and Colour. Mic array, early field, and FDN stay common. The Desktop FastAPI app is the current shared-editor stand-in.

---

## 10. What is exposed vs still ASSUMED

**You can turn:** W/H/L; free source/mic placement; `sy` / `my` (+ Link); mic setups and per-capsule pattern/yaw; Hadamard N; early/FDN/dry/g/IR length; Surfaces cards + diffusion seed; Colour / Polar views.

**Locked:** `c = 340`; `MCZ = L − MZ`; mirror leaf algebra; unscaled ±1 FDN (no `1/√N`).

**Still ASSUMED / open:** sample rate 44100; peaking/humidity coeffs; cardioid Core exact blend; FDN delay stagger and inject map; full Hadamard OCR signs; verified A–F→wall dictionary; fig‑8 Side decode fidelity; motion path demos.

---

## 11. How to A/B with the Reaktor `.ens`

1. Feed the **same dry WAV** into Reaktor and the Tweak App.
2. Match W/H/L, Space, and source/mic positions as far as labels allow.
3. For Reaktor-like toe, remember Diverg only spans ≈±4.3°; modern ORTF/XY need absolute yaw (parity toggle does not restore Diverg limits).
4. Render with motion off; compare early clarity and L/R first. Expect FDN-tail and Surfaces colour differences while stagger/A–F remain ASSUMED/PROPOSAL.
5. Prefer Structure **VERIFIED** algebra over inventing coefficients when something disagrees.

Engine check from `software/`:

```bat
.venv\Scripts\activate
cd engine
python selfcheck.py
```

---

## Further reading

- [`QUICKSTART.md`](QUICKSTART.md) · [`UI_GUIDE.md`](UI_GUIDE.md) · [`HOW_IT_WORKS_ILLUSTRATED.md`](HOW_IT_WORKS_ILLUSTRATED.md)
- `findings/structure-findings.md` · `findings/INDEX.md`
- `software/UI_NOTES.md` · `software/engine/`
