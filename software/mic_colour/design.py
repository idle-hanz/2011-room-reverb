"""One causal minimum-phase FIR from relative_db at a stated sample rate.

Phase 3 calls design_ir again at the AudioContext rate. There is no second
biquad, and these coefficients are not reused at another rate.
"""

from __future__ import annotations

import math

import numpy as np

from mic_colour.hpf import stack_hpf
from mic_colour.model import relative_db


def design_n_fft(sr: int) -> int:
    """About 80 ms, power of two, clamped to 1024…8192."""
    n = max(1024, int(round(0.08 * float(sr))))
    n = 1 << max(10, math.ceil(math.log2(n)))
    if n < 1024:
        return 1024
    if n > 8192:
        return 8192
    return int(n)


def response_db(model, theta_deg: float, sr: int, n_fft: int, hpf: dict | None, hpf_engaged: bool):
    freqs = np.fft.rfftfreq(int(n_fft), d=1.0 / float(sr))
    db = np.asarray(relative_db(model, freqs, float(theta_deg)), dtype=np.float64)
    if hpf_engaged and hpf:
        db = np.asarray(
            stack_hpf(db, freqs, hpf.get("hpf_hz"), hpf.get("hpf_slope") or 12, True),
            dtype=np.float64,
        )
    return freqs, db


def minimum_phase_from_db(db: np.ndarray, n_fft: int) -> np.ndarray:
    """Real cepstrum → minimum phase. Magnitude of the result matches `db`."""
    mag = np.power(10.0, np.asarray(db, dtype=np.float64) / 20.0)
    mag = np.maximum(mag, 1e-8)
    cep = np.fft.irfft(np.log(mag), n=int(n_fft))
    win = np.zeros(int(n_fft), dtype=np.float64)
    half = int(n_fft) // 2
    win[0] = 1.0
    if int(n_fft) % 2 == 0:
        win[half] = 1.0
        if half > 1:
            win[1:half] = 2.0
    else:
        win[1:half + 1] = 2.0
    spec = np.exp(np.fft.rfft(cep * win, n=int(n_fft)))
    ir = np.fft.irfft(spec, n=int(n_fft))
    return np.real(ir).astype(np.float64, copy=False)


def design_ir(model, theta_deg: float, sr: int, hpf: dict | None = None, hpf_engaged: bool = False):
    """Impulse, or None when H is 0 dB (identity, skip the convolution)."""
    n_fft = design_n_fft(int(sr))
    _freqs, db = response_db(model, float(theta_deg), int(sr), n_fft, hpf, bool(hpf_engaged))
    if float(np.max(np.abs(db))) < 1e-5:
        return None
    return minimum_phase_from_db(db, n_fft)


def apply_fir(buf: np.ndarray, ir: np.ndarray | None) -> np.ndarray:
    """Causal FIR, same length as `buf`. None leaves the buffer untouched."""
    if ir is None:
        return buf
    x = np.asarray(buf, dtype=np.float64)
    h = np.asarray(ir, dtype=np.float64)
    n = int(x.size + h.size - 1)
    if n <= 0:
        return x
    nfft = 1 << max(0, (n - 1).bit_length())
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return np.real(y[: x.size]).astype(np.float64, copy=False)
