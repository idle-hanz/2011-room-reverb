# Quick start — 2011 Room Reverb Tweak App

## What you need (Windows)

- **Python 3** from python.org (tick “Add to PATH”)
- First launch creates `software/.venv` and installs **numpy**, **fastapi**, **uvicorn**, **python-multipart**

## Launch

1. Open the pack folder → go into **`software`** (or double-click the pack-root **CLICK ME** shortcut).
2. Double-click **`Launch Tweak App.bat`**.
3. Browser opens at **http://127.0.0.1:7860** (first run may take a minute).

Linux / macOS: `cd software && bash launch_tweak_app.sh`

## First useful session

1. **Floor** — drag the gold **Src** handle and the blue **Mic** stand. Empty clicks pick the nearest handle.
2. **Side** — drag **Src H** and **Mic H** separately (source height `sy` is independent of mic height `my`). Optional **Link heights** if you want them tied.
3. **Mic** — zoomed desk: top / side / 3D of the array, plus **L / C / R** polar plots. Use **Mic setup** (AB, XY, ORTF, NOS, DIN, MS, …) or set pattern + yaw under each polar.
4. Set room **W / H / L**, **Hadamard size** (8–128; default 32 — scales image count and FDN lines together).
5. Load a dry WAV → **Render** → listen in-page or open `software/renders/out.wav`.

## Tab map

| Tab | What you do |
|-----|-------------|
| Floor · Side · 3D | Place source & mics; 3D is **orbit only** (no dragging objects) |
| Mic | Close-up stand + L/C/R polars + presets |
| Lattice | Image-source lattice in 3D |
| Paths | In-room folded paths ↔ last legs (toggle) |
| Colour | 1/3-octave colour of the IR (**ASSUMED** surface colouring) |
| Surfaces | A–F absorb / EQ / diffusion cards (**ASSUMED**) |
| Polar 3D | Mic pattern × frequency solid in the mic–source plane (**ASSUMED**) |

## If the bat fails

```bat
cd software
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app_server.py
```

## Read next

- Illustrated theory: `docs/HOW_IT_WORKS_ILLUSTRATED.md`
- Text twin: `docs/HOW_IT_WORKS.md`
- UI ↔ engine map: `docs/UI_GUIDE.md`
