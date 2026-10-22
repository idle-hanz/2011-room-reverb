"""Fit minimum-phase biquad cascades (RBJ shelves / peak) to the mic-colour magnitude.

Section types: 'LS' low shelf, 'HS' high shelf, 'PK' peaking (RBJ cookbook, all minimum phase
for positive Q/S). Parameters per section: log2(f), gain dB, log2(Q). Fit = least squares on the
dB error at log-spaced frequencies 20 Hz .. 20 kHz (weighted 1) + 20..23 kHz (weight 0.25).
"""
from __future__ import annotations
import math
import numpy as np
from scipy.optimize import least_squares

LAYOUTS = {
    2: ['LS', 'HS'],
    3: ['LS', 'HS', 'HS'],
    4: ['LS', 'HS', 'HS', 'PK'],
}


def rbj(kind, fs, f, gdb, q):
    A = 10 ** (gdb / 40.0); w0 = 2 * math.pi * f / fs
    cw, sw = math.cos(w0), math.sin(w0); al = sw / (2 * q)
    if kind == 'PK':
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    elif kind == 'LS':
        sA = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    else:  # HS
        sA = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    return np.array([b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0]])


def sos_db(sos, f, fs):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f) / fs)
    H = np.ones_like(z)
    for b0, b1, b2, a1, a2 in sos:
        H = H * (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20 * np.log10(np.maximum(np.abs(H), 1e-12))


def params_to_sos(p, layout, fs):
    out = []
    for i, k in enumerate(layout):
        lf, g, lq = p[3 * i: 3 * i + 3]
        f = float(np.clip(2 ** lf, 10.0, 0.49 * fs))
        out.append(rbj(k, fs, f, float(g), float(2 ** lq)))
    return np.array(out)


FIT_F = np.concatenate([np.geomspace(20, 20000, 240), np.linspace(20100, 23000, 12)])
FIT_W = np.concatenate([np.ones(240), 0.25 * np.ones(12)])


def init_params(target_db_fn, layout, fs):
    lo = float(target_db_fn(np.array([20.0]))[0]); hi = float(target_db_fn(np.array([16000.0]))[0])
    mid = float(target_db_fn(np.array([1000.0]))[0])
    p = []
    for i, k in enumerate(layout):
        if k == 'LS':
            p += [math.log2(150.0), lo - mid * 0.5, math.log2(0.6)]
        elif k == 'HS' and i == 1:
            p += [math.log2(1500.0), (hi - lo) * 0.6 + mid * 0.5, math.log2(0.5)]
        elif k == 'HS':
            p += [math.log2(8000.0), (hi - lo) * 0.4, math.log2(0.6)]
        else:
            p += [math.log2(3000.0), 0.0, math.log2(1.0)]
    return np.array(p)


def bounds(layout, fs):
    lo, hi = [], []
    for k in layout:
        lo += [math.log2(15.0), -40.0, math.log2(0.2)]
        hi += [math.log2(0.45 * fs), 30.0, math.log2(4.0 if k == 'PK' else 2.0)]
    return np.array(lo), np.array(hi)


def fit(target_db, fs, K, p0=None):
    """target_db: callable f->dB. Returns (sos, params, err dict)."""
    layout = LAYOUTS[K]
    tgt = target_db(FIT_F)
    def resid(p):
        return (sos_db(params_to_sos(p, layout, fs), FIT_F, fs) - tgt) * FIT_W
    lo, hi = bounds(layout, fs)
    starts = [p0] if p0 is not None else []
    starts.append(init_params(target_db, layout, fs))
    best = None
    for s in starts:
        s = np.clip(s, lo + 1e-6, hi - 1e-6)
        r = least_squares(resid, s, bounds=(lo, hi), x_scale='jac', max_nfev=400)
        if best is None or r.cost < best.cost:
            best = r
    sos = params_to_sos(best.x, layout, fs)
    return sos, best.x


def errors(sos, target_db, fs, fmax=20000.0):
    f = np.geomspace(20, fmax, 600)
    e = sos_db(sos, f, fs) - target_db(f)
    return float(np.max(np.abs(e))), float(np.sqrt(np.mean(e ** 2)))
