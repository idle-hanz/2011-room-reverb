# UI notes — 2011 Room Reverb (modern drag UI)

## What changed vs the Reaktor panel

The old Multi Display / red-line mic stem was a **Reaktor panel limitation**, not a product ideal.
This app replaces that Gradio/matplotlib click-to-place panel with a **pro spatial tool**:

| Then (Reaktor / early Gradio) | Now |
|---|---|
| Click map with Place Source / Place Mic radio | **Drag** Source and Mic stand on floor plan **and 3D** |
| Mic X locked to W/2 always | **Free mic X** by default; optional **Reaktor parity** toggle snaps MCX→W/2 |
| VERIFIED tags on every control | Plain English labels; VERIFIED / Structure locks only under **Advanced** |
| Red-line stem graphic in main UI | Removed from main UI (dark charcoal + teal accent) |
| Gradio chrome / science worksheet feel | Custom HTML/Canvas + **Three.js 3D room**, one primary **Render** button |

## Hero interaction

1. **Floor plan (top-down XZ)** — drag Source freely; drag Mic stand in X/Z (clamped to room).
   L/R capsules follow stand + Space; look arrows show toe-in; live metre readout.
2. **3D room (perspective)** — orbit (Alt / RMB), pan (Shift), scroll zoom; drag Src/Mic on the height plane (raycast Y=my). Local Three.js r160 vendor (offline-tolerant).
3. **Side elevation** — drag mic **Height** (source Y follows mic, Prepare SY=MY).
4. Optional: select Source / Mic tool, then click empty floor (2D or 3D) to place.

## Room size behaviour

Width / Ceiling / Length changes **do not scale** free-placed `sx` / `mcx` / `sz` / `mcz` / `my` / `space`.
Positions stay in absolute metres; only `clampRoom` if outside the new box.
(Reaktor parity ON still snaps MCX → W/2.)

## Engine

- Audio path unchanged: `engine/early_field.py`, `engine/fdn.py`, `render_pipeline.py`.
- `prepare_direct_field(..., mcx=None, toe_half_deg=None)` — `None` mcx ⇒ W/2 (parity); explicit mcx unlocks stand X; optional `toe_half_deg` overrides Diverg×0.3×±0.25 for XY/ORTF.
- Space is clamped so L/R capsules stay inside Width relative to MCX.
- MCZ = L − MZ still locked; no invented A–F / Hadamard tables.

## How to run

Double-click **`Launch Tweak App.bat`** (or `./launch_tweak_app.sh`).
Opens http://127.0.0.1:7860 — FastAPI + static Canvas UI.
Refresh the browser after pulling UI updates.

Legacy Gradio `tweak_app.py` is kept for reference but is **not** the one-click launcher.

## Smoke

```bash
.venv/bin/python test_smoke_drag_render.py
.venv/bin/python renders/ui_preview/capture_previews.py   # needs server on :7860
```


## Early-field image views (Lattice · Paths)

View switcher above the stage:

| Tab | What you see |
|---|---|
| **Floor · Side · 3D** | Existing drag editors (unchanged; absolute metres, no scale-on-resize) |
| **Lattice** | Method-of-images mirrored-room tiling — wireframe boxes at integer lattice cells from `early_field.build_image_indices()` + corner-origin `image_position()`. Home room gold; image sources marked; polarity colour (± from `polarity(n)`) |
| **Paths** | Single tab with on-page **In-room paths / Last legs** toggle (default: In-room). In-room = folded specular bounce paths; Last legs = final arrival segment. Lattice hides this toggle. |

**UI:** Paths tab hosts the In-room | Last-legs mode chips; switching mode reuses `imagesCache` (no extra fetch).

**Mic toggles:** default **C** only. L / C / R checkboxes (and **All**) recompute paths/last legs for those listeners. Lattice boxes are shared; path + last-leg views depend on selection.

**API:** `POST /api/images` with current room/source/mic params + `mics: ["C"]` (or L/R/`["L","C","R"]`). Returns lattice cells, folded polylines, and last-leg segments via `image_geometry.build_images_payload`. Uses VERIFIED Prepare + image algebra only — no invented A–F / Hadamard tables.

**Folding:** `image_geometry.folded_polyline` — intersect image→mic with planes x=kW, y=kH, z=kL; map each sample into `[0,W]×[0,H]×[0,L]` by even/odd mirror tiling (`fold_coord`).

**Perf:** default 32 images × up to 3 mics; orbit/pan/zoom match the 3D room (Alt/RMB, Shift, scroll).

## Hadamard size (images + FDN lines)

UI control in **Mix**: stepped buttons **N = 8 · 16 · 32 · 64 · 128** (Sylvester powers of 2 only).
Default **32** (live / Reaktor-era). Readout: “N images · N FDN lines”.

