# How the 2011 Room Reverb works

> **Illustrated edition:** see [`HOW_IT_WORKS_ILLUSTRATED.md`](HOW_IT_WORKS_ILLUSTRATED.md) (diagrams in [`diagrams/`](diagrams/)).  
> **UI map:** [`UI_GUIDE.md`](UI_GUIDE.md) · **Launch:** [`QUICKSTART.md`](QUICKSTART.md)

Text-first notes for Idle Hanz. Tags: **VERIFIED** (Structure / ens), **ASSUMED** (prototype choice), **PROPOSAL** (not from file).

The current product is a **Desktop FastAPI** tweak app (`software/app_server.py`, `Launch Tweak App.bat`) at **http://127.0.0.1:7860** — custom Canvas / Three.js UI. It is **not** Gradio. Legacy `tweak_app.py` is reference only.

---

## 1. What the 2011 ensemble is trying to do

The Reaktor ensemble models a rectangular room two ways at once:

1. **Early field (image sources).** For each reflection order, mirror the source across walls, measure distance to the mic array, delay by distance / speed of sound, and scale by Air Abs `1/r²`. That builds the first clear echoes and the L/R (and C) balance of the room.
2. **Late field (Hadamard FDN).** An **N**-line feedback delay network mixes energy with an **unscaled ±1 Hadamard** matrix. UI **Feedback** is Structure Gain 0–1; loop `g = Gain/N`. The FDN loop **is** the 2011 wet IR. Early FIR is an ASSUMED overlay only if `early_wet > 0`.

The Desktop rebuild copies the **verified leaf algebra** and Prepare mic/source math into Python. Software geometric level is amplitude `1/r` as of 2026-10-10 (Idle: AGC balance, close mics too loud, physical pressure law). The Structure Air Abs graph remains `1/r²`. **Hadamard N** (UI chips 8 · 16 · 32 · 64 · 128, default **32**) sizes the **image table and FDN lines together**. The pack does **not** invent a full Structure Hadamard OCR sign table (Sylvester; Voice 1–2 match Structure). Surfaces absorb/EQ/diffusion DSP is **ASSUMED**. Panel names B/D/E/F VERIFIED; A+C = Sides (Left/Right split ASSUMED). Masks are tabulated, not rendered.

---

## 2. Signal flow (in order)

1. **Prepare / geometry**  
   Room `W, H, L`. Mic stand: free `mcx` / `mcz` (or Reaktor parity `MCX = W × 0.5`), height `my`. Locked: `MCZ = L − MZ` (VERIFIED). Source: free `sx` / `sz`; height `sy` (modern UI — independent of `my` unless Link heights). Historically Prepare locked `SY = MY` (VERIFIED). Capsules L/R at `MCX ∓ Space/2`, shared Y/Z with centre.

2. **Image sources (N mirrors)**  
   Named mirror macros (`2W−X`, `−X`, `2H−Y`, `4L−Z`, …) produce image coordinates. Prototype grids for N = 8…128 (N = 32 = live / from-them table). Polarity `(−1)^(nx+ny+nz)` (from-them).

3. **Distances and Delays**  
   For each image vs L / C / R: `d = √(Δx² + Δy² + Δz²)`, `delay_ms = (d / 340) × 1000` (VERIFIED). Distances `1/x` is `1/340`. Software geometric amp is `1/r` (Idle 2026-10-10). The Structure Air Abs graph remains `1/r²` (VERIFIED 256). Direct Field `DD` readout stays **2D XZ** (VERIFIED). Direct listen spikes stay pattern-only (0.55 fold), with no distance law.

4. **Mic model + Surfaces colour**  
   Per-capsule pattern (omni / cardioid / fig‑8 ASSUMED) and yaw. Optional Surfaces A–F absorb × EQ × path-length diffusion jitter (**ASSUMED** DSP). Panel names B/D/E/F VERIFIED; A+C = Sides (Left/Right split ASSUMED). A–F **0|1** masks tabulated but **not** in the audio path.

