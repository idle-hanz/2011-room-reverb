"""RBJ biquads for measured mic colour. Parameters: log2(f), gain dB, log2(Q).

Layout K=3 is low shelf + two high shelves (the 27 Sep fit). No SciPy at import.
"""

from __future__ import annotations

import math

import numpy as np

LAYOUTS = {
    2: ["LS", "HS"],
    3: ["LS", "HS", "HS"],
    4: ["LS", "HS", "HS", "PK"],
}

MAGIC = -2011.0


def rbj(kind, fs, f, gdb, q):
    A = 10 ** (gdb / 40.0)
    w0 = 2 * math.pi * f / fs
    cw, sw = math.cos(w0), math.sin(w0)
    al = sw / (2.0 * q)
    if kind == "PK":
        b = [1 + al * A, -2 * cw, 1 - al * A]
        a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == "LS":
        sA = 2 * math.sqrt(A) * al
        b = [
            A * ((A + 1) - (A - 1) * cw + sA),
            2 * A * ((A - 1) - (A + 1) * cw),
            A * ((A + 1) - (A - 1) * cw - sA),
        ]
        a = [
            (A + 1) + (A - 1) * cw + sA,
            -2 * ((A - 1) + (A + 1) * cw),
            (A + 1) + (A - 1) * cw - sA,
        ]
    else:
        sA = 2 * math.sqrt(A) * al
        b = [
            A * ((A + 1) + (A - 1) * cw + sA),
            -2 * A * ((A - 1) + (A + 1) * cw),
            A * ((A + 1) + (A - 1) * cw - sA),
        ]
        a = [
            (A + 1) - (A - 1) * cw + sA,
            2 * ((A - 1) - (A + 1) * cw),
            (A + 1) - (A - 1) * cw - sA,
        ]
    inv = 1.0 / a[0]
    return np.array([b[0] * inv, b[1] * inv, b[2] * inv, a[1] * inv, a[2] * inv], dtype=np.float64)


def params_to_sos(p, layout, fs):
    out = []
    fs = float(fs)
    for i, k in enumerate(layout):
        lf, g, lq = p[3 * i : 3 * i + 3]
        f = float(np.clip(2 ** lf, 10.0, 0.49 * fs))
        out.append(rbj(k, fs, f, float(g), float(2 ** lq)))
    return np.asarray(out, dtype=np.float64)


def sos_db(sos, f, fs):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f, dtype=np.float64) / float(fs))
    H = np.ones_like(z, dtype=np.complex128)
    for b0, b1, b2, a1, a2 in np.asarray(sos, dtype=np.float64):
        H = H * (b0 + b1 * z + b2 * z * z) / (1.0 + a1 * z + a2 * z * z)
    return 20.0 * np.log10(np.maximum(np.abs(H), 1e-12))


def butter_hp_sos(fc, order, fs):
    """Digital Butterworth high-pass, a0 = 1. Uses SciPy when present."""
    from scipy.signal import butter

    hz = float(fc)
    n = int(order)
    if n < 1:
        n = 1
    if n > 6:
        n = 6
    rows = butter(n, hz, btype="highpass", fs=float(fs), output="sos")
    out = []
    for r in rows:
        a0 = float(r[3]) if abs(float(r[3])) > 1e-18 else 1.0
        out.append([r[0] / a0, r[1] / a0, r[2] / a0, r[4] / a0, r[5] / a0])
    return np.asarray(out, dtype=np.float64)


def hpf_order(slope) -> int:
    try:
        s = int(slope)
    except (TypeError, ValueError):
        s = 12
    return {6: 1, 12: 2, 18: 3, 24: 4}.get(s, 2)


def pack_record(sos) -> np.ndarray:
    sos = np.asarray(sos, dtype=np.float64)
    if sos.ndim != 2 or sos.shape[1] != 5 or sos.shape[0] < 1:
        raise ValueError("sos must be (K, 5)")
    k = int(sos.shape[0])
    out = np.empty(2 + 5 * k, dtype=np.float32)
    out[0] = MAGIC
    out[1] = float(k)
    out[2:] = sos.reshape(-1).astype(np.float32)
    return out


def unpack_record(arr):
    x = np.asarray(arr, dtype=np.float64).reshape(-1)
    if x.size < 7 or abs(float(x[0]) - MAGIC) > 1e-3:
        return None
    k = int(round(float(x[1])))
    if k < 1 or x.size < 2 + 5 * k:
        return None
    return x[2 : 2 + 5 * k].reshape(k, 5)


def _next_pow2(n: int) -> int:
    return 1 << max(0, int(n - 1).bit_length())


def _section_ir(b0, b1, b2, a1, a2, L):
    """One biquad's impulse response. Closed form from poles; a short recurrence if they repeat."""
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
        M = np.array([[p1, p2], [p1 * p1, p2 * p2]], dtype=complex)
        A, B = np.linalg.solve(M, np.array([h1, h2], dtype=complex))
        n = np.arange(1, L)
        h[1:] = np.real(A * np.power(p1, n) + B * np.power(p2, n))
        return h
    x = np.zeros(L)
    x[0] = 1.0
    z1 = z2 = 0.0
    for i in range(L):
        xi = x[i]
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        h[i] = yi
    return h


def _cascade_ir(sos, tol_db: float = -200.0, max_len: int = 1 << 20):
    sos = np.asarray(sos, dtype=np.float64).reshape(-1, 5)
    rmax = 0.0
    for _, _, _, a1, a2 in sos:
        rr = np.abs(np.roots([1.0, a1, a2])) if (a1 or a2) else np.array([0.0])
        rmax = max(rmax, float(np.max(rr)) if rr.size else 0.0)
    if rmax >= 1.0:
        raise ValueError(f"unstable section (pole radius {rmax})")
    ns = len(sos)
    if rmax <= 1e-12:
        L = 3 * ns + 1
    else:
        L = int(np.ceil((tol_db / 20.0) / np.log10(rmax))) + 64 * ns
    L = int(min(max(L, 3 * ns + 1), max_len))
    nfft = _next_pow2(2 * L)
    H = np.ones(nfft // 2 + 1, dtype=complex)
    for b0, b1, b2, a1, a2 in sos:
        H *= np.fft.rfft(_section_ir(b0, b1, b2, a1, a2, L), nfft)
    return np.fft.irfft(H, nfft)[:L]


def apply_sos(buf, sos) -> np.ndarray:
    """Causal SOS. Vectorised numpy cascade (FFT), same samples as TDF-II. No SciPy."""
    x = np.asarray(buf, dtype=np.float64).reshape(-1)
    sos = np.asarray(sos, dtype=np.float64)
    if sos.size == 0 or x.size == 0:
        return x
    h = _cascade_ir(sos)
    n = x.size + h.size - 1
    nfft = _next_pow2(n)
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[: x.size]
