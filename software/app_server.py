#!/usr/bin/env python3
"""2011 Room Reverb — modern tweak app (FastAPI + drag room editor)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from image_geometry import build_images_payload
from mic_display import (
    clamp_inside_room,
    format_position_readout,
    geometry,
    prepare_from_metres,
)
from render_pipeline import (
    SPEED_OF_SOUND_M_S,
    default_out_path,
    load_wav_mono,
    render,
    write_wav_stereo,
)

from polar_field import compute_polar_field
from surface_colour import (
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    parse_diffusion_seed,
    parse_lambda_ref,
    parse_surfaces,
    surfaces_payload,
    third_octave_levels,
)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="2011 Room Reverb", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

DEFAULTS = {
    "W": 6.0,
    "H": 3.0,
    "L": 8.0,
    "sx": 3.0,
    "sz": 4.75,
    "mcx": 3.0,
    "mcz": 1.5,
    "my": 1.5,
    "sy": 1.5,
    "link_heights": False,
    "space": 0.25,
    "diverg": 1.0,
    "car_omni": 1.0,
    "pattern_l": "cardioid",
    "pattern_c": "cardioid",
    "pattern_r": "cardioid",
    "yaw_l_deg": None,
    "yaw_c_deg": 0.0,
    "yaw_r_deg": None,
    "early_wet": 1.0,
    "fdn_wet": 0.12,
    "dry_gain": 0.10,
    "fdn_g": 0.08,
    "ir_length_ms": 400.0,
    "reaktor_parity": False,
    "path_on": False,
    "path_preset": "still",
    "ellipse_rate": 1.0,
    "ellipse_rx": 0.42,
    "ellipse_rz": 0.35,
    "hadamard_n": 32,
    "diffusion_seed": DEFAULT_DIFFUSION_SEED,
    "lambda_ref": DEFAULT_LAMBDA_REF_M,
}


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _b(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "yes", "on")
    return bool(v) if v is not None else default


def _optional_toe(body: dict):
    """Optional absolute half-angle (degrees). None → VERIFIED diverg formula."""
    if "toe_half_deg" not in body or body.get("toe_half_deg") is None:
        return None
    raw = body.get("toe_half_deg")
    if isinstance(raw, str) and raw.strip().lower() in ("", "null", "none"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _optional_float(body: dict, key: str, default=None):
    if key not in body or body.get(key) is None:
        return default
    raw = body.get(key)
    if isinstance(raw, str) and raw.strip().lower() in ("", "null", "none"):
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _optional_pattern(body: dict, key: str, default: str = "cardioid") -> str:
    raw = body.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return default
    p = str(raw).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    if p in ("omni", "o", "0"):
        return "omni"
    if p in ("fig8", "figure8", "bidirectional", "bi", "side"):
        return "fig8"
    return "cardioid"


def _capsule_from_body(body: dict) -> dict:
    """Per-capsule pattern + yaw. Prefer explicit yaw_*; else derive from toe_half."""
    toe = _optional_toe(body)
    yaw_l = _optional_float(body, "yaw_l_deg", None)
    yaw_c = _optional_float(body, "yaw_c_deg", 0.0)
    yaw_r = _optional_float(body, "yaw_r_deg", None)
    if yaw_l is None and yaw_r is None and toe is not None:
        yaw_l = -float(toe)
        yaw_r = float(toe)
    # If still None, leave None so prepare uses diverg
    pl = _optional_pattern(body, "pattern_l", DEFAULTS["pattern_l"])
    pc = _optional_pattern(body, "pattern_c", DEFAULTS["pattern_c"])
    pr = _optional_pattern(body, "pattern_r", DEFAULTS["pattern_r"])
    has_pat = any(k in body for k in ("pattern_l", "pattern_c", "pattern_r"))
    car = _f(body.get("car_omni"), DEFAULTS["car_omni"])
    if has_pat:
        # Legacy scalar from L/R patterns (API / old polar morph compat)
        lo = 0.0 if pl == "omni" else 1.0
        ro = 0.0 if pr == "omni" else 1.0
        car = 0.5 * (lo + ro)
    return {
        "pattern_l": pl,
        "pattern_c": pc,
        "pattern_r": pr,
        "yaw_l_deg": yaw_l,
        "yaw_c_deg": yaw_c if yaw_c is not None else 0.0,
        "yaw_r_deg": yaw_r,
        "car_omni": car,
        "toe_half_deg": toe,
    }




def _hadamard_n(body: dict) -> int:
    """Accept hadamard_n or grid; default 32. Powers of 2 only."""
    allowed = (8, 16, 32, 64, 128)
    raw = body.get("hadamard_n", None)
    if raw is None and body.get("grid") is not None:
        g = str(body.get("grid")).strip().lower()
        aliases = {"8": 8, "16": 16, "32": 32, "64": 64, "64like": 64, "128": 128}
        if g in aliases:
            return aliases[g]
    try:
        n = int(float(raw)) if raw is not None else 32
    except (TypeError, ValueError):
        n = 32
    if n not in allowed:
        # snap to nearest allowed power of 2 in the set
        n = min(allowed, key=lambda a: abs(a - n))
    return n

def params_from_body(body: dict) -> dict:
    W = _f(body.get("W"), DEFAULTS["W"])
    H = _f(body.get("H"), DEFAULTS["H"])
    L = _f(body.get("L"), DEFAULTS["L"])
    parity = _b(body.get("reaktor_parity"), False)
    sy_arg = None
    if "sy" in body and body.get("sy") is not None:
        raw_sy = body.get("sy")
        if not (isinstance(raw_sy, str) and raw_sy.strip().lower() in ("", "null", "none")):
            try:
                sy_arg = float(raw_sy)
            except (TypeError, ValueError):
                sy_arg = None
    sx, sz, my, mcz, space, mcx, sy = clamp_inside_room(
        W, H, L,
        sx=_f(body.get("sx"), DEFAULTS["sx"]),
        sz=_f(body.get("sz"), DEFAULTS["sz"]),
        my=_f(body.get("my"), DEFAULTS["my"]),
        mcz=_f(body.get("mcz"), DEFAULTS["mcz"]),
        space=_f(body.get("space"), DEFAULTS["space"]),
        mcx=_f(body.get("mcx"), W * 0.5),
        reaktor_parity=parity,
        sy=sy_arg,
    )
    sox, soz, mz = prepare_from_metres(W, L, sx, sz, mcz)
    cap = _capsule_from_body(body)
    return {
        "W": W, "H": H, "L": L,
        "sx": sx, "sz": sz, "my": my, "sy": sy,
        "mcx": mcx, "mcz": mcz, "space": space,
        "sox": sox, "soz": soz, "mz": mz,
        "diverg": _f(body.get("diverg"), DEFAULTS["diverg"]),
        "toe_half_deg": cap["toe_half_deg"],
        "car_omni": cap["car_omni"],
        "pattern_l": cap["pattern_l"],
        "pattern_c": cap["pattern_c"],
        "pattern_r": cap["pattern_r"],
        "yaw_l_deg": cap["yaw_l_deg"],
        "yaw_c_deg": cap["yaw_c_deg"],
        "yaw_r_deg": cap["yaw_r_deg"],
        "early_wet": _f(body.get("early_wet"), DEFAULTS["early_wet"]),
        "fdn_wet": _f(body.get("fdn_wet"), DEFAULTS["fdn_wet"]),
        "dry_gain": _f(body.get("dry_gain"), DEFAULTS["dry_gain"]),
        "fdn_g": _f(body.get("fdn_g"), DEFAULTS["fdn_g"]),
        "ir_length_ms": _f(body.get("ir_length_ms"), DEFAULTS["ir_length_ms"]),
        "reaktor_parity": parity,
        "path_on": _b(body.get("path_on"), False),
        "path_preset": str(body.get("path_preset") or "still"),
        "ellipse_rate": _f(body.get("ellipse_rate"), 1.0),
        "ellipse_rx": _f(body.get("ellipse_rx"), 0.42),
        "ellipse_rz": _f(body.get("ellipse_rz"), 0.35),
        "hadamard_n": _hadamard_n(body),
        "surfaces": parse_surfaces(body.get("surfaces")),
        "diffusion_seed": parse_diffusion_seed(body.get("diffusion_seed"), DEFAULT_DIFFUSION_SEED),
        "lambda_ref": parse_lambda_ref(body.get("lambda_ref"), DEFAULT_LAMBDA_REF_M),
    }


def geometry_payload(p: dict) -> dict:
    g = geometry(
        p["W"], p["H"], p["L"],
        mz=p["mz"], my=p["my"], space=p["space"],
        diverg=p["diverg"], sox=p["sox"], soz=p["soz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        yaw_c_deg=p.get("yaw_c_deg"),
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"),
        pattern_r=p.get("pattern_r"),
        sy=p.get("sy"),
    )
    prep = g["prep"]
    S, C = prep.source, prep.mic_centre
    Lm, Rm = prep.mic_left, prep.mic_right
    readout = format_position_readout(
        p["W"], p["H"], p["L"],
        mz=p["mz"], my=p["my"], space=p["space"],
        diverg=p["diverg"], sox=p["sox"], soz=p["soz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        sy=p.get("sy"),
    )
    return {
        "params": {
            "W": p["W"], "H": p["H"], "L": p["L"],
            "sx": p["sx"], "sz": p["sz"], "my": p["my"], "sy": p.get("sy", p["my"]),
            "mcx": p["mcx"], "mcz": p["mcz"], "space": p["space"],
            "sox": p["sox"], "soz": p["soz"], "mz": p["mz"],
            "diverg": p["diverg"], "car_omni": p["car_omni"],
            "toe_half_deg": p.get("toe_half_deg"),
            "pattern_l": p.get("pattern_l"),
            "pattern_c": p.get("pattern_c"),
            "pattern_r": p.get("pattern_r"),
            "yaw_l_deg": p.get("yaw_l_deg"),
            "yaw_c_deg": p.get("yaw_c_deg"),
            "yaw_r_deg": p.get("yaw_r_deg"),
            "reaktor_parity": p["reaktor_parity"],
            "hadamard_n": p.get("hadamard_n", 32),
            "diffusion_seed": p.get("diffusion_seed", DEFAULT_DIFFUSION_SEED),
            "lambda_ref": p.get("lambda_ref", DEFAULT_LAMBDA_REF_M),
            "max_space": 2.0 * min(p["mcx"], p["W"] - p["mcx"]),
        },
        "source": {"x": S[0], "y": S[1], "z": S[2]},
        "mic_centre": {"x": C[0], "y": C[1], "z": C[2]},
        "mic_left": {"x": Lm[0], "y": Lm[1], "z": Lm[2]},
        "mic_right": {"x": Rm[0], "y": Rm[1], "z": Rm[2]},
        "look_l": {"x": g["look_l"][0], "z": g["look_l"][1]},
        "look_r": {"x": g["look_r"][0], "z": g["look_r"][1]},
        "toe_l_deg": g["toe_l_deg"],
        "toe_r_deg": g["toe_r_deg"],
        "distances": {"sl": g["d_sl"], "sc": g["d_sc"], "sr": g["d_sr"]},
        "readout": readout,
        "c": SPEED_OF_SOUND_M_S,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/defaults")
def api_defaults():
    p = params_from_body(dict(DEFAULTS))
    return {"defaults": DEFAULTS, "geometry": geometry_payload(p)}


@app.post("/api/geometry")
async def api_geometry(body: dict):
    return geometry_payload(params_from_body(body))



@app.post("/api/images")
async def api_images(body: dict):
    """Early-field image lattice + folded paths + last legs for selected mics."""
    p = params_from_body(body)
    raw_mics = body.get("mics") or body.get("selected_mics") or ["C"]
    if isinstance(raw_mics, str):
        raw_mics = [m.strip() for m in raw_mics.split(",") if m.strip()]
    mics = [str(m).upper() for m in raw_mics]
    # Accept "all"
    if len(mics) == 1 and mics[0] == "ALL":
        mics = ["L", "C", "R"]
    payload = build_images_payload(
        W=p["W"], H=p["H"], L=p["L"],
        mz=p["mz"], my=p["my"], space=p["space"],
        diverg=p["diverg"], sox=p["sox"], soz=p["soz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        mics=mics,
        hadamard_n=p["hadamard_n"],
        sy=p.get("sy"),
    )
    payload["geometry"] = geometry_payload(p)
    return payload


@app.post("/api/render")
async def api_render(
    file: UploadFile = File(...),
    params_json: str = Form("{}"),
):
    try:
        body = json.loads(params_json or "{}")
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "Invalid params JSON"}, status_code=400)

    p = params_from_body(body)
    suffix = Path(file.filename or "in.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        src = tmp.name

    try:
        dry, sr = load_wav_mono(src)
    except Exception as e:
        Path(src).unlink(missing_ok=True)
        return JSONResponse({"ok": False, "error": f"Could not load WAV: {e}"}, status_code=400)

    try:
        Lch, Rch, info = render(
            dry, sr,
            W=p["W"], H=p["H"], L=p["L"],
            sox=p["sox"], soz=p["soz"],
            mz=p["mz"], my=p["my"], sy=p.get("sy"),
            space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
            early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"],
            fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"],
            path_on=p["path_on"], path_preset=p["path_preset"],
            ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
            mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
            hadamard_n=p["hadamard_n"],
            pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
            yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
            surfaces=p.get("surfaces"),
            diffusion_seed=p["diffusion_seed"],
            lambda_ref=p["lambda_ref"],
        )
        out = default_out_path()
        meta = write_wav_stereo(str(out), Lch, Rch, sr)
    except Exception as e:
        Path(src).unlink(missing_ok=True)
        return JSONResponse({"ok": False, "error": f"Render failed: {e}"}, status_code=500)
    Path(src).unlink(missing_ok=True)

    preview = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    preview.close()
    shutil.copy2(out, preview.name)

    status = (
        f"Wrote {out}\n"
        f"mode={info.get('mode')}  duration={meta['duration_s']:.2f}s  sr={sr}\n"
        f"c={SPEED_OF_SOUND_M_S} m/s  MCZ=L−MZ={info.get('mcz'):.3f} m\n"
        f"MCX={info.get('mcx'):.3f} m  "
        f"({'W/2 parity' if p['reaktor_parity'] else 'free'})\n"
        f"source={info.get('source')}  mic_centre={info.get('mic_centre')}\n"
        f"Hadamard N={p['hadamard_n']}  images={info.get('n_taps', p['hadamard_n'])}  "
        f"FDN lines={p['hadamard_n']}  (unscaled ±1)\n"
        f"peak_before_norm={info.get('peak_before_norm'):.4f}  "
        f"norm_scale={info.get('norm_scale'):.4f}"
    )
    colour = info.get("colour")
    if colour is None:
        # Fallback: analyse rendered wet mix (post dry) as last resort
        colour = colour_from_stereo(Lch, Rch, sr, ref_mode=str(body.get("ref_mode") or "peak"))

    status += (
        f"\nColour: 1/3-octave ({len(colour.get('centres_hz', []))} bands)  "
        f"Surfaces: ASSUMED absorb×EQ + path-length jitter "
        f"(seed={p['diffusion_seed']} λ_ref={p['lambda_ref']} m)"
    )
    return {
        "ok": True,
        "preview_url": f"/api/preview?path={preview.name}",
        "out_path": str(out),
        "status": status,
        "geometry": geometry_payload(p),
        "duration_s": meta["duration_s"],
        "colour": colour,
        "surfaces": surfaces_payload(p.get("surfaces") or default_surfaces()),
    }


@app.get("/api/preview")
def api_preview(path: str):
    fp = Path(path)
    if not fp.exists() or fp.suffix.lower() != ".wav":
        return JSONResponse({"error": "not found"}, status_code=404)
    allowed = str(fp).startswith(tempfile.gettempdir()) or str(fp).startswith(
        str(ROOT / "renders")
    )
    if not allowed:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    return FileResponse(str(fp), media_type="audio/wav", filename=fp.name)



@app.get("/api/surfaces")
def api_surfaces_defaults():
    """Default ASSUMED A–F surface cards (absorb / EQ / diffusion)."""
    return surfaces_payload(default_surfaces())


@app.post("/api/colour")
async def api_colour(body: dict):
    """Compute 1/3-octave Colour from a short wet IR (no dry file required).

    Uses current room + ASSUMED surfaces. Returns centres_hz + levels_db.
    """
    from render_pipeline import (
        DEFAULT_DEPTH,
        SPEED_OF_SOUND_M_S,
        MicStand,
        allpass_ir_for_stages,
        combined_ir,
        compute_taps,
        grid_bias_for_hadamard_n,
        normalize_hadamard_n,
        precompute_wall_peaking_coeffs,
        prepare_direct_field,
        propose_fdn_delays_samples,
    )
    import numpy as np

    p = params_from_body(body)
    surfaces = p.get("surfaces") or default_surfaces()
    room = (p["W"], p["H"], p["L"])
    sr = 44100
    c = SPEED_OF_SOUND_M_S
    n_had = normalize_hadamard_n(p["hadamard_n"])
    grid = grid_bias_for_hadamard_n(n_had)
    prep = prepare_direct_field(
        p["W"], p["H"], p["L"],
        mz=p["mz"], my=p["my"], space=p["space"], diverg=p["diverg"],
        sox=p["sox"], soz=p["soz"], mcx=p["mcx"],
        toe_half_deg=p.get("toe_half_deg"),
    )
    stand = MicStand.from_prepare(prep, car_omni=p["car_omni"], pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"), yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"))
    taps = compute_taps(
        room, prep.source, stand, c=c, grid=grid, origin="corner",
        z_face_4l=True, hadamard_n=n_had,
    )
    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEFAULT_DEPTH)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    delays = propose_fdn_delays_samples(p["W"], p["H"], p["L"], sr=sr, c=c, n=n_had)
    early_ms = min(90.0, float(p["ir_length_ms"]))
    fdn_ms = max(early_ms, min(float(p["ir_length_ms"]), 250.0))
    ir_L, ir_R = combined_ir(
        taps, room, sr, c, wall_cache, ap_cache, delays,
        early_ms=early_ms, fdn_ms=fdn_ms, fdn_g=float(np.clip(p["fdn_g"], 1e-6, 0.999)),
        early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], hadamard_n=n_had,
        surfaces=surfaces,
        diffusion_seed=p["diffusion_seed"],
        lambda_ref=p["lambda_ref"],
        mic_left=prep.mic_left,
        mic_right=prep.mic_right,
    )
    ref_mode = str((body or {}).get("ref_mode") or "peak")
    colour = colour_from_stereo(ir_L, ir_R, sr, ref_mode=ref_mode)
    return {
        "ok": True,
        "colour": colour,
        "surfaces": surfaces_payload(surfaces),
        "hadamard_n": n_had,
        "preview_ms": fdn_ms,
        "assumed": True,
        "diffusion_seed": p["diffusion_seed"],
        "lambda_ref": p["lambda_ref"],
    }


@app.post("/api/polar")
async def api_polar(body: dict):
    """ASSUMED mic polar × frequency in mic–source plane (L/C/R + Sum)."""
    p = params_from_body(body)
    n_az = int(body.get("n_az") or 72)
    n_az = max(24, min(180, n_az))
    sy = body.get("sy", None)
    if sy is not None:
        try:
            sy = float(sy)
        except (TypeError, ValueError):
            sy = None
    payload = compute_polar_field(
        W=p["W"], H=p["H"], L=p["L"],
        sox=p["sox"], soz=p["soz"],
        mz=p["mz"], my=p["my"],
        space=p["space"], diverg=p["diverg"],
        car_omni=p["car_omni"],
        mcx=p.get("mcx"),
        toe_half_deg=p.get("toe_half_deg"),
        sy=sy,
        hadamard_n=p["hadamard_n"],
        surfaces=p.get("surfaces"),
        n_az=n_az,
        diffusion_seed=p["diffusion_seed"],
        lambda_ref=p["lambda_ref"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
    )
    return payload



def main():
    print("2011 Room Reverb — Tweak App")
    print("Open http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="info")


if __name__ == "__main__":
    main()
