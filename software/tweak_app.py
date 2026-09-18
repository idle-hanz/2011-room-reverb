#!/usr/bin/env python3
"""
2011 Room Reverb — parameter tweak UI (Gradio).

Panel-aligned labels (Reaktor Controls tabs) + early-field / unscaled ±1 FDN.
Tags every control VERIFIED or ASSUMED. Does not invent A–F / Hadamard OCR.

Positioning UX (absolute metres + click-to-place):
  • Primary: Source X/Z, Mic Height MY, Mic stand MCZ in metres
  • Click room overview (Place Source | Place Mic stand)
  • Advanced accordion: panel SoX/SoZ/MZ (0–1 / Depth) synced both ways
  • Live readout under the map

Geometry plots update live (overview, close-up, side elevation).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import gradio as gr

from mic_display import (
    clamp,
    clamp_inside_room,
    format_position_readout,
    metres_from_prepare,
    overview_pixel_to_metres,
    prepare_from_metres,
    update_mic_plots,
)
from render_pipeline import (
    SPEED_OF_SOUND_M_S,
    default_out_path,
    load_wav_mono,
    render,
    write_wav_stereo,
)

# Re-export for label clarity (locked)
C_LOCKED = SPEED_OF_SOUND_M_S  # VERIFIED = 340

TAG = {
    "verified": "🟢 VERIFIED",
    "assumed": "🟡 ASSUMED",
    "locked": "🔒 LOCKED",
}


def _label(name: str, tag: str, extra: str = "") -> str:
    bit = TAG[tag]
    return f"{name}  [{bit}]{(' — ' + extra) if extra else ''}"


# Default room / Prepare (matches prior UI defaults)
_DEF_W, _DEF_H, _DEF_L = 6.0, 3.0, 8.0
_DEF_SOX, _DEF_SOZ = 0.5, 0.5
_DEF_MY, _DEF_MZ = 1.5, 6.5
_DEF_SX, _DEF_SZ, _DEF_MCZ = metres_from_prepare(
    _DEF_W, _DEF_L, _DEF_SOX, _DEF_SOZ, _DEF_MZ
)


def do_render(
    input_wav,
    W, H, L,
    sox, soz, my,
    mz, space, diverg, car_omni,
    early_wet, fdn_wet, dry_gain, fdn_g, ir_length_ms,
    path_on, path_preset, ellipse_rate, ellipse_rx, ellipse_rz,
    progress=gr.Progress(),
):
    if input_wav is None:
        return None, "Load an input WAV first.", ""
    src = input_wav if isinstance(input_wav, str) else getattr(input_wav, "name", None)
    if not src:
        return None, "Could not read uploaded file path.", ""

    progress(0.02, desc="Loading WAV…")
    dry, sr = load_wav_mono(src)

    def pcb(frac):
        progress(0.05 + 0.9 * float(frac), desc=f"Rendering… {100*frac:.0f}%")

    # MCZ = L − MZ is locked in engine; MZ panel Depth is what engine takes
    Lch, Rch, info = render(
        dry,
        sr,
        W=float(W),
        H=float(H),
        L=float(L),
        sox=float(sox),
        soz=float(soz),
        mz=float(mz),
        my=float(my),
        space=float(space),
        diverg=float(diverg),
        car_omni=float(car_omni),
        early_wet=float(early_wet),
        fdn_wet=float(fdn_wet),
        dry_gain=float(dry_gain),
        fdn_g=float(fdn_g),
        ir_length_ms=float(ir_length_ms),
        path_on=bool(path_on),
        path_preset=str(path_preset),
        ellipse_rate=float(ellipse_rate),
        ellipse_rx=float(ellipse_rx),
        ellipse_rz=float(ellipse_rz),
        progress_cb=pcb,
    )

    out = default_out_path()
    meta = write_wav_stereo(str(out), Lch, Rch, sr)
    progress(1.0, desc="Done")

    mcz = info.get("mcz")
    src_pos = info.get("source")
    mic = info.get("mic_centre")
    status = (
        f"Wrote {out}\n"
        f"mode={info.get('mode')}  duration={meta['duration_s']:.2f}s  sr={sr}\n"
        f"c={C_LOCKED} m/s 🔒  MCZ=L−MZ={mcz:.3f} m 🔒\n"
        f"source={src_pos}  mic_centre={mic}\n"
        f"peak_before_norm={info.get('peak_before_norm'):.4f}  "
        f"norm_scale={info.get('norm_scale'):.4f}"
    )
    preview = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    preview.close()
    shutil.copy2(out, preview.name)
    return preview.name, status, str(out)


def _plots_and_readout(W, H, L, sox, soz, my, mz, space, diverg, car_omni):
    ov, cu, rl, ov_meta = update_mic_plots(
        W, H, L, sox, soz, my, mz, space, diverg, car_omni
    )
    read = format_position_readout(
        float(W), float(H), float(L),
        mz=float(mz), my=float(my), space=float(space),
        diverg=float(diverg), sox=float(sox), soz=float(soz),
    )
    return ov, cu, rl, read, ov_meta


def sync_from_metres(W, H, L, sx, sz, my, mcz, space, diverg, car_omni):
    """Absolute metre sliders → SoX/SoZ/MZ + plots + readout (inside room only)."""
    W, H, L = float(W), float(H), float(L)
    sx, sz, my, mcz, space = clamp_inside_room(
        W, H, L, sx=sx, sz=sz, my=my, mcz=mcz, space=space
    )
    sox, soz, mz = prepare_from_metres(W, L, sx, sz, mcz)
    ov, cu, rl, read, ov_meta = _plots_and_readout(
        W, H, L, sox, soz, my, mz, space, diverg, car_omni
    )
    return (
        sx, sz, my, mcz, space,
        sox, soz, mz,
        ov, cu, rl, read, ov_meta,
    )


def sync_from_normalized(W, H, L, sox, soz, my, mz, space, diverg, car_omni):
    """Advanced SoX/SoZ/MZ → metre sliders + plots + readout (inside room only)."""
    W, H, L = float(W), float(H), float(L)
    sox, soz, mz = float(sox), float(soz), float(mz)
    sx, sz, mcz = metres_from_prepare(W, L, sox, soz, mz)
    sx, sz, my, mcz, space = clamp_inside_room(
        W, H, L, sx=sx, sz=sz, my=my, mcz=mcz, space=space
    )
    sox, soz, mz = prepare_from_metres(W, L, sx, sz, mcz)
    ov, cu, rl, read, ov_meta = _plots_and_readout(
        W, H, L, sox, soz, my, mz, space, diverg, car_omni
    )
    return (
        sx, sz, my, mcz, space,
        sox, soz, mz,
        ov, cu, rl, read, ov_meta,
    )


def sync_room_dims(W, H, L, sx, sz, my, mcz, space, diverg, car_omni):
    """Room W/H/L change → refresh maxima + keep source/mics inside the box."""
    W, H, L = float(W), float(H), float(L)
    sx, sz, my, mcz, space = clamp_inside_room(
        W, H, L, sx=sx, sz=sz, my=my, mcz=mcz, space=space
    )
    sox, soz, mz = prepare_from_metres(W, L, sx, sz, mcz)
    ov, cu, rl, read, ov_meta = _plots_and_readout(
        W, H, L, sox, soz, my, mz, space, diverg, car_omni
    )
    return (
        gr.update(maximum=W, value=sx),
        gr.update(maximum=L, value=sz),
        gr.update(maximum=H, value=my),
        gr.update(maximum=L, value=mcz),
        gr.update(maximum=max(W, 0.01), value=space),
        sox,
        soz,
        gr.update(maximum=max(L, 1.0), value=mz),
        ov, cu, rl, read, ov_meta,
    )


def on_overview_click(
    evt: gr.SelectData,
    place_mode,
    W, H, L,
    sx, sz, my, mcz,
    space, diverg, car_omni,
    ov_meta,
):
    """Click room overview → place Source (x,z) or Mic stand MCZ (x locked W/2)."""
    W, H, L = float(W), float(H), float(L)
    if evt is None or evt.index is None or not ov_meta:
        return sync_from_metres(W, H, L, sx, sz, my, mcz, space, diverg, car_omni)

    ix, iy = evt.index[0], evt.index[1]
    x_m, z_m = overview_pixel_to_metres(ix, iy, ov_meta)
    x_m = clamp(x_m, 0.0, W)
    z_m = clamp(z_m, 0.0, L)

    mode = (place_mode or "Place Source").strip()
    # Choices are "Place Source" / "Place Mic stand" — both start with "Place".
    # Exact match (or "Mic" in mode); never startswith("Mic") / startswith("Place").
    if mode == "Place Mic stand" or "Mic" in mode:
        # Mic centre X stays W/2 (Structure lock); click only sets MCZ from Z
        mcz = z_m
    else:
        sx, sz = x_m, z_m

    return sync_from_metres(W, H, L, sx, sz, my, mcz, space, diverg, car_omni)


def refresh_geo_only(W, H, L, sox, soz, my, mz, space, diverg, car_omni):
    """Space / Angle / CarOmni — clamp Space so L/R stay in-room, then refresh."""
    W, H, L = float(W), float(H), float(L)
    sx, sz, mcz = metres_from_prepare(W, L, sox, soz, mz)
    sx, sz, my, mcz, space = clamp_inside_room(
        W, H, L, sx=sx, sz=sz, my=my, mcz=mcz, space=space
    )
    sox, soz, mz = prepare_from_metres(W, L, sx, sz, mcz)
    ov, cu, rl, read, ov_meta = _plots_and_readout(
        W, H, L, sox, soz, my, mz, space, diverg, car_omni
    )
    return space, ov, cu, rl, read, ov_meta


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="2011 Room Reverb — Tweak App") as demo:
        gr.Markdown(
            """
