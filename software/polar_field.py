#!/usr/bin/env python3
"""
3D polar field — microphone pattern × frequency in the mic–source plane.

Not image-arrival directions. Rings are 20 / 63 / 125 / 250 / 1k / 4k / 8k / 16k.

MEASURED and BYPASS
    radius = abs(capsule gain) × 10^(H_db(θ, f) / 20)
    H_db is fitter relative_db in MEASURED, and 0 in BYPASS.
    Manufacturer HPF stacks on that curve when it is engaged.
    The LF→omni morph is not used.

ASSUMED_TOYS
    The old display morph: low rings toward omni, high rings toward the pattern.
    That is the legacy picture, not the fitter.

The gain is early_field.capsule_gain (the tap scalar), taken absolute for the
drawing. This file does not add another cardioid equation.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

_ENGINE = Path(__file__).resolve().parent / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from early_field import look_vector as _look_vector  # noqa: E402  (K1: single yaw convention)
from early_field import (  # noqa: E402
    MicStand,
    PATTERN_CARDIOID,
    PATTERN_OMNI,
    SPEED_OF_SOUND_M_S,
    capsule_gain,
    cardioid_gain,
    centre_position,
    look_vector,
    mic_positions,
    normalize_pattern,
    prepare_direct_field,
    direct_field_from_metres,
)

Vec3 = Tuple[float, float, float]

# Drawing rings. Same list on the Mic desk and on POST /api/polar.
RING_HZ: Tuple[float, ...] = (20.0, 63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0, 16000.0)
RING_LABELS: Tuple[str, ...] = ("20", "63", "125", "250", "1k", "4k", "8k", "16k")

# ASSUMED_TOYS display only: log-frequency morph from omni (LF) toward the pattern.
_F_LO_HZ = 125.0
_F_HI_HZ = 4000.0
# Visual stack height along plane normal (metres, display units)
_FREQ_STACK_M = 2.4


def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _vadd(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _vmul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def _vdot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _vcross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _vnorm(a: Vec3) -> float:
    return math.sqrt(max(_vdot(a, a), 0.0))


def _vunit(a: Vec3, fallback: Vec3 = (0.0, 1.0, 0.0)) -> Vec3:
    n = _vnorm(a)
    if n < 1e-9:
        return fallback
    return (a[0] / n, a[1] / n, a[2] / n)


def freq_cardioid_mix(fc: float, car_omni: float) -> float:
    """ASSUMED: smooth LF→omni, HF→cardioid × Car/Omni (0…1)."""
    car = _clamp(float(car_omni), 0.0, 1.0)
    t = _clamp(
        math.log10(max(float(fc), 20.0) / _F_LO_HZ)
        / math.log10(_F_HI_HZ / _F_LO_HZ),
        0.0,
        1.0,
    )
    t = t * t * (3.0 - 2.0 * t)  # smoothstep
    return car * t


def pattern_radius(theta: float, mix: float) -> float:
    """Unit polar radius at angle θ from look (legacy car_omni blend)."""
    return float(cardioid_gain(theta, mix))


def pattern_abs(
    theta: float,
    pattern: str,
    *,
    family: Optional[str] = None,
    polar: Optional[float] = None,
) -> float:
    """Absolute capsule gain. Same scalar the taps use; drawings drop the sign."""
    return abs(capsule_gain(
        theta, family=family, polar=polar, pattern=pattern, signed=True
    ))


def pattern_radius_named(
    theta: float,
    pattern: str,
    freq_mix: float,
    *,
    family: Optional[str] = None,
    polar: Optional[float] = None,
) -> float:
    """ASSUMED_TOYS display: freq_mix 0 → omni, 1 → abs(capsule gain)."""
    full = pattern_abs(theta, pattern, family=family, polar=polar)
    if polar is None and normalize_pattern(pattern) == PATTERN_OMNI:
        return 1.0
    return float((1.0 - freq_mix) * 1.0 + freq_mix * full)


def _plane_dirs(n_az: int, plane: str) -> np.ndarray:
    """Unit directions in one plane. Index 0 is +Z (front).

    xz: φ increases from +Z toward −X, matching look = (−sin φ, 0, cos φ).
    yz: φ increases from +Z toward +Y.
    """
    phi = np.arange(n_az, dtype=float) * (2.0 * math.pi / float(n_az))
    if plane == "yz":
        return np.stack((np.zeros(n_az), np.sin(phi), np.cos(phi)), axis=1)
    return np.stack((-np.sin(phi), np.zeros(n_az), np.cos(phi)), axis=1)


def _halo_magnitude(
    dirs: np.ndarray,
    mics: Sequence[dict],
    centres: Sequence[float],
    mode: str,
    engaged: bool,
) -> np.ndarray:
    """|gL + gR + gC| on one plane. Spacing delay is in the sum.

    Mono fold of the desk is left + right = gL + gR + gC, because centre
    is mixed at half into each side. Left and right do cancel here. They
    do not cancel in the speakers.
    """
    n_az = int(len(dirs))
    freqs = np.asarray(list(centres), dtype=float)
    n_f = int(len(freqs))
    measured = _drops_lf_morph(mode)
    total = np.zeros((n_az, n_f), dtype=np.complex128)
    omega = 2.0 * math.pi * freqs
    for mic in mics:
        look = np.asarray(mic["look"], dtype=float)
        cos_t = np.clip(dirs @ look, -1.0, 1.0)
        theta = np.arccos(cos_t)
        signed = np.array([
            capsule_gain(
                float(th),
                family=mic["family"],
                polar=mic["polar"],
                pattern=mic["pattern"],
                signed=True,
            )
            for th in theta
        ], dtype=float)
        on = engaged if mic.get("hpf_on") is None else bool(mic.get("hpf_on"))
        if measured:
            db = _h_db_grid(theta, centres, mode, mic["model"], mic["hpf"], on)
            lin = np.power(10.0, db / 20.0).T
            amp = signed[:, None] * lin
        else:
            amp = np.zeros((n_az, n_f), dtype=float)
            for bi, fc in enumerate(freqs):
                mix = freq_cardioid_mix(float(fc), 1.0)
                for ai, th in enumerate(theta):
                    mag = pattern_radius_named(
                        float(th), mic["pattern"], mix,
                        family=mic["family"], polar=mic["polar"],
                    )
                    if abs(signed[ai]) <= 1e-8:
                        amp[ai, bi] = 0.0
                    else:
                        amp[ai, bi] = math.copysign(mag, signed[ai])
        proj = dirs @ np.asarray(mic["pos"], dtype=float)
        phase = np.exp(1j * omega[None, :] * proj[:, None] / SPEED_OF_SOUND_M_S)
        total += amp * phase
    return np.abs(total).T


def _drops_lf_morph(mode: str) -> bool:
    """MEASURED and BYPASS use H_db. The LF→omni morph stays on ASSUMED_TOYS."""
    from mic_colour.modes import ASSUMED_TOYS, parse_colour_mode
    return parse_colour_mode(mode) != ASSUMED_TOYS


def _h_db_grid(
    thetas: np.ndarray,
    centres: Sequence[float],
    mode: str,
    model: Any,
    hpf: Optional[dict],
    engaged: bool,
) -> np.ndarray:
    """H_db as (n_bands, n_az). Fitter on MEASURED only. HPF stacks on every mode."""
    from mic_colour.hpf import stack_hpf
    from mic_colour.model import relative_db
    from mic_colour.modes import fitter_on_for, parse_colour_mode

    freqs = np.asarray(list(centres), dtype=float)
    n_az = int(len(thetas))
    n_f = int(len(freqs))
    if fitter_on_for(parse_colour_mode(mode)) and model is not None:
        degs = np.degrees(np.asarray(thetas, dtype=float))
        raw = np.asarray(relative_db(model, freqs, degs), dtype=float)
        if raw.ndim == 1:
            raw = raw.reshape(1, -1)
        db = raw
    else:
        db = np.zeros((n_az, n_f), dtype=float)
    spec = hpf or {}
    db = np.asarray(
        stack_hpf(db, freqs, spec.get("hpf_hz"), spec.get("hpf_slope") or 12, bool(engaged)),
        dtype=float,
    )
    if db.ndim == 1:
        db = db.reshape(1, -1)
    return db.T


def _mic_source_plane(
    left: Vec3,
    right: Vec3,
    source: Vec3,
    centre: Vec3,
) -> Dict[str, Any]:
    """Plane through L, R, and source (near-horizontal; tilts if heights differ)."""
    v_lr = _vsub(right, left)
    v_cs = _vsub(source, centre)
    n = _vcross(v_lr, v_cs)
    if _vnorm(n) < 1e-8:
        n = (0.0, 1.0, 0.0)
        e1 = _vunit(v_lr, (1.0, 0.0, 0.0))
        e2 = _vunit(_vcross(n, e1), (0.0, 0.0, 1.0))
        n = _vunit(_vcross(e1, e2), (0.0, 1.0, 0.0))
    else:
        n = _vunit(n)
        if n[1] < 0.0:
            n = _vmul(n, -1.0)
        e1 = _vunit(v_lr, (1.0, 0.0, 0.0))
        e1 = _vunit(_vsub(e1, _vmul(n, _vdot(e1, n))), (1.0, 0.0, 0.0))
        e2 = _vunit(_vcross(n, e1), (0.0, 0.0, 1.0))

    tilt_deg = math.degrees(math.acos(_clamp(_vdot(n, (0.0, 1.0, 0.0)), -1.0, 1.0)))
    return {
        "origin": list(centre),
        "e1": list(e1),
        "e2": list(e2),
        "normal": list(n),
        "tilt_deg": float(tilt_deg),
        "left": list(left),
        "right": list(right),
        "source": list(source),
    }


def _lr_source_plane(left: Vec3, right: Vec3, source: Vec3) -> Dict[str, Any]:
    """Plane through the two side mics and the source.

    e2 points toward the source in that plane (pattern front). e1 points
    toward the right mic. Frequency stacks along the normal.
    """
    v_lr = _vsub(right, left)
    v_ls = _vsub(source, left)
    n = _vcross(v_lr, v_ls)
    origin = (
        0.5 * (left[0] + right[0]),
        0.5 * (left[1] + right[1]),
        0.5 * (left[2] + right[2]),
    )
    if _vnorm(n) < 1e-8:
        n = (0.0, 1.0, 0.0)
        e1 = _vunit(v_lr, (1.0, 0.0, 0.0))
        e2 = _vunit(_vcross(n, e1), (0.0, 0.0, 1.0))
    else:
        n = _vunit(n)
        if n[1] < 0.0:
            n = _vmul(n, -1.0)
        e1 = _vunit(v_lr, (1.0, 0.0, 0.0))
        e1 = _vunit(_vsub(e1, _vmul(n, _vdot(e1, n))), (1.0, 0.0, 0.0))
        e2 = _vunit(_vcross(n, e1), (0.0, 0.0, 1.0))
    to_s = _vsub(source, origin)
    if _vdot(e2, to_s) < 0.0:
        e2 = _vmul(e2, -1.0)
        n = _vmul(n, -1.0)
        if n[1] < 0.0:
            n = _vmul(n, -1.0)
            e1 = _vmul(e1, -1.0)
    tilt_deg = math.degrees(math.acos(_clamp(_vdot(n, (0.0, 1.0, 0.0)), -1.0, 1.0)))
    return {
        "origin": [float(v) for v in origin],
        "e1": [float(v) for v in e1],
        "e2": [float(v) for v in e2],
        "normal": [float(v) for v in n],
        "tilt_deg": float(tilt_deg),
        "left": [float(v) for v in left],
        "right": [float(v) for v in right],
        "source": [float(v) for v in source],
    }


def _basis_at_mic(origin: Vec3, source: Vec3, normal: Vec3) -> Tuple[Vec3, Vec3]:
    """e_fwd (0°) toward source in plane; e_right = n × e_fwd."""
    to_s = _vsub(source, origin)
    to_s = _vsub(to_s, _vmul(normal, _vdot(to_s, normal)))
    e_fwd = _vunit(to_s, (0.0, 0.0, 1.0))
    e_right = _vunit(_vcross(normal, e_fwd), (1.0, 0.0, 0.0))
    e_fwd = _vunit(_vcross(e_right, normal), e_fwd)
    return e_fwd, e_right


def _basis_from_yaw(yaw_rad: float, normal: Vec3) -> Tuple[Vec3, Vec3]:
    """e_fwd = capsule look (yaw 0 = +Z) projected into plane; e_right = n × e_fwd."""
    # look_xz = (YAW_X_SIGN·sin(yaw), cos(yaw)) → 3D look (x, 0, z); one convention (early_field)
    look = _look_vector(yaw_rad)
    look = _vsub(look, _vmul(normal, _vdot(look, normal)))
    e_fwd = _vunit(look, (0.0, 0.0, 1.0))
    e_right = _vunit(_vcross(normal, e_fwd), (1.0, 0.0, 0.0))
    e_fwd = _vunit(_vcross(e_right, normal), e_fwd)
    return e_fwd, e_right


def _sample_mic_grid(
    origin: Vec3,
    source: Vec3,
    normal: Vec3,
    centres: Sequence[float],
    n_az: int,
    car_omni: float,
    stack_m: float = _FREQ_STACK_M,
    *,
    pattern: Optional[str] = None,
    yaw_rad: Optional[float] = None,
    family: Optional[str] = None,
    polar: Optional[float] = None,
    measured: bool = False,
    h_db: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (radii [n_bands, n_az], vertices flat xyz [n_bands*n_az*3]).

    measured: radius = abs(capsule gain) × 10^(H_db/20). No LF→omni morph.
    Otherwise the ASSUMED_TOYS morph. 0° is the capsule look when yaw is set.
    """
    n_bands = len(centres)
    if yaw_rad is not None:
        e_fwd, e_right = _basis_from_yaw(float(yaw_rad), normal)
    else:
        e_fwd, e_right = _basis_at_mic(origin, source, normal)
    pat = normalize_pattern(pattern) if pattern is not None else None
    radii = np.zeros((n_bands, n_az), dtype=np.float64)
    verts = np.zeros(n_bands * n_az * 3, dtype=np.float64)
    n_b = max(n_bands - 1, 1)
    for bi, fc in enumerate(centres):
        if measured:
            mix = 0.0
        elif pat is None:
            mix = freq_cardioid_mix(fc, car_omni)
        elif pat == PATTERN_OMNI:
            mix = 0.0
        else:
            mix = freq_cardioid_mix(fc, 1.0)
        h = (bi / n_b) * stack_m
        base = _vadd(origin, _vmul(normal, h))
        for ai in range(n_az):
            theta = (ai / n_az) * 2.0 * math.pi
            if measured:
                gdb = 0.0 if h_db is None else float(h_db[bi, ai])
                gain = pattern_abs(
                    theta, pat or PATTERN_CARDIOID, family=family, polar=polar
                )
                r = gain * (10.0 ** (gdb / 20.0))
            elif pat is None and polar is None and family is None:
                r = pattern_radius(theta, mix)
            else:
                r = pattern_radius_named(
                    theta, pat or PATTERN_CARDIOID, mix, family=family, polar=polar
                )
            radii[bi, ai] = r
            offset = _vadd(
                _vmul(e_fwd, r * math.cos(theta)),
                _vmul(e_right, r * math.sin(theta)),
            )
            p = _vadd(base, offset)
            idx = (bi * n_az + ai) * 3
            verts[idx : idx + 3] = p
    return radii, verts


