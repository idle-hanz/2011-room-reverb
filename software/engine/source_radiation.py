"""Source radiation for Render and Play. One coefficient law for both.

The stage is the first filter on each image: source, then air, then the mic.
Omni, and any on-axis direction, is a bypass and is not called. The FDN inject
uses the preset's diffuse (power-averaged) filter, so the tail does not follow
yaw. Presets ship in ``software/presets/source``. TU Berlin fits stay in the
handoff pack and are not loaded from there.

Do not import ``source_fitter`` (the package is the research fitter).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

N_LINES = 32
# rad_on A,B + two sources × (diffuse 7 + direct 3×10 + image 32×10)
SRC_PACK_LEN = 2 + 2 * (7 + 3 * 10 + N_LINES * 10)


@dataclass
class Coef:
    gain: float = 1.0
    b0: float = 1.0
    b1: float = 0.0
    b2: float = 0.0
    a1: float = 0.0
    a2: float = 0.0
    pole_g: float = 0.0
    pole_mix: float = 0.0
    order: int = 1
    bypass: bool = True


BYPASS = Coef()


@dataclass
class Plan:
    diffuse: Coef
    direct: Tuple[Coef, Coef, Coef]
    images: List[Coef]


def is_omni(preset_id) -> bool:
    return str(preset_id or "omni").strip().lower() in ("", "omni", "off", "none")


def preset_roots() -> List[Path]:
    """Shipped presets first. The handoff pack is a fallback for local fits."""
    here = Path(__file__).resolve()
    local = here.parents[1] / "presets" / "source"
    pack = here.parents[2] / "handoff_source_radiation_for_build" / "source_fitter" / "presets"
    roots: List[Path] = []
    if (local / "omni.json").is_file():
        roots.append(local)
    if (pack / "omni.json").is_file():
        roots.append(pack)
    if not roots:
        roots.append(local)
    return roots


def _reject_tu(data: dict) -> None:
    pid = str(data.get("id") or "")
    dataset = str((data.get("provenance") or {}).get("dataset") or "")
    if pid.startswith("tu_") or "TU Berlin" in dataset:
        raise ValueError(f"{pid} is a TU Berlin fit and is not loaded")


def load_preset(preset_id: str) -> dict:
    """Preset JSON. Unknown ids and TU Berlin fits become omni."""
    key = str(preset_id or "omni").strip()
    if is_omni(key) or key.startswith("tu_"):
        key = "omni"
    path = None
    for root in preset_roots():
        cand = root / f"{key}.json"
        if cand.is_file():
            path = cand
            break
    if path is None:
        for root in preset_roots():
            cand = root / "omni.json"
            if cand.is_file():
                path = cand
                break
    if path is None:
        return {"id": "omni", "params": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        _reject_tu(data)
    except ValueError:
        return {"id": "omni", "params": {}}
    return data


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v):
    n = math.sqrt(_dot(v, v))
    if n < 1e-12:
        return (1.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def facing_basis(yaw_deg: float, pitch_deg: float, roll_deg: float = 0.0):
    """Rows (forward, left, up) in engine coords. Yaw 0 faces +Z. +yaw turns toward +X."""
    ps = math.radians(float(yaw_deg))
    th = math.radians(float(pitch_deg))
    f = (math.sin(ps) * math.cos(th), math.sin(th), math.cos(ps) * math.cos(th))
    u0 = (0.0, 1.0, 0.0)
    u = (u0[0] - f[0] * _dot(u0, f), u0[1] - f[1] * _dot(u0, f), u0[2] - f[2] * _dot(u0, f))
    if _dot(u, u) < 1e-18:
        u = (-math.sin(ps), 0.0, -math.cos(ps))
    u = _norm(u)
    left = _cross(u, f)
    if roll_deg:
        r = math.radians(float(roll_deg))
        c, s = math.cos(r), math.sin(r)
        left, u = (
            (c * left[0] + s * u[0], c * left[1] + s * u[1], c * left[2] + s * u[2]),
            (-s * left[0] + c * u[0], -s * left[1] + c * u[1], -s * left[2] + c * u[2]),
        )
    return (f, left, u)


def emission_dir(n, image_pos, receiver) -> Tuple[float, float, float]:
    """World direction the real source emits toward this receiver, mirrors undone."""
    v = [float(receiver[i]) - float(image_pos[i]) for i in range(3)]
    for i, k in enumerate(n):
        if abs(int(k)) % 2 == 1:
            v[i] = -v[i]
    return _norm(v)


def local_dir(e_world, basis) -> Tuple[float, float, float]:
    return (_dot(basis[0], e_world), _dot(basis[1], e_world), _dot(basis[2], e_world))


def _axis_frame(aim_az: float, aim_el: float):
    az, el = math.radians(aim_az), math.radians(aim_el)
    a = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    up = (-math.sin(el) * math.cos(az), -math.sin(el) * math.sin(az), math.cos(el))
    left = _cross(up, a)
    return a, left, up


def _params(preset: dict) -> dict:
    p = dict(preset.get("params") or {})
    defaults = {
        "lo_db": 0.0, "hi_db": 0.0, "f0": 2000.0, "shelf_s": 0.7, "p": 1.0, "q": 0.0,
        "b_ud": 0.0, "b_lr": 0.0, "aim_az": 0.0, "aim_el": 0.0, "lp_hz": 24000.0,
        "lp_mix": 0.0, "p_lo": 1.0, "dip": 0.0, "lp_order": 1.0,
    }
    for k, v in defaults.items():
        if p.get(k) is None:
            p[k] = v
    return p


def weight_k2(params: dict, d_local) -> Tuple[float, float]:
    """(k_lo, k_hi). Both are 0 when the direction is the radiation axis."""
    a, left, up = _axis_frame(float(params["aim_az"]), float(params["aim_el"]))
    c = max(-1.0, min(1.0, _dot(d_local, a)))
    u = 0.5 * (1.0 - c)
    back = 1.0 - float(params["q"]) * (u ** 8)
    A = max(0.0, 1.0 + float(params["b_ud"]) * _dot(d_local, up) + float(params["b_lr"]) * _dot(d_local, left))
    k_hi = A * (u ** float(params["p"])) * back
    dip = float(params.get("dip") or 0.0)
    p_lo = float(params.get("p_lo") if params.get("p_lo") is not None else params["p"])
    k_lo = A * ((1.0 - dip) * (u ** p_lo) * back + dip * 4.0 * u * (1.0 - u))
    return k_lo, k_hi


def rbj_high_shelf(f0: float, gain_db: float, slope: float, fs: float):
    """RBJ high shelf, (b0, b1, b2, a1, a2), a0 normalised to 1."""
    A = 10.0 ** (float(gain_db) / 40.0)
    w0 = 2.0 * math.pi * min(float(f0), 0.45 * float(fs)) / float(fs)
    cw, sw = math.cos(w0), math.sin(w0)
    s = float(slope) if float(slope) > 1e-6 else 0.7
    alpha = sw / 2.0 * math.sqrt(max((A + 1.0 / A) * (1.0 / s - 1.0) + 2.0, 1e-9))
    sa = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cw + sa)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cw - sa)
    a0 = (A + 1.0) - (A - 1.0) * cw + sa
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cw)
    a2 = (A + 1.0) - (A - 1.0) * cw - sa
    if abs(a0) < 1e-18:
        return (1.0, 0.0, 0.0, 0.0, 0.0)
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def one_pole_g(fc: float, fs: float) -> float:
    return 1.0 - math.exp(-2.0 * math.pi * float(fc) / float(fs))


def coef_for_dir(params: dict, d_local, fs: float, size_scale: float = 1.0) -> Coef:
    k_lo, k = weight_k2(params, d_local)
    if (k <= 0.0 and k_lo <= 0.0) or (
        float(params["lo_db"]) == 0.0 and float(params["hi_db"]) == 0.0 and float(params["lp_mix"]) == 0.0
    ):
        return BYPASS
    scale = float(size_scale) if float(size_scale) > 1e-6 else 1.0
    g = 10.0 ** (k_lo * float(params["lo_db"]) / 20.0)
    b0, b1, b2, a1, a2 = rbj_high_shelf(
        float(params["f0"]) / scale, k * float(params["hi_db"]), float(params["shelf_s"]), fs,
    )
    pg, pm = 0.0, 0.0
    if float(params["lp_mix"]) > 1e-6 and k > 0.0:
        fc = float(params["lp_hz"]) / scale / k
        if fc < 0.45 * float(fs):
            pg = one_pole_g(fc, fs)
            pm = float(params["lp_mix"])
    order = int(params.get("lp_order") or 1)
    if order < 1:
        order = 1
    if order > 2:
        order = 2
    return Coef(g, b0, b1, b2, a1, a2, pg, pm, order, False)


def diffuse_coef(preset: dict, fs: float, size_scale: float = 1.0) -> Coef:
    """Power-averaged inject filter. Independent of yaw."""
    if is_omni(preset.get("id")):
        return BYPASS
    d = preset.get("diffuse_inject") or {}
    if not d:
        return BYPASS
    scale = float(size_scale) if float(size_scale) > 1e-6 else 1.0
    b0, b1, b2, a1, a2 = rbj_high_shelf(
        float(d.get("shelf_f0") or 1500.0) / scale,
        float(d.get("shelf_gain_db") or 0.0),
        float(d.get("shelf_s") or 0.7),
        fs,
    )
    g = 10.0 ** (float(d.get("gain_db") or 0.0) / 20.0)
    if abs(g - 1.0) < 1e-8 and abs(b0 - 1.0) < 1e-8 and abs(b1) < 1e-8 and abs(b2) < 1e-8:
        return BYPASS
    return Coef(g, b0, b1, b2, a1, a2, 0.0, 0.0, 1, False)


def _size_scale(preset: dict, size_m) -> float:
    if size_m is None:
        return 1.0
    try:
        user = float(size_m)
    except (TypeError, ValueError):
        return 1.0
    a = float((preset.get("size") or {}).get("a_eq_m") or 0.0)
    if a <= 0.0 or user <= 0.0:
        return 1.0
    return max(1e-3, user / a)


def plan_from_scene(
    preset_id,
    yaw_deg: float,
    pitch_deg: float,
    taps,
    source,
    mic_centre,
    capsules,
    sr: float,
    size_m=None,
    roll_deg: float = 0.0,
) -> Optional[Plan]:
    """None when the preset is omni: callers must not run the stage."""
    if is_omni(preset_id):
        return None
    preset = load_preset(str(preset_id))
    if is_omni(preset.get("id")):
        return None
    params = _params(preset)
    scale = _size_scale(preset, size_m)
    fs = float(sr)
    basis = facing_basis(yaw_deg, pitch_deg, roll_deg)
    images: List[Coef] = []
    n_t = len(taps) if taps is not None else 0
    for i in range(N_LINES):
        if n_t <= 0:
            images.append(BYPASS)
            continue
        t = taps[i % n_t]
        e = emission_dir(t.n, t.position, mic_centre)
        images.append(coef_for_dir(params, local_dir(e, basis), fs, scale))
    direct = []
    for cap in capsules:
        e = emission_dir((0, 0, 0), source, cap)
        direct.append(coef_for_dir(params, local_dir(e, basis), fs, scale))
    while len(direct) < 3:
        direct.append(BYPASS)
    return Plan(diffuse_coef(preset, fs, scale), (direct[0], direct[1], direct[2]), images)


def src_process(x, coef: Coef):
    """gain, then RBJ TDF-II, then the soft one-pole. Bypass returns the same array."""
    import numpy as np

    if coef is None or coef.bypass:
        return x
    y = np.empty_like(x, dtype=np.float64)
    z1 = z2 = pz = pz2 = 0.0
    g, b0, b1, b2, a1, a2 = coef.gain, coef.b0, coef.b1, coef.b2, coef.a1, coef.a2
    pg, pm, order = coef.pole_g, coef.pole_mix, int(coef.order)
    for i in range(len(x)):
        v = g * float(x[i])
        o = b0 * v + z1
        z1 = b1 * v - a1 * o + z2
        z2 = b2 * v - a2 * o
        if pg > 0.0:
            pz += pg * (o - pz)
            lp = pz
            if order >= 2:
                pz2 += pg * (pz - pz2)
                lp = pz2
            o = (1.0 - pm) * o + pm * lp
        y[i] = o
    return y


def apply_coef(buf, coef: Optional[Coef]):
    if coef is None or coef.bypass:
        return buf
    return src_process(buf, coef)


def _push_diff(a: list, c: Optional[Coef]) -> None:
    if c is None or c.bypass:
        a += [1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    else:
        a += [c.gain, c.b0, c.b1, c.b2, c.a1, c.a2, 1.0]


def _push_full(a: list, c: Optional[Coef]) -> None:
    if c is None or c.bypass:
        a += [1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    else:
        a += [c.gain, c.b0, c.b1, c.b2, c.a1, c.a2, c.pole_g, c.pole_mix, float(c.order), 1.0]


def _push_source(a: list, plan: Optional[Plan]) -> None:
    if plan is None:
        _push_diff(a, None)
        for _ in range(3):
            _push_full(a, None)
        for _ in range(N_LINES):
            _push_full(a, None)
        return
    _push_diff(a, plan.diffuse)
    for i in range(3):
        _push_full(a, plan.direct[i])
    for i in range(N_LINES):
        _push_full(a, plan.images[i] if i < len(plan.images) else None)


def pack_play(plan_a: Optional[Plan], plan_b: Optional[Plan]) -> list:
    """SRC_RAD payload. Empty when both sources are omni (the bit-exact path)."""
    if plan_a is None and plan_b is None:
        return []
    a = [1.0 if plan_a is not None else 0.0, 1.0 if plan_b is not None else 0.0]
    _push_source(a, plan_a)
    _push_source(a, plan_b)
    if len(a) != SRC_PACK_LEN:
        raise RuntimeError(f"SRC_RAD pack {len(a)} != {SRC_PACK_LEN}")
    return a


def yaw_pitch_toward(source, target) -> Tuple[float, float]:
    """Yaw and pitch that point the source at a receiver. Yaw 0 faces +Z."""
    dx = float(target[0]) - float(source[0])
    dy = float(target[1]) - float(source[1])
    dz = float(target[2]) - float(source[2])
    yaw = math.degrees(math.atan2(dx, dz))
    pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return yaw, pitch


def _pose_missing(v) -> bool:
    """Null or blank follows A. Zero is a real angle."""
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    try:
        x = float(v)
    except (TypeError, ValueError):
        return True
    return x != x


def effective_b_pose(p: dict) -> Tuple[str, float, float]:
    """Preset, yaw and pitch that source B plays.

    A null preset, yaw or pitch follows A. With mirror on and a null yaw,
    yaw is −yaw_A. An explicit "omni" stays omni, so an old save still loads.
    Size stays the one shared source_size_m. The JS twin is RoomMath.effectiveBPose.
    """
    preset_a = str(p.get("source_radiation") or "omni")
    yaw_a = 0.0 if _pose_missing(p.get("source_yaw")) else float(p.get("source_yaw"))
    pitch_a = 0.0 if _pose_missing(p.get("source_pitch")) else float(p.get("source_pitch"))
    mirror = bool(p.get("mirror_b")) if "mirror_b" in p and p.get("mirror_b") is not None else True
    raw_preset = p.get("source_radiation_b")
    if raw_preset is None or (isinstance(raw_preset, str) and not raw_preset.strip()):
        preset = preset_a
    else:
        preset = str(raw_preset)
    if _pose_missing(p.get("source_yaw_b")):
        yaw = -yaw_a if mirror else yaw_a
    else:
        yaw = float(p.get("source_yaw_b"))
    if _pose_missing(p.get("source_pitch_b")):
        pitch = pitch_a
    else:
        pitch = float(p.get("source_pitch_b"))
    return preset, float(yaw), float(pitch)


def response_db(coef: Optional[Coef], freq_hz: float, fs: float) -> float:
    """Magnitude of gain × shelf × soft one-pole. Bypass is 0 dB."""
    if coef is None or coef.bypass:
        return 0.0
    w = 2.0 * math.pi * float(freq_hz) / float(fs)
    z1 = complex(math.cos(-w), math.sin(-w))
    z2 = z1 * z1
    den = 1.0 + coef.a1 * z1 + coef.a2 * z2
    if abs(den) < 1e-18:
        return -120.0
    h = coef.gain * (coef.b0 + coef.b1 * z1 + coef.b2 * z2) / den
    if coef.pole_g > 0.0 and coef.pole_mix > 0.0:
        lp = coef.pole_g / (1.0 - (1.0 - coef.pole_g) * z1)
        if int(coef.order) >= 2:
            lp = lp * lp
        h *= (1.0 - coef.pole_mix) + coef.pole_mix * lp
    mag = abs(h)
    if mag < 1e-12:
        return -120.0
    return 20.0 * math.log10(mag)


def _local_from_angles(az_deg: float, el_deg: float) -> Tuple[float, float, float]:
    """Source frame. Azimuth 0 is forward, positive azimuth is toward source left."""
    az = math.radians(float(az_deg))
    el = math.radians(float(el_deg))
    return (
        math.cos(el) * math.cos(az),
        math.cos(el) * math.sin(az),
        math.sin(el),
    )


def _angles_from_local(d) -> Tuple[float, float]:
    fwd, left, up = float(d[0]), float(d[1]), float(d[2])
    az = math.degrees(math.atan2(left, fwd))
    el = math.degrees(math.asin(max(-1.0, min(1.0, up))))
    return az, el


PREVIEW_FREQS = (250, 500, 1000, 2000, 4000, 8000)


def catalog() -> list:
    """Shipped preset index. TU Berlin ids are dropped."""
    rows = []
    for root in preset_roots():
        path = root / "index.json"
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("presets") or []:
            pid = str(row.get("id") or "")
            if pid.startswith("tu_") or "TU Berlin" in str(row.get("dataset") or ""):
                continue
            rows.append(row)
        if rows:
            break
    return rows


def preview_pattern(preset_id, size_m, fs: float = 48000.0) -> dict:
    """Polar curves in the source frame. Yaw and pitch rotate these on the client."""
    preset = load_preset(preset_id)
    omni = is_omni(preset.get("id"))
    angles = list(range(-180, 181, 5))
    size = preset.get("size") or {}
    a_eq = float(size.get("a_eq_m") or 0.0)
    onset = float(size.get("beaming_onset_hz") or 0.0)
    params = _params(preset)
    if omni:
        flat = {str(f): [0.0] * len(angles) for f in PREVIEW_FREQS}
        return {
            "omni": True,
            "id": "omni",
            "angles": angles,
            "horizontal": flat,
            "vertical": flat,
            "a_eq_m": a_eq,
            "onset_hz": onset,
            "aim_az": 0.0,
            "aim_el": 0.0,
            "diffuse_text": "Omni. The tail is the unfiltered inject.",
            "diffuse_db": {str(f): 0.0 for f in PREVIEW_FREQS},
        }
    scale = _size_scale(preset, size_m)
    if a_eq > 0.0 and scale != 1.0:
        onset = onset / scale if onset else (340.0 / (2.0 * math.pi * a_eq * scale))
    horiz = {}
    vert = {}
    for freq in PREVIEW_FREQS:
        horiz[str(freq)] = []
        vert[str(freq)] = []
        for ang in angles:
            ch = coef_for_dir(params, _local_from_angles(ang, 0.0), fs, scale)
            cv = coef_for_dir(params, _local_from_angles(0.0, ang), fs, scale)
            horiz[str(freq)].append(round(response_db(ch, freq, fs), 2))
            vert[str(freq)].append(round(response_db(cv, freq, fs), 2))
    diff = diffuse_coef(preset, fs, scale)
    diffuse_db = {str(f): round(response_db(diff, f, fs), 2) for f in PREVIEW_FREQS}
    inj = preset.get("diffuse_inject") or {}
    shelf_db = float(inj.get("shelf_gain_db") or 0.0)
    shelf_f = float(inj.get("shelf_f0") or 0.0)
    if inj:
        diffuse_text = (
            f"{shelf_db:.1f} dB shelf at {shelf_f / 1000.0:.2f} kHz: does not change with yaw"
        )
    else:
        diffuse_text = "No diffuse shelf on this preset."
    return {
        "omni": False,
        "id": str(preset.get("id") or preset_id),
        "angles": angles,
        "horizontal": horiz,
        "vertical": vert,
        "a_eq_m": a_eq,
        "onset_hz": round(onset, 1) if onset else 0.0,
        "aim_az": float(params.get("aim_az") or 0.0),
        "aim_el": float(params.get("aim_el") or 0.0),
        "diffuse_text": diffuse_text,
        "diffuse_db": diffuse_db,
        "tag": preset.get("tag") or "",
        "label": preset.get("label") or "",
    }


def direct_db(preset_id, yaw_deg, pitch_deg, source, mic, freq_hz, size_m, fs: float = 48000.0) -> float:
    """Direct-path level at one frequency, source facing yaw/pitch, towards mic."""
    preset = load_preset(preset_id)
    if is_omni(preset.get("id")):
        return 0.0
    e = _norm((
        float(mic[0]) - float(source[0]),
        float(mic[1]) - float(source[1]),
        float(mic[2]) - float(source[2]),
    ))
    loc = local_dir(e, facing_basis(yaw_deg, pitch_deg))
    coef = coef_for_dir(_params(preset), loc, fs, _size_scale(preset, size_m))
    return response_db(coef, freq_hz, fs)


def _as_xyz(p) -> Tuple[float, float, float]:
    """Point as (x, y, z). The images API stores points as {x, y, z}."""
    if isinstance(p, dict):
        return (float(p.get("x") or 0.0), float(p.get("y") or 0.0), float(p.get("z") or 0.0))
    return (float(p[0]), float(p[1]), float(p[2]))


def annotate_taps(taps, preset_id, yaw_deg, pitch_deg, mic, size_m, fs: float = 48000.0) -> None:
    """Add source-frame az/el and 1 kHz / 4 kHz radiation dB onto path taps."""
    preset = load_preset(preset_id)
    omni = is_omni(preset.get("id"))
    params = _params(preset)
    scale = _size_scale(preset, size_m)
    basis = facing_basis(yaw_deg, pitch_deg)
    mic_xyz = _as_xyz(mic)
    for tap in taps or []:
        n = tap.get("n") or [0, 0, 0]
        try:
            img = _as_xyz(tap.get("image_xyz") or mic_xyz)
            e = emission_dir(n, img, mic_xyz)
        except (TypeError, ValueError, KeyError, IndexError):
            e = (0.0, 0.0, 1.0)
        loc = local_dir(e, basis)
        az, el = _angles_from_local(loc)
        if omni:
            db1 = db4 = 0.0
        else:
            coef = coef_for_dir(params, loc, fs, scale)
            db1 = response_db(coef, 1000.0, fs)
            db4 = response_db(coef, 4000.0, fs)
        tap["src_az_deg"] = round(az, 1)
        tap["src_el_deg"] = round(el, 1)
        tap["src_db_1k"] = round(db1, 2)
        tap["src_db_4k"] = round(db4, 2)