# 2011 Room Reverb — Tweak App
Panel-aligned controls (Reaktor **Surfaces | Room Dimension | Sound Position | Microphone | Mix**).
Early-field image sources + unscaled ±1 Hadamard FDN (no A–F dictionary invented).

Tags: **🟢 VERIFIED** from Structure / ens · **🟡 ASSUMED** prototype / not-yet-wired · **🔒 LOCKED** algebra.

`c = 340` m/s and `MCZ = L − MZ` (panel **Depth**) are locked. **MCX = W/2** locked.

**Place source & mic in metres** (sliders) or **click the room overview**. Render → `software/renders/out.wav`.
"""
        )
        with gr.Row():
            input_wav = gr.Audio(
                label="Input WAV (mono or stereo → mid)",
                type="filepath",
                sources=["upload"],
            )
            output_wav = gr.Audio(label="Render preview", type="filepath")

        with gr.Tabs():
            # --- Surfaces (placeholders; Structure A–F masks only) ---
            with gr.Tab("Surfaces"):
                gr.Markdown(
                    """
### Surfaces 🟢 VERIFIED panel labels (394)
**Not wired — Structure A–F masks only.** No invented A–F EQ / Hadamard surface dictionary.
Placeholders mirror panel columns Sides / Ahead / Behind / Floor / Ceiling.
"""
                )
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("**-Sides-**")
                        gr.Slider(20, 8000, value=100, step=1, label=_label("Freq", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 1.0, value=0.2, step=0.004, label=_label("BW", "assumed", "not wired"), interactive=False)
                        gr.Slider(-24, 24, value=0, step=0.1, label=_label("dB", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 1.0, value=0.16, step=0.01, label=_label("Diffusion", "assumed", "not wired"), interactive=False)
                    with gr.Column():
                        gr.Markdown("**-Ahead-**")
                        gr.Slider(20, 8000, value=438, step=1, label=_label("Freq", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 0.4, value=0.2, step=0.004, label=_label("BW", "verified", "Structure 0…0.4 def 0.2 — not wired"), interactive=False)
                        gr.Slider(-24, 24, value=0, step=0.1, label=_label("dB", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 1.0, value=0.25, step=0.01, label=_label("Diffusion", "assumed", "not wired"), interactive=False)
                    with gr.Column():
                        gr.Markdown("**-Behind-**")
                        gr.Slider(20, 8000, value=1567, step=1, label=_label("Freq", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 1.0, value=0.2, step=0.004, label=_label("BW", "assumed", "not wired"), interactive=False)
                        gr.Slider(-24, 24, value=0, step=0.1, label=_label("dB", "assumed", "not wired"), interactive=False)
                        gr.Slider(0.0, 1.0, value=0.33, step=0.01, label=_label("Diffusion", "assumed", "not wired"), interactive=False)
                    with gr.Column():
                        gr.Markdown("**-Floor-** / **-Ceiling-** (High+Low style)")
                        gr.Slider(20, 8000, value=517.8, step=0.1, label=_label("Floor High", "assumed", "not wired"), interactive=False)
                        gr.Slider(20, 8000, value=180, step=1, label=_label("Floor Low", "assumed", "not wired"), interactive=False)
                        gr.Slider(20, 8000, value=2400.8, step=0.1, label=_label("Ceiling High", "assumed", "not wired"), interactive=False)
                        gr.Slider(20, 8000, value=1145, step=1, label=_label("Ceiling Low", "assumed", "not wired"), interactive=False)
                with gr.Row():
                    diffusion_master = gr.Slider(
                        -1.0, 1.0, value=-0.5, step=0.01,
                        label=_label("Diffusion Master", "assumed", "panel VERIFIED name; not-yet-wired → MDiff"),
                        interactive=False,
                    )
                    humidity = gr.Slider(
                        0.0, 1.0, value=0.5, step=0.01,
                        label=_label("Humidity", "assumed", "panel VERIFIED name; DSP law UNKNOWN / not wired"),
                        interactive=False,
                    )
                gr.Markdown("*Stacked Macro Front/Sides/Rear/Floor/Ceiling/All — ASSUMED stubs (Structure On/Off gates) — not wired.*")

            # --- Room Dimension ---
            with gr.Tab("Room Dimension"):
                gr.Markdown(
                    f"""
