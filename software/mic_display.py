#!/usr/bin/env python3
"""Geometry helpers for the 2011 Room Reverb tweak app.

Absolute metres ↔ Prepare SoX/SoZ/MZ, clamping, and live readout.
Uses prepare_direct_field only — no invented A–F / Hadamard tables.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional, Tuple

_ENGINE = Path(__file__).resolve().parent / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from early_field import prepare_direct_field  # noqa: E402

Vec3 = Tuple[float, float, float]


def look_xz(yaw_rad: float) -> Tuple[float, float]:
    """Mic look in XZ for Prepare yaw. yaw=0 faces +Z."""
    return (-math.sin(yaw_rad), math.cos(yaw_rad))


def dist3(a: Vec3, b: Vec3) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def prepare_from_metres(
    W: float, L: float, sx: float, sz: float, mcz: float
) -> Tuple[float, float, float]:
    """Metres → (SoX, SoZ, MZ). VERIFIED inverse of Prepare."""
    W, L = float(W), float(L)
    sox = (sx / W) if abs(W) > 1e-12 else 0.0
    denom = L - float(mcz)
    soz = ((float(sz) - float(mcz)) / denom) if abs(denom) > 1e-12 else 0.0
    mz = L - float(mcz)
    return sox, soz, mz


def metres_from_prepare(
    W: float, L: float, sox: float, soz: float, mz: float
) -> Tuple[float, float, float]:
    """(SoX, SoZ, MZ) → (SX, SZ, MCZ)."""
    W, L = float(W), float(L)
    mcz = L - float(mz)
    sx = W * float(sox)
    sz = mcz + (L - mcz) * float(soz)
    return sx, sz, mcz


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(v)))


def max_space_m(W: float, mcx: Optional[float] = None) -> float:
    """Largest Space so L/R capsules stay in [0, W] given MCX."""
    W = float(W)
    mcx_v = (W * 0.5) if mcx is None else float(mcx)
    return max(0.0, 2.0 * min(mcx_v, W - mcx_v))


def clamp_inside_room(
    W: float,
    H: float,
    L: float,
    *,
    sx: float,
    sz: float,
    my: float,
    mcz: float,
    space: float,
    mcx: Optional[float] = None,
    reaktor_parity: bool = False,
    sy: Optional[float] = None,
) -> tuple:
    """Keep source + mic stand + L/R inside the room.

    Returns (sx, sz, my, mcz, space, mcx, sy).
    When reaktor_parity: MCX snaps to W/2.
    sy defaults to my when omitted (VERIFIED SY=MY).
    """
    W, H, L = float(W), float(H), float(L)
    sx = clamp(sx, 0.0, W)
    sz = clamp(sz, 0.0, L)
    my = clamp(my, 0.0, H)
    sy_v = clamp(my if sy is None else float(sy), 0.0, H)
    mcz = clamp(mcz, 0.0, L)
    if reaktor_parity or mcx is None:
        mcx_v = W * 0.5
    else:
        mcx_v = clamp(mcx, 0.0, W)
    space = clamp(space, 0.0, max_space_m(W, mcx_v))
    return sx, sz, my, mcz, space, mcx_v, sy_v


def geometry(
    W: float,
    H: float,
    L: float,
    *,
    mz: float,
    my: float,
    space: float,
    diverg: float,
    sox: float,
    soz: float,
    mcx: Optional[float] = None,
    toe_half_deg: Optional[float] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_c_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
    pattern_l: Optional[str] = None,
    pattern_c: Optional[str] = None,
    pattern_r: Optional[str] = None,
    sy: Optional[float] = None,
):
    prep = prepare_direct_field(
        W, H, L, mz=mz, my=my, space=space, diverg=diverg, sox=sox, soz=soz, mcx=mcx,
        toe_half_deg=toe_half_deg,
        yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
        sy=sy,
    )
    yaw_c = 0.0 if yaw_c_deg is None else math.radians(float(yaw_c_deg))
    S, C, Lm, Rm = prep.source, prep.mic_centre, prep.mic_left, prep.mic_right
    return {
        "prep": prep,
        "W": float(W),
        "H": float(H),
        "L": float(L),
        "my": float(my),
        "mz": float(mz),
        "space": float(space),
        "diverg": float(diverg),
        "d_sl": dist3(S, Lm),
        "d_sc": dist3(S, C),
        "d_sr": dist3(S, Rm),
        "look_l": look_xz(prep.mlalr),
        "look_c": look_xz(yaw_c),
        "look_r": look_xz(prep.mralr),
        "toe_l_deg": math.degrees(prep.mlalr),
        "toe_c_deg": math.degrees(yaw_c),
        "toe_r_deg": math.degrees(prep.mralr),
        "pattern_l": pattern_l,
        "pattern_c": pattern_c,
        "pattern_r": pattern_r,
    }


def format_position_readout(
    W: float,
    H: float,
    L: float,
    *,
    mz: float,
    my: float,
    space: float,
    diverg: float,
    sox: float,
    soz: float,
    mcx: Optional[float] = None,
    toe_half_deg: Optional[float] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_c_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
    sy: Optional[float] = None,
    **_extra,
) -> str:
    g = geometry(
        W, H, L, mz=mz, my=my, space=space, diverg=diverg, sox=sox, soz=soz, mcx=mcx,
        toe_half_deg=toe_half_deg,
        yaw_l_deg=yaw_l_deg, yaw_c_deg=yaw_c_deg, yaw_r_deg=yaw_r_deg,
        sy=sy,
    )
    prep = g["prep"]
    S, C = prep.source, prep.mic_centre
    sy_v = S[1]
    return (
        f"Source (x,y,z)=({S[0]:.3f}, {sy_v:.3f}, {S[2]:.3f}) m  |  "
        f"Mic C (x,z)=({C[0]:.3f}, {C[2]:.3f}) m  |  "
        f"Space={space:.3f} m  |  "
        f"|S−L|={g['d_sl']:.3f}  |S−C|={g['d_sc']:.3f}  |S−R|={g['d_sr']:.3f} m  |  "
        f"MY={my:.3f} m  SY={sy_v:.3f} m  MCZ={prep.mcz:.3f} m"
    )
