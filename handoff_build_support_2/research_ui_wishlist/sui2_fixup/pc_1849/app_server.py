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
import source_radiation as source_radiation
from mic_display import (
    clamp_inside_room,
    format_position_readout,
    geometry,
    prepare_from_metres,
)
from render_pipeline import (
    SPEED_OF_SOUND_M_S,
    default_out_path,
    live_fdn_params,
    load_wav_mono,
    load_wav_stereo,
    mirror_source_b,
    render,
    write_wav_stereo,
)

from polar_field import compute_polar_field
from fdn import DIFFUSION_MASTER_DEFAULT, DIFFUSION_MASTER_MIN  # locked 28 Sep 2026
from surface_colour import (
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    materials_public,
    mute_flags,
    parse_diffusion_seed,
    parse_solo,
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
    "sx": 2.6,  # K3 locked 28 Sep 2026
    "sz": 4.75,
    "mcx": 3.0,
    "mcz": 1.5,
    "my": 1.5,
    "sy": 1.2,  # K3 locked 28 Sep 2026
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
    "early_wet": 0.0,
    "fdn_wet": 1.0,
    "direct_wet": 1.0,
    "dry_gain": 0.0,
    "fdn_g": 1.0,
    "ir_length_ms": 1500.0,
    "reaktor_parity": False,
    "shared_tail": False,
    "path_on": False,
    "path_preset": "still",
    "ellipse_rate": 1.0,
    "ellipse_rx": 0.42,
    "ellipse_rz": 0.35,
    "hadamard_n": 32,
    "diffusion_seed": DEFAULT_DIFFUSION_SEED,
    "lambda_ref": DEFAULT_LAMBDA_REF_M,
    # Binaural (LOCKED 2026-09-30). Default mic setup stays ORTF.
    "binaural_preset": "SADIE2_KU100",
    "binaural_tail_mode": "diffuse_ic",
    "binaural_level_ref": "head_centre",
    "binaural_K": 6,
    "binaural_symmetric": True,
    "binaural_image_set": "binaural_rear32",
    "binaural_itd_mode": "table",
    "head_yaw_deg": 0.0,
    # ISO air. Humidity 0 is off. Above 0 the slider sets RH; right is drier.
    "air_climate": "studio_20C_50RH",
    "air_iso": True,
    # Source radiation. Omni is the current sound (the stage is not called).
    "source_radiation": "omni",
    "source_yaw": 0.0,
    "source_pitch": 0.0,
}