### Room Dimension 🟢 VERIFIED panel labels (395)
**Width X** · **Ceiling Y** · **Lenth Z** (panel typo kept).
**c = {C_LOCKED} m/s** [{TAG['locked']} · VERIFIED Distances Const]

Changing W / H / L refreshes Source X/Z, Mic Height, and Mic stand Z slider maxima.
"""
                )
                with gr.Row():
                    W = gr.Slider(
                        1.0, 100.0, value=_DEF_W, step=0.1,
                        label=_label("Width X", "verified", "room width W (m ASSUMED)"),
                    )
                    H = gr.Slider(
                        1.0, 100.0, value=_DEF_H, step=0.1,
                        label=_label("Ceiling Y", "verified", "room height H"),
                    )
                    L = gr.Slider(
                        2.0, 100.0, value=_DEF_L, step=0.5,
                        label=_label("Lenth Z", "verified", "room length L — panel typo; Structure Min2 Max100 Def51 Step0.5"),
                    )

            # --- Sound Position ---
            with gr.Tab("Sound Position"):
                gr.Markdown(
                    """
### Sound Position — absolute metres (primary)
**Source X** / **Source Z** in metres map to Prepare **SX = W×SoX**, **SZ = MCZ+(L−MCZ)×SoZ**.
Or click the room overview with **Place Source**. SY follows mic **Height** (MY).
"""
                )
                with gr.Row():
                    sx = gr.Slider(
                        0.0, _DEF_W, value=_DEF_SX, step=0.01,
                        label=_label("Source X", "verified", "metres; SX = W×SoX"),
                    )
                    sz = gr.Slider(
                        0.0, _DEF_L, value=_DEF_SZ, step=0.01,
                        label=_label("Source Z", "verified", "metres; SZ = MCZ+(L−MCZ)×SoZ"),
                    )
                with gr.Accordion("Advanced — normalized SoX / SoZ (panel 0–1)", open=False):
                    gr.Markdown(
                        "Panel Mouse Area pad. Synced both ways with metre sliders. "
                        "SoZ∈[0,1] ⇒ SZ∈[MCZ, L]; values outside come from Source Z beyond that span."
                    )
                    with gr.Row():
                        sox = gr.Slider(
                            0.0, 1.0, value=_DEF_SOX, step=0.01,
                            label=_label("SoX (Mouse Area X)", "verified", "SX = W×SoX"),
                        )
                        soz = gr.Slider(
                            -1.0, 2.0, value=_DEF_SOZ, step=0.01,
                            label=_label("SoZ (Mouse Area Y→Z)", "verified", "SZ = MCZ+(L−MCZ)×SoZ; panel typically 0–1"),
                        )

            # --- Microphone ---
            with gr.Tab("Microphone"):
                gr.Markdown(
                    """
