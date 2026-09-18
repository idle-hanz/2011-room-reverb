# Quick start — 2011 Room Reverb Tweak App

## Needs (Windows)

- **Python 3** (python.org; add to PATH)
- First launch installs **numpy**, **fastapi**, **uvicorn**, **python-multipart** into `software/.venv`

## Steps

1. Unzip / clone this pack.
2. Open **`software`** (or use the pack-root **CLICK ME** shortcut).
3. Double-click **`Launch Tweak App.bat`**.
4. Browser → `http://127.0.0.1:7860` (first run may take a minute).
5. Drag **source** and **mics** on Floor / Side; use **Mic** tab for array presets (AB, XY, ORTF, NOS, DIN, MS, …).
6. Set room size, Hadamard N (8–128), Colour / Surfaces as needed.
7. Load a dry WAV → **Render** → listen in-page or open `software/renders/out.wav`.

## If the bat fails

```bat
cd software
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app_server.py
```

## More

- Illustrated theory: `docs/HOW_IT_WORKS_ILLUSTRATED.md` + `docs/diagrams/`
- Structure notes: `findings/`
