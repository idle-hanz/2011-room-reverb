"""Each-mic pattern the polar graphs and the engine share.

Display only. Play and Render do not call this. Measured amplitude is the
fitted relative_db (and the manufacturer high-pass when it is engaged).
That fit is already the polar, so the ideal pattern is not multiplied again.
The sign of the ideal pattern is kept when it is not zero. Bypass is the
preset pattern with no colour. A coincident S passes colour_offset_rad
so the shelf is sampled on the M axis while the pattern stays on the S aim.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

import numpy as np

from early_field import capsule_gain


def _as_freq(freqs: Sequence[float]) -> np.ndarray:
    return np.asarray(list(freqs), dtype=float)


def colour_db(
    theta_colour: np.ndarray,
    freqs: Sequence[float],
    model: Any,
    hpf: Optional[dict],
    hpf_on: bool,
    measured: bool,
) -> np.ndarray:
    """H_db as (n_az, n_freq). Bypass is zeros. Measured is the fitter plus HPF."""
    freqs_a = _as_freq(freqs)
    n_az = int(len(theta_colour))
    n_f = int(len(freqs_a))
    if not measured or model is None:
        return np.zeros((n_az, n_f), dtype=float)
    from mic_colour.hpf import stack_hpf
    from mic_colour.model import relative_db

    degs = np.degrees(np.asarray(theta_colour, dtype=float))
    raw = np.asarray(relative_db(model, freqs_a, degs), dtype=float)
    if raw.ndim == 1:
        raw = raw.reshape(1, -1)
    spec = hpf or {}
    db = np.asarray(
        stack_hpf(raw, freqs_a, spec.get("hpf_hz"), spec.get("hpf_slope") or 12, bool(hpf_on)),
        dtype=float,
    )
    if db.ndim == 1:
        db = db.reshape(1, -1)
    return db


def signed_amp(
    theta: np.ndarray,
    freqs: Sequence[float],
    *,
    family: Optional[str],
    polar: Optional[float],
    pattern: Optional[str],
    model: Any = None,
    hpf: Optional[dict] = None,
    hpf_on: bool = False,
    measured: bool = False,
    colour_offset_rad: float = 0.0,
) -> np.ndarray:
    """Signed linear amplitude, shape (n_az, n_freq).

    Pattern theta is the angle from this capsule's aim. Colour theta is that
    angle plus colour_offset_rad (π/2 while S is coincident with M).
    """
    th = np.asarray(theta, dtype=float)
    freqs_a = _as_freq(freqs)
    g = np.array([
        capsule_gain(float(t), family=family, polar=polar, pattern=pattern, signed=True)
        for t in th
    ], dtype=float)
    colour_th = th + float(colour_offset_rad)
    db = colour_db(colour_th, freqs_a, model, hpf, hpf_on, measured)
    lin = np.power(10.0, db / 20.0)
    if measured:
        sign = np.sign(g)
        sign[sign == 0.0] = 1.0
        return sign[:, None] * lin
    return g[:, None] * lin


def rings_db(
    theta: np.ndarray,
    freqs: Sequence[float],
    *,
    family: Optional[str] = None,
    polar: Optional[float] = None,
    pattern: Optional[str] = None,
    model: Any = None,
    hpf: Optional[dict] = None,
    hpf_on: bool = False,
    measured: bool = False,
    colour_offset_rad: float = 0.0,
) -> np.ndarray:
    """dB radii, shape (n_freq, n_az). A true null is −300 dB, not −inf."""
    amp = signed_amp(
        theta, freqs,
        family=family, polar=polar, pattern=pattern,
        model=model, hpf=hpf, hpf_on=hpf_on,
        measured=measured, colour_offset_rad=colour_offset_rad,
    )
    mag = np.abs(amp)
    db = np.full(mag.shape, -300.0, dtype=float)
    ok = mag > 1.0e-12
    db[ok] = 20.0 * np.log10(mag[ok])
    return db.T