def _opt_follow(v: Any):
    """None follows A. A blank string follows. Any other value is B's own choice."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s or None
    return str(v)


def _opt_deg(v: Any):
    """None follows A. Zero is a real angle."""
    if v is None or (isinstance(v, str) and not str(v).strip()):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x:
        return None
    return x


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)


def _span(v: Any, default: float, lo: float, hi: float) -> float:
    x = _f(v, default)
    if x != x:
        return float(default)
    return float(max(lo, min(hi, x)))


def _phase(v: Any) -> float:
    try:
        return -1.0 if float(v) < 0.0 else 1.0
    except (TypeError, ValueError):
        return 1.0


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
    if p in ("supercardioid", "super", "hypercardioid", "hyper"):
        return "supercardioid"
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

    def _fam(key: str, pat: str) -> str:
        raw = body.get(key)
        if raw is None or (isinstance(raw, str) and not str(raw).strip()):
            return "bi" if pat == "fig8" else "cardioid"
        e = str(raw).strip().lower()
        if e in ("bi", "bidirectional", "fig8"):
            return "bi"
        return "cardioid"

    def _pol(key: str, pat: str) -> float:
        v = _optional_float(body, key, None)
        if v is not None:
            return max(0.0, min(1.0, float(v)))
        if pat == "omni":
            return 0.0
        if pat == "supercardioid":
            return 1.0
        return 0.5

    fl, fc, fr = _fam("family_l", pl), _fam("family_c", pc), _fam("family_r", pr)
    pol_l, pol_c, pol_r = _pol("polar_l", pl), _pol("polar_c", pc), _pol("polar_r", pr)
    if fl == "bi":
        pl = "fig8"
    if fc == "bi":
        pc = "fig8"
    if fr == "bi":
        pr = "fig8"
    dz = _f(body.get("centre_dz"), 0.0)
    dz = max(-0.20, min(0.20, dz))
    if _b(body.get("align_horizontal"), False):
        dz = 0.0
    return {
        "pattern_l": pl,
        "pattern_c": pc,
        "pattern_r": pr,
        "yaw_l_deg": yaw_l,
        "yaw_c_deg": yaw_c if yaw_c is not None else 0.0,
        "yaw_r_deg": yaw_r,
        "car_omni": car,
        "toe_half_deg": toe,
        "family_l": fl,
        "family_c": fc,
        "family_r": fr,
        "polar_l": pol_l,
        "polar_c": pol_c,
        "polar_r": pol_r,
        "centre_dz": dz,
        "mic_hp_on": _b(body.get("mic_hp_on"), False),
        "mic_hp_hz": max(12.0, min(250.0, _f(body.get("mic_hp_hz"), 40.0))),
        "mic_response_hz": max(10000.0, min(20000.0, _f(body.get("mic_response_hz"), 10000.0))),
        "mic_proximity": max(0.0, min(1.0, _f(
            body.get("mic_proximity") if "mic_proximity" in body else 0.25, 0.25))),
        "ms_decode": _b(body.get("ms_decode"), False) or str(body.get("mic_setup") or "") == "ms_classic",
        "capsule_mm": max(8.0, min(34.0, _f(body.get("capsule_mm"), 17.0))),
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
    elif body.get("my") is None:
        # K3 (locked 28 Sep 2026): a body with neither sy nor my gets the default source
        # height. A body that sends my but not sy keeps the legacy "sy follows my".
        sy_arg = DEFAULTS["sy"]
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
    mic_colour_fields = _mic_colour_fields(body, cap)
    mirror_b = _b(body.get("mirror_b") if "mirror_b" in body else True, True)
    if mirror_b:
        sx_b, sy_b, sz_b = mirror_source_b(W, sx, sy, sz)
    else:
        sx_b = _f(body.get("sx_b"), W - sx)
        sy_b = _f(body.get("sy_b"), sy)
        sz_b = _f(body.get("sz_b"), sz)
    sx_b = max(0.0, min(W, float(sx_b)))
    sy_b = max(0.0, min(H, float(sy_b)))
    sz_b = max(0.0, min(L, float(sz_b)))
    two_sources = _b(body.get("two_sources"), False)
    source_balance = _span(body.get("source_balance"), 0.0, -1.0, 1.0)
    mic_setup = str(body.get("mic_setup") or "ortf")
    binaural_on = mic_setup == "binaural"
    head_yaw = _span(body.get("head_yaw_deg"), 0.0, -180.0, 180.0)
    preset_id = str(body.get("binaural_preset") or DEFAULTS["binaural_preset"])
    if preset_id not in ("SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"):
        preset_id = DEFAULTS["binaural_preset"]
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
        "family_l": cap["family_l"],
        "family_c": cap["family_c"],
        "family_r": cap["family_r"],
        "polar_l": cap["polar_l"],
        "polar_c": cap["polar_c"],
        "polar_r": cap["polar_r"],
        "centre_dz": cap["centre_dz"],
        "mic_hp_on": cap["mic_hp_on"],
        "mic_hp_hz": cap["mic_hp_hz"],
        "mic_response_hz": cap["mic_response_hz"],
        "mic_proximity": cap["mic_proximity"],
        "ms_decode": cap["ms_decode"],
        "capsule_mm": cap["capsule_mm"],
        "early_wet": _f(body.get("early_wet") if "early_wet" in body else 1.0, 1.0),
        "fdn_wet": _f(body.get("fdn_wet"), DEFAULTS["fdn_wet"]),
        "direct_wet": _f(body.get("direct_wet"), DEFAULTS["direct_wet"]),
        "dry_gain": _f(body.get("dry_gain"), DEFAULTS["dry_gain"]),
        "fdn_g": _f(body.get("fdn_g"), DEFAULTS["fdn_g"]),
        "ir_length_ms": _f(body.get("ir_length_ms"), DEFAULTS["ir_length_ms"]),
        "reaktor_parity": parity,
        "shared_tail": _b(body.get("shared_tail"), False),
        "path_on": _b(body.get("path_on"), False),
        "path_preset": str(body.get("path_preset") or "still"),
        "ellipse_rate": _f(body.get("ellipse_rate"), 1.0),
        "ellipse_rx": _f(body.get("ellipse_rx"), 0.42),
        "ellipse_rz": _f(body.get("ellipse_rz"), 0.35),
        "hadamard_n": _hadamard_n(body),
        "surfaces": parse_surfaces(body.get("surfaces")),
        "surfaces_solo": parse_solo(body.get("surfaces_solo")),
        "surfaces_mute": mute_flags(body.get("surfaces_mute")),
        "diffusion_seed": parse_diffusion_seed(body.get("diffusion_seed"), DEFAULT_DIFFUSION_SEED),
        "lambda_ref": parse_lambda_ref(body.get("lambda_ref"), DEFAULT_LAMBDA_REF_M),
        "humidity": _f(body.get("humidity") if "humidity" in body else 0.35, 0.35),
        "air_lp": _f(body.get("air_lp"), 0.0),  # K2 locked: 1-pole kept, default mix 0
        "air_shelf": _f(body.get("air_shelf"), 1.0),
        "air_climate": str(body.get("air_climate") or DEFAULTS["air_climate"]),
        # Parity keeps the 2011 one-pole (air_lp) and turns the ISO shelves off.
        "air_iso": False if parity else _b(body.get("air_iso"), DEFAULTS["air_iso"]),
        "source_radiation": str(body.get("source_radiation") or DEFAULTS["source_radiation"]),
        "source_yaw": _f(body.get("source_yaw"), DEFAULTS["source_yaw"]),
        "source_pitch": _f(body.get("source_pitch"), DEFAULTS["source_pitch"]),
        # Null follows A. An explicit "omni" is B's own choice (old saves stay omni).
        "source_radiation_b": _opt_follow(body["source_radiation_b"]) if "source_radiation_b" in body else None,
        "source_yaw_b": _opt_deg(body["source_yaw_b"]) if "source_yaw_b" in body else None,
        "source_pitch_b": _opt_deg(body["source_pitch_b"]) if "source_pitch_b" in body else None,
        "source_size_m": body.get("source_size_m"),
        "diffusion_master": _span(body.get("diffusion_master"), DIFFUSION_MASTER_DEFAULT, DIFFUSION_MASTER_MIN, 0.0),
        "decay_s": _f(body.get("decay_s") if "decay_s" in body else 1.8, 1.8),
        "decay_lock": _b(body.get("decay_lock") if "decay_lock" in body else True, True),
        "mic_setup": mic_setup,
        "head_yaw_deg": head_yaw,
        "binaural_preset": preset_id,
        "binaural_tail_mode": "diffuse_ic",
        "binaural_level_ref": "head_centre",
        "binaural_image_set": "binaural_rear32",
        "mic_gain_l": _span(body.get("mic_gain_l"), 1.0, 0.0, 16.0),
        "mic_gain_c": 0.0 if binaural_on else _span(body.get("mic_gain_c"), 1.0, 0.0, 16.0),
        "mic_gain_r": _span(body.get("mic_gain_r"), 1.0, 0.0, 16.0),
        "mic_pan_l": _span(body.get("mic_pan_l"), -1.0, -1.0, 1.0),
        "mic_pan_c": _span(body.get("mic_pan_c"), 0.0, -1.0, 1.0),
        "mic_pan_r": _span(body.get("mic_pan_r"), 1.0, -1.0, 1.0),
        "mic_phase_l": _phase(body.get("mic_phase_l")),
        "mic_phase_c": _phase(body.get("mic_phase_c")),
        "mic_phase_r": _phase(body.get("mic_phase_r")),
        "two_sources": two_sources,
        "mirror_b": mirror_b,
        "source_balance": source_balance,
        "sx_b": sx_b,
        "sy_b": sy_b,
        "sz_b": sz_b,
        "colour_mode": mic_colour_fields["colour_mode"],
        "colour_impl": mic_colour_fields["colour_impl"],
        "mic_preset_l": mic_colour_fields["mic_preset_l"],
        "mic_preset_c": mic_colour_fields["mic_preset_c"],
        "mic_preset_r": mic_colour_fields["mic_preset_r"],
        "mic_hpf_engaged": mic_colour_fields["mic_hpf_engaged"],
        "mic_hpf_sides": mic_colour_fields["mic_hpf_sides"],
        "mic_hpf_centre": mic_colour_fields["mic_hpf_centre"],
        "sample_rate": body.get("sample_rate"),
        "colour_rev": body.get("colour_rev") or "",
    }


def _explicit_field(body: dict, key: str) -> bool:
    if key not in body or body.get(key) is None:
        return False
    raw = body.get(key)
    if isinstance(raw, str) and not str(raw).strip():
        return False
    if isinstance(raw, str) and str(raw).strip().lower() in ("null", "none"):
        return False
    return True


def _mic_colour_fields(body: dict, cap: dict) -> dict:
    """Missing preset/mode → SM57 × 3 and MEASURED_SHELF.

    An explicit preset id sets that capsule's pattern, family, and polar.
    Yaw, space, and mic_setup are left as the desk sent them.
    """
    from mic_colour.modes import parse_colour_impl, parse_colour_mode
    from mic_colour.pattern_map import capsule_law
    from mic_colour.preset_store import get_store, resolve_preset_id

    explicit_all = _explicit_field(body, "mic_preset")
    ids = {}
    applied = False
    # D-UI21 / D-UI22: Measured and Bypass always take the preset capsule law.
    # User defined still honours preset_owns_pattern. Binaural stays on its own pattern.
    colour_mode = parse_colour_mode(body.get("colour_mode"))
    force_law = (
        colour_mode in ("MEASURED_SHELF", "BYPASS")
        and str(body.get("mic_setup") or "") != "binaural"
    )
    for slot, key in (("l", "mic_preset_l"), ("c", "mic_preset_c"), ("r", "mic_preset_r")):
        if _explicit_field(body, key):
            pid = resolve_preset_id(body.get(key), explicit=True)
            apply = True
        elif explicit_all:
            pid = resolve_preset_id(body.get("mic_preset"), explicit=True)
            apply = True
        else:
            pid = resolve_preset_id(None)
            apply = False
        ids[slot] = pid
        # An explicit id applies the pattern law unless the desk has moved
        # pattern since that load (preset_owns_pattern false). Absent flag
        # keeps the Phase 1 behaviour: the explicit id owns the pattern.
        owns = True
        if not force_law and "preset_owns_pattern" in body:
            owns = _b(body.get("preset_owns_pattern"), True)
        if apply and owns:
            law = capsule_law(get_store().family_of(pid))
            cap[f"pattern_{slot}"] = law["pattern"]
            cap[f"family_{slot}"] = law["family"]
            cap[f"polar_{slot}"] = law["polar"]
            applied = True
    if applied:
        lo = 0.0 if cap["pattern_l"] == "omni" else 1.0
        ro = 0.0 if cap["pattern_r"] == "omni" else 1.0
        cap["car_omni"] = 0.5 * (lo + ro)
    return {
        "colour_mode": colour_mode,
        "colour_impl": parse_colour_impl(body.get("colour_impl")),
        "mic_preset_l": ids["l"],
        "mic_preset_c": ids["c"],
        "mic_preset_r": ids["r"],
        "mic_hpf_engaged": _b(body.get("mic_hpf_engaged"), False),
        "mic_hpf_sides": (
            _b(body.get("mic_hpf_sides"), False)
            if "mic_hpf_sides" in body or "mic_hpf_centre" in body
            else _b(body.get("mic_hpf_engaged"), False)
        ),
        "mic_hpf_centre": (
            _b(body.get("mic_hpf_centre"), False)
            if "mic_hpf_sides" in body or "mic_hpf_centre" in body
            else _b(body.get("mic_hpf_engaged"), False)
        ),
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
        sy=p.get("sy"), sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
    )
    prep = g["prep"]
    S, C = prep.source, prep.mic_centre
    Lm, Rm = prep.mic_left, prep.mic_right
    readout = format_position_readout(
        p["W"], p["H"], p["L"],
        mz=p["mz"], my=p["my"], space=p["space"],
        diverg=p["diverg"], sox=p["sox"], soz=p["soz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        sy=p.get("sy"), sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
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
            "two_sources": bool(p.get("two_sources")),
            "mirror_b": bool(p.get("mirror_b")),
            "source_balance": float(p.get("source_balance") or 0.0),
            "sx_b": p.get("sx_b"),
            "sy_b": p.get("sy_b"),
            "sz_b": p.get("sz_b"),
        },
        "source": {"x": S[0], "y": S[1], "z": S[2]},
        "source_b": (
            {"x": p["sx_b"], "y": p["sy_b"], "z": p["sz_b"]}
            if p.get("two_sources") else None
        ),
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


@app.post("/api/live_params")
async def api_live_params(body: dict):
    """Running-FDN coefficients for the AudioWorklet. Same algebra as Render."""
    try:
        p = params_from_body(body or {})
        return live_fdn_params(p)
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"live_params: {e}"}, status_code=500)



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
        sy=p.get("sy"), sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
        two_sources=bool(p.get("two_sources")),
        sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"),
    )
    payload["geometry"] = geometry_payload(p)
    _annotate_images(payload, p)
    return payload


def _annotate_images(payload: dict, p: dict) -> None:
    """Path hover: emission angle in the source frame, and 1 kHz / 4 kHz level."""
    geo = payload.get("geometry") or {}
    mic_c = geo.get("mic_centre") or {}
    mic = (mic_c.get("x", 0.0), mic_c.get("y", 0.0), mic_c.get("z", 0.0))
    size = p.get("source_size_m")
    for mic_id, taps in (payload.get("per_mic") or {}).items():
        cap = (payload.get("mics") or {}).get(mic_id) or mic
        if isinstance(cap, dict):
            cap = (cap.get("x", 0.0), cap.get("y", 0.0), cap.get("z", 0.0))
        source_radiation.annotate_taps(
            taps, p.get("source_radiation"), p.get("source_yaw") or 0.0,
            p.get("source_pitch") or 0.0, cap, size,
        )
    preset_b, yaw_b, pitch_b = source_radiation.effective_b_pose(p)
    if payload.get("per_mic_b"):
        for mic_id, taps in payload["per_mic_b"].items():
            cap = (payload.get("mics") or {}).get(mic_id) or mic
            if isinstance(cap, dict):
                cap = (cap.get("x", 0.0), cap.get("y", 0.0), cap.get("z", 0.0))
            source_radiation.annotate_taps(taps, preset_b, yaw_b, pitch_b, cap, size)
    payload["source_facing"] = {
        "yaw": p.get("source_yaw") or 0.0,
        "pitch": p.get("source_pitch") or 0.0,
        "preset": p.get("source_radiation") or "omni",
    }
    payload["source_facing_b"] = {
        "yaw": yaw_b,
        "pitch": pitch_b,
        "preset": preset_b,
    }


@app.get("/api/source_presets")
def api_source_presets():
    return {"presets": source_radiation.catalog()}


@app.post("/api/source_preview")
async def api_source_preview(body: dict):
    """Polar in the source frame, plus what the centre mic hears on the direct."""
    try:
        p = params_from_body(body or {})
        freq = float((body or {}).get("freq") or 1000.0)
        if freq < 20.0:
            freq = 20.0
        if freq > 20000.0:
            freq = 20000.0
        geo = geometry_payload(p)
        mic = geo["mic_centre"]
        src = geo["source"]
        which = str((body or {}).get("which") or "a")
        if which == "b":
            if geo.get("source_b"):
                src = geo["source_b"]
            preset, yaw, pitch = source_radiation.effective_b_pose(p)
        else:
            yaw = p.get("source_yaw") or 0.0
            pitch = p.get("source_pitch") or 0.0
            preset = p.get("source_radiation")
        pattern = source_radiation.preview_pattern(preset, p.get("source_size_m"), 48000.0)
        face = source_radiation.yaw_pitch_toward(
            (src["x"], src["y"], src["z"]),
            (mic["x"], mic["y"], mic["z"]),
        )
        db = source_radiation.direct_db(
            preset, yaw, pitch,
            (src["x"], src["y"], src["z"]),
            (mic["x"], mic["y"], mic["z"]),
            freq, p.get("source_size_m"), 48000.0,
        )
        pattern["direct_db"] = round(db, 2)
        pattern["freq"] = freq
        pattern["yaw"] = yaw
        pattern["pitch"] = pitch
        pattern["yaw_to_face"] = round(face[0], 2)
        pattern["pitch_to_face"] = round(face[1], 2)
        pattern["off_mic_deg"] = round(
            ((yaw - face[0] + 540.0) % 360.0) - 180.0, 2,
        )
        return pattern
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"source_preview: {e}"}, status_code=500)


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

    moving = bool(p.get("path_on")) and str(p.get("path_preset") or "still") != "still"
    use_two = bool(p.get("two_sources")) and not moving
    dry_l = None
    dry_r = None
    try:
        if use_two:
            left, right, sr, _nch = load_wav_stereo(src)
            if right is None:
                dry = left
                use_two = False
            else:
                dry = 0.5 * (left + right)
                dry_l, dry_r = left, right
        else:
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
            sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
            space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
            early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"],
            direct_wet=p.get("direct_wet", 1.0),
            fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"],
            path_on=p["path_on"], path_preset=p["path_preset"],
            ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
            mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
            hadamard_n=p["hadamard_n"],
            pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
            yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
            family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
            polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
            centre_dz=p.get("centre_dz") or 0.0,
            mic_hp_on=p.get("mic_hp_on") or False,
            mic_hp_hz=p.get("mic_hp_hz") or 40.0,
            mic_response_hz=p.get("mic_response_hz") or 10000.0,
            mic_proximity=p.get("mic_proximity") or 0.0,
            ms_decode=bool(p.get("ms_decode")),
            capsule_mm=p.get("capsule_mm") or 17.0,
            surfaces=p.get("surfaces"),
            surfaces_solo=p.get("surfaces_solo"),
            surfaces_mute=p.get("surfaces_mute"),
            diffusion_seed=p["diffusion_seed"],
            lambda_ref=p["lambda_ref"],
            humidity=p.get("humidity") or 0.0,
            air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.0,
            air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
            reaktor_parity=bool(p.get("reaktor_parity")),
            air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
            air_iso=bool(p.get("air_iso")) if p.get("air_iso") is not None else True,
            diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else DIFFUSION_MASTER_DEFAULT,
            decay_s=p.get("decay_s") or 0.0,
            decay_lock=bool(p.get("decay_lock")),
            mic_gain_l=p.get("mic_gain_l", 1.0),
            mic_gain_c=p.get("mic_gain_c", 1.0),
            mic_gain_r=p.get("mic_gain_r", 1.0),
            mic_pan_l=p.get("mic_pan_l", -1.0),
            mic_pan_c=p.get("mic_pan_c", 0.0),
            mic_pan_r=p.get("mic_pan_r", 1.0),
            mic_phase_l=p.get("mic_phase_l", 1.0),
            mic_phase_c=p.get("mic_phase_c", 1.0),
            mic_phase_r=p.get("mic_phase_r", 1.0),
            two_sources=use_two,
            source_balance=p.get("source_balance") or 0.0,
            mirror_b=bool(p.get("mirror_b")),
            sx_b=p.get("sx_b"),
            sy_b=p.get("sy_b"),
            sz_b=p.get("sz_b"),
            dry_l=dry_l,
            dry_r=dry_r,
            colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
            colour_impl=p.get("colour_impl") or "sos",
            mic_preset_l=p.get("mic_preset_l") or "ShureSM57",
            mic_preset_c=p.get("mic_preset_c") or "ShureSM57",
            mic_preset_r=p.get("mic_preset_r") or "ShureSM57",
            mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
            mic_hpf_sides=p.get("mic_hpf_sides"),
            mic_hpf_centre=p.get("mic_hpf_centre"),
            source_radiation=str(p.get("source_radiation") or "omni"),
            source_yaw=float(p.get("source_yaw") or 0.0),
            source_pitch=float(p.get("source_pitch") or 0.0),
            source_radiation_b=p.get("source_radiation_b"),
            source_yaw_b=p.get("source_yaw_b"),
            source_pitch_b=p.get("source_pitch_b"),
            source_size_m=p.get("source_size_m"),
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
        f"Mic colour={info.get('colour_mode')}  "
        f"L/C/R={info.get('mic_preset_l')}\n"
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
    if info.get("colour_notice"):
        status += "\n" + str(info.get("colour_notice"))
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



@app.get("/api/mic_presets")
def api_mic_presets():
    from mic_colour.preset_store import DEFAULT_PRESET_ID, get_store
    return {"ok": True, "default": DEFAULT_PRESET_ID, "presets": get_store().summaries()}


@app.get("/api/mic_presets/{mic_id}")
def api_mic_preset(mic_id: str):
    from mic_colour.pattern_map import capsule_law
    from mic_colour.preset_store import get_store, resolve_preset_id
    try:
        pid = resolve_preset_id(mic_id, explicit=True)
    except KeyError:
        return JSONResponse({"ok": False, "error": "unknown preset"}, status_code=404)
    preset = get_store().get(pid)
    if preset is None:
        return JSONResponse({"ok": False, "error": "unknown preset"}, status_code=404)
    return {
        "ok": True,
        "preset": preset,
        "capsule": capsule_law(preset.get("family")),
    }


@app.get("/api/surfaces")
def api_surfaces_defaults():
    """Default A–F surface cards (absorb / EQ / diffusion). B/D/E/F names VERIFIED; A/C split ASSUMED."""
    return surfaces_payload(default_surfaces())


@app.get("/api/surface_materials")
def api_surface_materials():
    """Role-tagged material library. Curtain is wall-only. Carpet is floor-only."""
    from surface_colour import LETTER_ROLE
    return {
        "ok": True,
        "letter_role": LETTER_ROLE,
        "materials": materials_public(),
    }


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
        direct_field_from_params,
        propose_fdn_delays_samples,
        fdn_delays_from_taps,
    )
    import numpy as np

    p = params_from_body(body)
    from mic_colour.colour import MicColour
    mic_colour = MicColour(
        p.get("colour_mode"),
        p.get("mic_preset_l"),
        p.get("mic_preset_c"),
        p.get("mic_preset_r"),
        44100,
        hpf_engaged=bool(p.get("mic_hpf_engaged")),
        hpf_sides=p.get("mic_hpf_sides"),
        hpf_centre=p.get("mic_hpf_centre"),
        colour_impl=p.get("colour_impl") or "sos",
    )
    surfaces = p.get("surfaces") or default_surfaces()
    room = (p["W"], p["H"], p["L"])
    sr = 44100
    c = SPEED_OF_SOUND_M_S
    n_had = normalize_hadamard_n(p["hadamard_n"])
    grid = grid_bias_for_hadamard_n(n_had)
    prep = direct_field_from_params(p)
    stand = MicStand.from_prepare(
        prep, car_omni=p["car_omni"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
        polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0,
    )
    taps = compute_taps(
        room, prep.source, stand, c=c, grid=grid, origin="corner",
        z_face_4l=False, hadamard_n=n_had,
        include_offaxis_shelf=mic_colour.include_offaxis_shelf,
        reaktor_parity=bool(p.get("reaktor_parity")),
    )
    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEFAULT_DEPTH)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
    early_ms = min(90.0, float(p["ir_length_ms"]))
    fdn_ms = max(early_ms, min(float(p["ir_length_ms"]), 1000.0))
    ir_L, ir_R = combined_ir(
        taps, room, sr, c, wall_cache, ap_cache, delays,
        early_ms=early_ms, fdn_ms=fdn_ms, fdn_g=float(np.clip(p["fdn_g"], 1e-6, 0.999)),
        early_wet=p["early_wet"], fdn_wet=p["fdn_wet"],
        direct_wet=p.get("direct_wet", 1.0), hadamard_n=n_had,
        surfaces=surfaces,
        diffusion_seed=p["diffusion_seed"],
        lambda_ref=p["lambda_ref"],
        mic_left=prep.mic_left,
        mic_right=prep.mic_right,
        colour=mic_colour,
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
        sy=sy, sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
        hadamard_n=p["hadamard_n"],
        surfaces=p.get("surfaces"),
        n_az=n_az,
        diffusion_seed=p["diffusion_seed"],
        lambda_ref=p["lambda_ref"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
        polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0,
        colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
        mic_preset_l=p.get("mic_preset_l") or "ShureSM57",
        mic_preset_c=p.get("mic_preset_c") or "ShureSM57",
        mic_preset_r=p.get("mic_preset_r") or "ShureSM57",
        mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
        mic_hpf_sides=p.get("mic_hpf_sides"),
        mic_hpf_centre=p.get("mic_hpf_centre"),
    )
    return payload



def main():
    print("2011 Room Reverb — Tweak App")
    print("Open http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="info")


if __name__ == "__main__":
    main()
