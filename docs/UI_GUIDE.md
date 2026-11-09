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
| **Upload WAV** | Dry input for Play live and Render |
| **Play live** | Running preview in the browser. Dragging source or mic updates delays while it plays |
| **Save / Load** | Scene JSON |
| **Render** | Build the IR and write `software/renders/out.wav` |

Minimum IR length and “Also bake an IR when I drop Src / Mic” sit on **Preview**, not in this bar.

---

## Stage tabs

| Tab | What you see |
|-----|----------------|
| **Room** | Floor, 3D room, and Side. The button reads **Source**. Source hides those three views and keeps the source sliders beside Place and face. The button then reads **Room**. |
| **Mic** | Each mic is first: Left, Centre, and Right. Top and the combined pattern follow. There is no Open Polar panel. |
| **Mix** | Mic strips and Direct, FDN, Early. A capsule the setup does not use is dimmed and labelled off. The fader number stays. |
| **Space** | Lattice, Paths, and 1st–all. Shape stays on Room. The linked floor plan and side elevation sit under Hadamard size. |
| **Surfaces** | Room result, then the material row. ASSUMED tags stay. Absorb sliders and the room-colour analyser start folded. |
| **Polar** | One mic, All mics summed, At the speakers. The six extra plots start unticked. |

**Link heights** (Floor and Mic): when on, source height and mic height stay equal.

---

## Room sidebar

Width, Ceiling, and Length come first, with Studio, Club, and Hall beside them. The place line is one sentence. Shape, ratios, tilt, plan, and the treatment objects start inside one disclosure. Smooth and Movement stay out. Movement 0 reads **still tail**. The posted value stays 0.

Floor is titled **Floor**. Side is titled **Side**. The drag hints are on the title, not in the heading.

**+ Link track** stays disabled. Its title is one line: “Not in this build yet.”

---

## Listen

Mic setup, capsule space, stand, and the two heights. The Mic tab holds the pattern, yaw, and preset controls. A setup with no centre capsule shows the Centre strip off. The same paint covers any capsule the setup does not include.

---

## Mix desk

Stereo pair, M/S pair, and Independent. 2011 linear and Constant power. Physical ceiling, Rumble filter, and Off-axis tail keep those names. Two sources stays disabled until the WAV is stereo, and the title then reads **Load a stereo WAV**.

The 3D readout is one line: source and stand. Per-capsule distance, angle, height, level, and delay are on the hover.

---

## Preview

| Control | Meaning |
|---------|---------|
| **Minimum IR length** | `ir_length_ms`, 50–2000 ms, default 1500 |
| **Also bake an IR when I drop Src / Mic** | `live_drag_render`, off until ticked |
| One source / Two sources | File split. Two sources needs a stereo WAV |
| File name / player / status | Last render |

---

## Space sidebar

Hadamard size 8, 16, 32, 64, 128. The note stays: the matrix is unscaled ±1 Sylvester, and 64 and 128 are Render-only. Under that, the same floor plan and side elevation as Room, large enough to drag.

---

## Surfaces

The tab opens on Room result and the material row. The ASSUMED banner, the ASSUMED orientation tag, and the ASSUMED absorb and EQ labels stay. Absorb sliders start closed. The room-colour analyser starts closed. Air amount, climate, and ISO depth stay on the tab.

---

## Polar

One mic is the first page. Six extra plots (one mic at a band, response at an angle, readouts, compare, arrivals, balloon) start unticked. Nothing on that row is posted.

---

## Advanced / Structure locks

Shown on every tab. The 2011 snapshot and the colour-filter choice stay hidden until `?dev=1`. Lighter CPU (shared tail) is Play only.

---

## Original Reaktor panel (archive)

For Structure screenshot catalogs (Surfaces / Room Dimension / Sound Position / Microphone categories, GainF, Clip Diffusion, etc.) see [`panel-controls.md`](panel-controls.md). That document describes the **2011 ensemble panel**, not this Desktop app.
