"""D-PROX early floor and proximity shelf. Shared by Play and Render.

The floor is a per-tap early scale only. geometric_level, level_*, and the
FDN inject stay 1/r. The shelf is y = x + g*LP(x). g is 0 unless the tick
is on and the source-to-capsule distance is inside 0.5 m. A zero g must not
touch samples.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

import numpy as np

from maths_pattern import polar_a_from_slider
from early_field import (
    arrival_cos_ray,
    centre_position,
    mic_positions,
)

RR_PROX_RFLOOR = 0.5
RR_PROX_D0 = 0.055
RR_PROX_FC = 20.0
RR_PROX_CAP_HZ = 100.0
RR_PROX_CAP_DB = 18.0
RR_PROX_CT_MIN = 0.1
RR_PROX_C = 343.0
RR_PROX_N = 32
# [0] snap flag, [1:4] gA, [4:7] gB, [7:103] scaleA, [103:199] scaleB.
PROX_DOUBLES = 1 + 6 + RR_PROX_N * 3 * 2


def early_scale(distance: float) -> float:
    """d / max(d, 0.5). Exactly 1 at and beyond the floor, and at a dead tap.

    Callers skip the multiply when this returns 1 so a far tap stays bit-exact.
    """
    d = float(distance)
    if d <= 1e-9 or d >= RR_PROX_RFLOOR:
        return 1.0
    return d / RR_PROX_RFLOOR


def pattern_a(family: Optional[str], polar: Optional[float]) -> float:
    """First-order a. Bidirectional forces fig-8 (a = 0). Otherwise the polar slider."""
    fam = (family or "").strip().lower()
    if fam in ("bi", "bidirectional", "fig8"):
        return 0.0
    return float(polar_a_from_slider(0.5 if polar is None else polar))


def _lp_parts(hz: float, fc: float) -> Tuple[float, float]:
    w0 = 2.0 * math.pi * float(fc)
    w = 2.0 * math.pi * float(hz)
    den = w0 * w0 + w * w
    return (w0 * w0) / den, -(w0 * w) / den


def analog_boost_db(g: float, hz: float = RR_PROX_CAP_HZ, fc: float = RR_PROX_FC) -> float:
    """20*log10(|1 + g*w0/(jw+w0)|) at hz. This is the audible shelf, not the DC plateau."""
    lr, li = _lp_parts(hz, fc)
    mag2 = (1.0 + float(g) * lr) ** 2 + (float(g) * li) ** 2
    if mag2 <= 0.0:
        return -300.0
    return 10.0 * math.log10(mag2)


def cap_g(g: float, cap_db: float = RR_PROX_CAP_DB) -> float:
    """Leave g alone unless the analog 100 Hz boost exceeds the cap.

    The positive root of |1 + g*Lp| = 10^(cap/20) is the scaled g.
    """
    g = float(g)
    if not math.isfinite(g) or g <= 0.0:
        return 0.0
    if analog_boost_db(g) <= float(cap_db) + 1e-9:
        return g
    target = 10.0 ** (float(cap_db) / 20.0)
    lr, li = _lp_parts(RR_PROX_CAP_HZ, RR_PROX_FC)
    a = lr * lr + li * li
    b = 2.0 * lr
    c = 1.0 - target * target
    disc = b * b - 4.0 * a * c
    if a <= 0.0 or disc < 0.0:
        return g
    root = (-b + math.sqrt(disc)) / (2.0 * a)
    if root < 0.0:
        root = 0.0
    if root > g:
        root = g
    return float(root)


def shelf_g(r: float, a: float, cos_theta: float, tick: bool) -> float:
    """Uncapped formula, then the 100 Hz cap. Exactly 0 when the tick is off or r >= 0.5 m."""
    if not tick:
        return 0.0
    dist = float(r)
    if not (dist < RR_PROX_RFLOOR) or dist <= 1e-9:
        return 0.0
    c_t = float(cos_theta)
    if c_t < RR_PROX_CT_MIN:
        c_t = RR_PROX_CT_MIN
    aa = float(a)
    r_eff = dist + RR_PROX_D0
    num = (1.0 - aa) * c_t * (RR_PROX_C / r_eff)
    den = (2.0 * math.pi * RR_PROX_FC) * (aa + (1.0 - aa) * c_t)
    if den == 0.0 or not math.isfinite(den):
        return 0.0
    g = num / den
    if not math.isfinite(g) or g <= 0.0:
        return 0.0
    return cap_g(g)


def apply_prox_shelf(x, g: float, sr: float):
    """One-pole shelf. g == 0 returns the same array and does not read it."""
    if g == 0.0 or x is None:
        return x
    src = np.asarray(x, dtype=np.float64)
    p = math.exp(-2.0 * math.pi * RR_PROX_FC / float(sr))
    y = np.empty(src.shape[0], dtype=np.float64)
    lp = 0.0
    one_p = 1.0 - p
    gg = float(g)
    for i in range(src.shape[0]):
        xi = float(src[i])
        lp = one_p * xi + p * lp
        y[i] = xi + gg * lp
    return y


def scales_from_taps(taps, n: int = RR_PROX_N) -> list:
    """Per-line early scales, bus order L, C, R. Unused lines stay 1."""
    n = int(n)
    if n < 1:
        n = 1
    if n > RR_PROX_N:
        n = RR_PROX_N
    sc = [[1.0] * RR_PROX_N for _ in range(3)]
    if not taps:
        return sc
    n_t = len(taps)
    for i in range(n):
        t = taps[i % n_t]
        sc[0][i] = early_scale(float(t.distance_l))
        sc[1][i] = early_scale(float(getattr(t, "distance_c", 0.0) or 0.0))
        sc[2][i] = early_scale(float(t.distance_r))
    return sc


def capsule_gains(stand, source, tick_l, tick_c, tick_r) -> Tuple[float, float, float]:
    """Capped g for L, C, R. Theta is the pattern yaw, not the colour yaw."""
    left, right = mic_positions(stand)
    centre = centre_position(stand)
    mics = (left, centre, right)
    yaws = (float(stand.mlalr), float(stand.mcalr), float(stand.mralr))
    fams = (stand.family_l, stand.family_c, stand.family_r)
    pols = (stand.polar_l, stand.polar_c, stand.polar_r)
    ticks = (bool(tick_l), bool(tick_c), bool(tick_r))
    out = []
    sx, sy, sz = float(source[0]), float(source[1]), float(source[2])
    for mic, yaw, fam, pol, tick in zip(mics, yaws, fams, pols, ticks):
        dx = sx - float(mic[0])
        dy = sy - float(mic[1])
        dz = sz - float(mic[2])
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        cos_t = arrival_cos_ray(mic, (sx, sy, sz), yaw)
        out.append(shelf_g(dist, pattern_a(fam, pol), cos_t, tick))
    return (out[0], out[1], out[2])


def pack_prox(g_a: Sequence[float], g_b: Sequence[float], scale_a, scale_b) -> list:
    """199 floats for live_set_prox. Index 0 is the snap flag (the worklet overwrites it)."""
    out = [0.0]
    for g in (g_a, g_b):
        for i in range(3):
            out.append(float(g[i]) if g is not None and i < len(g) else 0.0)
    for scale in (scale_a, scale_b):
        for bus in range(3):
            row = scale[bus] if scale is not None and bus < len(scale) else None
            for i in range(RR_PROX_N):
                v = 1.0
                if row is not None and i < len(row):
                    v = float(row[i])
                out.append(v if math.isfinite(v) else 1.0)
    if len(out) != PROX_DOUBLES:
        raise RuntimeError(f"prox pack {len(out)} != {PROX_DOUBLES}")
    return out


def prox_is_bypass(buf) -> bool:
    """g is 0 and every scale is 1. The snap flag is not part of the law.

    A far scene omits the key so the live MD5 stays the room blob.
    """
    if not buf or len(buf) != PROX_DOUBLES:
        return False
    for i in range(1, 7):
        if float(buf[i]) != 0.0:
            return False
    for i in range(7, PROX_DOUBLES):
        if float(buf[i]) != 1.0:
            return False
    return True
