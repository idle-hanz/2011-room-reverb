#!/usr/bin/env python3
"""2011 Room Reverb — modern tweak app (FastAPI + drag room editor)."""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import threading
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
    smooth_active,
    load_wav_mono,
    load_wav_stereo,
    mirror_source_b,
    publish_out_copy,
    render,
    limiter_message,
    replace_preview,
    write_wav_stereo,
)

from polar_field import compute_polar_field
from fdn import DIFFUSION_MASTER_DEFAULT, DIFFUSION_MASTER_MIN  # locked 28 Sep 2026
from surface_colour import (
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    load_material_sets,
    materials_public,
    mute_flags,
    parse_diffusion_seed,
    parse_solo,
    parse_lambda_ref,
    mirror_left_to_right,
    parse_surfaces,
    surfaces_payload,
    third_octave_levels,
)

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="2011 Room Reverb", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

_render_lock = threading.Lock()


class BadParam(Exception):
    """A posted number is missing, non-numeric, or non-finite. `key` is the field name."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(key)


@app.exception_handler(BadParam)
def _bad_param(_request, exc: BadParam):
    return JSONResponse({"ok": False, "error": str(exc.key)}, status_code=400)

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
    "smooth": True,
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


def _sides_mirrored(body: Any) -> bool:
    """A left/right symmetric polygon is always one pair. Box copies left onto right only when Mirror L/R is on."""
    if not isinstance(body, dict):
        return False
    from poly_room import lr_symmetric, normalize_shape
    shape = normalize_shape(body.get("room_shape")) if "room_shape" in body else "box"
    if shape != "box":
        return lr_symmetric(shape)
    if "mirror_lr" not in body:
        return False
    return _b(body.get("mirror_lr"), False)


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

# Slider limits. parameters.csv has no W/H/L/decay row; these are the HTML ranges.
# ir_length_ms is intentionally absent: the harness posts 3000 and the UI max is only a control.
_UI_RANGES = {
    "W": (1.0, 80.0),
    "H": (1.0, 40.0),
    "L": (2.0, 120.0),
    "decay_s": (0.05, 8.0),
}
_CSV_RANGES: dict | None = None


def _csv_numeric_ranges() -> dict:
    """Numeric ranges written as ±N in parameters.csv. Enum rows are not clamped here."""
    global _CSV_RANGES
    if _CSV_RANGES is not None:
        return _CSV_RANGES
    out: dict = {}
    path = ROOT / "parameters.csv"
    if path.exists():
        import csv
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = (row.get("key") or "").strip()
                rng = (row.get("range") or "").strip()
                if not key or not rng.startswith("±"):
                    continue
                try:
                    n = float(rng[1:])
                except ValueError:
                    continue
                out[key] = (-n, n)
    _CSV_RANGES = out
    return out


def _finite_number(raw: Any, key: str):
    """Float, or None when the field is blank. BadParam when it is not a finite number."""
    if isinstance(raw, bool):
        raise BadParam(key)
    if isinstance(raw, str):
        s = raw.strip()
        if s.lower() in ("", "null", "none"):
            return None
        try:
            val = float(s)
        except ValueError:
            raise BadParam(key) from None
    elif isinstance(raw, (int, float)):
        val = float(raw)
    else:
        raise BadParam(key)
    if val != val or val == float("inf") or val == float("-inf"):
        raise BadParam(key)
    return val


def _opt_height(body: dict, key: str, H: float):
    """Per-capsule height. Absent or blank stays None (the stand). Else [0.02, H−0.02]."""
    if key not in body:
        return None
    raw = body.get(key)
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().lower() in ("", "null", "none"):
        return None
    val = _finite_number(raw, key)
    if val is None:
        return None
    hi = float(H) - 0.02
    if hi < 0.02:
        hi = 0.02
    return float(min(hi, max(0.02, val)))


def clamp_body(body: dict) -> list:
    """Clamp out-of-range numbers in place. Returns the warning keys. Raises BadParam."""
    warnings: list = []
    ranges = dict(_csv_numeric_ranges())
    ranges.update(_UI_RANGES)
    for key, (lo, hi) in ranges.items():
        if key not in body or body.get(key) is None:
            continue
        val = _finite_number(body.get(key), key)
        if val is None:
            continue
        if val < lo or val > hi:
            body[key] = float(min(hi, max(lo, val)))
            warnings.append(key)
    W = float(body["W"]) if "W" in body and body.get("W") is not None else float(DEFAULTS["W"])
    H = float(body["H"]) if "H" in body and body.get("H") is not None else float(DEFAULTS["H"])
    L = float(body["L"]) if "L" in body and body.get("L") is not None else float(DEFAULTS["L"])
    for key, hi in (
        ("sx", W), ("mcx", W), ("sx_b", W),
        ("sz", L), ("mcz", L), ("sz_b", L),
        ("my", H), ("sy", H), ("sy_b", H),
    ):
        if key not in body or body.get(key) is None:
            continue
        val = _finite_number(body.get(key), key)
        if val is None:
            continue
        if val < 0.0 or val > hi:
            body[key] = float(min(hi, max(0.0, val)))
            warnings.append(key)
    body["_clamp_warnings"] = warnings
    return warnings


def _attach_warnings(payload, body):
    if isinstance(payload, dict) and isinstance(body, dict):
        w = body.get("_clamp_warnings") or []
        if w:
            payload["warnings"] = list(w)
    return payload


DECAY_MODES = ("flat", "surfaces")   # SL7a adds "natural"


def _decay_mode(v) -> str:
    """SL2: missing / unknown = 'flat' (old scenes recall as Flat 2011)."""
    v = str(v or "flat").strip().lower()
    return v if v in DECAY_MODES else "flat"


def _surf_treatment(v):
    """SL5: Treatment rows. Invalid lists are dropped whole (never half-applied)."""
    if not isinstance(v, list) or not v:
        return []
    import surf_panels as _SP
    rows = []
    for r in v[:48]:
        if not isinstance(r, dict):
            return []
        rr = {k: r[k] for k in ("id", "face", "type", "on", "coverage", "material", "f0", "q", "amax", "build",
                               "suggested", "assumed", "m", "d", "eps") if k in r}
        try:
            rr["coverage"] = float(rr.get("coverage", 0.0))
            for k in ("f0", "q", "amax"):
                if k in rr:
                    rr[k] = float(rr[k])
        except (TypeError, ValueError):
            return []
        rr["on"] = bool(rr.get("on", True))
        rr["suggested"] = bool(rr.get("suggested", False))
        rows.append(rr)
    return [] if _SP.validate_rows(rows) else rows


def _surf_cal(v):
    """SL4: 7 per-octave calibration factors from the last Render, clamped 0.6-1.6, else None."""
    if not isinstance(v, (list, tuple)) or len(v) != 7:
        return None
    try:
        return [min(1.6, max(0.6, float(x))) for x in v]
    except (TypeError, ValueError):
        return None


def params_from_body(body: dict) -> dict:
    if not isinstance(body, dict):
        raise BadParam("body")
    clamp_body(body)
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
    from desk_matrix import desk_active
    ms_on = bool(cap["ms_decode"])
    # An old MS-classic body has no pair mode and no routes, so it stays on
    # the kept ms_decode branch. A desk that is actually in use must not
    # also set that branch, or the side capsule is decoded twice.
    if desk_active(body):
        ms_on = False
    # D20. An empty body, or ORTF with neither third_mic nor mic_gain_c, is C off.
    # A stored third_mic or mic_gain_c wins, so old scenes keep their centre.
    third_set = _explicit_field(body, "third_mic")
    gain_set = _explicit_field(body, "mic_gain_c")
    third = str(body.get("third_mic") or "").strip().lower() if third_set else ""
    if binaural_on or third == "off":
        gain_c = 0.0
    elif (not third_set) and (not gain_set) and mic_setup in ("", "ortf"):
        gain_c = 0.0
        third = "off"
    else:
        gain_c = _span(body.get("mic_gain_c"), 1.0, 0.0, 16.0)
    head_yaw = _span(body.get("head_yaw_deg"), 0.0, -180.0, 180.0)
    preset_id = str(body.get("binaural_preset") or DEFAULTS["binaural_preset"])
    if preset_id not in ("SADIE2_KU100", "SADIE2_KEMAR", "THK_KU100_FF"):
        preset_id = DEFAULTS["binaural_preset"]
    surfaces = parse_surfaces(body.get("surfaces"))
    # Absent or false on a box leaves A and C alone, so the live MD5 stays.
    if _sides_mirrored(body):
        mirror_left_to_right(surfaces)
    early_wet = _f(body.get("early_wet") if "early_wet" in body else 1.0, 1.0)
    fdn_wet = _f(body.get("fdn_wet"), DEFAULTS["fdn_wet"])
    smooth_on = smooth_active(
        {
            "reaktor_parity": parity,
            "smooth": body.get("smooth") if "smooth" in body else None,
            "fdn_wet": fdn_wet,
            "early_wet": early_wet,
            "mirror_null": bool(body.get("mirror_null") or body.get("null_mode")),
            "surfaces": surfaces,
        },
        surfaces,
    )
    out = {
        "W": W, "H": H, "L": L,
        "sx": sx, "sz": sz, "my": my, "sy": sy,
        "my_l": _opt_height(body, "my_l", H),
        "my_r": _opt_height(body, "my_r", H),
        "my_c": _opt_height(body, "my_c", H),
        "align_horizontal": _b(body.get("align_horizontal"), False),
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
        "prox_l": True if "prox_l" not in body or body.get("prox_l") is None else _b(body.get("prox_l"), True),
        "prox_c": True if "prox_c" not in body or body.get("prox_c") is None else _b(body.get("prox_c"), True),
        "prox_r": True if "prox_r" not in body or body.get("prox_r") is None else _b(body.get("prox_r"), True),
        "ms_decode": ms_on,
        "capsule_mm": cap["capsule_mm"],
        "early_wet": early_wet,
        "fdn_wet": fdn_wet,
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
        "surfaces": surfaces,
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
        "decay_mode": _decay_mode(body.get("decay_mode")),
        # Missing is off. Flat ignores it. Surfaces uses the material length.
        "treat_sets_decay": (
            _b(body["treat_sets_decay"], False) if "treat_sets_decay" in body else False
        ),
        # Missing key is ON. An explicit false stays off and adds no live key.
        "phys_ceiling": (_b(body["phys_ceiling"], True) if "phys_ceiling" in body else True),
        # Missing key is ON. An explicit false adds no live-dict field.
        "sub_hp": _b(body["sub_hp"], True) if "sub_hp" in body else True,
        # Missing or explicit false stays off. Only a true reaches the live dict.
        "offaxis_tail": _b(body["offaxis_tail"], False) if "offaxis_tail" in body else False,
        # Absent or box is the shoebox. A polygon word reaches Play and Render.
        "room_shape": (
            str(body.get("room_shape") or "box").strip().lower()
            if "room_shape" in body else None
        ),
        "surf_treatment": _surf_treatment(body.get("surf_treatment")),
        "surf_cal": _surf_cal(body.get("surf_cal")),
        # Missing stays room average. Surfaces mode posts true (D-SL2).
        "surf_directional": _b(body.get("surf_directional") if "surf_directional" in body else False, False),
        # Missing key is ON. Parity, flat, mirror/null, and direct-only store off.
        "smooth": bool(smooth_on),
        # Missing key is OFF. The engine forces 0 in the same cases as Smooth.
        "movement": _span(body.get("movement"), 0.0, 0.0, 100.0) if "movement" in body else 0.0,
        "mirror_null": bool(body.get("mirror_null") or body.get("null_mode")),
        "mic_setup": mic_setup,
        "head_yaw_deg": head_yaw,
        "binaural_preset": preset_id,
        "binaural_tail_mode": "diffuse_ic",
        "binaural_level_ref": "head_centre",
        "binaural_image_set": "binaural_rear32",
        "mic_gain_l": _span(body.get("mic_gain_l"), 1.0, 0.0, 16.0),
        "mic_gain_c": gain_c,
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
        "mic_hpf_l": mic_colour_fields["mic_hpf_l"],
        "mic_hpf_r": mic_colour_fields["mic_hpf_r"],
        "sample_rate": body.get("sample_rate"),
        "colour_rev": body.get("colour_rev") or "",
        "pair_mode": str(body.get("pair_mode") or ""),
        "pan_law": str(body.get("pan_law") or "linear"),
        "mic_route_l": str(body.get("mic_route_l") or body.get("route_l") or "pan"),
        "mic_route_c": str(body.get("mic_route_c") or body.get("route_c") or "pan"),
        "mic_route_r": str(body.get("mic_route_r") or body.get("route_r") or "pan"),
        "third_mic": third,
        "ms_s": str(body.get("ms_s") or "l"),
        "ms_m": str(body.get("ms_m") or "c"),
        "s_detached": _b(body.get("s_detached"), False),
        "link_mode": str(body.get("link_mode") or ""),
        "mic_x_l": body.get("mic_x_l"),
        "mic_y_l": body.get("mic_y_l"),
        "mic_z_l": body.get("mic_z_l"),
        "mic_x_c": body.get("mic_x_c"),
        "mic_y_c": body.get("mic_y_c"),
        "mic_z_c": body.get("mic_z_c"),
        "mic_x_r": body.get("mic_x_r"),
        "mic_y_r": body.get("mic_y_r"),
        "mic_z_r": body.get("mic_z_r"),
        "mic_pos_l": body.get("mic_pos_l"),
        "mic_pos_c": body.get("mic_pos_c"),
        "mic_pos_r": body.get("mic_pos_r"),
    }
    _bloom_keys = (
        "bloom_amount", "bloom_preset", "bloom_colour", "glue_colour",
        "pre_colour", "pre_drive_db", "predelay_ms",
        "bloom_attack_scale", "bloom_release_scale",
    )
    if any(k in body for k in _bloom_keys):
        out["bloom_preset"] = str(body.get("bloom_preset") or "natural")
        out["bloom_amount"] = _f(body.get("bloom_amount"), 0.0)
        out["bloom_colour"] = _b(body.get("bloom_colour"), False)
        out["glue_colour"] = _b(body.get("glue_colour"), False)
        out["pre_colour"] = str(body.get("pre_colour") or "off")
        out["pre_drive_db"] = _f(body.get("pre_drive_db"), 0.0)
        out["predelay_ms"] = _f(body.get("predelay_ms"), 0.0)
        out["bloom_attack_scale"] = _f(body.get("bloom_attack_scale"), 1.0)
        out["bloom_release_scale"] = _f(body.get("bloom_release_scale"), 1.0)
    for _ch in ("l", "c", "r"):
        _pk = "place_" + _ch
        if _pk in body and body.get(_pk) not in (None, ""):
            out[_pk] = "room" if str(body.get(_pk)).strip().lower() == "room" else "array"
    _route_keys = (
        "array_amount", "array_preset", "array_pre", "array_drive_db",
        "room_amount", "room_preset", "room_pre", "room_drive_db",
    )
    if any(k in body for k in _route_keys):
        for _prefix in ("array", "room"):
            out[_prefix + "_preset"] = str(body.get(_prefix + "_preset") or "natural")
            out[_prefix + "_amount"] = _f(body.get(_prefix + "_amount"), 0.0)
            out[_prefix + "_pre"] = str(body.get(_prefix + "_pre") or "off")
            out[_prefix + "_drive_db"] = _f(body.get(_prefix + "_drive_db"), 0.0)
    return out


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
    """Missing preset/mode → U87 Ai Cardioid × 3 and MEASURED_SHELF.

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
        "mic_hpf_l": bool(body.get("mic_hpf_l")) if "mic_hpf_l" in body else None,
        "mic_hpf_r": bool(body.get("mic_hpf_r")) if "mic_hpf_r" in body else None,
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
            "pair_mode": p.get("pair_mode") or "",
            "pan_law": p.get("pan_law") or "linear",
            "mic_route_l": p.get("mic_route_l") or "pan",
            "mic_route_c": p.get("mic_route_c") or "pan",
            "mic_route_r": p.get("mic_route_r") or "pan",
            "third_mic": p.get("third_mic") or "",
            "ms_s": p.get("ms_s") or "l",
            "ms_m": p.get("ms_m") or "c",
            "s_detached": bool(p.get("s_detached")),
            "link_mode": p.get("link_mode") or "",
            "mic_x_l": p.get("mic_x_l"),
            "mic_y_l": p.get("mic_y_l"),
            "mic_z_l": p.get("mic_z_l"),
            "mic_x_c": p.get("mic_x_c"),
            "mic_y_c": p.get("mic_y_c"),
            "mic_z_c": p.get("mic_z_c"),
            "mic_x_r": p.get("mic_x_r"),
            "mic_y_r": p.get("mic_y_r"),
            "mic_z_r": p.get("mic_z_r"),
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
def api_geometry(body: dict):
    p = params_from_body(body)
    return _attach_warnings(geometry_payload(p), body)


