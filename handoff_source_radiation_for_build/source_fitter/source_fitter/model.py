"""Source radiation model v1 — mirror of the mic model (dual shelf + soft one-pole).

Relative response H(dir, f) / H(axis, f) in dB, *as realised by the DSP*:
    per direction d (source frame x=fwd, y=left, z=up):
      theta = angle between d and the radiation axis (axis = fwd rotated by aim_az/aim_el)
      u     = (1 - cos theta)/2                       (0 on axis, 1 at the back)
      w     = u**p * (1 - q * u**8)                   (q = back-lobe recovery, 0..1)
      A     = max(0, 1 + b_ud * d_up + b_lr * d_left) (vertical / lateral asymmetry)
      k     = w * A                                   (0 on axis -> exact bypass)
      k_lo  = A * ((1-dip) u**p_lo (1-q u**8) + dip*4u(1-u))   (broadband stage; dip = open-back side null)
    DSP per image (FIRST stage of the serial cascade):
      broadband gain      g_db = k_lo * lo_db
      RBJ high shelf      (f0, gain = k * hi_db, S = shelf_s)  @ fs
      soft beaming LP     fc = lp_hz / k (bypass if >= 0.45 fs), mix = lp_mix, order 1 or 2
                          y = (1-lp_mix) x + lp_mix LP^order(x)   (same form as mic 'soft one-pole')
On axis k = 0 -> gain 0 dB, shelf 0 dB, LP bypassed -> bit-exact null.
Size: a_eq = c / (2 pi f0) (piston ka = 1 beaming onset). UI 'size' rescales f0 and lp_hz by a_preset/a_user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import numpy as np

C = 343.0
FS = 48000.0
MODEL_NAME = "radiation_shelf_plus_soft_one_pole"
PRESET_SCHEMA = "source_fitter.preset.v1"

PARAM_NAMES: Tuple[str, ...] = ("lo_db", "hi_db", "f0", "shelf_s", "p", "q", "b_ud", "b_lr",
                                "aim_az", "aim_el", "lp_hz", "lp_mix", "p_lo", "dip")
PARAM_BOUNDS: Dict[str, Tuple[float, float]] = {
    "lo_db": (-15.0, 4.0),      # broadband (all-frequency) depth at full weight
    "hi_db": (-40.0, 6.0),      # extra high-shelf depth at full weight
    "f0": (150.0, 12000.0),     # shelf corner  (a_eq = c/(2 pi f0))
    "shelf_s": (0.25, 1.0),     # RBJ shelf slope S (<=1: no overshoot)
    "p": (0.3, 4.0),            # angle-law exponent
    "q": (0.0, 1.0),            # back-lobe recovery at 180 deg (open-back / dipole-ish)
    "b_ud": (-0.8, 0.8),        # + = more attenuation upward
    "b_lr": (-0.8, 0.8),        # + = more attenuation to the source's left
    "aim_az": (-35.0, 35.0),    # radiation axis offset from 'facing' (deg, + = left)
    "aim_el": (-35.0, 35.0),    # (deg, + = up)
    "lp_hz": (150.0, 24000.0),  # beaming low-pass knee at full weight (fc = lp_hz / k)
    "lp_mix": (0.0, 1.0),
    "p_lo": (0.3, 4.0),         # angle-law exponent for the broadband (LF) stage
    "dip": (0.0, 1.0),          # broadband-stage dipole share: side null, front+back open (open-back cabs)
}
OMNI = {"lo_db": 0.0, "hi_db": 0.0, "f0": 2000.0, "shelf_s": 0.7, "p": 1.0, "q": 0.0, "b_ud": 0.0,
        "b_lr": 0.0, "aim_az": 0.0, "aim_el": 0.0, "lp_hz": 24000.0, "lp_mix": 0.0, "p_lo": 1.0, "dip": 0.0}


def axis_frame(aim_az_deg: float, aim_el_deg: float):
    az, el = np.deg2rad(aim_az_deg), np.deg2rad(aim_el_deg)
    a = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    up = np.array([-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)])
    left = np.cross(up, a)
    return a, left, up


def weight_k2(params: Dict[str, float], dirs: np.ndarray):
    """Returns (k_lo, k_hi): angle weights for the broadband stage and the shelf/pole stage.
    k_hi = A * u^p (1 - q u^8);  k_lo = A * ((1-dip) u^p_lo (1 - q u^8) + dip * 4u(1-u))."""
    a, left, up = axis_frame(params["aim_az"], params["aim_el"])
    c = np.clip(dirs @ a, -1.0, 1.0)
    u = 0.5 * (1.0 - c)
    back = (1.0 - params["q"] * u ** 8)
    A = np.maximum(0.0, 1.0 + params["b_ud"] * (dirs @ up) + params["b_lr"] * (dirs @ left))
    k_hi = A * u ** params["p"] * back
    dip = params.get("dip", 0.0)
    k_lo = A * ((1.0 - dip) * u ** params.get("p_lo", params["p"]) * back + dip * 4.0 * u * (1.0 - u))
    return k_lo, k_hi


def weight_k(params: Dict[str, float], dirs: np.ndarray) -> np.ndarray:
    return weight_k2(params, dirs)[1]


def rbj_high_shelf(f0, gain_db, S, fs=FS):
    """Vectorised RBJ cookbook high shelf; returns (b0,b1,b2,a1,a2) normalised."""
    gain_db = np.asarray(gain_db, float)
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2 * np.pi * min(f0, 0.45 * fs) / fs
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2 * np.sqrt(np.maximum((A + 1 / A) * (1 / S - 1) + 2, 1e-9))
    sa = 2 * np.sqrt(A) * alpha
    b0 = A * ((A + 1) + (A - 1) * cw + sa)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - sa)
    a0 = (A + 1) - (A - 1) * cw + sa
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - sa
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def biquad_mag_db(coefs, freqs, fs=FS):
    b0, b1, b2, a1, a2 = [np.asarray(c)[..., None] for c in coefs]
    z1 = np.exp(-1j * 2 * np.pi * np.asarray(freqs) / fs)
    num = b0 + b1 * z1 + b2 * z1 ** 2
    den = 1 + a1 * z1 + a2 * z1 ** 2
    return 20 * np.log10(np.maximum(np.abs(num / den), 1e-12))


def one_pole_g(fc, fs=FS):
    return 1.0 - np.exp(-2 * np.pi * np.asarray(fc, float) / fs)


def soft_pole_mag_db(k, lp_hz, lp_mix, freqs, fs=FS, order=1):
    """Soft beaming low-pass: y = (1-mix) x + mix * LP^order(x), LP = one-pole at fc = lp_hz / k.
    order 2 = two cascaded identical one-poles (12 dB/oct, piston-like main-lobe narrowing)."""
    k = np.asarray(k, float)[..., None]
    fc = lp_hz / np.maximum(k, 1e-9)
    byp = fc >= 0.45 * fs
    g = one_pole_g(np.minimum(fc, 0.45 * fs), fs)
    z1 = np.exp(-1j * 2 * np.pi * np.asarray(freqs) / fs)
    H = (g / (1 - (1 - g) * z1)) ** int(order)
    Hs = (1 - lp_mix) + lp_mix * H
    Hs = np.where(byp, 1.0 + 0j, Hs)
    return 20 * np.log10(np.maximum(np.abs(Hs), 1e-12))


def relative_db(params: Dict[str, float], dirs: np.ndarray, freqs: np.ndarray, fs=FS,
                size_scale: float = 1.0) -> np.ndarray:
    """(D,F) dB relative to on-axis. size_scale = a_user / a_preset (bigger -> lower f0)."""
    k_lo, k = weight_k2(params, dirs)
    f0 = params["f0"] / size_scale
    coefs = rbj_high_shelf(f0, k * params["hi_db"], params["shelf_s"], fs)
    out = biquad_mag_db(coefs, freqs, fs) + (k_lo * params["lo_db"])[:, None]
    if params["lp_mix"] > 1e-6:
        out = out + soft_pole_mag_db(k, params["lp_hz"] / size_scale, params["lp_mix"], freqs, fs,
                                     order=int(params.get("lp_order", 1)))
    return out


def fib_sphere(n=2000):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def directivity_index_db(params, freqs, fs=FS, n=3000, size_scale=1.0):
    """DI(f) = 10log10(|H(axis)|^2 / mean_sphere |H|^2), axis = model on-axis (0 dB)."""
    d = fib_sphere(n)
    r = relative_db(params, d, freqs, fs, size_scale)
    return -10 * np.log10(np.mean(10 ** (r / 10), 0))


def omni_params():
    return dict(OMNI)


def vec_to_params(x: Sequence[float]) -> Dict[str, float]:
    return {n: float(v) for n, v in zip(PARAM_NAMES, x)}