5. **Sound Processing (2011 wet)**  
   **Diffuser Delay** holds image times (max 1000 ms). **Hadamard** mixes delayed voices and feeds back into the same delay. Three L/C/R columns. First read at `d_i` is that image.

6. **Mixer**  
   `L + 0.5·C`, `R + 0.5·C` (477). Voice Combiner sums 32 voices (479). **× Receive RMS Volume** (478). Structure AGC On Send is `√(Σ 1/r²)` (260). **Render** uses IR RMS makeup (ASSUMED, compensates loop gain). **Play live** uses the same target from inject energy × `1/(1−(g√N)²)`. No delay. `dry_gain` is an ASSUMED host-style dry mix.

7. **Render / Play live**  
   FDN loop is the 2011 wet IR. Early FIR overlay if `early_wet > 0` (ASSUMED). **Render** FFT-convolves and writes `software/renders/out.wav`. **Play live** runs the same 32-line algebra in an AudioWorklet (`/api/live_params`) including air 1-pole, high-shelf, and cut-only peaking; drag updates delays while it plays. N locked to 32.

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
| `−2W+X` | `X − (2·W)` | VERIFIED shot 402; same Sub as `-2H+Y` / `-2L+Z` |
| `4L−Z` | `(4·L) − Z` | VERIFIED (Z only) |
| `MCZ` | `L − MZ` | VERIFIED / LOCKED |
| `MCX` | `W × 0.5` | VERIFIED (parity); modern free `mcx` is an extension |
| `MLX` / `MRX` | `MCX − Space/2` / `MCX + Space/2` | VERIFIED |
| `MLALR` / `MRALR` | `Diverg×0.5 − 0.25` / `+ 0.25` | VERIFIED Add (403); included L−R always 0.5 rad |
| `SX` / `SY` / `SZ` | `W×SoX` / `MY` / `MCZ+(L−MCZ)×SoZ` | VERIFIED Prepare; modern free sx/sz and editable `sy` |
| Speed of sound `c` | `340` m/s | VERIFIED Const |
| Delay | `(d/340)×1000` ms | VERIFIED |
| Geometric level | Structure graph `1/r²` (Dis×Dis then `1/x`). Software amplitude `1/r` | Graph VERIFIED (256). Software: Idle 2026-10-10 |
| Image distance | 3D Euclidean `√(Δx²+Δy²+Δz²)` | VERIFIED (420–433) |
| Direct Field `DD` | 2D XZ (`√(Δx²+Δz²)`; Y ignored) | VERIFIED |
| Arrival angle | Structure: ΔX/ΔZ → ArcTan + Sine/Cosine stack; polar only needs `cos θ` = XZ look · r / \|r\| | chain VERIFIED (417, 450, 451); dot form equivalent, not wired as a new path |

**Live-32 image grid** (420/434/435 + Dis 462): ordered poly voices in `LIVE_32`. 29 unique, three duplicate voices, no `±2W`, no `−Z`, `nz=+2` is `2L+Z` not `4L−Z`. Direct is voice 3. Other N values are ASSUMED/PROPOSAL (see Mix Hadamard chips / `software/UI_NOTES.md`).

---

## 4. To V 17–52 and A–F masks

**To V** collectors are indexed event writers shared across Reflection Codes (and Absorb). One shared index is one image voice: an X-macro pick + Y-macro pick + Z-macro pick.

- X Code maps macros onto repeating indices **17–52** (Structure batch-4 / 206).
- Y/Z first-column To V subset is now tabulated (`findings/yz-to-v-reverified.md`, `to_v_tables.py`) — **not** a full 1–52 Y/Z map; still **not** in the audio path.
- A–F Codes write **0 or 1** into those voice slots — a **mask** bus (VERIFIED that writers exist).

Panel names (VERIFIED, Diffusion Matrix 359 / panel 394): **B** Ahead/Front · **D** Behind/Rear · **E** Floor · **F** Ceiling · **A and C** share one **Sides** panel. The Desktop desk still splits **A Left (−X)** and **C Right (+X)** so each card is audible — that split is **ASSUMED**. Geometric wall hits colour taps; Structure A–F 0|1 masks are tabulated in `software/engine/absorb_masks.py` and are **not** in the audio path (voice↔tap map UNKNOWN).