@app.post("/api/live_params")
def api_live_params(body: dict):
    """Running-FDN coefficients for the AudioWorklet. Same algebra as Render."""
    try:
        src = body or {}
        p = params_from_body(src)
        return _attach_warnings(live_fdn_params(p), src)
    except BadParam:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"live_params: {e}"}, status_code=500)



def _image_mic_override(p: dict, stand_mics: dict):
    """Room-mic spots for the lattice only. No keys means None (stand payload)."""
    from desk_matrix import position_override

    out = {}
    for letter, slot in (("L", "l"), ("C", "c"), ("R", "r")):
        base = stand_mics.get(letter) or {}
        fallback = (
            float(base.get("x", 0.0)),
            float(base.get("y", 0.0)),
            float(base.get("z", 0.0)),
        )
        ov = position_override(p, slot, fallback)
        if ov is None:
            continue
        if (
            abs(ov[0] - fallback[0]) < 1e-9
            and abs(ov[1] - fallback[1]) < 1e-9
            and abs(ov[2] - fallback[2]) < 1e-9
        ):
            continue
        out[letter] = ov
    return out or None


def _images_payload(p: dict, mics, mic_override=None):
    return build_images_payload(
        W=p["W"], H=p["H"], L=p["L"],
        mz=p["mz"], my=p["my"], space=p["space"],
        diverg=p["diverg"], sox=p["sox"], soz=p["soz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        mics=mics,
        hadamard_n=p["hadamard_n"],
        sy=p.get("sy"), sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
        two_sources=bool(p.get("two_sources")),
        sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"),
        mic_override=mic_override,
    )


@app.post("/api/images")
def api_images(body: dict):
    """Early-field image lattice + folded paths + last legs for selected mics."""
    p = params_from_body(body)
    raw_mics = body.get("mics") or body.get("selected_mics") or ["C"]
    if isinstance(raw_mics, str):
        raw_mics = [m.strip() for m in raw_mics.split(",") if m.strip()]
    mics = [str(m).upper() for m in raw_mics]
    # Accept "all"
    if len(mics) == 1 and mics[0] == "ALL":
        mics = ["L", "C", "R"]
    payload = _images_payload(p, mics)
    override = _image_mic_override(p, payload.get("mics") or {})
    if override:
        payload = _images_payload(p, mics, override)
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
def api_source_preview(body: dict):
    """Polar in the source frame, plus what the centre mic hears on the direct."""
    try:
        src = body or {}
        p = params_from_body(src)
        freq = float(src.get("freq") or 1000.0)
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
        return _attach_warnings(pattern, src)
    except BadParam:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"source_preview: {e}"}, status_code=500)


