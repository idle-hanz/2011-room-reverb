#!/usr/bin/env python3
"""
3D polar field (ASSUMED) — microphone polar pattern × frequency.

Not image-arrival directions. Each slice is the mic's directional response in the
mic–source plane; stacked 1/3-octave bands form a solid:

  - Low bands (bottom) → round / omni
  - High bands (top)   → cardioid (morphed by Car↔Omni)

Honesty
-------
- Cardioid↔omni algebra: VERIFIED early_field.cardioid_gain.
- Log-frequency LF→HF omni→cardioid crossfade: ASSUMED display model.
- Plane = mics + source (tilts when source Y ≠ mic Y). Prepare locks SY=MY;
  optional ``sy`` overrides source height for this view / smoke.
- Colour / Surfaces / seeded diffusion stay intact elsewhere; this view does
  not claim Structure OCR or surface-EQ colouration of the pattern mesh.
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

from early_field import (  # noqa: E402
    MicStand,
    PATTERN_CARDIOID,
    PATTERN_FIG8,
    PATTERN_OMNI,
    cardioid_gain,
    mic_positions,
    normalize_pattern,
    pattern_gain,
    prepare_direct_field,
)
from surface_colour import THIRD_OCTAVE_HZ  # noqa: E402

Vec3 = Tuple[float, float, float]

# ASSUMED: log-frequency morph from omni (LF) toward cardioid (HF)
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


def pattern_radius_named(theta: float, pattern: str, freq_mix: float) -> float:
    """Polar radius for discrete pattern × ASSUMED freq morph (display ≥ 0).

    freq_mix 0→omni-ish, 1→full pattern (cardioid / |fig8|).
    """
    p = normalize_pattern(pattern)
    if p == PATTERN_OMNI:
        return 1.0
    full = pattern_gain(theta, p, signed=False)
    # blend toward omni at LF
    return float((1.0 - freq_mix) * 1.0 + freq_mix * full)


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
    # look_xz = (-sin(yaw), cos(yaw)) → 3D look (x, 0, z)
    look = (-math.sin(yaw_rad), 0.0, math.cos(yaw_rad))
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
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (radii [n_bands, n_az], vertices flat xyz [n_bands*n_az*3]).

    When pattern/yaw set: 0° = capsule look (yaw); else legacy 0° toward source
    with car_omni blend.
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
        if pat is None:
            mix = freq_cardioid_mix(fc, car_omni)
        elif pat == PATTERN_OMNI:
            mix = 0.0
        else:
            # ASSUMED: same log-f morph toward full cardioid/fig8
            mix = freq_cardioid_mix(fc, 1.0)
        h = (bi / n_b) * stack_m
        base = _vadd(origin, _vmul(normal, h))
        for ai in range(n_az):
            theta = (ai / n_az) * 2.0 * math.pi
            if pat is None:
                r = pattern_radius(theta, mix)
            else:
                r = pattern_radius_named(theta, pat, mix)
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
    centres: Sequence[float] = THIRD_OCTAVE_HZ,
    diffusion_seed: int = 0,
    lambda_ref: float = 0.02,
    pattern_l: Optional[str] = None,
    pattern_c: Optional[str] = None,
    pattern_r: Optional[str] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_c_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
) -> Dict[str, Any]:
    """Mic polar × frequency mesh in the mic–source plane.

    Per-capsule ``pattern_*`` + ``yaw_*_deg`` drive each L/C/R solid (0° = look).
    ``surfaces`` / ``diffusion_seed`` / ``lambda_ref`` / ``hadamard_n`` are
    accepted for API compatibility with Colour/Surfaces desks; they do not
    reshape this ASSUMED mic-pattern solid.
    """
    del surfaces, diffusion_seed, lambda_ref, hadamard_n  # API compat only
    n_az = int(max(24, min(180, int(n_az))))
    car = _clamp(float(car_omni), 0.0, 1.0)
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
    )
    left, right = mic_positions(stand)
    centre: Vec3 = (stand.cx, stand.cy, stand.cz)
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

    grids: Dict[str, np.ndarray] = {}
    verts: Dict[str, np.ndarray] = {}
    mic_specs = (
        ("L", left, stand.pattern_l, stand.mlalr),
        ("C", centre, stand.pattern_c, stand.mcalr),
        ("R", right, stand.pattern_r, stand.mralr),
    )
    for key, origin, pat, yaw in mic_specs:
        g, v = _sample_mic_grid(
            origin, source, normal, centres, n_az, car,
            pattern=pat, yaw_rad=yaw,
        )
        grids[key] = g
        verts[key] = v

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

    return {
        "ok": True,
        "assumed": True,
        "assumed_note": (
            "ASSUMED mic polar × frequency: per-capsule pattern + yaw; LF→omni, "
            "HF→full pattern (log-f crossfade). Fig-8 = |cos θ| (ASSUMED). "
            "Plane = mics+source (tilts if sy≠my). 0° = capsule look (yaw 0 = +Z). "
            "Not image-arrival directions; not Structure OCR."
        ),
        "kind": "mic_polar_freq",
        "centres_hz": [float(c) for c in centres],
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
        "vertices": {
            "L": verts["L"].tolist(),
            "C": verts["C"].tolist(),
            "R": verts["R"].tolist(),
            "sum": verts["sum"].tolist(),
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
