"""Shoebox image positions. Corner origin is the live path.

Full room size R (W, H, or L). No half-W. The page twin is RRImage.
First-order marks use k in −1, 0, 1. Higher |k| is the same algebra the
engine uses, including the PROPOSAL extension past the named macros.
"""
from __future__ import annotations

from typing import Tuple

Vec3 = Tuple[float, float, float]


def macro_passthrough(s: float) -> float:
    """S / X / Y / Z — pass-through."""
    return s


def macro_neg(s: float) -> float:
    """-X / -Y — unary invert (−x). VERIFIED (-X shot 353; -Y shot 319)."""
    return -s


def macro_2R_minus_S(s: float, R: float) -> float:
    """2W-X / 2H-Y / 2L-Z = (2·R) − S. VERIFIED (2W-X 207/329; 2H-Y 317; 2L-Z 326)."""
    return (2.0 * R) - s


def macro_2R_plus_S(s: float, R: float) -> float:
    """2W+X / 2H+Y / 2L+Z = (2·R) + S. VERIFIED (2W+X 330/352; 2H+Y 318; 2L+Z 325)."""
    return (2.0 * R) + s


def macro_S_minus_2R(s: float, R: float) -> float:
    """-2H+Y / -2L+Z = S − (2·R). VERIFIED (321 / 324).

    Same Sub pin order used for X-family -2W+X. VERIFIED shot 402: plus=SX,
    minus=2W → X − (2·W). Matches -2H+Y / -2L+Z. Do not invent a half-W form.
    """
    return s - (2.0 * R)


def macro_4L_minus_Z(z: float, L: float) -> float:
    """4L-Z = (4·L) − Z (Const 4). VERIFIED (328)."""
    return (4.0 * L) - z


def corner_axis_from_macro(s: float, R: float, k: int) -> float:
    """Map image index k → VERIFIED named-macro algebra on one axis.

    k: 0→S, -1→-S, 1→2R-S, 2→2R+S, -2→S-(2R)  [= -2R+S]
    Full R (never half-W). Denser |k|>2 = PROPOSAL extension only.
    """
    if k == 0:
        return macro_passthrough(s)
    if k == -1:
        return macro_neg(s)
    if k == 1:
        return macro_2R_minus_S(s, R)
    if k == 2:
        return macro_2R_plus_S(s, R)
    if k == -2:
        return macro_S_minus_2R(s, R)
    # Extension for denser grids (PROPOSAL — not from macros):
    if k % 2 == 0:
        return k * R + s
    return k * R + (R - s) if k > 0 else k * R - s


def image_position_centre(source: Vec3, room: Vec3, n: Tuple[int, int, int]) -> Vec3:
    """Centre-origin (from-them paper): image = (-1)^n * source + n * roomSize per axis.

    Kept for A/B; source/mic are centre-relative. Not deleted when corner became default.
    """
    sx, sy, sz = source
    W, H, L = room
    nx, ny, nz = n
    ix = ((-1) ** nx) * sx + nx * W
    iy = ((-1) ** ny) * sy + ny * H
    iz = ((-1) ** nz) * sz + nz * L
    return (ix, iy, iz)


def image_position_corner(
    source: Vec3,
    room: Vec3,
    n: Tuple[int, int, int],
    *,
    z_face_4l: bool = False,
) -> Vec3:
    """Corner-origin positions via VERIFIED mirror leaves (default live path).

    Prepare MCX=W×0.5 implies corner at 0. Live-32 nz=+2 is 2L+Z (435).
    n==(0,0,2) → 4L-Z only when z_face_4l (macro exists, not in live 32).
    """
    sx, sy, sz = source
    W, H, L = room
    nx, ny, nz = n
    ix = corner_axis_from_macro(sx, W, nx)
    iy = corner_axis_from_macro(sy, H, ny)
    if z_face_4l and n == (0, 0, 2):
        iz = macro_4L_minus_Z(sz, L)
    else:
        iz = corner_axis_from_macro(sz, L, nz)
    return (ix, iy, iz)


def image_position(
    source: Vec3,
    room: Vec3,
    n: Tuple[int, int, int],
    *,
    origin: str = "corner",
    z_face_4l: bool = False,
) -> Vec3:
    """Dispatch image position by origin. Default corner (see image_position_corner)."""
    o = origin.strip().lower()
    if o == "corner":
        return image_position_corner(source, room, n, z_face_4l=z_face_4l)
    if o == "centre" or o == "center":
        return image_position_centre(source, room, n)
    raise ValueError(f"origin must be 'corner' or 'centre', got {origin!r}")