_BLOOM_RENDER_KEYS = (
    "bloom_amount", "bloom_preset", "bloom_colour", "glue_colour",
    "pre_colour", "pre_drive_db", "predelay_ms",
    "bloom_attack_scale", "bloom_release_scale",
)


_ROUTE_RENDER_KEYS = (
    "array_amount", "array_preset", "array_pre", "array_drive_db",
    "room_amount", "room_preset", "room_pre", "room_drive_db",
)


def _routing_render_kw(p: dict) -> dict:
    """Array and room inserts. Absent stays off. Master stays the Bloom keys."""
    if not any(k in p for k in _ROUTE_RENDER_KEYS):
        return {}

    def side(prefix: str) -> dict:
        return {
            prefix + "_preset": str(p.get(prefix + "_preset") or "natural"),
            prefix + "_amount": float(p.get(prefix + "_amount") or 0.0),
            prefix + "_pre": str(p.get(prefix + "_pre") or "off"),
            prefix + "_drive_db": float(p.get(prefix + "_drive_db") or 0.0),
        }

    out = {}
    out.update(side("array"))
    out.update(side("room"))
    return out


def _bloom_render_kw(p: dict) -> dict:
    """Forward Bloom only when the body carried a Bloom key. Absent stays the render default."""
    if not any(k in p for k in _BLOOM_RENDER_KEYS):
        return {}
    return {
        "bloom_preset": str(p.get("bloom_preset") or "natural"),
        "bloom_amount": float(p.get("bloom_amount") or 0.0),
        "bloom_attack_scale": float(p.get("bloom_attack_scale") if p.get("bloom_attack_scale") is not None else 1.0),
        "bloom_release_scale": float(p.get("bloom_release_scale") if p.get("bloom_release_scale") is not None else 1.0),
        "predelay_ms": float(p.get("predelay_ms") or 0.0),
        "bloom_colour": bool(p.get("bloom_colour")),
        "glue_colour": bool(p.get("glue_colour")),
        "pre_colour": str(p.get("pre_colour") or "off"),
        "pre_drive_db": float(p.get("pre_drive_db") or 0.0),
    }