### Microphone 🟢 VERIFIED panel labels (399)
**Mic stand Z** is **MCZ** (metres from Width wall / Z=0). Engine gets **MZ = L − MCZ**.
**MCX = W/2** locked — click-to-place only moves stand along Z. Angles: `Diverg×0.3×±0.25`.
"""
                )
                with gr.Row():
                    with gr.Column():
                        mic_response = gr.Slider(
                            20.0, 20000.0, value=10000.0, step=1.0,
                            label=_label("Mic Response", "assumed", "panel VERIFIED; HF/Res LIKELY Hz — not-yet-wired"),
                            interactive=False,
                        )
                        diverg = gr.Slider(
                            0.0, 2.0, value=1.0, step=0.01,
                            label=_label("Angle", "verified", "panel Mic Angle; Structure Diverg×0.3×±0.25 → ML/MRALR"),
                        )
                        my = gr.Slider(
                            0.0, _DEF_H, value=_DEF_MY, step=0.05,
                            label=_label("Mic Height MY", "verified", "metres 0…H; SY = MY"),
                        )
                    with gr.Column():
                        mcz = gr.Slider(
                            0.0, _DEF_L, value=_DEF_MCZ, step=0.05,
                            label=_label("Mic stand Z (MCZ)", "verified", "metres from Z=0 / Width wall; MZ=L−MCZ for engine"),
                        )
                        car_omni = gr.Slider(
                            0.0, 1.0, value=1.0, step=0.01,
                            label=_label("Car/Omni", "assumed", "0=omni … 1=cardioid lerp; panel VERIFIED name"),
                        )
                        space = gr.Slider(
                            0.0, _DEF_W, value=0.25, step=0.01,
                            label=_label("Space", "verified", "L–R separation; clamped so mics stay inside Width"),
                        )
                with gr.Accordion("Advanced — panel Depth MZ (normalized path)", open=False):
                    mz = gr.Slider(
                        0.0, max(_DEF_L, 20.0), value=_DEF_MZ, step=0.05,
                        label=_label("Depth (MZ)", "verified", "panel Depth; MCZ=L−MZ locked in engine"),
                    )

            # --- Mix (shared strip + prototype wet) ---
            with gr.Tab("Mix"):
                gr.Markdown(
                    """
