#!/usr/bin/env python3
"""
Early-field image-source prototype for the 2011 room reverb rebuild (v2).

Implements the AGREED design (see README for tags and assumptions).
FDN / Hadamard: see fdn.py (audio) and fdn_stub.py (legacy inject API notes).

Constants / tags (2026-09-17 Structure locks):
  SPEED_OF_SOUND_M_S = 340.0  — VERIFIED (Distances Const)
  delay_ms           = (d/340)*1000 — VERIFIED Distances law
  geometric level    = 1/r — software (Idle 2026-10-10). Structure Air Abs graph remains 1/r² (256: Dis×Dis then 1/x)
  Mirror leaves      = full-R Mul/Sub algebra — VERIFIED Structure (see macro_*)
  Prepare MCZ        = L − MZ — VERIFIED; MCX = W×0.5 — VERIFIED
  Direct Field DD    = 2D XZ — VERIFIED; image Distances = 3D Euclidean — VERIFIED
  SAMPLE_RATE_HZ     = 44100  — ASSUMED
  ALLPASS delays     = 1.2 ms / 2.7 ms — ASSUMED
  Peaking Q          = 1.5 — ASSUMED (do not invent Res filter Q/dB from file)
  Air Abs 1-pole     = LP, fc = Wet/Dis (256). Humidity Wet 100–700 default 400 (486)
  Air Abs high-shelf = ISO 9613-1 dual RBJ shelf (candidate C). 1-pole stays separate.
  Mic 1-pole         = LP after delay; P = FtoP(Res)×(1-(2·|Dir|)^C/O) (410, 466)
  Image origin       = corner (default) | centre — see image_position*
  Live-32            = symmetric τ order; Reaktor 29-unique order is LIVE_32_REAKTOR
  A–F surface dict / full Hadamard OCR rows — NOT invented here
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore

try:
    from fdn_stub import stub_note
except ImportError:  # pragma: no cover
    def stub_note() -> str:  # type: ignore
        return "FDN omitted (fdn_stub not importable)."


# --- Speed / rate ------------------------------------------------------------
# VERIFIED-from-file: Distances and Delays embeds Constant 340.0 (ens-mining-notes).
# LIKELY: used as speed of sound (m/s). Primary Dly is in ms (R5 digest).
SPEED_OF_SOUND_M_S = 340.0  # was ASSUMED 343 → now VERIFIED-from-file Const 340.0
SAMPLE_RATE_HZ = 44100      # ASSUMED — not readable in ensemble
MIC_OFFAXIS_SHELF_DB = -6.0  # ASSUMED prototype scalar (not Res dB from file)

# Short Schroeder allpass delay times — ASSUMED, not from file
ALLPASS_MS_ORDER2 = 1.2   # ASSUMED ~1.2 ms for |n|>=2 (one stage)
ALLPASS_MS_ORDER4 = 2.7   # ASSUMED ~2.7 ms nested with 1.2 for order>=4
ALLPASS_G_ORDER2 = 0.4    # ASSUMED feedback
ALLPASS_G_ORDER4 = 0.55   # ASSUMED feedback (outer/nested)

PEAKING_Q = 1.5  # ASSUMED mid of Q~1–2 from them
# ROOMTONE (Idle 2026-10-16). In-loop harmonic cuts. Tune these by ear.
# Not UI knobs. Negative HARM_DB is a cut. The page does not read the two
# measure overrides below.
HARM_Q = 8.0
HARM_DB = -0.3
HARM_MAX = 16
HARM_HZ_CAP = 500.0
HARM_OFF = False
HARM_DB_OVERRIDE = None
# Humidity rotary (486 Function): Min 100, Max 700, Default 400, Step 6.
# Wet = that value; fc = Wet/Dis Hz (256). UI humidity 0 = bypass;
# 0..1 maps 100..700 (0.5 = Structure default 400).
HUMIDITY_WET_MIN = 100.0
HUMIDITY_WET_MAX = 700.0
HUMIDITY_WET_DEFAULT = 400.0
AIR_ABS_WET_HZ_M = HUMIDITY_WET_MAX  # humidity=1 → 700; old name kept for tests
HUMIDITY_DB_PER_METRE = -0.15  # ASSUMED upgrade shelf, not Structure
HUMIDITY_SHELF_RATIO = 0.35    # ASSUMED: shelf corner ~ 0.35 * Nyquist
# Mic Response (399 / Idle Hanz): 10 kHz dynamic → 20 kHz condenser. Live dump 10 k.
MIC_RES_MIN = 10000.0
MIC_RES_MAX = 20000.0
MIC_RES_HZ = 10000.0
MIC_CO = 1.0                   # Power Y; C/O panel value unread (not Car/Omni)
# -----------------------------------------------------------------------------


Vec3 = Tuple[float, float, float]


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


# --- Mirror leaves (Structure VERIFIED 2026-09-17) ---------------------------
# Corner origin, full room size R (W/H/L). No half-W. Sub pin order as opened.
# Named after ensemble macros; Const 2 / Const 4 / unary -x as Structure.

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
    Full R (never half-W). Densеr |k|>2 = PROPOSAL extension only.
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
    """Dispatch image position by origin. Default **corner** (see image_position_corner)."""
    o = origin.strip().lower()
    if o == "corner":
        return image_position_corner(source, room, n, z_face_4l=z_face_4l)
    if o == "centre" or o == "center":
        return image_position_centre(source, room, n)
    raise ValueError(f"origin must be 'corner' or 'centre', got {origin!r}")


def polarity(n: Tuple[int, int, int]) -> int:
    """from them: (-1)^(nx+ny+nz)."""
    nx, ny, nz = n
    return 1 if ((nx + ny + nz) % 2 == 0) else -1


def image_order(n: Tuple[int, int, int]) -> int:
    return abs(n[0]) + abs(n[1]) + abs(n[2])


def chebyshev_radius(n: Tuple[int, int, int]) -> int:
    """max(|nx|,|ny|,|nz|) — cubic shell radius."""
    return max(abs(n[0]), abs(n[1]), abs(n[2]))


# Hadamard / early-field sizes (Sylvester powers of 2). Default 32 = live / Reaktor-era.
HADAMARD_NS: Tuple[int, ...] = (8, 16, 32, 64, 128)
DEFAULT_HADAMARD_N = 32

# bias name used by enumerate_scaled_grid for each N
_HADAMARD_BIAS: Dict[int, str] = {
    8: "8",
    16: "16",
    32: "32",
    64: "64like",
    128: "128",
}


def normalize_hadamard_n(n: int) -> int:
    """Accept only Sylvester sizes 8·16·32·64·128."""
    ni = int(n)
    if ni not in HADAMARD_NS:
        raise ValueError(f"hadamard_n must be one of {HADAMARD_NS}, got {n!r}")
    return ni


def grid_bias_for_hadamard_n(n: int) -> str:
    """Map Hadamard N → enumerate_scaled_grid bias string."""
    return _HADAMARD_BIAS[normalize_hadamard_n(n)]


def hadamard_n_for_grid(grid: str) -> int:
    """Inverse: grid / bias name → N. Accepts '64' as alias for '64like'."""
    g = str(grid).strip().lower()
    aliases = {
        "8": 8, "16": 16, "32": 32,
        "64": 64, "64like": 64,
        "128": 128,
    }
    if g not in aliases:
        raise ValueError(f"grid must be one of {sorted(aliases)}, got {grid!r}")
    return aliases[g]


# Default Play/Render table. X-symmetric multiset, τ=(b0 b4)(b1 b3) order.
# Line 0 stays (0,2,0) so the coherent Hadamard sum is not the direct image.
# Direct (0,0,0) is index 10. 30 unique. The 2011 Reaktor voice order,
# including its X gap, is LIVE_32_REAKTOR under reaktor_parity.
LIVE_32: Tuple[Tuple[int, int, int], ...] = (
    (0, 2, 0),
    (-1, 1, 0),
    (0, 0, 1),
    (1, -2, 0),
    (0, -2, 0),
    (1, 2, 0),
    (-1, 0, 1),
    (1, -1, 1),
    (0, 0, 1),
    (-1, -1, 0),
    (0, 0, 0),
    (1, 1, 1),
    (1, 0, 1),
    (1, 0, 0),
    (0, -1, 0),
    (0, 1, 1),
    (1, 1, 0),
    (0, 1, 0),
    (1, -1, 0),
    (1, 2, 1),
    (-1, 2, 0),
    (0, 2, 1),
    (-1, 0, 0),
    (1, -2, 1),
    (-1, -2, 0),
    (-1, 2, 1),
    (-1, 1, 1),
    (0, 1, 2),
    (-1, -1, 1),
    (-1, -2, 1),
    (0, 1, 1),
    (0, 0, 2),
)

# Reaktor poly voices 1–32 from Distances SX/SY/SZ (420, 434, 435).
# 29 unique, three duplicates. No ±2W, no −Z. Voice 3 (index 2) is direct.
# Kept for reaktor_parity so the 2011 patch, including its X gap, stays bit-exact.
LIVE_32_REAKTOR: Tuple[Tuple[int, int, int], ...] = (
    (0, 2, 0),
    (0, 1, 0),
    (0, 0, 0),
    (0, -1, 0),
    (0, -2, 0),
    (0, 2, 1),
    (0, 1, 1),
    (0, 1, 1),
    (0, 0, 1),
    (0, 0, 1),
    (1, 2, 1),
    (1, 1, 1),
    (1, 0, 1),
    (1, -1, 1),
    (1, -2, 1),
    (1, 2, 0),
    (1, 1, 0),
    (1, 0, 0),
    (1, -1, 0),
    (1, -2, 0),
    (-1, 2, 0),
    (-1, 1, 0),
    (-1, 0, 0),
    (-1, -2, 0),
    (-1, -2, 0),
    (-1, 2, 1),
    (-1, 1, 1),
    (-1, 0, 1),
    (-1, -1, 1),
    (-1, -2, 1),
    (0, 1, 2),
    (0, 0, 2),
)

# Binaural mode only (LOCKED 2026-09-30). LIVE_32 order, 7 slots replaced:
# 3 duplicate voices, 4 weakest order-4 corners, 2 missing partners, 5 rear
# images (n_z = -1). Direct stays index 2. Other mic setups keep LIVE_32.
BINAURAL_REAR32: Tuple[Tuple[int, int, int], ...] = (
    (0, 2, 0),
    (0, 1, 0),
    (0, 0, 0),
    (0, -1, 0),
    (0, -2, 0),
    (0, 2, 1),
    (0, 1, 1),
    (0, -1, 1),
    (0, 0, 1),
    (0, 0, -1),
    (1, 0, -1),
    (1, 1, 1),
    (1, 0, 1),
    (1, -1, 1),
    (0, 1, -1),
    (1, 2, 0),
    (1, 1, 0),
    (1, 0, 0),
    (1, -1, 0),
    (1, -2, 0),
    (-1, 2, 0),
    (-1, 1, 0),
    (-1, 0, 0),
    (-1, -2, 0),
    (-1, -1, 0),
    (-1, 0, -1),
    (-1, 1, 1),
    (-1, 0, 1),
    (-1, -1, 1),
    (0, -1, -1),
    (0, 1, 2),
    (0, 0, 2),
)

_BINAURAL_PRESET_CACHE: Dict[str, dict] = {}


def binaural_pack_dir() -> Path:
    """Shipped head presets. A copy under mic_colour wins; otherwise the pack."""
    here = Path(__file__).resolve()
    local = here.parents[1] / "mic_colour" / "presets" / "binaural"
    pack = here.parents[2] / "handoff_binaural" / "presets" / "binaural"
    if (local / "SADIE2_KU100.json").is_file():
        return local
    return pack


def load_binaural_preset(preset_id: str = "SADIE2_KU100") -> dict:
    pid = str(preset_id or "SADIE2_KU100")
    hit = _BINAURAL_PRESET_CACHE.get(pid)
    if hit is not None:
        return hit
    path = binaural_pack_dir() / f"{pid}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    _BINAURAL_PRESET_CACHE[pid] = data
    return data


def binaural_ear_spacing_m(preset_id: str = "SADIE2_KU100") -> float:
    return float(load_binaural_preset(preset_id)["ear_spacing_m"])


def _lerp(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    if x <= float(xs[0]):
        return float(ys[0])
    if x >= float(xs[-1]):
        return float(ys[-1])
    lo = 0
    hi = len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if float(xs[mid]) <= x:
            lo = mid
        else:
            hi = mid
    span = float(xs[hi]) - float(xs[lo])
    if span == 0.0:
        return float(ys[lo])
    t = (x - float(xs[lo])) / span
    return float(ys[lo]) + t * (float(ys[hi]) - float(ys[lo]))


def binaural_itd_correction_s(preset: dict, az_deg: float, el_deg: float) -> float:
    """Far-ear correction (seconds). Table is measured LF ITD minus (s/c) sin θ."""
    it = preset["itd"]
    th = math.degrees(math.asin(max(-1.0, min(1.0,
        math.cos(math.radians(el_deg)) * math.sin(math.radians(az_deg))))))
    return 1e-6 * _lerp(th, it["table_lateral_deg"], it["correction_us"])


def binaural_head_relative(head: Vec3, image: Vec3, head_yaw_deg: float) -> Tuple[float, float, float]:
    """Room point → (SOFA az deg, + = left), elevation deg, range from the head centre."""
    dx = image[0] - head[0]
    dy = image[1] - head[1]
    dz = image[2] - head[2]
    r = math.sqrt(dx * dx + dy * dy + dz * dz)
    if r < 1e-12:
        return 0.0, 0.0, 0.0
    psi = math.radians(head_yaw_deg)
    look = (YAW_X_SIGN * math.sin(psi), 0.0, math.cos(psi))
    right = (math.cos(psi), 0.0, -YAW_X_SIGN * math.sin(psi))
    forward = (dx * look[0] + dz * look[2]) / r
    lateral = (dx * right[0] + dz * right[2]) / r
    az = math.degrees(math.atan2(-lateral, forward))
    el = math.degrees(math.asin(max(-1.0, min(1.0, dy / r))))
    return az, el, r


def binaural_ear_positions(head: Vec3, spacing_m: float, head_yaw_deg: float) -> Tuple[Vec3, Vec3]:
    """Ears rotate with the head. L = H − (s/2)·right, R = H + (s/2)·right."""
    psi = math.radians(head_yaw_deg)
    right = (math.cos(psi), 0.0, -YAW_X_SIGN * math.sin(psi))
    h = 0.5 * float(spacing_m)
    left = (head[0] - h * right[0], head[1] - h * right[1], head[2] - h * right[2])
    right_ear = (head[0] + h * right[0], head[1] + h * right[1], head[2] + h * right[2])
    return left, right_ear


def direct_line_index(taps, n_lines: int = 32) -> int:
    """FDN line of n=(0,0,0). LIVE_32 voice 3 → index 2. ASSUMED Mix split."""
    n_lines = int(n_lines)
    n_t = len(taps) if taps is not None else 0
    for i in range(min(n_lines, n_t)):
        n = getattr(taps[i], "n", None)
        if n is not None and tuple(n) == (0, 0, 0):
            return i
    if n_lines > 2:
        return 2
    return 0


def build_image_indices(
    hadamard_n: int = DEFAULT_HADAMARD_N,
    reaktor_parity: bool = False,
) -> List[Tuple[int, int, int]]:
    """Image index table sized to Hadamard N (default 32 = live Structure).

    32: symmetric LIVE_32. reaktor_parity keeps the 2011 voice order.
    Other N: see enumerate_scaled_grid. The first argument stays hadamard_n.
    """
    if reaktor_parity and int(hadamard_n) == 32:
        return list(LIVE_32_REAKTOR)
    return enumerate_scaled_grid(bias=grid_bias_for_hadamard_n(hadamard_n))


def enumerate_scaled_grid(
    R: int = 1,
    *,
    metric: str = "chebyshev",
    face_extras: bool = False,
    omit_behind_mic: bool = False,
    bias: Optional[str] = None,
) -> List[Tuple[int, int, int]]:
    """Enumerate a cubic (or biased) image-index lattice for early-field scaling.

    Tags:
      - bias="32": Structure live poly 1–32 (LIVE_32; ignores R/metric extras)
      - bias="64like" (alias bias="64"): proposal denser +z subset of Chebyshev R=2 (exactly 64)
      - bias="8" / "16" / "128": ASSUMED/PROPOSAL deterministic lattices sized to Hadamard N
        (prefer live-32 as subset when N≥32; do not invent A–F OCR tables)
      - otherwise: constructive family (proposal) — see /workspace/grid-scaling.md

    Parameters
    ----------
    R : shell radius. Chebyshev → max|n_i|≤R; Manhattan → sum|n_i|≤R.
    metric : "chebyshev" | "manhattan"
    face_extras : if True and metric is chebyshev, add axial face centres at
        distance R+1 on ±X,±Y,±Z (then optionally drop behind-mic).
    omit_behind_mic : drop pure behind-mic axis points (0,0,-k) for k≥2
        (keeps first-order (0,0,-1) when present).
    bias : None | "8" | "16" | "32" | "64" | "64like" | "128" — named presets;
        when set, other flags are ignored except as documented above.

    Pair with FDN(n) of matching Hadamard size via grid_bias_for_hadamard_n.
    """
    if bias == "8":
        # ASSUMED/PROPOSAL: axial shell — direct + six ±1 faces + forward (0,0,2).
        # Exactly 8. Not Structure-verified.
        imgs = [
            (0, 0, 0),
            (-1, 0, 0), (1, 0, 0),
            (0, -1, 0), (0, 1, 0),
            (0, 0, -1), (0, 0, 1),
            (0, 0, 2),
        ]
        assert len(imgs) == 8
        return imgs

    if bias == "16":
        # ASSUMED/PROPOSAL: Manhattan ≤1 (7) + four XY edges at z=0 + five
        # |n|=2 axials. Exactly 16. Not Structure-verified.
        imgs = [
            (0, 0, 0),
            (-1, 0, 0), (1, 0, 0),
            (0, -1, 0), (0, 1, 0),
            (0, 0, -1), (0, 0, 1),
            (-1, -1, 0), (-1, 1, 0), (1, -1, 0), (1, 1, 0),
            (-2, 0, 0), (2, 0, 0), (0, -2, 0), (0, 2, 0), (0, 0, 2),
        ]
        assert len(imgs) == 16
        return imgs

    if bias == "32":
        imgs = list(LIVE_32)
        assert len(imgs) == 32
        return imgs

    if bias in ("64like", "64"):
        # proposal: Chebyshev R≤1 core + full +z face at nz=2 + lateral axials
        # at |n|=2 + crown at nz=1 with one lateral |coord|=2. Exactly 64.
        # Omits entire nz=-2 slab and (0,0,-2). Keeps (0,0,-1).
        imgs_set = set()
        for nx in range(-1, 2):
            for ny in range(-1, 2):
                for nz in range(-1, 2):
                    imgs_set.add((nx, ny, nz))
        for nx in range(-2, 3):
            for ny in range(-2, 3):
                imgs_set.add((nx, ny, 2))
        for extra in ((-2, 0, 0), (2, 0, 0), (0, -2, 0), (0, 2, 0)):
            imgs_set.add(extra)
        for sx in (-1, 1):
            for sy in (-1, 1):
                imgs_set.add((2 * sx, sy, 1))
                imgs_set.add((sx, 2 * sy, 1))
        imgs = sorted(imgs_set)
        assert len(imgs) == 64, f"64like expected 64, got {len(imgs)}"
        assert (0, 0, -2) not in imgs_set
        return imgs

    if bias == "128":
        # ASSUMED/PROPOSAL: Chebyshev R≤2 (125) + three outer axials.
        # Superset of live-32 and of 64like. Not Structure-verified; no A–F OCR.
        imgs_set = set()
        for nx in range(-2, 3):
            for ny in range(-2, 3):
                for nz in range(-2, 3):
                    imgs_set.add((nx, ny, nz))
        for extra in ((3, 0, 0), (-3, 0, 0), (0, 0, 3)):
            imgs_set.add(extra)
        imgs = sorted(imgs_set)
        assert len(imgs) == 128, f"128 expected 128, got {len(imgs)}"
        return imgs

    if bias is not None:
        raise ValueError(
            f"unknown bias={bias!r}; use None, '8', '16', '32', '64'/'64like', or '128'"
        )

    if R < 0:
        raise ValueError("R must be >= 0")
    metric = metric.lower().strip()
    if metric not in ("chebyshev", "manhattan"):
        raise ValueError("metric must be 'chebyshev' or 'manhattan'")

    imgs_set = set()
    span = range(-R, R + 1)
    for nx in span:
        for ny in span:
            for nz in span:
                n = (nx, ny, nz)
                if metric == "chebyshev":
                    if chebyshev_radius(n) <= R:
                        imgs_set.add(n)
                else:
                    if image_order(n) <= R:
                        imgs_set.add(n)

    if face_extras and metric == "chebyshev":
        k = R + 1
        for extra in ((-k, 0, 0), (k, 0, 0), (0, -k, 0), (0, k, 0), (0, 0, -k), (0, 0, k)):
            imgs_set.add(extra)

    if omit_behind_mic:
        imgs_set = {n for n in imgs_set if not (n[0] == 0 and n[1] == 0 and n[2] <= -2)}

    return sorted(imgs_set)


def dist(a: Vec3, b: Vec3) -> float:
    """3D Euclidean √(Δx²+Δy²+Δz²) — VERIFIED Distances (420–433, 430)."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def dist_xz(a: Vec3, b: Vec3) -> float:
    """2D XZ distance — VERIFIED Direct Field DD (√(Δx²+Δz²); Y ignored)."""
    return math.sqrt((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2)


def delay_ms_from_distance(d: float, c: float = SPEED_OF_SOUND_M_S) -> float:
    """VERIFIED Distances law: (d/c)*1000 with c=340."""
    return (d / c) * 1000.0


# --- Prepare / Direct Field (Structure VERIFIED 2026-09-17 shots 331–354) ----

def prepare_mcx(W: float) -> float:
    """Mic Centre X = W × 0.5. VERIFIED Prepare."""
    return W * 0.5


def prepare_mcz(L: float, mz: float) -> float:
    """Mic Centre Z = L − MZ. VERIFIED (331/332/354); settles prior L+MZ / L×MZ conflict."""
    return L - mz


def prepare_mic_triplet(
    W: float,
    L: float,
    mz: float,
    my: float,
    space: float,
    mcx: Optional[float] = None,
) -> Tuple[Vec3, Vec3, Vec3]:
    """Return (mic_left, mic_centre, mic_right) from Prepare panel params.

    VERIFIED (Reaktor parity default):
      MCX = W×0.5; MCZ = L−MZ
      MLX = MCX − Space/2; MRX = MCX + Space/2
      MLY = MCY = MRY = MY; MLZ = MCZ = MRZ = MCZ

    Modern UI: pass mcx to unlock mic stand X (parity off). None → W×0.5.
    """
    mcx_v = prepare_mcx(W) if mcx is None else float(mcx)
    mcz = prepare_mcz(L, mz)
    half = space * 0.5
    centre = (mcx_v, my, mcz)
    left = (mcx_v - half, my, mcz)
    right = (mcx_v + half, my, mcz)
    return left, centre, right


def prepare_angles(diverg: float) -> Tuple[float, float]:
    """MLALR / MRALR from Diverg Parallel Converge.

    Shot 403: Info on the −0.25 module is Add (“sum of the input values”).
    Path: MDPC → Mul **0.5**, then Add **−0.25** (Left) / Add **+0.25** (Right).

    VERIFIED: MLALR = Diverg×0.5 − 0.25; MRALR = Diverg×0.5 + 0.25.
    Included L−R is always 0.5 rad. At diverg=0: ±0.25 rad (converge).
    At diverg=0.5: L=0. Still too small/odd for XY/ORTF; use toe_half_deg.
    Units: panel Diverg normalized; result is Direct Field toe (not degrees).
    """
    mlalr = diverg * 0.5 + (-0.25)
    mralr = diverg * 0.5 + 0.25
    return mlalr, mralr


def angles_from_toe_half_deg(toe_half_deg: float) -> Tuple[float, float]:
    """Absolute L/R look angles from forward (modern UI / mic presets).

    ASSUMED / modern: toe_half_deg = angle of each L/R capsule from +Z forward
    (included angle = 2×toe_half_deg). Returns (mlalr, mralr) radians.
    L = −half, R = +half (same sign convention as prepare_angles).
    """
    half = math.radians(float(toe_half_deg))
    return (-half, +half)


def resolve_mic_angles(
    diverg: float,
    toe_half_deg: Optional[float] = None,
) -> Tuple[float, float]:
    """Prefer absolute toe_half_deg when set; else VERIFIED prepare_angles(diverg)."""
    if toe_half_deg is not None:
        return angles_from_toe_half_deg(toe_half_deg)
    return prepare_angles(diverg)


def diverg_approx_from_toe_half_deg(toe_half_deg: float) -> float:
    """Map absolute half-angle → Reaktor Diverg via the LEFT Add law.

    MLALR = 0.5·d − 0.25, so d = 2·(θ_L + 0.25). Reaktor L/R included angle
    is locked at 0.5 rad, so this is not a true inverse for modern ORTF toes.
    """
    th = -abs(math.radians(float(toe_half_deg)))
    return 2.0 * (th + 0.25)


def prepare_source(
    W: float,
    L: float,
    mcz: float,
    my: float,
    sox: float,
    soz: float,
    sy: Optional[float] = None,
) -> Vec3:
    """Source from Prepare SoX/SoZ (0–1).

    VERIFIED (354): SX = W×SoX; SY = MY; SZ = MCZ + (L−MCZ)×SoZ.
    Modern UI may pass absolute sy; None keeps the VERIFIED SY=MY lock.
    """
    sx = W * sox
    sy_v = float(my) if sy is None else float(sy)
    sz = mcz + (L - mcz) * soz
    return (sx, sy_v, sz)


@dataclass
class PrepareResult:
    """Corner-absolute geometry from Prepare panel knobs (VERIFIED algebra)."""

    source: Vec3
    mic_centre: Vec3
    mic_left: Vec3
    mic_right: Vec3
    mlalr: float
    mralr: float
    mcx: float
    mcz: float
    mz: float


def prepare_direct_field(
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
    yaw_r_deg: Optional[float] = None,
    sy: Optional[float] = None,
) -> PrepareResult:
    """Full Prepare → Direct Field geometry. H unused in these VERIFIED equations.

    mcx: optional mic-centre X. None → W×0.5 (Reaktor parity).
    toe_half_deg: optional absolute L/R half-angle from forward (degrees).
      When set (modern UI / presets), overrides VERIFIED diverg×0.5±0.25 Add.
      Reaktor parity mic-X lock does not block absolute toes.
    yaw_l_deg / yaw_r_deg: per-capsule yaw (degrees). When either is set, they
      override toe_half_deg / diverg for mlalr/mralr. Yaw 0 = +Z forward.
    sy: optional absolute source height. None → VERIFIED SY=MY.
    """
    del H  # room height not in SX/SY/SZ / mic XZ prepare locks
    left, centre, right = prepare_mic_triplet(W, L, mz, my, space, mcx=mcx)
    mcx_v, _, mcz = centre
    if yaw_l_deg is not None or yaw_r_deg is not None:
        mlalr = math.radians(float(yaw_l_deg if yaw_l_deg is not None else 0.0))
        mralr = math.radians(float(yaw_r_deg if yaw_r_deg is not None else 0.0))
    else:
        mlalr, mralr = resolve_mic_angles(diverg, toe_half_deg=toe_half_deg)
    source = prepare_source(W, L, mcz, my, sox, soz, sy=sy)
    return PrepareResult(
        source=source,
        mic_centre=centre,
        mic_left=left,
        mic_right=right,
        mlalr=mlalr,
        mralr=mralr,
        mcx=mcx_v,
        mcz=mcz,
        mz=mz,
    )


def direct_field_from_metres(
    W: float,
    H: float,
    L: float,
    *,
    sx: float,
    sy: float,
    sz: float,
    mcx: float,
    my: float,
    mcz: float,
    space: float,
    diverg: float = 1.0,
    toe_half_deg: Optional[float] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
) -> PrepareResult:
    """Live geometry from absolute metres (Back-Left-Floor origin).

    Does not call prepare_source / prepare_mcz. Source may sit behind the
    stand (sz < mcz) or the mic on the Front wall (mcz ≈ L). mz on the
    result is derived (L − mcz) for PrepareResult compatibility only.
    """
    del H
    half = float(space) * 0.5
    mcx_v = float(mcx)
    my_v = float(my)
    mcz_v = float(mcz)
    centre = (mcx_v, my_v, mcz_v)
    left = (mcx_v - half, my_v, mcz_v)
    right = (mcx_v + half, my_v, mcz_v)
    if yaw_l_deg is not None or yaw_r_deg is not None:
        mlalr = math.radians(float(yaw_l_deg if yaw_l_deg is not None else 0.0))
        mralr = math.radians(float(yaw_r_deg if yaw_r_deg is not None else 0.0))
    else:
        mlalr, mralr = resolve_mic_angles(diverg, toe_half_deg=toe_half_deg)
    return PrepareResult(
        source=(float(sx), float(sy), float(sz)),
        mic_centre=centre,
        mic_left=left,
        mic_right=right,
        mlalr=mlalr,
        mralr=mralr,
        mcx=mcx_v,
        mcz=mcz_v,
        mz=float(L) - mcz_v,
    )


def direct_field_from_params(p: dict) -> PrepareResult:
    """Live params dict → PrepareResult.

    Prefers sx/sy/sz/mcx/my/mcz metres. Falls back to Prepare knobs
    (sox/soz/mz) when metres are missing (CLI / old tests).
    """
    W = float(p["W"])
    H = float(p["H"])
    L = float(p["L"])
    space = float(p["space"])
    diverg = float(p.get("diverg") if p.get("diverg") is not None else 1.0)
    if p.get("sx") is not None and p.get("sz") is not None and p.get("mcz") is not None:
        my = float(p["my"])
        sy = p.get("sy")
        sy_v = my if sy is None else float(sy)
        mcx = p.get("mcx")
        mcx_v = prepare_mcx(W) if mcx is None else float(mcx)
        return direct_field_from_metres(
            W, H, L,
            sx=float(p["sx"]), sy=sy_v, sz=float(p["sz"]),
            mcx=mcx_v, my=my, mcz=float(p["mcz"]),
            space=space, diverg=diverg,
            toe_half_deg=p.get("toe_half_deg"),
            yaw_l_deg=p.get("yaw_l_deg"),
            yaw_r_deg=p.get("yaw_r_deg"),
        )
    return prepare_direct_field(
        W, H, L,
        mz=float(p["mz"]), my=float(p["my"]), space=space, diverg=diverg,
        sox=float(p["sox"]), soz=float(p["soz"]), mcx=p.get("mcx"),
        toe_half_deg=p.get("toe_half_deg"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        sy=p.get("sy"),
    )


# --- Per-capsule pattern + yaw (modern UI) ------------------------------------
# Yaw convention (document + keep consistent everywhere):
#   yaw = 0 → look toward +Z (room forward / +look).
#   look_xz = (YAW_X_SIGN·sin(yaw), cos(yaw)) with YAW_X_SIGN = +1:
#   positive yaw rotates look toward +X (the UI's right).
#   L capsule (smaller X): outward toward −X ⇒ negative yaw (e.g. ORTF −55°, MS −90°).
#   R capsule (larger X): outward toward +X ⇒ positive yaw (e.g. ORTF +55°, MS +90°).
#   K1 fix (Idle, 28 Sep 2026): the old convention was YAW_X_SIGN = −1, which aimed
#   every L-negative/R-positive preset INWARD (crossed capsules). Stored yaw numbers
#   (presets, saves) are unchanged; only this one sign flipped. JS mirror:
#   RoomMath.YAW_X_SIGN (static/js/room_math.js). Keep both equal.
YAW_X_SIGN = 1.0
# (Superseded note, kept for history: "Idle Hanz 'facing each other' / MS inward =
#  L −90°, R +90°" described the old −1 convention. Locked decision K1 = outward.)
PATTERN_OMNI = "omni"
PATTERN_CARDIOID = "cardioid"
PATTERN_SUPER = "supercardioid"
PATTERN_FIG8 = "fig8"
PATTERN_NAMES = (PATTERN_OMNI, PATTERN_CARDIOID, PATTERN_SUPER, PATTERN_FIG8)
# First-order supercardioid a + (1−a)cosθ. ASSUMED textbook 0.37 (not Structure OCR).
SUPER_A = 0.37
CENTRE_DZ_MAX_M = 0.20  # Mic-desk centre setback; ASSUMED UI, not Prepare


def normalize_pattern(pattern: Optional[str], default: str = PATTERN_CARDIOID) -> str:
    if pattern is None:
        return default
    p = str(pattern).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    if p in ("omni", "o", "0"):
        return PATTERN_OMNI
    if p in ("fig8", "figure8", "bidirectional", "bi", "side"):
        return PATTERN_FIG8
    if p in ("supercardioid", "super", "hypercardioid", "hyper"):
        return PATTERN_SUPER
    if p in ("cardioid", "cardio", "car", "1", "subcardioid"):
        return PATTERN_CARDIOID
    return default


def polar_a_from_slider(polar: float) -> float:
    """Map Omni(0) → Cardioid(0.5) → Super(1) onto first-order a.

    a=1 omni, a=0.5 cardioid, a=SUPER_A supercardioid. ASSUMED continuum.
    """
    d = max(0.0, min(1.0, float(polar)))
    if d <= 0.5:
        return 1.0 - d
    return 0.5 - (d - 0.5) * (0.5 - SUPER_A) / 0.5


def first_order_gain(theta: float, a: float, *, signed: bool = True) -> float:
    g = float(a) + (1.0 - float(a)) * math.cos(theta)
    if not signed:
        return abs(g)
    return g


def family_from_pattern(pattern: str) -> str:
    return "bi" if normalize_pattern(pattern) == PATTERN_FIG8 else "cardioid"


def polar_from_pattern(pattern: str) -> float:
    p = normalize_pattern(pattern)
    if p == PATTERN_OMNI:
        return 0.0
    if p == PATTERN_SUPER:
        return 1.0
    if p == PATTERN_FIG8:
        return 0.5
    return 0.5


def pattern_from_car_omni(car_omni: float) -> str:
    """Map legacy Car↔Omni slider to discrete pattern (threshold 0.5)."""
    return PATTERN_CARDIOID if float(car_omni) >= 0.5 else PATTERN_OMNI


def car_omni_from_pattern(pattern: str) -> float:
    """Legacy scalar: omni→0, directional→1."""
    p = normalize_pattern(pattern)
    return 0.0 if p == PATTERN_OMNI else 1.0


def pattern_gain(theta: float, pattern: str, *, signed: bool = True) -> float:
    """Directional gain at angle θ from capsule look (radians).

    - omni: 1
    - cardioid: 0.5*(1+cos θ)  — VERIFIED
    - supercardioid: SUPER_A + (1−SUPER_A)cos θ — ASSUMED first-order
    - fig8: cos θ — ASSUMED (not Structure OCR); negative = rear polarity
    """
    p = normalize_pattern(pattern)
    if p == PATTERN_OMNI:
        return 1.0
    if p == PATTERN_FIG8:
        g = math.cos(theta)
        return float(g if signed else abs(g))
    if p == PATTERN_SUPER:
        return first_order_gain(theta, SUPER_A, signed=signed)
    return 0.5 * (1.0 + math.cos(theta))


def capsule_gain(
    theta: float,
    *,
    family: Optional[str] = None,
    polar: Optional[float] = None,
    pattern: Optional[str] = None,
    signed: bool = True,
) -> float:
    """Prefer family+polar slider; fall back to named pattern."""
    press, grad = capsule_press_grad(
        theta, family=family, polar=polar, pattern=pattern, signed=signed
    )
    return press + grad


def capsule_press_grad(
    theta: float,
    *,
    family: Optional[str] = None,
    polar: Optional[float] = None,
    pattern: Optional[str] = None,
    signed: bool = True,
) -> Tuple[float, float]:
    """Split first-order capsule into pressure (omni) + gradient (cosθ).

    ASSUMED. Real capsules: gradient is weak at LF → more omni in the bass.
    """
    fam = (family or "").strip().lower()
    if fam in ("bi", "bidirectional", "fig8"):
        g = math.cos(theta)
        if not signed:
            g = abs(g)
        return 0.0, float(g)
    a = 0.5
    if polar is not None:
        a = polar_a_from_slider(polar)
    else:
        p = normalize_pattern(pattern or PATTERN_CARDIOID)
        if p == PATTERN_OMNI:
            a = 1.0
        elif p == PATTERN_SUPER:
            a = SUPER_A
        elif p == PATTERN_FIG8:
            g = math.cos(theta)
            if not signed:
                g = abs(g)
            return 0.0, float(g)
        else:
            a = 0.5
    press = float(a)
    grad = (1.0 - a) * math.cos(theta)
    if not signed:
        return press, abs(grad)
    return press, float(grad)


def gradient_hp_hz(capsule_mm: float) -> float:
    """Gradient high-pass corner. Larger capsule → lower LF (more directional bass)."""
    d = max(8.0, min(34.0, float(capsule_mm)))
    return 150.0 * (17.0 / d)


def beaming_lp_hz(theta: float, capsule_mm: float) -> float:
    """Off-axis HF beaming. Larger capsule and more off-axis → lower LP. ASSUMED."""
    d = max(8.0, min(34.0, float(capsule_mm)))
    off = min(1.0, abs(float(theta)) / math.pi)
    f = 22000.0 * (17.0 / d) / (1.0 + 2.2 * off)
    return max(2500.0, min(22000.0, f))



@dataclass
class MicStand:
    """Stereo mic stand. cx/cy/cz = Mic Centre; mlalr/mralr/mcalr = capsule yaw (rad).

    Yaw 0 = +Z forward. Patterns are per-capsule source of truth; car_omni is
    legacy master / fallback when patterns omitted.
    """

    cx: float
    cy: float
    cz: float
    space: float
    car_omni: float
    mlalr: float = 0.0  # L yaw rad
    mralr: float = 0.0  # R yaw rad
    mcalr: float = 0.0  # C yaw rad
    pattern_l: str = PATTERN_CARDIOID
    pattern_c: str = PATTERN_CARDIOID
    pattern_r: str = PATTERN_CARDIOID
    family_l: str = "cardioid"
    family_c: str = "cardioid"
    family_r: str = "cardioid"
    polar_l: float = 0.5
    polar_c: float = 0.5
    polar_r: float = 0.5
    centre_dz: float = 0.0
    ms_decode: bool = False
    capsule_mm: float = 17.0
    # Flag name is not `binaural`: that name is the classmethod below.
    is_binaural: bool = False
    head_yaw_deg: float = 0.0
    binaural_preset: str = "SADIE2_KU100"
    # Per-mic position overrides. None keeps the stand algebra (VERIFIED space/2).
    pos_l: Optional[Tuple[float, float, float]] = None
    pos_c: Optional[Tuple[float, float, float]] = None
    pos_r: Optional[Tuple[float, float, float]] = None
    # Per-capsule height (H-1). None keeps the stand height cy. A placed pos_* wins.
    hy_l: Optional[float] = None
    hy_r: Optional[float] = None
    hy_c: Optional[float] = None
    # Shelf and stored colour theta. None means the capsule yaw. Pattern gain
    # always uses mlalr / mralr / mcalr.
    colour_yaw_l: Optional[float] = None
    colour_yaw_c: Optional[float] = None
    colour_yaw_r: Optional[float] = None

    @classmethod
    def binaural(
        cls,
        cx: float,
        cy: float,
        cz: float,
        head_yaw_deg: float = 0.0,
        preset: str = "SADIE2_KU100",
        **_ignored,
    ) -> "MicStand":
        """Dummy-head stand. Space, capsule yaw, and pattern are the head, not the desk.

        Ears sit at the preset spacing and ±90° (K1). User space / yaw / pattern
        are ignored. Head yaw rotates both ears together.
        """
        pid = str(preset or "SADIE2_KU100")
        return cls(
            cx=float(cx),
            cy=float(cy),
            cz=float(cz),
            space=binaural_ear_spacing_m(pid),
            car_omni=0.0,
            mlalr=math.radians(-90.0),
            mralr=math.radians(90.0),
            mcalr=0.0,
            pattern_l="omni",
            pattern_c="omni",
            pattern_r="omni",
            family_l="cardioid",
            family_c="cardioid",
            family_r="cardioid",
            polar_l=0.0,
            polar_c=0.0,
            polar_r=0.0,
            centre_dz=0.0,
            ms_decode=False,
            is_binaural=True,
            head_yaw_deg=float(head_yaw_deg),
            binaural_preset=pid,
        )

    @classmethod
    def from_prepare(
        cls,
        prep: PrepareResult,
        car_omni: float = 1.0,
        *,
        pattern_l: Optional[str] = None,
        pattern_c: Optional[str] = None,
        pattern_r: Optional[str] = None,
        yaw_l_deg: Optional[float] = None,
        yaw_c_deg: Optional[float] = None,
        yaw_r_deg: Optional[float] = None,
        patterns: Optional[Dict[str, str]] = None,
        family_l: Optional[str] = None,
        family_c: Optional[str] = None,
        family_r: Optional[str] = None,
        polar_l: Optional[float] = None,
        polar_c: Optional[float] = None,
        polar_r: Optional[float] = None,
        centre_dz: float = 0.0,
        ms_decode: bool = False,
        capsule_mm: float = 17.0,
    ) -> "MicStand":
        fallback = pattern_from_car_omni(car_omni)

        def _pat(explicit: Optional[str], key: str) -> str:
            if explicit is not None:
                return normalize_pattern(explicit, fallback)
            if patterns and key in patterns and patterns[key] is not None:
                return normalize_pattern(patterns[key], fallback)
            return fallback

        ml = math.radians(float(yaw_l_deg)) if yaw_l_deg is not None else float(prep.mlalr)
        mr = math.radians(float(yaw_r_deg)) if yaw_r_deg is not None else float(prep.mralr)
        mc = math.radians(float(yaw_c_deg)) if yaw_c_deg is not None else 0.0
        pl = _pat(pattern_l, "L")
        pc = _pat(pattern_c, "C")
        pr = _pat(pattern_r, "R")

        def _fam(explicit: Optional[str], pat: str) -> str:
            if explicit:
                e = str(explicit).strip().lower()
                if e in ("bi", "bidirectional", "fig8"):
                    return "bi"
                return "cardioid"
            return family_from_pattern(pat)

        def _pol(explicit: Optional[float], pat: str) -> float:
            if explicit is not None:
                return max(0.0, min(1.0, float(explicit)))
            return polar_from_pattern(pat)

        fl, fc, fr = _fam(family_l, pl), _fam(family_c, pc), _fam(family_r, pr)
        pol_l, pol_c, pol_r = _pol(polar_l, pl), _pol(polar_c, pc), _pol(polar_r, pr)
        if fl == "bi":
            pl = PATTERN_FIG8
        if fc == "bi":
            pc = PATTERN_FIG8
        if fr == "bi":
            pr = PATTERN_FIG8
        # Legacy scalar: prefer mean of L/R cardioids when patterns set
        car = float(car_omni)
        if pattern_l is not None or pattern_r is not None or patterns or polar_l is not None:
            car = 0.5 * (car_omni_from_pattern(pl) + car_omni_from_pattern(pr))
        dz = max(-CENTRE_DZ_MAX_M, min(CENTRE_DZ_MAX_M, float(centre_dz)))
        return cls(
            cx=prep.mic_centre[0],
            cy=prep.mic_centre[1],
            cz=prep.mic_centre[2],
            space=(prep.mic_right[0] - prep.mic_left[0]),
            car_omni=car,
            mlalr=ml,
            mralr=mr,
            mcalr=mc,
            pattern_l=pl,
            pattern_c=pc,
            pattern_r=pr,
            family_l=fl,
            family_c=fc,
            family_r=fr,
            polar_l=pol_l,
            polar_c=pol_c,
            polar_r=pol_r,
            centre_dz=dz,
            ms_decode=bool(ms_decode),
            capsule_mm=max(8.0, min(34.0, float(capsule_mm))),
        )


def mic_positions(stand: MicStand) -> Tuple[Vec3, Vec3]:
    """MLX = MCX − Space/2; MRX = MCX + Space/2; Y/Z shared. VERIFIED (354).

    Binaural ears rotate with head yaw. A plain stand does not.
    """
    if getattr(stand, "is_binaural", False):
        return binaural_ear_positions(
            (stand.cx, stand.cy, stand.cz),
            stand.space,
            float(getattr(stand, "head_yaw_deg", 0.0)),
        )
    half = stand.space * 0.5
    left = (stand.cx - half, stand.cy, stand.cz)
    right = (stand.cx + half, stand.cy, stand.cz)
    pl = getattr(stand, "pos_l", None)
    pr = getattr(stand, "pos_r", None)
    if pl is not None:
        left = (float(pl[0]), float(pl[1]), float(pl[2]))
    elif getattr(stand, "hy_l", None) is not None:
        left = (left[0], float(stand.hy_l), left[2])
    if pr is not None:
        right = (float(pr[0]), float(pr[1]), float(pr[2]))
    elif getattr(stand, "hy_r", None) is not None:
        right = (right[0], float(stand.hy_r), right[2])
    return left, right


def centre_position(stand: MicStand) -> Vec3:
    """Centre capsule. pos_c replaces the stand centre; otherwise cx, cy, cz+dz.

    hy_c is the C capsule height. The stand reference cy is left alone so the
    FDN lines can stay at my.
    """
    pc = getattr(stand, "pos_c", None)
    if pc is not None:
        return (float(pc[0]), float(pc[1]), float(pc[2]))
    y = stand.cy
    if getattr(stand, "hy_c", None) is not None:
        y = float(stand.hy_c)
    return (
        stand.cx,
        y,
        stand.cz + float(getattr(stand, "centre_dz", 0.0)),
    )


def apply_capsule_heights(stand: Optional["MicStand"], p: Optional[dict]) -> Optional["MicStand"]:
    """H-1. Absolute capsule heights, defaulting to the stand. None means 'use cy'.

    Coincident M/S and binaural ignore them. align_horizontal keeps L = R.
    A value equal to cy is stored as None so a flat stand stays the old algebra.
    """
    if stand is None or not isinstance(p, dict):
        return stand
    stand.hy_l = None
    stand.hy_r = None
    stand.hy_c = None
    if getattr(stand, "is_binaural", False) or getattr(stand, "ms_decode", False):
        return stand
    if str(p.get("mic_setup") or "") == "binaural":
        return stand
    pair = str(p.get("pair_mode") or "").strip().lower()
    if pair == "ms" and not p.get("s_detached"):
        return stand
    H = p.get("H")
    try:
        room_h = float(H) if H is not None else 0.0
    except (TypeError, ValueError):
        room_h = 0.0
    hi = room_h - 0.02 if room_h > 0.04 else 0.02

    def one(key: str):
        if key not in p or p.get(key) is None or p.get(key) == "":
            return None
        try:
            y = float(p.get(key))
        except (TypeError, ValueError):
            return None
        if y != y or y in (float("inf"), float("-inf")):
            return None
        return float(min(hi, max(0.02, y)))

    yl, yr, yc = one("my_l"), one("my_r"), one("my_c")
    if p.get("align_horizontal"):
        paired = yl if yl is not None else yr
        yl = yr = paired

    def keep(y):
        if y is None or float(y) == float(stand.cy):
            return None
        return float(y)

    stand.hy_l = keep(yl)
    stand.hy_r = keep(yr)
    stand.hy_c = keep(yc)
    return stand


def fdn_reference_positions(stand: "MicStand"):
    """Same XZ as the capsules, Y at the stand height. Placed pos_* still wins."""
    import copy

    flat = copy.copy(stand)
    flat.hy_l = None
    flat.hy_r = None
    flat.hy_c = None
    left, right = mic_positions(flat)
    return left, right, centre_position(flat)


def direction_angles(from_mic: Vec3, to_image: Vec3, yaw_rad: float) -> Tuple[float, float]:
    """Signed XZ off-axis angle and elevation (atan2 after yaw).

    Structure Distances does this the long way: ΔX/ΔZ Divider → ArcTan,
    then Sine/Cosine of MLALR, more squares, another ArcTan (417 / 450 / 451).
    That horizontal angle is what the patch did. compute_taps uses
    arrival_theta_ray instead (aim · incoming ray).
    """
    dx = to_image[0] - from_mic[0]
    dy = to_image[1] - from_mic[1]
    dz = to_image[2] - from_mic[2]
    c, s = math.cos(yaw_rad), YAW_X_SIGN * math.sin(yaw_rad)
    rx = c * dx - s * dz
    rz = s * dx + c * dz
    ry = dy
    horiz = math.atan2(rx, rz)
    r_xz = math.sqrt(rx * rx + rz * rz)
    vert = math.atan2(ry, r_xz)
    return horiz, vert


def arrival_cos_xz(from_mic: Vec3, to_image: Vec3, yaw_rad: float) -> float:
    """cos of the XZ off-axis angle = look · r_xz / |r_xz|.

    Same value as cos(direction_angles(...)[0]). Drops height on purpose.
    Structure's primary ArcTan is ΔX/ΔZ, so this helper stays XZ.
    compute_taps does not call it.
    """
    dx = to_image[0] - from_mic[0]
    dz = to_image[2] - from_mic[2]
    hyp = math.hypot(dx, dz)
    if hyp <= 1e-12:
        return 1.0
    c, s = math.cos(yaw_rad), YAW_X_SIGN * math.sin(yaw_rad)
    rz = s * dx + c * dz
    return max(-1.0, min(1.0, rz / hyp))


def look_vector(yaw_rad: float) -> Vec3:
    """Horizontal aim. Yaw 0 looks toward +Z: (YAW_X_SIGN·sin yaw, 0, cos yaw). No tilt."""
    return (YAW_X_SIGN * math.sin(yaw_rad), 0.0, math.cos(yaw_rad))


def arrival_cos_ray(from_mic: Vec3, to_image: Vec3, yaw_rad: float) -> float:
    """cosθ = clamp(look · û, −1, 1). Image on the capsule is on-axis (1).

    û is the unit vector from the capsule to the image. θ is the angle
    between that incoming ray and the horizontal aim, not the floor-plan angle.
    """
    dx = to_image[0] - from_mic[0]
    dy = to_image[1] - from_mic[1]
    dz = to_image[2] - from_mic[2]
    r = math.sqrt(dx * dx + dy * dy + dz * dz)
    if r <= 1e-12:
        return 1.0
    lx, ly, lz = look_vector(yaw_rad)
    c = (lx * dx + ly * dy + lz * dz) / r
    if c > 1.0:
        return 1.0
    if c < -1.0:
        return -1.0
    return c


def arrival_theta_ray(from_mic: Vec3, to_image: Vec3, yaw_rad: float) -> float:
    """θ = acos(look · û), radians, 0 straight ahead to π straight behind."""
    return math.acos(arrival_cos_ray(from_mic, to_image, yaw_rad))


def cardioid_gain(theta: float, car_omni: float) -> float:
    """Blend omni (car_omni=0) ↔ cardioid (car_omni=1). VERIFIED algebra."""
    cardio = 0.5 * (1.0 + math.cos(theta))
    return (1.0 - car_omni) * 1.0 + car_omni * cardio


def offaxis_shelf_gain_linear(theta: float) -> float:
    t = min(abs(theta) / math.pi, 1.0)
    db = t * MIC_OFFAXIS_SHELF_DB
    return 10.0 ** (db / 20.0)


def geometric_level(distance: float) -> float:
    """Software amplitude 1/r (Idle, 2026-10-10).

    The Structure Air Abs graph is still 1/r² (shot 256: Dis×Dis then 1/x).
    Idle chose 1/r for the whole software, Play and Render: AGC balance,
    close mics too loud, and the physical pressure law (about 6 dB per
    doubling). Distances 1/x stays 1/340 (delay), not this gain.
    """
    if distance <= 1e-9:
        return 0.0
    return 1.0 / distance


def axial_mode_hz(c: float, dim_m: float) -> float:
    """First axial: f = c / (2 * dim). Russell / from them standing-wave target."""
    if dim_m <= 1e-9:
        return 0.0
    return c / (2.0 * dim_m)


def harmonic_gain_db() -> float:
    """Shipped cut, unless a listen script set HARM_DB_OVERRIDE."""
    if HARM_DB_OVERRIDE is None:
        return float(HARM_DB)
    return float(HARM_DB_OVERRIDE)


def harmonic_stages(
    room: Tuple[float, float, float],
    sr: int,
    c: float,
    decay_s: float,
) -> Optional[List[List[Tuple[float, float, float, float, float]]]]:
    """Per-axis normalized biquads, or None when the cascade is idle.

    Gate: every first axial is at or above KEEP_CUT_BELOW_HZ. Harmonics are
    n >= 2 of axial_mode_hz (c = 340), up to min(500 Hz, schroeder_hz).
    Not modes(). At most HARM_MAX stages on one axis. None omits the live key.
    """
    if HARM_OFF:
        return None
    width, height, length = float(room[0]), float(room[1]), float(room[2])
    volume = width * height * length
    decay = float(decay_s)
    if volume <= 1e-9 or decay <= 0.05 or int(sr) < 2:
        return None
    import surf_loop as _SL
    import surf_target as _ST
    keep = float(_SL.KEEP_CUT_BELOW_HZ)
    dims = (width, height, length)
    first = [axial_mode_hz(float(c), dim) for dim in dims]
    if any(freq < keep for freq in first):
        return None
    cap = min(float(HARM_HZ_CAP), float(_ST.schroeder_hz(decay, volume)))
    if cap <= 0.0:
        return None
    gain = harmonic_gain_db()
    if gain == 0.0:
        return None
    q = float(HARM_Q)
    nyquist = float(sr) * 0.49
    axes: List[List[Tuple[float, float, float, float, float]]] = []
    any_stage = False
    for f1 in first:
        stages: List[Tuple[float, float, float, float, float]] = []
        if f1 > 0.0:
            n = 2
            while n * f1 <= cap and len(stages) < int(HARM_MAX):
                f0 = n * f1
                if f0 >= nyquist:
                    break
                stages.append(normalize_biquad(rbj_peaking(float(sr), f0, q, gain)))
                n += 1
        if stages:
            any_stage = True
        axes.append(stages)
    if not any_stage:
        return None
    return axes


def harmonic_pack(
    room: Tuple[float, float, float],
    sr: int,
    c: float,
    decay_s: float,
) -> Optional[List[float]]:
    """243 floats: nX, nY, nZ, then 3 * HARM_MAX * (b0,b1,b2,a1,a2).

    None when the size gate is off, so the live MD5 omits the key.
    """
    stages = harmonic_stages(room, sr, c, decay_s)
    if stages is None:
        return None
    out: List[float] = [float(len(stages[0])), float(len(stages[1])), float(len(stages[2]))]
    for axis in stages:
        for k in range(int(HARM_MAX)):
            if k < len(axis):
                b0, b1, b2, a1, a2 = axis[k]
                out.extend((float(b0), float(b1), float(b2), float(a1), float(a2)))
            else:
                out.extend((1.0, 0.0, 0.0, 0.0, 0.0))
    want = 3 + 3 * int(HARM_MAX) * 5
    if len(out) != want:
        raise RuntimeError(f"harm pack {len(out)} != {want}")
    return out


# --- Wall-crossing / peaking combination keys ---------------------------------
# Panel map (from file adjacency / from them): Sides=A→X (shared L/R), Floor=E→Y,
# Cieling=F→Y, Ahead=B / Behind=D → ±Z. Behind = −z crossings (nz < 0).
# Images that are *only* behind-mic axis points (0,0,−k) for k≥2 are already
# omitted from the live 32 and 64like tables — see enumerate_scaled_grid.
#
# |n_i| ≥ 2 still counts that axis **once** for peaking (once-per-axis stages),
# not twice. The frozenset key is the set of axes whose walls were crossed.
AXIS_ORDER: Tuple[str, ...] = ("X", "Y", "Z")


def crossed_axes(n: Tuple[int, int, int]) -> FrozenSet[str]:
    """Axes whose walls this image crossed: nonzero nx/ny/nz → {X,Y,Z}.

    Once-per-axis: |n_i|≥2 still yields a single membership of that axis.
    Direct (0,0,0) → empty frozenset (no wall peaking).
    """
    s: set = set()
    if n[0] != 0:
        s.add("X")
    if n[1] != 0:
        s.add("Y")
    if n[2] != 0:
        s.add("Z")
    return frozenset(s)


def axes_with_peaking(n: Tuple[int, int, int]) -> List[str]:
    """Ordered axis list for peaking stages (X then Y then Z). Same as crossed set."""
    key = crossed_axes(n)
    return [a for a in AXIS_ORDER if a in key]


def behind_z_crossed(n: Tuple[int, int, int]) -> bool:
    """True if this image crossed the Behind (−z) wall family (nz < 0)."""
    return n[2] < 0


def wall_combo_key(n: Tuple[int, int, int]) -> FrozenSet[str]:
    """Combination key for precomputed peaking filters (= crossed_axes)."""
    return crossed_axes(n)


def all_wall_combo_keys() -> List[FrozenSet[str]]:
    """All 2^3 = 8 possible axis frozensets (incl. empty = direct)."""
    keys: List[FrozenSet[str]] = []
    for mask in range(8):
        s: set = set()
        if mask & 1:
            s.add("X")
        if mask & 2:
            s.add("Y")
        if mask & 4:
            s.add("Z")
        keys.append(frozenset(s))
    return keys


def precompute_wall_peaking_coeffs(
    room: Vec3,
    sr: int,
    c: float,
    depth_per_axis: float,
) -> Dict[FrozenSet[str], List[Tuple[float, float, float, float, float, float]]]:
    """Precompute peaking biquad cascades keyed by frozenset of crossed axes.

    Sides=X is one shared stage (same coeffs for L and R channels).
    Only axes in the key get a peaking cut at f=c/(2·dim).
    """
    W, H, L = room
    dims = {"X": W, "Y": H, "Z": L}
    gain_db = -abs(depth_per_axis)
    cache: Dict[FrozenSet[str], List[Tuple[float, float, float, float, float, float]]] = {}
    for key in all_wall_combo_keys():
        stages: List[Tuple[float, float, float, float, float, float]] = []
        for ax in AXIS_ORDER:
            if ax not in key:
                continue
            f0 = axial_mode_hz(c, dims[ax])
            if f0 <= 0.0 or f0 >= sr * 0.49:
                continue
            stages.append(rbj_peaking(float(sr), f0, PEAKING_Q, gain_db))
        cache[key] = stages
    return cache


# --- biquad helpers (RBJ peaking / high-shelf) -------------------------------

def normalize_biquad(
    coeffs: Tuple[float, float, float, float, float, float],
) -> Tuple[float, float, float, float, float]:
    """a0-normalized (b0,b1,b2,a1,a2) for the worklet / FDN DF1 form."""
    b0, b1, b2, a0, a1, a2 = coeffs
    if abs(float(a0)) < 1e-18:
        return 1.0, 0.0, 0.0, 0.0, 0.0
    inv = 1.0 / float(a0)
    return b0 * inv, b1 * inv, b2 * inv, a1 * inv, a2 * inv


def rbj_peaking(sr: float, f0: float, q: float, gain_db: float) -> Tuple[float, float, float, float, float, float]:
    """RBJ peaking EQ. gain_db negative = cut. Returns b0,b1,b2,a0,a1,a2."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q) if q > 1e-9 else 0.0
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cosw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha / A
    return b0, b1, b2, a0, a1, a2


def rbj_lowpass(sr: float, f0: float, q: float = 0.707) -> Tuple[float, float, float, float, float, float]:
    """RBJ low-pass. Used as Mic Response HF limit (ASSUMED)."""
    w0 = 2.0 * math.pi * max(20.0, min(float(f0), float(sr) * 0.45)) / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q) if q > 1e-9 else 0.0
    b0 = (1.0 - cosw) * 0.5
    b1 = 1.0 - cosw
    b2 = (1.0 - cosw) * 0.5
    a0 = 1.0 + alpha
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha
    return b0, b1, b2, a0, a1, a2


def butterworth_highpass(sr: float, f0: float = 15.0) -> Tuple[float, float, float, float, float]:
    """Causal 2nd-order Butterworth high-pass. Q is 1/sqrt(2).

    Designed at the posted sample rate. No frequency clamp and no
    forward-backward pass. Returns a0-normalized (b0, b1, b2, a1, a2)
    for the DF1 form used by Play and Render.
    """
    q = 2.0 ** -0.5
    w0 = 2.0 * math.pi * float(f0) / float(sr)
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q)
    b0 = (1.0 + cosw) * 0.5
    b1 = -(1.0 + cosw)
    b2 = (1.0 + cosw) * 0.5
    a0 = 1.0 + alpha
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha
    return normalize_biquad((b0, b1, b2, a0, a1, a2))


def rbj_highpass(sr: float, f0: float, q: float = 0.707) -> Tuple[float, float, float, float, float, float]:
    """RBJ high-pass. Mic stand rumble (ASSUMED). Panel name High Pass Freq."""
    w0 = 2.0 * math.pi * max(10.0, min(float(f0), float(sr) * 0.45)) / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q) if q > 1e-9 else 0.0
    b0 = (1.0 + cosw) * 0.5
    b1 = -(1.0 + cosw)
    b2 = (1.0 + cosw) * 0.5
    a0 = 1.0 + alpha
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha
    return b0, b1, b2, a0, a1, a2


# No callers. D-PROX is the shelf that ships. This function stays.
def apply_capsule_colour(
    L: "np.ndarray",
    R: "np.ndarray",
    sr: float,
    *,
    hp_on: bool = False,
    hp_hz: float = 40.0,
    response_hz: float = MIC_RES_HZ,
    proximity: float = 0.0,
    polar_mean: float = 0.5,
) -> Tuple["np.ndarray", "np.ndarray"]:
    """Stereo wet colour after IR. ASSUMED — not Structure OCR.

    - High-pass: panel High Pass Freq / HP In
    - Mic Response: one-pole-ish LPF at the named HF limit (snapshot was 10 kHz)
    - Proximity: low-shelf amount × how directional the pair is
    """
    if np is None:
        return L, R
    stages: List[Tuple[float, float, float, float, float, float]] = []
    if hp_on and hp_hz > 12.0:
        stages.append(rbj_highpass(sr, hp_hz))
    if response_hz and response_hz < float(sr) * 0.48:
        stages.append(rbj_lowpass(sr, response_hz))
    prox = max(0.0, min(1.0, float(proximity)))
    a = polar_a_from_slider(polar_mean)
    # Directional capsules (low a) get more proximity bass. Omni (a=1) gets none.
    if prox > 1e-3 and a < 0.98:
        db = prox * (1.0 - a) * 6.0
        stages.append(rbj_lowshelf_safe(sr, 120.0, db))
    if not stages:
        return L, R
    return cascade_biquads(L, stages), cascade_biquads(R, stages)


def rbj_lowshelf_safe(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Tuple[float, float, float, float, float, float]:
    """RBJ low-shelf. Local copy so capsule colour does not import surface_colour."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw)
    a2 = (A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2


def rbj_highshelf(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Tuple[float, float, float, float, float, float]:
    """RBJ high-shelf. gain_db negative = HF cut. ASSUMED humidity tilt."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw)
    a2 = (A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2


def biquad_process(
    x: "np.ndarray",
    coeffs: Tuple[float, float, float, float, float, float],
) -> "np.ndarray":
    b0, b1, b2, a0, a1, a2 = coeffs
    inv_a0 = 1.0 / a0
    b0, b1, b2 = b0 * inv_a0, b1 * inv_a0, b2 * inv_a0
    a1, a2 = a1 * inv_a0, a2 * inv_a0
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    for i in range(len(x)):
        xi = float(x[i])
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    return y


def cascade_biquads(x: "np.ndarray", stages: Sequence[Tuple[float, float, float, float, float, float]]) -> "np.ndarray":
    y = x
    for c in stages:
        y = biquad_process(y, c)
    return y


@dataclass
class ImageTap:
    index: int
    n: Tuple[int, int, int]
    position: Vec3
    distance_l: float
    distance_r: float
    delay_ms_l: float
    delay_ms_r: float
    polarity: int
    order: int
    cardio_l: float
    cardio_r: float
    level_l: float
    level_r: float
    theta_l: float
    theta_r: float
    shelf_l: float
    shelf_r: float
    peak_axes: Tuple[str, ...]
    peak_freqs: Tuple[float, ...]
    wall_combo: FrozenSet[str]  # frozenset of crossed axes {X,Y,Z}; once-per-axis
    behind_z: bool  # nz < 0 → Behind (−z) wall family crossed
    allpass_stages: int  # 0, 1, or 2
    press_l: float = 0.0
    press_r: float = 0.0
    grad_l: float = 0.0
    grad_r: float = 0.0
    distance_c: float = 0.0
    delay_ms_c: float = 0.0
    cardio_c: float = 0.0
    level_c: float = 0.0
    theta_c: float = 0.0
    shelf_c: float = 0.0
    press_c: float = 0.0
    grad_c: float = 0.0
    az_head_deg: float = 0.0
    el_head_deg: float = 0.0
    # H-1: line length, line diffuser and line air. None means use distance_*.
    fdn_distance_l: Optional[float] = None
    fdn_distance_r: Optional[float] = None
    fdn_distance_c: Optional[float] = None


def compute_taps(
    room: Vec3,
    source: Vec3,
    stand: MicStand,
    c: float = SPEED_OF_SOUND_M_S,
    grid: str = "32",
    indices: Optional[Sequence[Tuple[int, int, int]]] = None,
    origin: str = "corner",
    z_face_4l: bool = False,
    hadamard_n: Optional[int] = None,
    include_offaxis_shelf: bool = True,
    reaktor_parity: bool = False,
) -> List[ImageTap]:
    """Build taps for the chosen image table.

    grid: "8"|"16"|"32"|"64"|"64like"|"128" (or set hadamard_n=8..128).
    hadamard_n: if set, overrides grid via grid_bias_for_hadamard_n (pairs with FDN N).
    indices: optional explicit list; overrides grid / hadamard_n when provided.
    origin: "corner" (default, macro algebra) or "centre" (from-them paper).
    Image distances: 3D Euclidean (Distances and Delays VERIFIED).
    Delay ms = (d/c)*1000 with c=340 VERIFIED. Direct Field DD is separate 2D XZ
    (see dist_xz); not substituted into image taps here.
    θ is arrival_theta_ray (aim · incoming ray). include_offaxis_shelf False
    leaves the −6 dB level shelf out of the scalars (Measured / Bypass).
    """
    left, right = mic_positions(stand)
    yaw_l = stand.mlalr  # VERIFIED Prepare MLALR
    yaw_r = stand.mralr  # VERIFIED Prepare MRALR
    is_binaural = bool(getattr(stand, "is_binaural", False))
    ms_decode = bool(getattr(stand, "ms_decode", False)) and not is_binaural
    centre = centre_position(stand)
    use_fdn_ref = (
        not is_binaural
        and not ms_decode
        and any(getattr(stand, name, None) is not None for name in ("hy_l", "hy_r", "hy_c"))
    )
    if use_fdn_ref:
        left_f, right_f, centre_f = fdn_reference_positions(stand)
    else:
        left_f, right_f, centre_f = left, right, centre
    yaw_m = float(stand.mcalr)
    yaw_s = yaw_m + 0.5 * math.pi  # Side fig-8 looks +X when Mid looks +Z
    W, H, L = room
    fx = axial_mode_hz(c, W)
    fy = axial_mode_hz(c, H)
    fz = axial_mode_hz(c, L)
    freq_map = {"X": fx, "Y": fy, "Z": fz}
    if indices is not None:
        imgs = list(indices)
    else:
        if hadamard_n is not None:
            bias = grid_bias_for_hadamard_n(hadamard_n)
        else:
            bias = grid.strip().lower()
            # validate via hadamard_n_for_grid (accepts 64 / 64like aliases)
            hadamard_n_for_grid(bias)
        imgs = enumerate_scaled_grid(bias=bias)
        if reaktor_parity and bias == "32" and not is_binaural:
            imgs = list(LIVE_32_REAKTOR)
        if is_binaural and bias == "32":
            imgs = list(BINAURAL_REAR32)
    taps: List[ImageTap] = []
    bin_preset = load_binaural_preset(getattr(stand, "binaural_preset", "SADIE2_KU100")) if is_binaural else None
    head_xyz = (stand.cx, stand.cy, stand.cz)

    def _shelf(theta: float) -> float:
        if not include_offaxis_shelf:
            return 1.0
        return offaxis_shelf_gain_linear(theta)

    for i, n in enumerate(imgs):
        pos = image_position(source, room, n, origin=origin, z_face_4l=z_face_4l)
        pol = polarity(n)
        order = image_order(n)
        fdn_l = fdn_r = fdn_c = None
        if ms_decode:
            d_l = dist(centre, pos)
            d_r = d_l
            th_m = arrival_theta_ray(centre, pos, yaw_m)
            th_s = arrival_theta_ray(centre, pos, yaw_s)
            p_m, g_m = capsule_press_grad(
                th_m,
                family=getattr(stand, "family_c", None),
                polar=getattr(stand, "polar_c", None),
                pattern=getattr(stand, "pattern_c", None) or PATTERN_CARDIOID,
            )
            _p_s, g_s = capsule_press_grad(
                th_s, family="bi", polar=0.5, pattern=PATTERN_FIG8
            )
            geo = geometric_level(d_l) * pol
            sh_l = _shelf(th_m)
            sh_r = sh_l
            press_l = geo * p_m * sh_l
            press_r = geo * p_m * sh_r
            grad_l = geo * (g_m + g_s) * sh_l
            grad_r = geo * (g_m - g_s) * sh_r
            th_l, th_r = th_m, th_m
            g_l = p_m + g_m + g_s
            g_r = p_m + g_m - g_s
            lev_l = press_l + grad_l
            lev_r = press_r + grad_r
            d_c = d_l
            th_c = th_m
            sh_c = sh_l
            g_c = p_m + g_m
            press_c = geo * p_m * sh_c
            grad_c = geo * g_m * sh_c
            lev_c = press_c + grad_c
        else:
            d_l = dist(left, pos)
            d_r = dist(right, pos)
            d_c = dist(centre, pos)
            fdn_l = fdn_r = fdn_c = None
            if use_fdn_ref:
                fdn_l = dist(left_f, pos)
                fdn_r = dist(right_f, pos)
                fdn_c = dist(centre_f, pos)
            th_l = arrival_theta_ray(left, pos, yaw_l)
            th_r = arrival_theta_ray(right, pos, yaw_r)
            th_c = arrival_theta_ray(centre, pos, yaw_m)
            th_l_pat, th_r_pat, th_c_pat = th_l, th_r, th_c
            cy_l = getattr(stand, "colour_yaw_l", None)
            cy_r = getattr(stand, "colour_yaw_r", None)
            cy_c = getattr(stand, "colour_yaw_c", None)
            if cy_l is not None:
                th_l = arrival_theta_ray(left, pos, float(cy_l))
            if cy_r is not None:
                th_r = arrival_theta_ray(right, pos, float(cy_r))
            if cy_c is not None:
                th_c = arrival_theta_ray(centre, pos, float(cy_c))
            p_l, g_l_d = capsule_press_grad(
                th_l_pat,
                family=getattr(stand, "family_l", None),
                polar=getattr(stand, "polar_l", None),
                pattern=getattr(stand, "pattern_l", None) or pattern_from_car_omni(stand.car_omni),
            )
            p_r, g_r_d = capsule_press_grad(
                th_r_pat,
                family=getattr(stand, "family_r", None),
                polar=getattr(stand, "polar_r", None),
                pattern=getattr(stand, "pattern_r", None) or pattern_from_car_omni(stand.car_omni),
            )
            p_c, g_c_d = capsule_press_grad(
                th_c_pat,
                family=getattr(stand, "family_c", None),
                polar=getattr(stand, "polar_c", None),
                pattern=getattr(stand, "pattern_c", None) or pattern_from_car_omni(stand.car_omni),
            )
            sh_l = _shelf(th_l)
            sh_r = _shelf(th_r)
            sh_c = _shelf(th_c)
            geo_l = geometric_level(d_l) * pol * sh_l
            geo_r = geometric_level(d_r) * pol * sh_r
            geo_c = geometric_level(d_c) * pol * sh_c
            press_l, press_r = geo_l * p_l, geo_r * p_r
            press_c = geo_c * p_c
            grad_l, grad_r = geo_l * g_l_d, geo_r * g_r_d
            grad_c = geo_c * g_c_d
            g_l, g_r = p_l + g_l_d, p_r + g_r_d
            g_c = p_c + g_c_d
            lev_l, lev_r = press_l + grad_l, press_r + grad_r
            lev_c = press_c + grad_c
        combo = wall_combo_key(n)
        axes = axes_with_peaking(n)  # ordered view of combo; once-per-axis
        freqs = tuple(freq_map[a] for a in axes)
        # Spec: one allpass for |n|_1 >= 2; two nested for the five |n|=2 face rooms
        # (Manhattan order is 2 for those, but design table calls them "order 4").
        if max(abs(n[0]), abs(n[1]), abs(n[2])) >= 2:
            ap_stages = 2
        elif order >= 2:
            ap_stages = 1
        else:
            ap_stages = 0
        delay_ms_l = delay_ms_from_distance(d_l, c)
        delay_ms_r = delay_ms_from_distance(d_r, c)
        delay_ms_c = delay_ms_from_distance(d_c, c)
        az_h = 0.0
        el_h = 0.0
        if is_binaural and bin_preset is not None:
            # 1/r from the head centre (both ears equal). ITD on the far ear only.
            # Centre capsule stays mute. Toys shelf stays off.
            az_h, el_h, r_h = binaural_head_relative(
                head_xyz, pos, float(getattr(stand, "head_yaw_deg", 0.0)),
            )
            corr = binaural_itd_correction_s(bin_preset, az_h, el_h)
            delay_ms_l = 1000.0 * (d_l / c + max(-corr, 0.0))
            delay_ms_r = 1000.0 * (d_r / c + max(corr, 0.0))
            delay_ms_c = 0.0
            d_c = 0.0
            geo = geometric_level(r_h) * pol
            lev_l = lev_r = press_l = press_r = geo
            grad_l = grad_r = 0.0
            lev_c = press_c = grad_c = 0.0
            g_l = g_r = 1.0
            g_c = 0.0
            sh_l = sh_r = sh_c = 1.0
        taps.append(
            ImageTap(
                index=i,
                n=n,
                position=pos,
                distance_l=d_l,
                distance_r=d_r,
                delay_ms_l=delay_ms_l,
                delay_ms_r=delay_ms_r,
                polarity=pol,
                order=order,
                cardio_l=g_l,
                cardio_r=g_r,
                level_l=lev_l,
                level_r=lev_r,
                theta_l=th_l,
                theta_r=th_r,
                shelf_l=sh_l,
                shelf_r=sh_r,
                distance_c=d_c,
                delay_ms_c=delay_ms_c,
                cardio_c=g_c,
                level_c=lev_c,
                theta_c=th_c,
                shelf_c=sh_c,
                press_c=press_c,
                grad_c=grad_c,
                peak_axes=tuple(axes),
                peak_freqs=freqs,
                wall_combo=combo,
                behind_z=behind_z_crossed(n),
                allpass_stages=ap_stages,
                press_l=press_l,
                press_r=press_r,
                grad_l=grad_l,
                grad_r=grad_r,
                az_head_deg=az_h,
                el_head_deg=el_h,
                fdn_distance_l=fdn_l,
                fdn_distance_r=fdn_r,
                fdn_distance_c=fdn_c,
            )
        )
    return taps


def print_table(taps: Sequence[ImageTap], depth_per_axis: float, file=sys.stdout) -> None:
    hdr = (
        f"{'#':>3} {'nx':>3} {'ny':>3} {'nz':>3} {'ord':>3} {'pol':>4} "
        f"{'dist_L':>8} {'dly_L_ms':>9} {'card_L':>7} {'lvl_L':>9} "
        f"{'peak':>8} {'ap':>3}"
    )
    print(hdr, file=file)
    print("-" * len(hdr), file=file)
    for t in taps:
        peak = ",".join(t.peak_axes) if t.peak_axes else "-"
        print(
            f"{t.index:3d} {t.n[0]:3d} {t.n[1]:3d} {t.n[2]:3d} {t.order:3d} {t.polarity:4d} "
            f"{t.distance_l:8.3f} {t.delay_ms_l:9.3f} {t.cardio_l:7.3f} {t.level_l:9.4f} "
            f"{peak:>8} {t.allpass_stages:3d}",
            file=file,
        )
    print(
        f"\nPeaking: depth_per_axis={depth_per_axis:.2f} dB cut, Q={PEAKING_Q} ASSUMED; "
        f"once-per-axis frozenset combos (Sides=X shared L/R; Behind=−z). "
        f"Corners get 2–3 stages, not 9 dB if depth capped.",
        file=file,
    )
    print(
        f"Allpass: order0/1 bypass; order>=2 one @ {ALLPASS_MS_ORDER2} ms ASSUMED; "
        f"|n|=2 face rooms nested + {ALLPASS_MS_ORDER4} ms ASSUMED.",
        file=file,
    )


def schroeder_allpass_ir(n_samples: int, delay: int, g: float) -> "np.ndarray":
    """Short Schroeder allpass impulse (y[n] = -g x[n] + x[n-d] + g y[n-d])."""
    assert np is not None
    x = np.zeros(n_samples)
    y = np.zeros(n_samples)
    x[0] = 1.0
    for i in range(n_samples):
        xd = x[i - delay] if i >= delay else 0.0
        yd = y[i - delay] if i >= delay else 0.0
        y[i] = -g * x[i] + xd + g * yd
    return y


def allpass_ir_for_stages(stages: int, sr: int) -> Optional["np.ndarray"]:
    """
    Return short IR for 0/1/2 nested Schroeder allpasses.
    Delay times ASSUMED 1.2 ms / 2.7 ms — not from ensemble.
    """
    if stages <= 0:
        return None
    d1 = max(1, int(round(ALLPASS_MS_ORDER2 * 0.001 * sr)))
    if stages == 1:
        return schroeder_allpass_ir(d1 * 4 + 16, d1, ALLPASS_G_ORDER2)
    d2 = max(1, int(round(ALLPASS_MS_ORDER4 * 0.001 * sr)))
    ir1 = schroeder_allpass_ir(d1 * 4 + 16, d1, ALLPASS_G_ORDER4)
    ir2 = schroeder_allpass_ir(d2 * 4 + 16, d2, ALLPASS_G_ORDER4 * 0.9)
    return np.convolve(ir1, ir2)


def apply_allpass_to_dirac(buf: "np.ndarray", delay_samp: int, amp: float, stages: int, sr: int) -> None:
    """Scatter a single impulse into a short allpass tail in-place (add). Bypass stages==0."""
    if stages <= 0:
        if 0 <= delay_samp < len(buf):
            buf[delay_samp] += amp
        return
    ir = allpass_ir_for_stages(stages, sr)
    assert ir is not None
    for k, v in enumerate(ir):
        idx = delay_samp + k
        if 0 <= idx < len(buf):
            buf[idx] += amp * float(v)


def peaking_stages_for_tap(
    tap: ImageTap,
    room: Vec3,
    sr: int,
    c: float,
    depth_per_axis: float,
    wall_cache: Optional[
        Dict[FrozenSet[str], List[Tuple[float, float, float, float, float, float]]]
    ] = None,
) -> List[Tuple[float, float, float, float, float, float]]:
    """
    One peaking cut per crossed axis at f=c/(2*dim), Q~1.5 (once-per-axis).
    depth_per_axis is positive dB magnitude of the cut (CLI default 1.5 → −1.5 dB).
    Prefer wall_cache from precompute_wall_peaking_coeffs (frozenset keys).
    """
    key = getattr(tap, "wall_combo", None) or wall_combo_key(tap.n)
    if wall_cache is not None:
        return list(wall_cache.get(key, []))
    W, H, L = room
    dims = {"X": W, "Y": H, "Z": L}
    gain_db = -abs(depth_per_axis)
    stages: List[Tuple[float, float, float, float, float, float]] = []
    for ax in AXIS_ORDER:
        if ax not in key:
            continue
        f0 = axial_mode_hz(c, dims[ax])
        if f0 <= 0.0 or f0 >= sr * 0.49:
            continue
        stages.append(rbj_peaking(float(sr), f0, PEAKING_Q, gain_db))
    return stages


def air_abs_wet_from_humidity(humidity: float) -> float:
    """UI 0..1 → Wet. 0 = bypass; else 100..700 (486). 0.5 = Default 400."""
    h = max(0.0, min(1.0, float(humidity)))
    if h <= 0.0:
        return 0.0
    return HUMIDITY_WET_MIN + h * (HUMIDITY_WET_MAX - HUMIDITY_WET_MIN)


def air_abs_cutoff_hz(distance: float, wet: float) -> float:
    """Air Abs 1-Pole (256): Log F = Wet/Dis, P → filter.

    Log is F→P; 1-Pole P is pitch. Units cancel ⇒ fc = Wet/Dis Hz.
    Humidity macro (257) is a Wet latch. wet<=0 or d<=0 ⇒ bypass (0 Hz).
    """
    if wet <= 0.0 or distance <= 1e-9:
        return 0.0
    return float(wet) / float(distance)


def one_pole_lp_ir(n_samp: int, fc: float, sr: int) -> "np.ndarray":
    """Impulse of y[n] = g x[n] + (1-g) y[n-1], g = 1−exp(−2π fc/sr). DC gain 1."""
    y = np.zeros(max(0, int(n_samp)), dtype=np.float64)
    if y.size < 1:
        return y
    if fc <= 0.0 or sr < 1:
        y[0] = 1.0
        return y
    cap = 0.49 * float(sr)
    g = 1.0 - math.exp(-2.0 * math.pi * min(float(fc), cap) / float(sr))
    a = 1.0 - g
    n = np.arange(y.size, dtype=np.float64)
    y[:] = g * np.power(a, n)
    return y


def one_pole_lp_process(buf: "np.ndarray", fc: float, sr: int) -> "np.ndarray":
    """In-place-equivalent 1-pole LP. fc<=0 leaves buf unchanged."""
    if fc <= 0.0 or sr < 1 or buf.size < 1:
        return buf
    cap = 0.49 * float(sr)
    g = 1.0 - math.exp(-2.0 * math.pi * min(float(fc), cap) / float(sr))
    y = 0.0
    out = np.empty_like(buf)
    for i in range(buf.size):
        y += g * (float(buf[i]) - y)
        out[i] = y
    return out


def humidity_shelf_coeffs(
    distance: float,
    sr: int,
    humidity: float,
) -> Optional[Tuple[float, float, float, float, float, float]]:
    """ASSUMED upgrade: high-shelf HF cut vs path distance. humidity 0 disables.

    Runs *after* the Structure 1-pole. Not in the 2011 graph.
    """
    if humidity <= 0.0 or distance <= 0.0:
        return None
    gain_db = HUMIDITY_DB_PER_METRE * distance * humidity
    gain_db = max(gain_db, -12.0)
    f0 = HUMIDITY_SHELF_RATIO * (sr * 0.5)
    return rbj_highshelf(float(sr), f0, gain_db)


def mic_power_gain(dir_rad: float, co: float = MIC_CO) -> float:
    """Microphone Gain (466): 1 − (2·|Dir|)^C/O. Clip [0, 1] LIKELY."""
    ad = abs(float(dir_rad))
    if ad < 1e-15:
        return 1.0
    base = 2.0 * ad
    try:
        g = 1.0 - (base ** float(co))
    except OverflowError:
        g = 0.0
    if g < 0.0:
        return 0.0
    if g > 1.0:
        return 1.0
    return g


def f_to_p(freq_hz: float) -> float:
    """Reaktor Log F→P (MIDI). P = 69 + 12 log2(F/440). LIKELY constants."""
    f = max(float(freq_hz), 1e-6)
    return 69.0 + 12.0 * math.log(f / 440.0, 2.0)


def p_to_f(pitch: float) -> float:
    """Inverse of f_to_p."""
    return 440.0 * (2.0 ** ((float(pitch) - 69.0) / 12.0))


def mic_cutoff_hz(res_hz: float, gain: float) -> float:
    """410: Log F=Res → P × Gain → 1-Pole P. Gain=1 ⇒ fc=Res."""
    g = max(0.0, min(1.0, float(gain)))
    if g <= 0.0:
        return p_to_f(0.0)
    if g >= 1.0:
        return max(float(res_hz), 0.0)
    return p_to_f(f_to_p(res_hz) * g)


def clamp_mic_res_hz(res_hz: float) -> float:
    """Panel Mic Response: 10 kHz–20 kHz (dynamic → condenser)."""
    return max(MIC_RES_MIN, min(MIC_RES_MAX, float(res_hz)))


def one_pole_g_from_fc(fc: float, sr: int) -> float:
    """y += g (x − y), g = 1−exp(−2π fc/sr). fc<=0 ⇒ 0 (bypass)."""
    if fc <= 0.0 or sr < 1:
        return 0.0
    cap = 0.49 * float(sr)
    return 1.0 - math.exp(-2.0 * math.pi * min(float(fc), cap) / float(sr))


def mic_one_pole_coeff(dir_rad: float, sr: int, res_hz: float = MIC_RES_HZ, co: float = MIC_CO) -> float:
    """1-pole g for Microphone output LP. Not in the Hadamard loop."""
    fc = mic_cutoff_hz(clamp_mic_res_hz(res_hz), mic_power_gain(dir_rad, co))
    return one_pole_g_from_fc(fc, sr)


def iso_shelf_pair(
    distance: float,
    sr: int,
    mix: float,
    climate: str = "studio_20C_50RH",
    humidity: float = None,
):
    """Two RBJ high shelves for the ISO dual-shelf. (None, None) when off.

    Slope is 1. The log-sigmoid slope in the preset is the analytic fit only.
    humidity None keeps the climate preset. Above 0, the slider sets RH.
    """
    if float(mix) <= 0.0 or float(distance) <= 0.0:
        return None, None
    import air_iso
    rh = None
    if humidity is not None:
        rh = air_iso.rh_pct_from_slider(humidity, climate)
        if rh is None:
            return None, None
    specs = air_iso.shelf_specs(distance, mix, climate, sr, rh)
    out = []
    for f0, gain_db in specs:
        if abs(float(gain_db)) < 1e-12:
            out.append(None)
        else:
            out.append(rbj_highshelf(float(sr), float(f0), float(gain_db), slope=1.0))
    while len(out) < 2:
        out.append(None)
    return out[0], out[1]


def apply_air_absorption(
    buf: "np.ndarray",
    distance: float,
    sr: int,
    humidity: float,
    air_lp: float = 0.25,
    air_shelf: float = 1.0,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
) -> "np.ndarray":
    """Air absorption: Structure 1-pole, then the ISO dual high-shelf.

    humidity ≤ 0 bypasses both stages (the buffer is returned unchanged).
    air_lp is the 1-pole dry/wet mix. air_shelf scales the ISO dB.
    air_iso False leaves the shelf off. Above 0, humidity sets the climate's
    relative humidity for the ISO shelf. Temperature stays on the preset.
    """
    if humidity <= 0.0:
        return buf
    lp = max(0.0, min(1.0, float(air_lp)))
    sh = max(0.0, min(1.0, float(air_shelf)))
    if lp > 0.0:
        fc = air_abs_cutoff_hz(distance, air_abs_wet_from_humidity(humidity))
        if fc > 0.0:
            filt = one_pole_lp_process(np.copy(buf), fc, sr)
            buf = (1.0 - lp) * buf + lp * filt
    if sh > 0.0 and air_iso:
        low, high = iso_shelf_pair(distance, sr, sh, air_climate, humidity)
        if low is not None:
            buf = biquad_process(buf, low)
        if high is not None:
            buf = biquad_process(buf, high)
    return buf


def filter_tap_impulse(
    n_samp: int,
    delay_samp: int,
    amp: float,
    stages_ap: int,
    sr: int,
    peak_coeffs: Sequence[Tuple[float, float, float, float, float, float]],
    hum_coeffs: Optional[Tuple[float, float, float, float, float, float]] = None,
    humidity: float = 0.0,
    distance: float = 0.0,
    air_lp: float = 0.25,
    air_shelf: float = 1.0,
) -> "np.ndarray":
    """Dirac → allpass → peaking → air 1-pole mix + high-shelf mix."""
    buf = np.zeros(n_samp, dtype=np.float64)
    apply_allpass_to_dirac(buf, delay_samp, amp, stages_ap, sr)
    if peak_coeffs:
        buf = cascade_biquads(buf, peak_coeffs)
    if hum_coeffs is not None:
        buf = biquad_process(buf, hum_coeffs)
    return apply_air_absorption(
        buf, distance, sr, humidity, air_lp=air_lp, air_shelf=air_shelf,
    )


def render_wav(
    taps: Sequence[ImageTap],
    out_path: str,
    room: Vec3,
    sr: int = SAMPLE_RATE_HZ,
    c: float = SPEED_OF_SOUND_M_S,
    length_ms: float = 200.0,
    depth_per_axis: float = 1.5,
    humidity: float = 0.0,
) -> None:
    """Render stereo early-field IR with peaking cuts, allpass, optional humidity.

    Peaking uses precomputed frozenset wall-combo keys (Sides=X shared L/R).
    """
    if np is None:
        raise RuntimeError("numpy required for WAV render — pip install numpy")
    n_samp = int(sr * length_ms / 1000.0) + 1
    Lch = np.zeros(n_samp, dtype=np.float64)
    Rch = np.zeros(n_samp, dtype=np.float64)
    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, depth_per_axis)
    for t in taps:
        dl = int(round(t.distance_l / c * sr))
        dr = int(round(t.distance_r / c * sr))
        peaks = peaking_stages_for_tap(t, room, sr, c, depth_per_axis, wall_cache=wall_cache)
        # Same peaking cascade for L and R (Sides=X shared; combo is geometric)
        Lch += filter_tap_impulse(
            n_samp, dl, t.level_l, t.allpass_stages, sr, peaks,
            humidity=humidity, distance=t.distance_l,
        )
        Rch += filter_tap_impulse(
            n_samp, dr, t.level_r, t.allpass_stages, sr, peaks,
            humidity=humidity, distance=t.distance_r,
        )
    peak = max(float(np.max(np.abs(Lch))), float(np.max(np.abs(Rch))), 1e-12)
    scale = 0.8 / peak  # ASSUMED safety normalize
    Lch *= scale
    Rch *= scale
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        interleaved = np.empty(n_samp * 2, dtype=np.float64)
        interleaved[0::2] = Lch
        interleaved[1::2] = Rch
        clipped = np.clip(interleaved, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype("<i2")
        w.writeframes(pcm.tobytes())


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="2011 room reverb — early-field image list / optional IR render (v2)"
    )
    p.add_argument("--W", type=float, required=True, help="Room width X (metres, full wall-to-wall)")
    p.add_argument("--H", type=float, required=True, help="Room height Y (metres)")
    p.add_argument("--L", type=float, required=True, help="Room length Z (metres)")
    p.add_argument("--sx", type=float, default=None, help="Source X absolute (or omit with --use-prepare)")
    p.add_argument("--sy", type=float, default=None, help="Source Y absolute (or omit with --use-prepare)")
    p.add_argument("--sz", type=float, default=None, help="Source Z absolute (or omit with --use-prepare)")
    p.add_argument("--mic-x", type=float, default=0.0, help="Mic stand centre X (absolute; ignored with --use-prepare)")
    p.add_argument("--mic-y", type=float, default=0.0, help="Mic Y / Prepare MY")
    p.add_argument("--mic-z", type=float, default=-1.0, help="Mic centre Z absolute, or Prepare MZ with --use-prepare")
    p.add_argument("--space", type=float, default=0.2, help="L/R separation metres (=MSS Space)")
    p.add_argument("--angle-deg", type=float, default=0.0,
                   help="ASSUMED legacy toe-in degrees → ±rad (ignored if --diverg set or --use-prepare)")
    p.add_argument("--diverg", type=float, default=None,
                   help="Prepare Diverg Parallel Converge → MLALR/MRALR = Diverg×0.5±0.25 (VERIFIED Add)")
    p.add_argument("--use-prepare", action="store_true",
                   help="Derive mic/source from Prepare: MCZ=L−MZ, SX=W×SoX, SZ=MCZ+(L−MCZ)×SoZ")
    p.add_argument("--sox", type=float, default=0.5, help="Prepare SoX 0–1 (with --use-prepare)")
    p.add_argument("--soz", type=float, default=0.5, help="Prepare SoZ 0–1 (with --use-prepare)")
    p.add_argument("--car-omni", type=float, default=1.0, help="0=omni .. 1=cardioid (file C/O)")
    p.add_argument(
        "--c",
        type=float,
        default=SPEED_OF_SOUND_M_S,
        help=f"Speed of sound m/s (default {SPEED_OF_SOUND_M_S}; VERIFIED-from-file Const 340)",
    )
    p.add_argument("--sr", type=int, default=SAMPLE_RATE_HZ, help="Sample rate (ASSUMED 44100)")
    p.add_argument(
        "--origin",
        choices=("corner", "centre", "center"),
        default="corner",
        help="Image origin: corner=macro algebra (default); centre=from-them paper",
    )
    p.add_argument(
        "--z-face-4l",
        action="store_true",
        help="With corner origin, use 4L-Z for n=(0,0,2); live-32 uses 2L+Z",
    )
    p.add_argument(
        "--depth-per-axis",
        type=float,
        default=1.5,
        help="Peaking cut depth per non-zero axis in dB (0..3; default 1.5 → −1.5 dB/stage)",
    )
    p.add_argument(
        "--humidity",
        type=float,
        default=0.0,
        help="0..1 scales ASSUMED distance high-shelf air tilt (0=off; separate from walls)",
    )
    p.add_argument(
        "--grid",
        choices=("8", "16", "32", "64", "64like", "128"),
        default="32",
        help="Image table sized to Hadamard N (default 32 live; 8/16/128 ASSUMED/PROPOSAL)",
    )
    p.add_argument(
        "--hadamard-n",
        type=int,
        default=None,
        choices=list(HADAMARD_NS),
        help="Override --grid with Hadamard size (images + FDN lines when paired)",
    )
    p.add_argument(
        "--render",
        metavar="WAV",
        nargs="?",
        const="/workspace/early-field/out_early.wav",
        default=None,
        help="Render stereo early IR WAV (default path if flag alone)",
    )
    p.add_argument("--length-ms", type=float, default=200.0, help="IR length ms when rendering")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    room = (args.W, args.H, args.L)
    depth = max(0.0, min(3.0, abs(args.depth_per_axis)))
    humidity = max(0.0, min(1.0, args.humidity))
    car = max(0.0, min(1.0, args.car_omni))

    if args.use_prepare:
        diverg = 0.0 if args.diverg is None else float(args.diverg)
        prep = prepare_direct_field(
            args.W, args.H, args.L,
            mz=args.mic_z, my=args.mic_y, space=args.space,
            diverg=diverg, sox=args.sox, soz=args.soz,
        )
        source = prep.source
        stand = MicStand.from_prepare(prep, car_omni=car)
        print("Prepare VERIFIED: MCZ=L−MZ; MLX/MRX=MCX∓Space/2; SX=W×SoX; SZ=MCZ+(L−MCZ)×SoZ")
        print(f"  MZ={prep.mz} → MCZ={prep.mcz}; MCX={prep.mcx}; MLALR={prep.mlalr}; MRALR={prep.mralr}")
    else:
        if args.sx is None or args.sy is None or args.sz is None:
            raise SystemExit("--sx/--sy/--sz required unless --use-prepare")
        source = (args.sx, args.sy, args.sz)
        if args.diverg is not None:
            mlalr, mralr = prepare_angles(float(args.diverg))
        else:
            # ASSUMED legacy: ±radians(angle_deg) — not Structure Prepare
            a = math.radians(args.angle_deg)
            mlalr, mralr = (+a, -a)
        stand = MicStand(
            cx=args.mic_x, cy=args.mic_y, cz=args.mic_z,
            space=args.space, car_omni=car, mlalr=mlalr, mralr=mralr,
        )

    fx = axial_mode_hz(args.c, args.W)
    fy = axial_mode_hz(args.c, args.H)
    fz = axial_mode_hz(args.c, args.L)
    origin = "centre" if args.origin in ("centre", "center") else "corner"
    print(
        "c =", args.c, "m/s (VERIFIED Const 340); delay_ms=(d/c)*1000; 1/r software (Air Abs graph 1/r²);",
        "sr =", args.sr, "ASSUMED; origin =", origin, "; cardioid (1+cosθ)/2 LIKELY",
    )
    print("Room W,H,L =", room, "  source =", source)
    print(
        "Mic stand centre =",
        (stand.cx, stand.cy, stand.cz),
        "space =",
        stand.space,
        "MLALR =",
        stand.mlalr,
        "MRALR =",
        stand.mralr,
        "car_omni =",
        stand.car_omni,
    )
    print(f"Axial peaking freqs (c/2dim): X={fx:.2f} Hz  Y={fy:.2f} Hz  Z={fz:.2f} Hz  Q={PEAKING_Q}")
    print(f"depth_per_axis = −{depth:.2f} dB/stage (capped 0..3); humidity={humidity:.2f}")
    hn = args.hadamard_n
    print(
        f"grid={args.grid} hadamard_n={hn}  "
        f"(wall combos = frozenset once-per-axis)"
    )
    print(stub_note())
    print()
    taps = compute_taps(
        room, source, stand, c=args.c, grid=args.grid,
        origin=origin, z_face_4l=args.z_face_4l,
        hadamard_n=hn,
    )
    print(f"Image count = {len(taps)}")
    combos = sorted({tuple(sorted(t.wall_combo)) for t in taps}, key=lambda t: (len(t), t))
    print("Wall combo keys used:", ", ".join("{" + ",".join(c) + "}" if c else "{}" for c in combos))
    n_behind = sum(1 for t in taps if t.behind_z)
    print(f"Behind (−z) crossings present on {n_behind} images; pure (0,0,−k) k≥2 omitted by grid.")
    print_table(taps, depth_per_axis=depth)
    if args.render is not None:
        path = args.render
        render_wav(
            taps,
            path,
            room=room,
            sr=args.sr,
            c=args.c,
            length_ms=args.length_ms,
            depth_per_axis=depth,
            humidity=humidity,
        )
        print()
        print(
            f"Wrote {path}  (sr={args.sr} ASSUMED, c={args.c} VERIFIED-from-file-default, "
            f"origin={origin}, depth_per_axis={depth}, humidity={humidity})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