def _render_impl(
    file: UploadFile,
    params_json: str,
):
    try:
        body = json.loads(params_json or "{}")
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "Invalid params JSON"}, status_code=400)

    p = params_from_body(body)
    from mic_colour.preset_store import DEFAULT_PRESET_ID
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
            smooth=bool(p.get("smooth", True)),
            movement=float(p.get("movement") or 0.0),
            mirror_null=bool(p.get("mirror_null")),
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
            mic_preset_l=p.get("mic_preset_l") or DEFAULT_PRESET_ID,
            mic_preset_c=p.get("mic_preset_c") or DEFAULT_PRESET_ID,
            mic_preset_r=p.get("mic_preset_r") or DEFAULT_PRESET_ID,
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
            desk=p,
            mic_hpf_l=p.get("mic_hpf_l"),
            mic_hpf_r=p.get("mic_hpf_r"),
            decay_mode=p.get("decay_mode") or "flat",
            phys_ceiling=bool(p.get("phys_ceiling")),
            sub_hp=bool(p.get("sub_hp")),
            offaxis_tail=bool(p.get("offaxis_tail")),
            room_shape=p.get("room_shape"),
            surf_treatment=p.get("surf_treatment"),
            surf_cal=p.get("surf_cal"),
            # SL4. Missing or false stays room average. Surfaces-only.
            surf_directional=bool(p.get("surf_directional")),
            prox_l=bool(p.get("prox_l", True)),
            prox_c=bool(p.get("prox_c", True)),
            prox_r=bool(p.get("prox_r", True)),
            **_bloom_render_kw(p),
            **_routing_render_kw(p),
        )
        out = default_out_path()
        meta = write_wav_stereo(str(out), Lch, Rch, sr)
        publish_out_copy(out)
    except Exception as e:
        Path(src).unlink(missing_ok=True)
        return JSONResponse({"ok": False, "error": f"Render failed: {e}"}, status_code=500)
    Path(src).unlink(missing_ok=True)

    preview = replace_preview(out)

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
    if info.get("fdn_ms") is not None:
        status += (
            f"\nFDN {float(info['fdn_ms']) / 1000.0:.2f} s"
            f"  T60 {float(info.get('t60_s') or 0.0):.2f} s"
        )
    lim_n = int(info.get("limiter_samples") or 0)
    lim_line = limiter_message(float(info.get("limiter_db") or 0.0), lim_n)
    if lim_line:
        status = lim_line + "\n" + status
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
    payload = {
        "ok": True,
        "preview_url": f"/api/preview?path={preview}",
        "out_path": str(out),
        "status": status,
        "geometry": geometry_payload(p),
        "duration_s": meta["duration_s"],
        "limiter_db": float(info.get("limiter_db") or 0.0),
        "limiter_samples": int(info.get("limiter_samples") or 0),
        "colour": colour,
        "surfaces": surfaces_payload(p.get("surfaces") or default_surfaces()),
    }
    return _attach_warnings(payload, body)