Both the early-field image table and the FDN feedback matrix use the same N:

| N | Image grid bias | Tag | Notes |
|---|---|---|---|
| 8 | `8` | ASSUMED/PROPOSAL | Direct + six ±1 faces + (0,0,2). Subset of live-32. |
| 16 | `16` | ASSUMED/PROPOSAL | Manhattan ≤1 (7) + four XY edges at z=0 + five live-32 face extras. Subset of live-32. |
| 32 | `32` | from-them / live | 3×3×3 + five face centres two steps out; omit (0,0,−2). |
| 64 | `64like` | proposal | Existing denser +z table (exactly 64). Superset of live-32. |
| 128 | `128` | ASSUMED/PROPOSAL | Chebyshev R≤2 (125) + axials (3,0,0),(−3,0,0),(0,0,3). Superset of live-32 and 64like. |

**Matrix:** unscaled ±1 Sylvester Hadamard — **no 1/√N**. Keep Decay (FDN g) under **1/√N** for stability (e.g. g≲0.177 at N=32, g≲0.088 at N=128).

**API:** `hadamard_n` on `/api/images` and `/api/render` (also accepts `grid`). Lattice / In-room / Last-leg refresh immediately on change; Render uses N-line FDN + N early taps.

Do **not** invent A–F OCR / Structure Hadamard sign rows — construction is Sylvester recursive only.

## Colour · Surfaces · Polar 3D (hybrid C)

### Colour — tuning instrument
- Long-term room colouration from the **wet IR** as a **1/3-octave** magnitude curve (ISO-ish centres).
- Updates after **Render**; `/api/colour` can preview without a dry file.
- **Compare curves:** previous Colour becomes a **Last** ghost overlay after re-Render. Optional **Hold A / Hold B** snapshots; **Clear** drops Last + holds. Legend: Now (teal) · Last (grey dashed) · Hold A (amber) · Hold B (violet).
- **Engineer readout:**
  - **0 dB reference** selectable: **Peak band** (default) or **1 kHz** (nearest 1/3-octave centre). Documented in meta + API (`ref_mode`, `levels_db_peak`, `levels_db_1khz`, `levels_db_abs`).
  - Labelled frequency marks at **125 / 250 / 500 / 1k / 2k / 4k / 8k**.
  - Hover a band → **Hz + dB** tooltip and live readout.
- **Room net / orientation (ASSUMED):** Surfaces A–F are mapped to real faces — **A Left (−X) · B Front (+Z) · C Right (+X) · D Back (−Z) · E Floor (−Y) · F Ceiling (+Y)**. An **unfolded room net** (Ceiling / Left–Front–Right–Back / Floor) sits above the surface cards; click a face to select. Each face shows a facing arrow, axis, and absorb×EQ spark. Colour panel shows a **face badge** (arrow + name + facing) and a **tiny net inset** on the plot with the selected face lit. Orientation is unmistakable — not a naked EQ strip.
- **Tie to Surfaces:** selecting A–F dims Colour bars by that surface’s absorb and overlays an ASSUMED absorb×EQ influence curve; **sparkline** under the main plot shows that surface’s EQ (amber) and 1−α transmission (grey dashed).
- Not razor FFT as the primary view. ASSUMED tags stay honest.

### Surfaces (A–F) — **ASSUMED**
- Cards A–F with friendly labels + Advanced letter.
- Each card: **absorb vs frequency**, **EQ** (low shelf / peak / high shelf), **diffusion** slider (0…1).
- Clearly tagged **ASSUMED** — does **not** claim Structure-locked A–F EQ dictionary.
- Engine wiring (ASSUMED): when an image’s geometric wall-crossing hits surface S, apply that surface’s absorb×EQ.
- **Diffusion is seeded path-length jitter** (replaces the old allpass-stage proxy):
  - `Δd = D · λ_ref · sin²(θ) · u` then `d' = max(ε, d + Δd)` (metres, not a `(1+sin²θ)` scale).
  - `θ` = angle between the unfolded image→mic ray and that wall’s inward normal (0 = normal incidence → no jitter).
  - `u ∈ [-1, 1]` Uniform from a **seeded** SHA-256 stream keyed by `(seed, image index, surface, mic)`.
  - Default `λ_ref = 0.02` m (ASSUMED small roughness length; exposed on Surfaces).
  - **Diffusion seed** (default `0`) on Surfaces and Mix — one seed at start of each Render. Same params + seed ⇒ **bit-identical** IR. No unseeded `random()` in the audio path.
  - `D = 0` ⇒ `Δd = 0` ⇒ specular delays.
- Wall normal / last-hit: last bounce from folded path; fallback = image-index parity / crossed axes (`surfaces_hit_by_n`).
- Structure VERIFIED elsewhere: A–F 0|1 mask writers into image voices exist — this desk uses geometric hits until OCR voice↔tap map is locked.

