# How the 2011 Room Reverb works (illustrated)

Companion to [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md). Diagrams live in [`diagrams/`](diagrams/).  
Tags stay honest: **VERIFIED** = Structure / ens · **ASSUMED** / **PROPOSAL** = labeled as such.

Current UI: **Desktop FastAPI** at http://127.0.0.1:7860 (`Launch Tweak App.bat`) — **not** Gradio.  
Regenerate diagrams: `python docs/generate_diagrams.py` (venv with matplotlib).

---

## 1. Design goals

The 2011 Reaktor ensemble models a rectangular room in two cooperating layers:

1. **Early field (image sources)** — mirrors, 3D distance, `c = 340`, geometric `1/r`.
2. **Late field (unscaled Hadamard FDN)** — N lines, ±1 matrix, loop gain `g`; early taps excite the FDN; early wet stays a separate Mix path.

The Desktop rebuild keeps Structure locks readable, exposes a drag UI that does not invent OCR coefficients, and tags ASSUMED Surfaces / Colour / Polar desks clearly.

---

## 2. Signal flow

![Signal flow](diagrams/01_signal_flow.png)

| Step | Block | Tag |
|------|-------|-----|
| 1 | Prepare geometry (`sy` / `my` / MCZ) | VERIFIED locks; modern height split ASSUMED |
| 2 | Image sources (N mirrors) | VERIFIED macros; N grids partly ASSUMED |
| 3 | Distances & Delays (`c=340`, `1/r`) | VERIFIED |
| 4 | Mic pattern + Surfaces colour | Pattern LIKELY; Surfaces ASSUMED |
| 5 | Early wet | — |
| 6 | FDN (N, unscaled ±1, ×g) | Size 32 from-them; matrix construction ASSUMED |
| 7 | Mix → `software/renders/out.wav` (FFT convolution for long WAVs) | — |

---

## 3. Room Floor · Side

![Floor and Side with sy ≠ my](diagrams/07_floor_side_heights.png)

![XZ plan](diagrams/02_room_geometry_xz.png)

- **Floor** — drag source and mic stand in XZ metres.
- **Side** — drag source height `sy` and mic height `my` independently; **Link heights** optional.
- **3D** — orbit only; place on Floor or Mic desk.
- **MCZ = L − MZ** remains LOCKED.

---

## 4. Prepare / MCZ algebra

![Prepare algebra](diagrams/04_prepare_algebra.png)

| Symbol | Formula | Tag |
|--------|---------|-----|
| `MCX` | `W × 0.5` | VERIFIED (parity); free `mcx` modern |
| `MCZ` | `L − MZ` | VERIFIED / LOCKED |
| `MLX` / `MRX` | `MCX ∓ Space/2` | VERIFIED |
| `c` | 340 m/s | VERIFIED |

---

## 5. Image-source mirrors

![Image-source mirrors](diagrams/03_image_mirrors.png)

Delay `(d/340)×1000` ms · level `1/r` · image distance 3D Euclidean — VERIFIED.

---

## 6. Direct Field 2D vs image 3D

![Direct vs image distance](diagrams/06_direct_vs_image_distance.png)

---

## 7. Unscaled Hadamard FDN

![FDN schematic](diagrams/05_fdn_schematic.png)

- **N** chips 8 · 16 · 32 · 64 · 128 (default 32) — same N for images + FDN lines.
- Unscaled ±1 Hadamard — **no `1/√N`**.
- Early images **excite** the FDN.

---

## 8. Mic desk · L/C/R polars · MS

![Mic desk](diagrams/08_mic_desk_polars.png)

Zoomed stand + three polars. Presets: AB, XY, ORTF, NOS, DIN, **MS** (omni mid + inward cardioids), mono centre.

---

## 9. Lattice · Paths

![Lattice and Paths](diagrams/09_lattice_paths.png)

---

## 10. Colour · Surfaces

![Colour and Surfaces](diagrams/10_colour_surfaces.png)

**ASSUMED** long-term colouring — Structure mask writers exist; wall dictionary not OCR-locked.

---

## 11. Polar × frequency field

![Polar frequency field](diagrams/11_polar_field.png)

**ASSUMED** — not a plot of image-arrival directions.

---

## 12. Studio One linked track-FX (vision)

![Studio One vision](diagrams/12_track_fx_instances.png)

Intended architecture — not a claim that a Studio One plugin ships in this pack.

---

## Further reading

| Doc | Role |
|-----|------|
| [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md) | Text-first twin |
| [`QUICKSTART.md`](QUICKSTART.md) | Launch / render |
| [`UI_GUIDE.md`](UI_GUIDE.md) | Tab / control → engine |

Diagrams: `01`…`12` under [`diagrams/`](diagrams/).