@app.post("/api/render")
def api_render(
    file: UploadFile = File(...),
    params_json: str = Form("{}"),
):
    """One render at a time. A second call does not queue."""
    if not _render_lock.acquire(blocking=False):
        return {"ok": False, "error": "render busy"}
    try:
        return _render_impl(file, params_json)
    finally:
        _render_lock.release()


@app.get("/api/preview")
def api_preview(path: str):
    try:
        fp = Path(path).resolve()
    except OSError:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if fp.suffix.lower() != ".wav":
        return JSONResponse({"error": "not found"}, status_code=404)
    temp = Path(tempfile.gettempdir()).resolve()
    renders = (ROOT / "renders").resolve()
    try:
        allowed = fp.is_relative_to(temp) or fp.is_relative_to(renders)
    except ValueError:
        allowed = False
    if not allowed:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if not fp.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
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
        "sets": load_material_sets(),
    }


@app.post("/api/room_result")
def api_room_result(body: dict):
    """SL1: Room result model (read-only, no audio). T(f) per 1/3 octave, faces vs faces + air, target,
    Schroeder, EBU Tm with pass/fail, axial modes. Treatment rows (SL5) count once accepted."""
    import numpy as _np
    import surf_panels as _SP
    import surf_target as _ST
    p = params_from_body(body)
    rows = p.get("surf_treatment") or []
    cards = _SP.cards_with_treatment(p["surfaces"], rows)
    out = _ST.room_result(p["W"], p["H"], p["L"], p["surfaces"], float(p.get("humidity") or 0.0),
                          decay_s=p.get("decay_s"), decay_lock=bool(p.get("decay_lock")), cards_with_fn=cards,
                          rendered_t20=body.get("rendered_t20") if isinstance(body.get("rendered_t20"), dict) else None)
    out["decay_mode"] = p.get("decay_mode", "flat")
    out["rows"] = rows
    out["rows_problems"] = _SP.validate_rows(rows)
    face_alpha = {}
    for k, c in cards.items():
        face_alpha[k] = [round(float(x), 4) for x in _ST.card_alpha(c, _np.asarray(out["f"], float))]
    out["face_alpha"] = face_alpha
    out["ok"] = True
    return out


