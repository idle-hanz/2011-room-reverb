2011 Room Reverb — Tweak App
============================
Double-click:  Launch Tweak App.bat
Needs:         Python 3 (first run creates .venv)
Opens:         http://127.0.0.1:7860
Output:        renders\out.wav

What to do
----------
  1. Drag Source (gold) and Mic stand (blue) on the floor plan.
  2. Drag mic height on the side elevation.
  3. Upload a WAV, hit Render, listen in Preview.

Reaktor parity (Advanced): lock mic X to room centre (W/2). Off by default.

See UI_NOTES.md for what changed vs the old Reaktor / Gradio panel.
Engine: engine\  (early-field + FDN). Smoke: python test_smoke_drag_render.py
