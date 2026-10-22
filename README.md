# 2011 Room Reverb

Rebuild of Idle Hanz’s 2011 Reaktor room reverb: **image-source early field** + **unscaled Hadamard FDN**, mic-array model, and a local **FastAPI** Desktop tweak app.

Live page: [idlehanz.com/tools/room-reverb](https://idlehanz.com/tools/room-reverb/)

## Quick start (Windows)

1. Install **Python 3** (Add to PATH).  
2. Open `software/` → double-click **`Launch Tweak App.bat`**.  
3. Browser → **http://127.0.0.1:7860**.  
4. Place source / mics (Floor · Side · Mic desk), set Hadamard N, load a dry WAV → **Play live** (drag while it plays) and/or **Render** → `software/renders/out.wav`.

Details: [`docs/QUICKSTART.md`](docs/QUICKSTART.md)

## Docs (updated edition)

| Doc | Contents |
|-----|----------|
| [`docs/HOW_IT_WORKS_ILLUSTRATED.md`](docs/HOW_IT_WORKS_ILLUSTRATED.md) | Illustrated theory + **12 diagrams** (Mic desk, Lattice/Paths, Colour, Polar, track-FX, …) |
| [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md) | Text twin |
| [`docs/UI_GUIDE.md`](docs/UI_GUIDE.md) | Every tab / knob → engine meaning |
| [`docs/diagrams/`](docs/diagrams/) | PNG figures |

## Layout

| Path | What |
|------|------|
| `software/` | FastAPI app, static UI, engine |
| `HANDOVER.md` | **Start here** for a new agent chat |
| `docs/` | Guides + diagrams |
| `findings/` | Structure mining notes |
| `ensemble/` | Original `.ens` (reference) |

## Locks

- `c = 340`, `MCZ = L − MZ`  
- Unscaled ±1 Hadamard FDN (**no `1/√N`**)  
- Image times **are** Diffuser Delay; Hadamard only mixes and feeds back  

Agent sessions: read **`HANDOVER.md`** first. UI and docs mark **VERIFIED** vs **ASSUMED**. Panel names: B Ahead · D Behind · E Floor · F Ceiling · A+C Sides (Left/Right split ASSUMED). FDN uses Sylvester, not OCR Hadamard rows.

Next session: read [`HANDOVER.md`](HANDOVER.md).

© Idle Hanz
