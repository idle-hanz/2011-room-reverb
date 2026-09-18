# 2011 Room Reverb

Rebuild of Idle Hanz’s 2011 Reaktor room reverb: **image-source early field** + **unscaled Hadamard FDN** tail, mic array model, and a local Desktop tweak app.

This is a **working rebuild / research pack**, not a finished commercial plugin. Docs mark **VERIFIED** (from the original Structure) vs **ASSUMED**.

Live page: [idlehanz.com/tools/room-reverb](https://idlehanz.com/tools/room-reverb/)

## Quick start (Windows)

1. Install **Python 3** (tick “Add to PATH”).
2. Open `software/` and double-click **`Launch Tweak App.bat`** (or the pack-root **`CLICK ME - Open Tweak App.bat`**).
3. First run creates `software/.venv` and installs `requirements.txt` (numpy, FastAPI, uvicorn).
4. Browser opens at **http://127.0.0.1:7860**.
5. Place source / mics on Floor / Side / Mic desk, set Colour / Surfaces / Hadamard size, load a dry WAV, **Render** → `software/renders/out.wav`.

Linux/macOS: `cd software && bash launch_tweak_app.sh`

## Layout

| Path | What |
|------|------|
| `software/` | FastAPI tweak app + engine + static UI |
| `software/static/` | Floor / Side / 3D / Mic / Lattice / Paths / Colour / Surfaces / Polar |
| `software/engine/` | Early field + Hadamard FDN |
| `docs/` | QUICKSTART, HOW_IT_WORKS (+ illustrated + PDF), diagrams |
| `findings/` | Structure mining notes from the 2011 ensemble |
| `ensemble/` | Original Reaktor `.ens` (optional reference) |
| `demos/` | Small reference assets (large WAVs not in this repo) |

## Locked / design notes

- Keep the **unscaled Hadamard FDN** character; early images excite the FDN.
- Speed of sound **c = 340**; mic centre Z **MCZ = L − MZ** (Structure-locked).
- Intended Studio One use: linked track-FX instances as sources in one shared room (editor outside the plugins).

## Licence / credit

© Idle Hanz. Built from the 2011 Reaktor ensemble (Puckette / Hadamard-style FDN character preserved). Contact via [idlehanz.com](https://idlehanz.com).
