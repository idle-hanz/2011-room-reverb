"""Vectorised, SciPy-free replacement for mic_colour.sos_fit.apply_sos (build_support_2, decision 7).

Idea: each biquad's impulse response has a closed form from its poles/residues,
    h[0] = b0,  h[n] = A p1^n + B p2^n  (n >= 1),
so the cascade IR is built with numpy (no per-sample Python loop), truncated where the
slowest pole has decayed below `tol_db` relative to the IR peak, and applied with one FFT
convolution. Repeated / nearly repeated poles (|p1 - p2| < 1e-7) fall back to the exact
recurrence for that section's IR only (length L loop, not length-of-signal).
Output = first len(x) samples of the causal filter, same as apply_sos (zero initial state).
"""
from __future__ import annotations
import numpy as np


def _next_pow2(n: int) -> int:
    return 1 << max(0, int(n - 1).bit_length())


def _section_ir(b0, b1, b2, a1, a2, L):
    h = np.zeros(L, dtype=np.float64)
    h0 = b0
    h1 = b1 - a1 * h0
    h2 = b2 - a1 * h1 - a2 * h0
    r = np.roots([1.0, a1, a2]) if abs(a2) > 0 or abs(a1) > 0 else np.array([0.0, 0.0])
    h[0] = h0
    if L == 1:
        return h
    if len(r) == 2 and abs(r[0] - r[1]) > 1e-7:
        p1, p2 = complex(r[0]), complex(r[1])
        # h1 = A p1 + B p2 ; h2 = A p1^2 + B p2^2
        M = np.array([[p1, p2], [p1 * p1, p2 * p2]], dtype=complex)
        A, B = np.linalg.solve(M, np.array([h1, h2], dtype=complex))
        n = np.arange(1, L)
        h[1:] = np.real(A * np.power(p1, n) + B * np.power(p2, n))
        return h
    # repeated poles or degenerate section: exact recurrence (short)
    x = np.zeros(L); x[0] = 1.0
    z1 = z2 = 0.0
    for i in range(L):
        xi = x[i]; yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        h[i] = yi
    return h


def cascade_ir(sos, tol_db: float = -200.0, max_len: int = 1 << 20):
    sos = np.asarray(sos, dtype=np.float64).reshape(-1, 5)
    rmax = 0.0
    for _, _, _, a1, a2 in sos:
        rr = np.abs(np.roots([1.0, a1, a2])) if (a1 or a2) else np.array([0.0])
        rmax = max(rmax, float(np.max(rr)) if rr.size else 0.0)
    if rmax >= 1.0:
        raise ValueError(f'unstable section (pole radius {rmax})')
    ns = len(sos)
    if rmax <= 1e-12:
        L = 3 * ns + 1
    else:
        # slowest pole below tol_db, plus polynomial growth margin for cascaded poles
        L = int(np.ceil((tol_db / 20.0) / np.log10(rmax))) + 64 * ns
    L = int(min(max(L, 3 * ns + 1), max_len))
    h = np.zeros(L); h[0] = 1.0
    nfft = _next_pow2(2 * L)
    H = np.ones(nfft // 2 + 1, dtype=complex)
    for b0, b1, b2, a1, a2 in sos:
        H *= np.fft.rfft(_section_ir(b0, b1, b2, a1, a2, L), nfft)
    return np.fft.irfft(H, nfft)[:L]


def apply_sos_numpy(buf, sos, tol_db: float = -200.0) -> np.ndarray:
    x = np.asarray(buf, dtype=np.float64).reshape(-1)
    sos = np.asarray(sos, dtype=np.float64)
    if sos.size == 0 or x.size == 0:
        return x
    h = cascade_ir(sos, tol_db)
    n = x.size + h.size - 1
    nfft = _next_pow2(n)
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[: x.size]