@app.post("/api/auto_treat")
def api_auto_treat(body: dict):
    """SL6. Suggest Treatment rows. Nothing is written onto the scene.

    body.t_mid is seconds or "ebu". Accepted rows count. Suggested rows are
    ignored. The caller keeps the list until Accept.
    """
    import surf_autotreat as _AT
    p = params_from_body(body or {})
    W, H, L = p["W"], p["H"], p["L"]
    t_mid = (body or {}).get("t_mid")
    if t_mid == "ebu":
        t_mid = _AT.ebu_preset_t_mid(W, H, L)
    try:
        t_mid = float(t_mid if t_mid is not None else (p.get("decay_s") or 0.8))
    except (TypeError, ValueError):
        raise BadParam("t_mid")
    t_mid = min(max(t_mid, 0.15), 6.0)
    accepted = [r for r in (p.get("surf_treatment") or []) if not r.get("suggested")]
    out = _AT.auto_treat(W, H, L, p["surfaces"], float(p.get("humidity") or 0.0), t_mid, existing_rows=accepted)
    out["t_mid"] = round(t_mid, 3)
    out["ok"] = True
    return out


@app.post("/api/make_panel")
def api_make_panel(body: dict):
    """SL5. One tuned row for the Treatment list. Below 300 Hz, else null.

    The page puts the row on the selected face. Helmholtz stays on the
    formula f0 and Q 3.
    """
    import surf_autotreat as _AT
    p = params_from_body(body or {})
    try:
        f0 = float((body or {}).get("f0"))
    except (TypeError, ValueError):
        raise BadParam("f0")
    accepted = [r for r in (p.get("surf_treatment") or []) if not r.get("suggested")]
    return {"ok": True, "row": _AT.make_it_a_panel(f0, p["W"], p["H"], p["L"], accepted)}


