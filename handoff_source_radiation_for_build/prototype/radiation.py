"""Reference implementation of SOURCE RADIATION for the 2011 Room Reverb engine.

Pure-python/numpy, written to be ported 1:1 into the shared C core
(engine/live_stereo.c for Play via WASM, ctypes for Render).

Engine coords (VERIFIED early_field.py): x = width, y = height, z = length,
corner origin; right-handed, so facing +z with +y up -> source LEFT = +x.
Image parity (VERIFIED early_field.corner_axis_from_macro): an axis index k is
mirrored iff k is odd (k=-1 -> -S, k=1 -> 2R-S; k=+-2 -> +-2R+S).
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "source_fitter"))
from source_fitter import model as SM  # noqa: E402


# ---------------------------------------------------------------- geometry
def facing_basis(yaw_deg: float, pitch_deg: float, roll_deg: float = 0.0):
    """Rows f (fwd), l (left), u (up) in engine coords.
    yaw 0 = facing +z (down the room length, same zero as mic yaw 'Yaw 0 = +Z forward' VERIFIED),
    yaw + turns toward +x; pitch + tilts up; roll about f (later)."""
    ps, th = math.radians(yaw_deg), math.radians(pitch_deg)
    f = np.array([math.sin(ps) * math.cos(th), math.sin(th), math.cos(ps) * math.cos(th)])
    u0 = np.array([0.0, 1.0, 0.0])
    u = u0 - f * np.dot(u0, f)
    if np.linalg.norm(u) < 1e-9:
        u = np.array([-math.sin(ps), 0.0, -math.cos(ps)])
    u /= np.linalg.norm(u)
    l = np.cross(u, f)
    if roll_deg:
        r = math.radians(roll_deg)
        l, u = math.cos(r) * l + math.sin(r) * u, -math.sin(r) * l + math.cos(r) * u
    return np.stack([f, l, u])


def yaw_to_face(src, target):
    dx, dz = target[0] - src[0], target[2] - src[2]
    return math.degrees(math.atan2(dx, dz))


def emission_dir(n: Tuple[int, int, int], image_pos, receiver_pos) -> np.ndarray:
    """Unit direction in which the REAL source emits the ray that arrives at
    `receiver_pos` via image n: (receiver - image), un-mirrored on odd axes."""
    v = np.asarray(receiver_pos, float) - np.asarray(image_pos, float)
    s = np.array([-1.0 if (abs(k) % 2) == 1 else 1.0 for k in n])
    v = v * s
    return v / max(np.linalg.norm(v), 1e-12)


def local_dir(e_world, basis) -> np.ndarray:
    return basis @ e_world  # (fwd, left, up)


# ---------------------------------------------------------------- coefficients
@dataclass
class SrcCoef:
    """Per (image, capsule) coefficients — what the C core stores per line."""
    gain: float          # linear broadband
    b0: float; b1: float; b2: float; a1: float; a2: float  # RBJ high shelf (normalised)
    pole_g: float        # one-pole coefficient (0 = bypass)
    pole_mix: float
    bypass: bool         # k == 0 -> exact identity
    order: int = 1       # 1 or 2 cascaded identical one-poles


def coef_for_dir(params: Dict[str, float], d_local: np.ndarray, fs: float, size_scale: float = 1.0) -> SrcCoef:
    klo, khi = SM.weight_k2(params, d_local[None, :])
    k_lo, k = float(klo[0]), float(khi[0])
    if (k <= 0.0 and k_lo <= 0.0) or (params["lo_db"] == 0.0 and params["hi_db"] == 0.0 and params["lp_mix"] == 0.0):
        return SrcCoef(1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, True)
    g = 10 ** (k_lo * params["lo_db"] / 20.0)
    b0, b1, b2, a1, a2 = [float(x) for x in SM.rbj_high_shelf(params["f0"] / size_scale, k * params["hi_db"], params["shelf_s"], fs)]
    pg, pm = 0.0, 0.0
    if params["lp_mix"] > 1e-6 and k > 0.0:
        fc = params["lp_hz"] / size_scale / k
        if fc < 0.45 * fs:
            pg = float(SM.one_pole_g(fc, fs)); pm = float(params["lp_mix"])
    return SrcCoef(g, b0, b1, b2, a1, a2, pg, pm, False, int(params.get("lp_order", 1)))


def diffuse_coef(preset: Dict, fs: float, size_scale: float = 1.0) -> SrcCoef:
    """Power-averaged (diffuse-field) source filter for the FDN inject path."""
    d = preset.get("diffuse_inject") or {}
    if not d or preset.get("id") == "omni":
        return SrcCoef(1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, True)
    b0, b1, b2, a1, a2 = [float(x) for x in SM.rbj_high_shelf(d["shelf_f0"] / size_scale, d["shelf_gain_db"], d.get("shelf_s", 0.7), fs)]
    return SrcCoef(10 ** (d["gain_db"] / 20.0), b0, b1, b2, a1, a2, 0.0, 0.0, False)


# ---------------------------------------------------------------- DSP (block, stateful — C-portable)
class SrcFilterState:
    __slots__ = ("z1", "z2", "pz", "pz2")

    def __init__(self):
        self.z1 = self.z2 = self.pz = self.pz2 = 0.0


def src_process(x: np.ndarray, c: SrcCoef, st: SrcFilterState | None = None) -> np.ndarray:
    """gain -> RBJ shelf (TDF-II) -> soft one-pole. Identity when c.bypass (bit-exact)."""
    if c.bypass:
        return x
    st = st or SrcFilterState()
    y = np.empty_like(x)
    z1, z2, pz, pz2 = st.z1, st.z2, st.pz, st.pz2
    g, b0, b1, b2, a1, a2, pg, pm = c.gain, c.b0, c.b1, c.b2, c.a1, c.a2, c.pole_g, c.pole_mix
    for i in range(len(x)):
        v = g * x[i]
        o = b0 * v + z1
        z1 = b1 * v - a1 * o + z2
        z2 = b2 * v - a2 * o
        if pg > 0.0:
            pz += pg * (o - pz)
            lp = pz
            if c.order == 2:
                pz2 += pg * (pz - pz2)
                lp = pz2
            o = (1.0 - pm) * o + pm * lp
        y[i] = o
    st.z1, st.z2, st.pz, st.pz2 = z1, z2, pz, pz2
    return y


def src_process_fast(x: np.ndarray, c: SrcCoef) -> np.ndarray:
    """Same maths via scipy.signal.lfilter (offline Render speed)."""
    if c.bypass:
        return x
    from scipy.signal import lfilter
    y = lfilter([c.b0, c.b1, c.b2], [1.0, c.a1, c.a2], c.gain * x)
    if c.pole_g > 0.0:
        lp = lfilter([c.pole_g], [1.0, -(1.0 - c.pole_g)], y)
        if c.order == 2:
            lp = lfilter([c.pole_g], [1.0, -(1.0 - c.pole_g)], lp)
        y = (1.0 - c.pole_mix) * y + c.pole_mix * lp
    return y


def size_jitter_m(size_a: float, e_local: np.ndarray, seed_index: int, seed: int = 2011) -> float:
    """Cheap extended-source cue: each image 'sees' a different point of a
    sphere of radius a (one random emission point per image). Returns the
    path-length change (metres) = -(p . e) with p a fixed pseudo-random point
    in the source ball. Independent of the surfaces 'diffusion' jitter (kept separate)."""
    if size_a <= 0.0:
        return 0.0
    rng = np.random.default_rng(seed * 1000003 + seed_index)
    v = rng.normal(size=3)
    v /= np.linalg.norm(v)
    r = size_a * rng.random() ** (1 / 3)
    return -float(np.dot(r * v, e_local))