---

## 5. FDN rules used here

| Rule | Value | Tag |
|------|-------|-----|
| Size | N ∈ {8,16,32,64,128}, default 32 | 32 from-them; other N ASSUMED/PROPOSAL grids |
| Matrix | unscaled ±1 Hadamard (Sylvester in code) | construction ASSUMED; no OCR rows VERIFIED |
| Loop gain | UI Feedback = Structure Gain 0–1; `g = Gain/N` (default `1/32`) | VERIFIED (218) |
| Scaling | **no `1/√N` on the matrix** | lock |
| Stability hint | keep loop `g < 1/√N`; Desktop clamps to `0.99/√N` | practical (UI note) |
| Delays | Primary **Diffuser Delay** (built-in allpass; no nested graph). `Dly` ms = image Distances (460 = TL). `Dffs` = internal allpass; 0 = pure delay. Buffer **Max Delay = 1000 ms**, High Quality Interpolation | module VERIFIED (472); buffer VERIFIED (476); Dly list VERIFIED |
| Hadamard role | mix / unique inversions per voice; **Fr.V** is a voice picker, not a delay | VERIFIED (215–218, 468–471) |
| Feedback | Adder on Diffuser Delay In (473) + Hadamard × `(1/32)×Gain` | adder **VERIFIED** (473, both summands cyan) |
| Desktop split | FDN loop is the 2011 wet; early FIR overlay if `early_wet > 0` | overlay ASSUMED (Mixer has no FIR, 477) |
| Inject | tap level at **t = 0** into that delay line | VERIFIED topology (poly copy + Dly); was delayed Hadamard-column PROPOSAL |

---

## 6. Mic model (modern UI)

Not one global cardioid↔omni knob for the product story. The Listen panel and **Mic** desk expose:

| Setup | Space (approx) | Notes |
|-------|----------------|-------|
| AB omni / AB cardioid | ~0.80 m | Spaced pair |
| XY 90° / 120° | ~0.01 m | Coincident; absolute toe degrees |
| ORTF (default) | ~0.17 m | ±55° half-angle |
| NOS / DIN | ~0.30 / ~0.20 m | ±45° |
| **MS** | ~0.05 m | Omni mid (polar C) + inward cardioids L −90° / R +90°. Audio is L/R; C is the polar Mid. ASSUMED |
| MS classic | ~0.05 m | Mid cardioid + Side fig‑8 decode (`ms_decode`, L=M+S / R=M−S). Fig‑8 ASSUMED |
| Mono centre | 0 | C only |
| Custom | — | Free tweak after drift |

Per capsule: pattern (omni / cardioid / fig‑8 ASSUMED) and yaw (0° = room forward +Z). Cardioid/fig‑8 only need `cos θ`; Structure Distances builds θ the long way (ΔX/ΔZ ArcTan). Engine `arrival_cos_xz` is the equivalent XZ dot product — **not** wired into taps. Mic Gain leaf (466–467) is **\|Dir\| × 2**, then **Power `X^Y`** (`Gain = 1 − (2·\|Dir\|)^C/O`), into the 1-pole **cutoff** with Log(Res) — not polar audio gain. **Wired** on delay out, not in the Hadamard loop (410, 466). Res live **10 kHz** (399); C/O Power Y still 1 LIKELY. Tap polar is first-order `a+(1−a)cosθ` plus an ASSUMED off-axis shelf. Absolute toe / yaw is a **modern ASSUMED extension** beyond VERIFIED Diverg×0.5±0.25 Add.

---

## 7. Colour, Surfaces, Polar 3D