### Polar 3D — **ASSUMED** (mic polar × frequency)
- Tab **Polar 3D**: L / C / R + **Sum** (default **Sum** — stereo pair story).
- **Plane** = mics + sound source (near-horizontal; **tilts** when source Y ≠ mic Y). Wire plane shown so tilt is visible. Prepare locks SY=MY; API accepts optional `sy` override.
- **In that plane**: polar angle around the chosen mic; **0° toward the source**; radius = pattern strength at that angle for the band.
- **Height of the mesh** = 1/3-octave frequency (stacked along plane normal):
  - Low bands (bottom) → round / omni
  - High bands (top) → cardioid / mic figure (Car↔Omni morphs; ASSUMED log-frequency crossfade ~125–4000 Hz)
- Not image-arrival directions. Cardioid algebra VERIFIED; freq morph ASSUMED.
- Orbit drag / scroll zoom. Refresh or auto on Render when Colour/Surfaces/Polar desk is open.

### Workflow
1. Edit a surface absorb/EQ/diffusion (and optional Diffusion seed / λ_ref).
2. **Render**.
3. Colour 1/3-octave updates; Polar 3D refreshes the mic-pattern×frequency solid (same 1/3-octave bands as Colour).

### API
- `POST /api/render` — includes `colour` + accepts `surfaces`, `diffusion_seed`, `lambda_ref` in `params_json`. Colour payload carries `levels_db` (active ref), `levels_db_peak`, `levels_db_1khz`, `levels_db_abs`, `ref_mode`, `ref_hz`.
- `POST /api/colour` — short wet-IR colour preview (same seed / jitter); optional `ref_mode`: `"peak"` | `"1khz"`.
- `GET /api/surfaces` — default ASSUMED cards + diffusion model note.
- `POST /api/polar` — L/C/R/sum radius grids + world `vertices` + `plane` (tilt); optional `sy` for source height; Car/Omni morphs HF.

### Smoke
```bash
.venv/bin/python test_smoke_colour_surfaces_polar.py
.venv/bin/python test_smoke_diffusion_jitter.py
```

## Mic setup presets (Listen panel) — **modern UI**

Canonical stereo techniques as a **Mic setup** dropdown next to Capsule space / Angle / Cardioid↔Omni.

| Id | Name | Space | Toe (half) | Pattern |
|----|------|-------|------------|---------|
| `ab_omni` | AB spaced pair (omni) | ~0.80 m | ±0° | Omni |
| `ab_card` | AB spaced pair (cardioid) | ~0.80 m | ±5° | Cardioid |
| `xy_90` | XY coincident 90° | ~0.01 m | ±45° (90° included) | Cardioid |
| `xy_120` | XY 120° | ~0.01 m | ±60° | Cardioid |
| `ortf` | ORTF (default) | ~0.17 m | ±55° (~110° included) | Cardioid |
| `nos` | NOS | ~0.30 m | ±45° | Cardioid |
| `din` | DIN | ~0.20 m | ±45° | Cardioid |
| `ms` | MS (Mid + Side + image) | ~0.05 m | ±0° | Cardioid; polar L+C+R |
| `mono_c` | Mono centre | 0 | ≈0° | Cardioid; C only |
| `custom` | Custom | — | no snap | — |

Hint: *“Snaps space, toe-in, and pattern — then tweak freely.”*  
Preset name stays until space / Angle / Car↔Omni drift → then label becomes **Custom**.

### Angle mapping (VERIFIED vs modern)

- **VERIFIED Reaktor:** `mlalr = diverg × 0.3 × (−0.25)` → only **±4.3°** at `diverg=1`. Too small for XY/ORTF.
- **Modern UI (ASSUMED extension):** `toe_half_deg` = angle of each L/R capsule from forward (+Z).  
  Mapped to absolute `mlalr/mralr` radians and wired through `prepare_direct_field` → `MicStand` → `render_pipeline` / polar / room look arrows.  
  Reaktor parity mic-X lock does **not** block toe/space presets.
- Listen **Angle** slider is in **degrees** (0–90 half-angle). Hidden `diverg` kept for approx / API compat.
- Omitting `toe_half_deg` in API still uses VERIFIED diverg formula (tests / parity).

### MS — **ASSUMED**

Engine has **no true figure-8 Side** yet. Preset story: **C = Mid cardioid**; L/R = narrow spaced / decode stand-in. Polar enables L+C+R. Documented as ASSUMED until fig-8 lands.

### Smoke

```bash
.venv/bin/python test_smoke_mic_presets.py
```

Selecting `ortf` → space≈0.17 m, toes≈±55°; polar/render accept `toe_half_deg`.