def _impulse_render(p: dict, **over):
    """One-sample Render of a scene. Same kwargs the slow SL tests use."""
    import inspect
    import numpy as np
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    kw.update(over)
    yl, yr, info = render(dry, 48000, **kw)
    ir = np.stack([np.asarray(yl, float), np.asarray(yr, float)], 1)
    return ir, info


@app.post("/api/surf_calibrate")
def api_surf_calibrate(body: dict):
    """D-SL4. One impulse Render, T20 per octave, factors, a second Render.

    Surfaces only. Stores nothing itself: the page keeps surf_cal on the scene
    and Play posts that list. Factors stay inside 0.6-1.6. A band that gets
    more than 10 points worse is refused and the factors are not returned.
    """
    import numpy as np
    import surf_loop as _SL
    if not _render_lock.acquire(blocking=False):
        return JSONResponse({"ok": False, "error": "render busy"}, status_code=409)
    try:
        p = params_from_body(body or {})
        if str(p.get("decay_mode") or "flat").lower() != "surfaces":
            return {"ok": False, "error": "Calibrate is Surfaces only"}
        directional = bool(p.get("surf_directional"))
        ir0, info0 = _impulse_render(p, surf_directional=directional, surf_cal=None)
        surf0 = info0.get("surf") or {}
        target = surf0.get("target_T_oct")
        if not target:
            return {"ok": False, "error": "no Surfaces target"}
        t20_before = _SL.t20_per_octave(ir0.sum(1))
        cal = _SL.factors_for_calibrate(t20_before, target, directional)
        ir1, info1 = _impulse_render(p, surf_directional=directional, surf_cal=cal)
        t20_after = _SL.t20_per_octave(ir1.sum(1))
        tgt = np.asarray(target, float)
        before = np.abs(np.asarray(t20_before, float) / tgt - 1.0)
        after = np.abs(np.asarray(t20_after, float) / tgt - 1.0)
        finite = np.isfinite(before) & np.isfinite(after)
        if finite.any() and bool(np.any(after[finite] > before[finite] + 0.10)):
            return {"ok": False, "error": "calibration made a band worse by more than 10 points"}
        bands = [int(x) for x in _SL.OCT]
        n_ok = int(np.sum(finite & (after <= 0.10))) if finite.any() else 0
        return {
            "ok": True,
            "surf_cal": cal,
            "surf_directional": directional,
            "rendered_t20": {"f": bands, "t20": [None if not np.isfinite(x) else round(float(x), 4) for x in t20_after]},
            "n_within_10": n_ok,
            "n_bands": int(len(tgt)),
        }
    except BadParam:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Calibrate failed: {e}"}, status_code=500)
    finally:
        _render_lock.release()