| Desk | Role | Tag |
|------|------|-----|
| **Colour** | 1/3-octave magnitude of wet IR after Render; Hold A/B compare; 0 dB = peak band or 1 kHz | ASSUMED long-term colouration view |
| **Surfaces** | Cards A–F: absorb vs freq, EQ shelves/peak, diffusion 0…1; path-length jitter `Δd` seeded | ASSUMED; seed ⇒ bit-identical IR |
| **Polar 3D** | Pattern × frequency mesh in the mic–source plane (tilts when `sy ≠ my`); not image arrivals | Pattern algebra LIKELY/VERIFIED-ish; freq morph ASSUMED |

Diffusion, two layers — do not mix:

- **2011 Diffuser Delay (VERIFIED module):** NI allpass. `Dly` = image ms; **Dffs** = internal feedback (0 = pure delay). Deterministic from Dis × Dff × 1/Diffusion (462–464). No RNG.
- **Desktop Surfaces (ASSUMED):** seeded path-length jitter `Δd = D · λ_ref · sin²(θ) · u`, default `λ_ref = 0.02` m, `u` from SHA-256. Prefer **Δd** over scaling `d` by `1+sin²(θ)`. `D = 0` ⇒ specular. Same seed ⇒ bit-identical IR.

---

## 8. UI mapping (tabs → engine)

| Stage tab | Engine meaning |
|-----------|----------------|
| Floor · Side · 3D | Edit `sx,sz,mcx,mcz,my,sy`; floor Front at top; 3D is a Front 3/4 (Left on the left), orbit above the floor |
| Mic | Same geometry, zoomed; L/C/R polar + pattern/yaw |
| Lattice | Visualise N image cells / polarity |
| Paths | Folded in-room polylines ↔ last-leg segments (`image_geometry`) |
| Colour / Surfaces / Polar 3D | Post-render / ASSUMED colour desks |

Sidebar: **Room size**, **Listen** (setup + capsules), **Mix** (Hadamard N, early/FDN/dry, Feedback Gain, Decay, Humidity, IR length, 2011 snapshot, Play live, diffusion seed), **Preview**, **Advanced** (Reaktor parity mic-X lock).

---

## 9. Studio One vision (intended architecture)

**PROPOSAL / vision — not a shipping plugin claim.** Linked track-FX instances would each be a **source** in one shared rectangular room; a shared room editor (outside the plugins) would own W/H/L, Surfaces, and Colour. Mic array, early field, and FDN stay common. The Desktop FastAPI app is the current shared-editor stand-in.

---

## 10. What is exposed vs still ASSUMED

**You can turn:** W/H/L; free source/mic placement; `sy` / `my` (+ Link); mic setups and per-capsule pattern/yaw; Hadamard N; early/FDN/dry/Feedback/Decay/Humidity/IR length; Surfaces cards + diffusion seed; Colour / Polar views; **Play live**.

**Locked:** `c = 340`; `MCZ = L − MZ`; mirror leaf algebra; unscaled ±1 FDN (no `1/√N` on the matrix); Humidity Wet 100–700 default 400; Diffusion Master 0…−0.5; Mic Res live 10 kHz.

**Still ASSUMED / open:** sample rate 44100; peaking coeffs; C/O Power Y still 1 LIKELY; Dff source (geometric hits LIKELY); full Hadamard OCR signs; A vs C side-wall split; A–F mask→tap map; motion path demos. Inject is t=0 per line (1-pole IR if humidity>0, offline). MS classic fig‑8 decode is in the engine (ASSUMED). Old 20 kHz·m Wet scale is **rejected**.

---

## 11. How to A/B with the Reaktor `.ens`

1. Feed the **same dry WAV** into Reaktor and the Tweak App.
2. Match W/H/L, Space, and source/mic positions as far as labels allow.
3. For Reaktor-like toe, remember Prepare Add keeps a **0.5 rad** L−R spread (`Diverg×0.5±0.25`); modern ORTF/XY need absolute yaw.
4. Match with Mix **2011 Reaktor snapshot** when A/B-ing the dump hall. Play live and/or Render with motion off; compare early clarity and L/R first. Expect FDN-tail and Surfaces colour differences while stagger/A–F remain ASSUMED/PROPOSAL. Play live N is 32; Hadamard chips other than 32 are Render-only.
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