def compute_polar_field(
    *,
    W: float,
    H: float,
    L: float,
    sox: float,
    soz: float,
    mz: float,
    my: float,
    space: float,
    diverg: float,
    car_omni: float,
    mcx: Optional[float] = None,
    toe_half_deg: Optional[float] = None,
    sy: Optional[float] = None,
    hadamard_n: int = 32,
    surfaces: Any = None,
    n_az: int = 72,
    centres: Sequence[float] = RING_HZ,
    diffusion_seed: int = 0,
    lambda_ref: float = 0.02,
    pattern_l: Optional[str] = None,
    pattern_c: Optional[str] = None,
    pattern_r: Optional[str] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_c_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
    family_l: Optional[str] = None,
    family_c: Optional[str] = None,
    family_r: Optional[str] = None,
    polar_l: Optional[float] = None,
    polar_c: Optional[float] = None,
    polar_r: Optional[float] = None,
    centre_dz: float = 0.0,
    sx: Optional[float] = None,
    sz: Optional[float] = None,
    mcz: Optional[float] = None,
    colour_mode: str = "MEASURED_SHELF",
    mic_preset_l: str = "ShureSM57",
    mic_preset_c: str = "ShureSM57",
    mic_preset_r: str = "ShureSM57",
    mic_hpf_engaged: bool = False,
    mic_hpf_sides: Optional[bool] = None,
    mic_hpf_centre: Optional[bool] = None,
    desk: Optional[dict] = None,
) -> Dict[str, Any]:
    """Mic polar × frequency mesh in the mic–source plane.

    Per-capsule ``pattern_*`` + ``yaw_*_deg`` drive each L/C/R solid (0° = look).
    MEASURED / BYPASS radii follow H_db. ASSUMED_TOYS keeps the LF morph.
    ``surfaces`` / ``diffusion_seed`` / ``lambda_ref`` / ``hadamard_n`` are
    accepted for API compatibility; they do not reshape the solid.
    """
    del surfaces, diffusion_seed, lambda_ref, hadamard_n  # API compat only
    n_az = int(max(24, min(180, int(n_az))))
    car = _clamp(float(car_omni), 0.0, 1.0)
    if sx is not None and sz is not None and mcz is not None:
        sy_v = float(my) if sy is None else float(sy)
        mcx_v = (float(W) * 0.5) if mcx is None else float(mcx)
        prep = direct_field_from_metres(
            float(W), float(H), float(L),
            sx=float(sx), sy=sy_v, sz=float(sz),
            mcx=mcx_v, my=float(my), mcz=float(mcz),
            space=space, diverg=diverg,
            toe_half_deg=toe_half_deg,
            yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
        )
    else:
        prep = prepare_direct_field(
            float(W), float(H), float(L),
            mz=mz, my=my, space=space, diverg=diverg, sox=sox, soz=soz, mcx=mcx,
            toe_half_deg=toe_half_deg,
            yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
        )
    stand = MicStand.from_prepare(
        prep, car_omni=car,
        pattern_l=pattern_l, pattern_c=pattern_c, pattern_r=pattern_r,
        yaw_l_deg=yaw_l_deg, yaw_c_deg=yaw_c_deg, yaw_r_deg=yaw_r_deg,
        family_l=family_l, family_c=family_c, family_r=family_r,
        polar_l=polar_l, polar_c=polar_c, polar_r=polar_r,
        centre_dz=centre_dz,
    )
    if desk:
        from desk_matrix import place_stand
        place_stand(stand, desk)
    left, right = mic_positions(stand)
    centre: Vec3 = centre_position(stand)
    # Optional source-Y override (Prepare locks SY=MY; tilt smoke uses sy≠my)
    src = prep.source
    if sy is not None:
        source: Vec3 = (float(src[0]), float(sy), float(src[2]))
    else:
        source = (float(src[0]), float(src[1]), float(src[2]))

    plane = _mic_source_plane(left, right, source, centre)
    normal: Vec3 = (
        float(plane["normal"][0]),
        float(plane["normal"][1]),
        float(plane["normal"][2]),
    )

    from mic_colour.modes import parse_colour_mode
    from mic_colour.preset_store import get_store, resolve_preset_id

    mode = parse_colour_mode(colour_mode)
    measured = _drops_lf_morph(mode)
    sides_on = bool(mic_hpf_engaged) if mic_hpf_sides is None else bool(mic_hpf_sides)
    centre_on = bool(mic_hpf_engaged) if mic_hpf_centre is None else bool(mic_hpf_centre)
    hpf_on = {"L": sides_on, "R": sides_on, "C": centre_on}
    store = get_store()
    preset_ids = {
        "L": resolve_preset_id(mic_preset_l),
        "C": resolve_preset_id(mic_preset_c),
        "R": resolve_preset_id(mic_preset_r),
    }
    thetas = np.asarray([(i / n_az) * 2.0 * math.pi for i in range(n_az)], dtype=float)
    bundles = {}
    for key, pid in preset_ids.items():
        preset = store.get(pid) or {}
        model = None
        if measured:
            try:
                model = store.model_for(pid)
            except KeyError:
                model = None
        bundles[key] = {
            "id": pid,
            "display_name": preset.get("display_name") or pid,
            "honesty": preset.get("honesty") or "ASSUMED",
            "hpf": store.hpf_of(pid),
            "model": model,
        }

    grids: Dict[str, np.ndarray] = {}
    verts: Dict[str, np.ndarray] = {}
    mic_specs = (
        ("L", left, stand.pattern_l, stand.mlalr, stand.family_l, stand.polar_l),
        ("C", centre, stand.pattern_c, stand.mcalr, stand.family_c, stand.polar_c),
        ("R", right, stand.pattern_r, stand.mralr, stand.family_r, stand.polar_r),
    )
    for key, origin, pat, yaw, fam, pol in mic_specs:
        bundle = bundles[key]
        h_db = None
        if measured:
            h_db = _h_db_grid(
                thetas, centres, mode, bundle["model"], bundle["hpf"], hpf_on[key]
            )
        g, v = _sample_mic_grid(
            origin, source, normal, centres, n_az, car,
            pattern=pat, yaw_rad=yaw, family=fam, polar=pol,
            measured=measured, h_db=h_db,
        )
        grids[key] = g
        verts[key] = v

    from mic_colour.modes import fitter_on_for
    from mic_pattern import rings_db, signed_amp

    # Bypass is the pattern with no fitter colour. Measured is the fitter.
    fitter = bool(fitter_on_for(mode))
    each_db: Dict[str, np.ndarray] = {}
    yaw_of = {"L": float(stand.mlalr), "C": float(stand.mcalr), "R": float(stand.mralr)}
    fam_of = {"L": stand.family_l, "C": stand.family_c, "R": stand.family_r}
    pol_of = {"L": stand.polar_l, "C": stand.polar_c, "R": stand.polar_r}
    pat_of = {"L": stand.pattern_l, "C": stand.pattern_c, "R": stand.pattern_r}
    for key in ("L", "C", "R"):
        slot = key.lower()
        cy = getattr(stand, "colour_yaw_" + slot, None)
        offset = 0.0 if cy is None else yaw_of[key] - float(cy)
        each_db[key] = rings_db(
            thetas, centres,
            family=fam_of[key], polar=pol_of[key], pattern=pat_of[key],
            model=bundles[key]["model"], hpf=bundles[key]["hpf"],
            hpf_on=hpf_on[key], measured=fitter,
            colour_offset_rad=offset,
        )

    # At speakers: P_L/R(θ) = Σ w · g(θ) · e^{−jωτ}. τ is the spacing from C.
    from desk_matrix import fold_for
    w_spk, _mk_spk, _dw_spk = fold_for(desk)
    w_of = {
        "L": (float(w_spk["ll"]), float(w_spk["lr"])),
        "C": (float(w_spk["cl"]), float(w_spk["cr"])),
        "R": (float(w_spk["rl"]), float(w_spk["rr"])),
    }
    pos_of = {"L": left, "C": centre, "R": right}
    phi = np.arange(n_az, dtype=float) * (2.0 * math.pi / float(n_az))
    dirs = np.stack((-np.sin(phi), np.zeros(n_az), np.cos(phi)), axis=1)
    freqs = np.asarray(list(centres), dtype=float)
    omega = 2.0 * math.pi * freqs
    acc_l = np.zeros((n_az, len(freqs)), dtype=np.complex128)
    acc_r = np.zeros((n_az, len(freqs)), dtype=np.complex128)
    for key in ("L", "C", "R"):
        look = np.asarray(look_vector(yaw_of[key]), dtype=float)
        cos_t = np.clip(dirs @ look, -1.0, 1.0)
        th = np.arccos(cos_t)
        slot = key.lower()
        cy = getattr(stand, "colour_yaw_" + slot, None)
        offset = 0.0 if cy is None else yaw_of[key] - float(cy)
        amp = signed_amp(
            th, freqs,
            family=fam_of[key], polar=pol_of[key], pattern=pat_of[key],
            model=bundles[key]["model"], hpf=bundles[key]["hpf"],
            hpf_on=hpf_on[key], measured=fitter,
            colour_offset_rad=offset,
        )
        rel = np.asarray(pos_of[key], dtype=float) - np.asarray(centre, dtype=float)
        phase = np.exp(-1j * omega[None, :] * (dirs @ rel)[:, None] / SPEED_OF_SOUND_M_S)
        acc_l += float(w_of[key][0]) * amp * phase
        acc_r += float(w_of[key][1]) * amp * phase
    speaker_l = np.abs(acc_l).T
    speaker_r = np.abs(acc_r).T

    # Sum = mean of L/C/R radii; mesh centred on C in the same plane
    grids["sum"] = (grids["L"] + grids["C"] + grids["R"]) / 3.0
    e_fwd, e_right = _basis_at_mic(centre, source, normal)
    n_bands = len(centres)
    sum_verts = np.zeros(n_bands * n_az * 3, dtype=np.float64)
    n_b = max(n_bands - 1, 1)
    for bi in range(n_bands):
        h = (bi / n_b) * _FREQ_STACK_M
        base = _vadd(centre, _vmul(normal, h))
        for ai in range(n_az):
            theta = (ai / n_az) * 2.0 * math.pi
            r = float(grids["sum"][bi, ai])
            offset = _vadd(
                _vmul(e_fwd, r * math.cos(theta)),
                _vmul(e_right, r * math.sin(theta)),
            )
            p = _vadd(base, offset)
            idx = (bi * n_az + ai) * 3
            sum_verts[idx : idx + 3] = p
    verts["sum"] = sum_verts

    az = [i * (360.0 / n_az) for i in range(n_az)]

    def as_lists(mag: np.ndarray) -> List[List[float]]:
        return mag.tolist()

    ref = (float(stand.cx), float(stand.cy), float(stand.cz))
    halo_mics = []
    for origin, yaw, pat, fam, pol, key in (
        (left, stand.mlalr, stand.pattern_l, stand.family_l, stand.polar_l, "L"),
        (centre, stand.mcalr, stand.pattern_c, stand.family_c, stand.polar_c, "C"),
        (right, stand.mralr, stand.pattern_r, stand.family_r, stand.polar_r, "R"),
    ):
        halo_mics.append({
            "pos": (
                float(origin[0]) - ref[0],
                float(origin[1]) - ref[1],
                float(origin[2]) - ref[2],
            ),
            "look": look_vector(float(yaw)),
            "pattern": pat,
            "family": fam,
            "polar": pol,
            "model": bundles[key]["model"],
            "hpf": bundles[key]["hpf"],
            "hpf_on": hpf_on[key],
        })
    halo_xz = _halo_magnitude(_plane_dirs(n_az, "xz"), halo_mics, centres, mode, bool(mic_hpf_engaged))
    halo_yz = _halo_magnitude(_plane_dirs(n_az, "yz"), halo_mics, centres, mode, bool(mic_hpf_engaged))

    base_plane = _lr_source_plane(left, right, source)
    e1b = tuple(base_plane["e1"])
    e2b = tuple(base_plane["e2"])
    nb = tuple(base_plane["normal"])
    phi = np.arange(n_az, dtype=float) * (2.0 * math.pi / float(n_az))
    base_dirs = (
        np.cos(phi)[:, None] * np.asarray(e2b, dtype=float)
        + np.sin(phi)[:, None] * np.asarray(e1b, dtype=float)
    )
    base_mag = _halo_magnitude(base_dirs, halo_mics, centres, mode, bool(mic_hpf_engaged))
    # Size the stack from 1 kHz toward the source. The 20 Hz ring is the
    # wrong ruler: a high-pass shrinks it, and dividing by that tiny value
    # inflates every other ring.
    ref_i = 0
    for i, hz in enumerate(centres):
        if abs(float(hz) - 1000.0) < 1.0:
            ref_i = i
            break
    ref = float(base_mag[ref_i, 0]) if base_mag.size else 1.0
    if ref < 1e-3:
        ref = float(np.max(base_mag)) if base_mag.size else 1.0
    base_radii = base_mag / max(ref, 1e-9)
    base_origin = tuple(base_plane["origin"])
    n_b_stack = max(len(centres) - 1, 1)
    base_verts = np.zeros(len(centres) * n_az * 3, dtype=np.float64)
    for bi in range(len(centres)):
        h = (bi / n_b_stack) * _FREQ_STACK_M
        base = _vadd(base_origin, _vmul(nb, h))
        for ai in range(n_az):
            ang = (ai / n_az) * 2.0 * math.pi
            r = float(base_radii[bi, ai]) * 0.9
            offset = _vadd(
                _vmul(e2b, r * math.cos(ang)),
                _vmul(e1b, r * math.sin(ang)),
            )
            pnt = _vadd(base, offset)
            idx = (bi * n_az + ai) * 3
            base_verts[idx : idx + 3] = pnt

    return {
        "ok": True,
        "assumed": not measured,
        "measured": measured,
        "colour_mode": mode,
        "mic_hpf_engaged": bool(mic_hpf_engaged),
        "presets": {
            key: {
                "id": bundles[key]["id"],
                "display_name": bundles[key]["display_name"],
                "honesty": bundles[key]["honesty"],
                "hpf_hz": (bundles[key]["hpf"] or {}).get("hpf_hz"),
            }
            for key in ("L", "C", "R")
        },
        "assumed_note": (
            "Radius = |capsule gain| × 10^(H_db/20). "
            "MEASURED H_db is the fitter. BYPASS H_db is 0. "
            "No LF→omni morph. Rings 20 / 63 / 125 / 250 / 1k / 4k / 8k / 16k."
            if measured else
            "ASSUMED_TOYS display morph: low rings toward omni, high rings toward "
            "the pattern. Not the fitter. Rings at the same eight frequencies."
        ),
        "kind": "mic_polar_freq",
        "centres_hz": [float(c) for c in centres],
        "ring_labels": list(RING_LABELS) if list(centres) == list(RING_HZ) else [
            (f"{int(c/1000)}k" if c >= 1000 else str(int(c))) for c in centres
        ],
        "azimuth_deg": az,
        "n_az": n_az,
        "n_bands": n_bands,
        "car_omni": car,
        "toe_half_deg": None if toe_half_deg is None else float(toe_half_deg),
        "mlalr": float(stand.mlalr),
        "mralr": float(stand.mralr),
        "mcalr": float(stand.mcalr),
        "patterns": {"L": stand.pattern_l, "C": stand.pattern_c, "R": stand.pattern_r},
        "yaw_deg": {
            "L": math.degrees(stand.mlalr),
            "C": math.degrees(stand.mcalr),
            "R": math.degrees(stand.mralr),
        },
        "freq_lo_hz": _F_LO_HZ,
        "freq_hi_hz": _F_HI_HZ,
        "stack_m": _FREQ_STACK_M,
        "plane": plane,
        "mic_origins": {"L": list(left), "C": list(centre), "R": list(right)},
        "source": list(source),
        "source_y_override": sy is not None,
        "L": as_lists(grids["L"]),
        "C": as_lists(grids["C"]),
        "R": as_lists(grids["R"]),
        "sum": as_lists(grids["sum"]),
        "each_db": {key: each_db[key].tolist() for key in ("L", "C", "R")},
        "speaker_l": as_lists(speaker_l),
        "speaker_r": as_lists(speaker_r),
        "desk_w": [float(w_spk[k]) for k in ("ll", "lr", "cl", "cr", "rl", "rr")],
        "halo_xz": as_lists(halo_xz),
        "halo_yz": as_lists(halo_yz),
        "base": as_lists(base_radii),
        "base_plane": base_plane,
        "base_note": (
            "Pattern in the plane through the side mics and the source. "
            "Centre is added at its real position, with its delay. "
            "The stack is frequency."
        ),
        "halo_note": (
            "Three capsules added in this plane, with the delay between them. "
            "High rings lobe where they cancel. Left and right stay apart in the speakers."
        ),
        "vertices": {
            "L": verts["L"].tolist(),
            "C": verts["C"].tolist(),
            "R": verts["R"].tolist(),
            "sum": verts["sum"].tolist(),
            "base": base_verts.tolist(),
        },
    }


if __name__ == "__main__":
    p = compute_polar_field(
        W=6, H=3, L=8, sox=0.5, soz=0.55, mz=6.5, my=1.5,
        space=0.25, diverg=1.0, car_omni=1.0, mcx=3.0, n_az=36,
    )
    mid = len(p["centres_hz"]) // 2
    rear = p["n_az"] // 2
    print("LF front/rear", p["C"][0][0], p["C"][0][rear])
    print("HF front/rear", p["C"][-1][0], p["C"][-1][rear])
    print("tilt", p["plane"]["tilt_deg"], "verts", len(p["vertices"]["C"]))
    p2 = compute_polar_field(
        W=6, H=3, L=8, sox=0.5, soz=0.55, mz=6.5, my=1.5,
        space=0.25, diverg=1.0, car_omni=1.0, mcx=3.0, n_az=36, sy=2.5,
    )
    print("tilt sy≠my", p2["plane"]["tilt_deg"])
