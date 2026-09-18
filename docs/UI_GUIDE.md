# UI guide — 2011 Room Reverb Desktop tweak app

Maps every **current** FastAPI UI tab and control to engine meaning.  
Source of truth for labels: `software/static/index.html`. Developer detail: `software/UI_NOTES.md`.

Tags: **VERIFIED** · **ASSUMED** · **PROPOSAL** · modern extension.

The app is **not** Gradio. Launch: `software/Launch Tweak App.bat` → http://127.0.0.1:7860.

> Older Reaktor panel catalog (batch-6 screenshots) lives in [`panel-controls.md`](panel-controls.md) for Structure archaeology — not the live Desktop UI.

---

## Top bar

| Control | Meaning |
|---------|---------|
| **Upload WAV** | Dry input for render |
| **Render** | Build IR, FFT-convolve long files, write `software/renders/out.wav`, refresh Colour / Polar when open |

---

## Stage view switcher

| Tab | What you see / do | Engine |
|-----|-------------------|--------|
| **Floor · Side · 3D** | Floor plan (XZ) drag Src/Mic; Side elevation (ZY) heights; 3D orbit/pan/zoom | `sx,sz,mcx,mcz,my,sy` |
| **Mic** | Zoomed stand: top / side / 3D + L/C/R polar plots | Same geometry + per-capsule pattern/yaw |
| **Lattice** | Mirrored-room image tiling | `POST /api/images` lattice cells |
| **Paths** | In-room paths ↔ Last legs toggle | Folded polylines / last-leg segments |
| **Colour** | 1/3-octave wet-IR bars + compare tools | After Render / `/api/colour` (**ASSUMED**) |
| **Surfaces** | A–F absorb / EQ / diffusion cards | **ASSUMED** surface model |
| **Polar 3D** | Pattern × frequency solid | `/api/polar` (**ASSUMED** freq morph) |

**Mic toggles** (Lattice / Paths): L · C · R · All — which listeners to draw paths for (default C).

**Paths mode chips:** In-room paths | Last legs.

**Link heights** (Floor and Mic desks): when on, `sy` and `my` stay equal. Off by default so **sy ≠ my** is allowed (modern; Prepare historically SY=MY **VERIFIED**).

---

## Sidebar — Room size

| Control | Engine | Notes |
|---------|--------|-------|
| Width / Ceiling / Length | `W` / `H` / `L` (metres) | Size changes **clamp** positions; do not scale them |

---

## Sidebar — Listen

| Control | Engine | Notes |
|---------|--------|-------|
| **Mic setup** | Preset snap | AB omni/card, XY 90/120, ORTF, NOS, DIN, **MS (omni mid + inward cardioids)**, MS classic, Mono C, Custom |
| Capsule space | `space` (m) | L/R separation about stand |
| Stand X / Stand Z | `mcx` / `mcz` | Free by default; Advanced parity locks X to W/2 |
| Mic height / Src height | `my` / `sy` | Independent unless Link heights |
| L / C / R **pattern** | `pattern_l/c/r` | omni · cardioid · fig‑8 (**ASSUMED**) |
| L / C / R **yaw** | `yaw_*_deg` | 0° = forward (+Z); MS inward L −90° / R +90° |

Hidden legacy fields (`diverg`, `toe_half_deg`, `car_omni`) remain for API compat. Omitting absolute toe in API still uses VERIFIED Diverg formula.

---

## Sidebar — Mix

| Control | Engine | Notes |
|---------|--------|-------|
| **Hadamard size** 8/16/32/64/128 | `hadamard_n` | **N images · N FDN lines**; default 32 |
| Early reflections | `early_wet` | Image-field wet gain |
| Late reverb (FDN) | `fdn_wet` | FDN wet gain |
| Dry | `dry_gain` | Dry bypass |
| Decay (FDN g) | `fdn_g` | Loop gain; keep under `1/√N` |
| IR length ms | `ir_length_ms` | Render length |
| Diffusion seed | `diffusion_seed` | **ASSUMED**; same seed ⇒ bit-identical IR |

Matrix is unscaled ±1 Sylvester — **no `1/√N`**.

---

## Sidebar — Preview

| Control | Meaning |
|---------|---------|
| File name / audio player | Last render preview |
| Status / out path | Progress and `renders/out.wav` |

---

## Advanced / Structure locks

| Control | Meaning |
|---------|---------|
| **Reaktor parity** | Lock mic X to room centre (`MCX = W/2`) |
| Notes | Reminds: `MCZ = L − MZ`, `c = 340`, Diverg angle span, free mic X / absolute yaw as modern extensions, diffusion `λ_ref` default 0.02 m (**ASSUMED**) |

---

## Colour desk (stage)

| Control | Meaning | Tag |
|---------|---------|-----|
| Now / Last / Hold A / Hold B | Compare curves after re-Render | ASSUMED view |
| 0 dB ref | Peak band or 1 kHz | — |
| Face badge / net | Selected Surfaces face orientation | ASSUMED map A–F → walls |

---

## Surfaces desk (stage)

| Control | Meaning | Tag |
|---------|---------|-----|
| Cards A–F | absorb vs freq, EQ, diffusion 0…1 | ASSUMED |
| Diffusion λ_ref / seed | Path-length jitter params | ASSUMED |

Orientation used in UI (ASSUMED): A Left (−X) · B Front (+Z) · C Right (+X) · D Back (−Z) · E Floor (−Y) · F Ceiling (+Y).

---

## Polar 3D desk (stage)

| Control | Meaning | Tag |
|---------|---------|-----|
| L / C / R / Sum | Which pattern solids to show (default Sum) | — |
| Refresh | Re-fetch `/api/polar` | — |
| Orbit / scroll | Inspect mesh; plane tilts if `sy ≠ my` | Freq morph ASSUMED |

---

## Mic desk detail

| Pane | Action |
|------|--------|
| Top · plan | Drag body to place; drag amber arc to yaw |
| Side · height | Drag Src H / Mic H only |
| 3D · array | Orbit only; look cones |
| Polar L/C/R | Pattern × yaw readout; capsule slots under plots |

---

## Original Reaktor panel (archive)

For Structure screenshot catalogs (Surfaces / Room Dimension / Sound Position / Microphone categories, GainF, Clip Diffusion, etc.) see [`panel-controls.md`](panel-controls.md). That document describes the **2011 ensemble panel**, not this Desktop app.
