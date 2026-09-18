# UI guide — 2011 Room Reverb Desktop tweak app

Maps every **current** FastAPI UI tab and control to engine meaning.
Source of truth for labels: `software/static/index.html`.

Tags: **VERIFIED** · **ASSUMED** · **PROPOSAL** · modern extension.

The app is **not** Gradio. Launch: `software/Launch Tweak App.bat` → http://127.0.0.1:7860.

---

## Stage view switcher

| Tab | What you see / do |
|-----|-------------------|
| **Floor · Side · 3D** | Floor (XZ) drag Src/Mic; Side heights; 3D orbit only |
| **Mic** | Zoomed stand + L/C/R polars + presets |
| **Lattice** | Image-source lattice |
| **Paths** | In-room paths ↔ last legs |
| **Colour** | 1/3-octave IR colour (**ASSUMED**) |
| **Surfaces** | A–F absorb / EQ / diffusion (**ASSUMED**) |
| **Polar 3D** | Pattern × frequency solid (**ASSUMED**) |

**Link heights**: when on, `sy` and `my` stay equal. Off by default.

## Room / Listen / Mix

| Control | Engine |
|---------|--------|
| W / H / L | Room metres |
| Mic setup | AB, XY, ORTF, NOS, DIN, MS (omni mid + inward cardioids), … |
| Space, stand X/Z, my/sy | Geometry |
| Pattern / yaw L·C·R | Per-capsule (**ASSUMED** pattern algebra; yaw is UI) |
| Hadamard N 8…128 | Images **and** FDN lines together; unscaled ±1; **no 1/√N** |
| Early / FDN / Dry / g | Mix bus |

## Structure locks

`c = 340`, `MCZ = L − MZ`. Optional Reaktor parity locks mic X to `W/2`.

See also `docs/HOW_IT_WORKS.md` and `docs/HOW_IT_WORKS_ILLUSTRATED.md`.