### Mix / shared bottom strip 🟢 VERIFIED panel names
**GainF** · **AGC** · **Volume trim** (+ prototype Early/FDN wet — ASSUMED).
GainF / AGC / Volume trim are **ASSUMED stubs** until wired into the render path (panel names VERIFIED).
"""
                )
                with gr.Row():
                    gain_f = gr.Slider(
                        0.0, 1.0, value=1.0, step=0.01,
                        label=_label("GainF", "assumed", "panel VERIFIED name; FDN/feedback factor — not-yet-wired"),
                        interactive=False,
                    )
                    agc_on = gr.Checkbox(
                        value=True,
                        label=_label("AGC On", "assumed", "panel VERIFIED UI; law UNKNOWN — not-yet-wired"),
                        interactive=False,
                    )
                    agc_db = gr.Slider(
                        -20.0, 20.0, value=0.0, step=0.1,
                        label=_label("AGC dB", "assumed", "panel ±20 — not-yet-wired"),
                        interactive=False,
                    )
                    volume_trim = gr.Slider(
                        0.0, 1.0, value=0.93, step=0.01,
                        label=_label("Volume trim", "assumed", "panel VERIFIED name — not-yet-wired"),
                        interactive=False,
                    )
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Prototype wet (ASSUMED — in render path)")
                        early_wet = gr.Slider(0.0, 2.0, value=1.0, step=0.01, label=_label("Early wet", "assumed"))
                        fdn_wet = gr.Slider(0.0, 1.0, value=0.12, step=0.01, label=_label("FDN wet", "assumed"))
                        dry_gain = gr.Slider(0.0, 1.0, value=0.10, step=0.01, label=_label("Dry", "assumed"))
                        fdn_g = gr.Slider(0.0, 1.0, value=0.08, step=0.005, label=_label("FDN g", "assumed", "loop gain 0…1, no 1/√N"))
                        ir_length_ms = gr.Slider(50.0, 2000.0, value=400.0, step=10.0, label=_label("IR length (ms)", "assumed", "FDN IR; early capped ~90 ms"))
                    with gr.Column():
                        gr.Markdown("#### Motion (path shapes ASSUMED)")
                        path_on = gr.Checkbox(value=False, label=_label("Path on", "assumed", "block/OLA like moving_room_demo"))
                        path_preset = gr.Radio(
                            choices=["still", "ellipse", "perimeter"],
                            value="ellipse",
                            label=_label("Path preset", "assumed"),
                        )
                        ellipse_rate = gr.Slider(0.25, 4.0, value=1.0, step=0.05, label=_label("Ellipse rate (loops/clip)", "assumed"))
                        ellipse_rx = gr.Slider(0.0, 0.48, value=0.42, step=0.01, label=_label("Ellipse radius SoX", "assumed"))
                        ellipse_rz = gr.Slider(0.0, 0.48, value=0.35, step=0.01, label=_label("Ellipse radius SoZ", "assumed"))

        gr.Markdown("### Room map — click to place 🟢 VERIFIED Prepare geometry (live)")
        place_mode = gr.Radio(
            choices=["Place Source", "Place Mic stand"],
            value="Place Source",
            label="Click target on room overview",
            info="Mic stand: Z from click, X locked to room centre",
        )
        with gr.Row():
            room_plot = gr.Image(
                label="Room overview (top-down XZ) — click to place · dashed MCX=W/2 · S / C / L / R",
                type="numpy",
                interactive=False,
            )
            closeup_plot = gr.Image(
                label="Mic stand close-up — Space, Angle toe-in°, |S−mic|, Height / MCZ",
                type="numpy",
                interactive=False,
            )
            side_plot = gr.Image(
                label="Side view (height) — easy read · floor / ceiling / mic height / source",
                type="numpy",
                interactive=False,
            )
        position_readout = gr.Textbox(
            label="Position readout",
            lines=2,
            interactive=False,
        )

        render_btn = gr.Button("Render → software/renders/out.wav", variant="primary")
        status = gr.Textbox(label="Status", lines=6)
        out_path = gr.Textbox(label="Output path", interactive=False)

        gr.Markdown(
            """