@app.post("/api/phys_preview")
def api_phys_preview(body: dict):
    """Read-only octave ceiling. Not a live-dict key.

    The knob stays the armed dial. The row is this room's T_phys(f; k),
    the same helper the pack uses. k is solved for this room so the
    500 Hz-1 kHz mean equals the dial. Lock off omits the pack, so the
    row is not applied.
    """
    import surf_loop as _SLP
    import surf_panels as _SP
    p = params_from_body(body or {})
    on = bool(p.get("phys_ceiling"))
    dial = float(p.get("decay_s") or 0.0)
    armed = bool(p.get("decay_lock")) and dial > 0.05
    if not on:
        return {"ok": True, "on": False, "armed": armed, "dial_s": dial}
    if not armed:
        return {"ok": True, "on": True, "armed": False, "dial_s": dial}
    cards = _SP.cards_with_treatment(p["surfaces"], p.get("surf_treatment") or [])
    state = _SLP.phys_ceiling_row(p["W"], p["H"], p["L"], cards, dial)
    bands = []
    for hz, t in zip(state["hz"], state["t"]):
        bands.append({"hz": int(hz), "t": round(float(t), 4)})
    return {
        "ok": True,
        "on": True,
        "armed": True,
        "dial_s": dial,
        "k": round(float(state["k"]), 6),
        "s": state["s"],
        "mean_500_1k": round(float(state["mid"]), 4),
        "reachable": bool(state["reachable"]),
        "reached_mid": round(float(state["reached_mid"]), 4),
        "bands": bands,
    }


@app.post("/api/colour")
def api_colour(body: dict):
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
    from render_pipeline import _place_stand
    stand_mk = copy.copy(stand)
    stand = _place_stand(stand, p)
    taps = compute_taps(
        room, prep.source, stand, c=c, grid=grid, origin="corner",
        z_face_4l=False, hadamard_n=n_had,
        include_offaxis_shelf=mic_colour.include_offaxis_shelf,
        include_pattern=not mic_colour.measured,
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
    tail_sos = None
    if p.get("offaxis_tail"):
        from mic_colour.tail_diffuse import design_pack
        tail_sos = design_pack(
            (p.get("mic_preset_l"), p.get("mic_preset_c"), p.get("mic_preset_r")),
            sr,
            (p.get("polar_l"), p.get("polar_c"), p.get("polar_r")),
        )
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
        mic_gain_l=p.get("mic_gain_l", 1.0),
        mic_gain_c=p.get("mic_gain_c", 1.0),
        mic_gain_r=p.get("mic_gain_r", 1.0),
        mic_pan_l=p.get("mic_pan_l", -1.0),
        mic_pan_c=p.get("mic_pan_c", 0.0),
        mic_pan_r=p.get("mic_pan_r", 1.0),
        mic_phase_l=p.get("mic_phase_l", 1.0),
        mic_phase_c=p.get("mic_phase_c", 1.0),
        mic_phase_r=p.get("mic_phase_r", 1.0),
        desk=p,
        smooth=bool(p.get("smooth", True)),
        makeup_stand=stand_mk,
        makeup_source=prep.source,
        makeup_grid=grid,
        makeup_shelf=mic_colour.include_offaxis_shelf,
        tail_sos=tail_sos,
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
def api_polar(body: dict):
    """ASSUMED mic polar × frequency in mic–source plane (L/C/R + Sum)."""
    from mic_colour.preset_store import DEFAULT_PRESET_ID
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
        mic_preset_l=p.get("mic_preset_l") or DEFAULT_PRESET_ID,
        mic_preset_c=p.get("mic_preset_c") or DEFAULT_PRESET_ID,
        mic_preset_r=p.get("mic_preset_r") or DEFAULT_PRESET_ID,
        mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
        mic_hpf_sides=p.get("mic_hpf_sides"),
        mic_hpf_centre=p.get("mic_hpf_centre"),
        desk=p,
    )
    return payload



def fitter_model_path() -> Path:
    """Sibling mic_fitter package. app_server.py lives in software/."""
    return Path(__file__).resolve().parents[1] / "mic_fitter" / "mic_fitter" / "model.py"


def require_fitter() -> None:
    path = fitter_model_path()
    if not path.is_file():
        raise SystemExit("Cannot start: sibling mic_fitter/ is missing (" + str(path) + ")")


def main():
    require_fitter()
    print("2011 Room Reverb — Tweak App")
    print("Open http://127.0.0.1:7860")
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="info")


if __name__ == "__main__":
    main()