### Locked algebra (cannot invent here)
| Item | Tag |
|------|-----|
| Mirror leaves `2W−X`, `2W+X`, `−X`, Y/Z family, `4L−Z` | VERIFIED |
| `MCZ = L − MZ` (panel **Depth**), `MCX = W×0.5` | VERIFIED / LOCKED |
| Angles `Diverg×0.3×±0.25` (panel **Angle**) | VERIFIED |
| `c = 340`, delay `(d/340)×1000`, geometric `1/r` | VERIFIED |
| Unscaled ±1 Hadamard, **no** `1/√N` | from-them / lock |
| A–F surface dictionary / full Hadamard OCR table | **not invented** |
"""
        )

        # Silence unused stub refs for linters / future wiring
        _ = (diffusion_master, humidity, mic_response, gain_f, agc_on, agc_db, volume_trim)

        overview_meta = gr.State({})

        metre_ctrls = [sx, sz, my, mcz]
        norm_ctrls = [sox, soz, mz]
        room_ctrls = [W, H, L]
        angle_ctrls = [space, diverg, car_omni]

        sync_out = [
            sx, sz, my, mcz, space, sox, soz, mz,
            room_plot, closeup_plot, side_plot, position_readout, overview_meta,
        ]
        # Space first so it snaps back if L/R would leave the room
        plot_out = [space, room_plot, closeup_plot, side_plot, position_readout, overview_meta]

        # Initial load from metre defaults (via sox/soz/mz derived)
        demo.load(
            fn=sync_from_metres,
            inputs=[W, H, L, sx, sz, my, mcz, space, diverg, car_omni],
            outputs=sync_out,
        )

        # Metre sliders → normalize + plots
        for ctrl in metre_ctrls:
            ctrl.change(
                fn=sync_from_metres,
                inputs=[W, H, L, sx, sz, my, mcz, space, diverg, car_omni],
                outputs=sync_out,
            )

        # Advanced normalized → metres + plots
        for ctrl in norm_ctrls:
            ctrl.change(
                fn=sync_from_normalized,
                inputs=[W, H, L, sox, soz, my, mz, space, diverg, car_omni],
                outputs=sync_out,
            )

        # Room dims → maxima + clamp metres
        for ctrl in room_ctrls:
            ctrl.change(
                fn=sync_room_dims,
                inputs=[W, H, L, sx, sz, my, mcz, space, diverg, car_omni],
                outputs=sync_out,
            )

        # Space / Angle / CarOmni — plots only (positions via current sox/soz/mz)
        for ctrl in angle_ctrls:
            ctrl.change(
                fn=refresh_geo_only,
                inputs=[W, H, L, sox, soz, my, mz, space, diverg, car_omni],
                outputs=plot_out,
            )

        # Click-to-place on overview (pixel→metre via stored axes bbox meta)
        room_plot.select(
            fn=on_overview_click,
            inputs=[
                place_mode, W, H, L, sx, sz, my, mcz,
                space, diverg, car_omni, overview_meta,
            ],
            outputs=sync_out,
        )

        render_btn.click(
            fn=do_render,
            inputs=[
                input_wav,
                W, H, L,
                sox, soz, my,
                mz, space, diverg, car_omni,
                early_wet, fdn_wet, dry_gain, fdn_g, ir_length_ms,
                path_on, path_preset, ellipse_rate, ellipse_rx, ellipse_rz,
            ],
            outputs=[output_wav, status, out_path],
        )
    return demo


def main():
    demo = build_ui()
    demo.queue().launch(
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True,
        show_error=True,
    )


if __name__ == "__main__":
    main()
