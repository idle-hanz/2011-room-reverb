"""Minimum-phase RBJ biquad cascade fit to one ear's dB magnitude.

Same RBJ formulas and parameterisation as Build's mic_colour/sos_fit.py
(per section: log2 f, gain dB, log2 Q; a0 normalised; rows b0 b1 b2 a1 a2) so the
tables drop into the existing `pack_record` / `run_sos` path. Layouts here add
peaking (PK) sections for pinna notches / concha resonance:

  K=3: LS HS PK   K=4: LS HS PK PK   K=5: LS HS PK PK PK   K=6: LS HS PK PK PK PK
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares

from .core import FGRID, EVAL_MASK

LAYOUTS = {k: ["LS", "HS"] + ["PK"] * (k - 2) for k in range(2, 9)}

# Fit weights: 1 inside 100 Hz..16 kHz, 0.3 outside (keeps >16 kHz sane, not driving it)
FIT_W = np.where(EVAL_MASK, 1.0, 0.3)


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
        b = [A * ((A + 1) - (A - 1) * cw + sA), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - sA)]
        a = [(A + 1) + (A - 1) * cw + sA, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - sA]
    else:
        sA = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * cw + sA), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sA)]
        a = [(A + 1) - (A - 1) * cw + sA, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sA]
    inv = 1.0 / a[0]
    return np.array([b[0] * inv, b[1] * inv, b[2] * inv, a[1] * inv, a[2] * inv])


def params_to_sos(p, layout, fs):
    out = []
    for i, k in enumerate(layout):
        lf, g, lq = p[3 * i: 3 * i + 3]
        f = float(np.clip(2 ** lf, 10.0, 0.49 * fs))
        out.append(rbj(k, fs, f, float(g), float(2 ** lq)))
    return np.asarray(out)


def sos_db(sos, f, fs):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f) / fs)
    H = np.ones_like(z)
    for b0, b1, b2, a1, a2 in np.asarray(sos):
        H = H * (b0 + b1 * z + b2 * z * z) / (1.0 + a1 * z + a2 * z * z)
    return 20 * np.log10(np.maximum(np.abs(H), 1e-12))


def bounds(layout, fs):
    lo, hi = [], []
    for k in layout:
        if k == "LS":
            lo += [math.log2(30.0), -24.0, math.log2(0.3)]
            hi += [math.log2(1500.0), 24.0, math.log2(2.0)]
        elif k == "HS":
            lo += [math.log2(800.0), -40.0, math.log2(0.3)]
            hi += [math.log2(0.45 * fs), 24.0, math.log2(2.0)]
        else:
            lo += [math.log2(150.0), -36.0, math.log2(0.3)]
            hi += [math.log2(0.45 * fs), 24.0, math.log2(12.0)]
    return np.array(lo), np.array(hi)


def _resid_fn(tgt, layout, fs, f=FGRID, w=FIT_W):
    def r(p):
        return (sos_db(params_to_sos(p, layout, fs), f, fs) - tgt) * w
    return r


def _solve(tgt, layout, fs, p0):
    lo, hi = bounds(layout, fs)
    p0 = np.clip(p0, lo + 1e-6, hi - 1e-6)
    return least_squares(_resid_fn(tgt, layout, fs), p0, bounds=(lo, hi), x_scale="jac", max_nfev=600)


def _extrema(res_db, fs, n=3):
    """Largest |residual| peaks (weighted band) as PK seeds: (f, gain)."""
    m = EVAL_MASK & (FGRID < 0.44 * fs)
    r = np.where(m, res_db, 0.0)
    seeds = []
    rr = r.copy()
    for _ in range(n):
        i = int(np.argmax(np.abs(rr)))
        if abs(rr[i]) < 0.05:
            break
        seeds.append((float(FGRID[i]), float(rr[i])))
        lo, hi = FGRID[i] / 2 ** 0.35, FGRID[i] * 2 ** 0.35
        rr[(FGRID > lo) & (FGRID < hi)] = 0.0
    return seeds


def fit_ear(tgt_db: np.ndarray, fs: int, Kmax: int = 6, Kmin: int = 3):
    """Greedy-then-joint fit for K = 2..Kmax. Returns {K: (params, sos)} for K >= Kmin."""
    out = {}
    lf = float(np.interp(80.0, FGRID, tgt_db))
    mid = float(np.interp(1000.0, FGRID, tgt_db))
    hf = float(np.interp(12000.0, FGRID, tgt_db))
    best = None
    for hs_f in (2500.0, 6000.0, 10000.0):
        p0 = np.array([math.log2(200.0), lf - mid, math.log2(0.7),
                       math.log2(hs_f), hf - mid, math.log2(0.7)])
        # overall gain rides in the LS/HS pair: LS gain = lf - mid; add mid via both shelves
        p0[1] = lf
        p0[4] = hf - lf
        r = _solve(tgt_db, LAYOUTS[2], fs, p0)
        if best is None or r.cost < best.cost:
            best = r
    p = best.x
    for K in range(3, Kmax + 1):
        layout = LAYOUTS[K]
        res = tgt_db - sos_db(params_to_sos(p, LAYOUTS[K - 1], fs), FGRID, fs)
        cands = []
        for (f0, g0) in _extrema(res, fs, 3):
            for q0 in (1.5, 4.0):
                cands.append(np.concatenate([p, [math.log2(f0), g0, math.log2(q0)]]))
        if not cands:
            cands.append(np.concatenate([p, [math.log2(4000.0), 0.0, math.log2(1.0)]]))
        bestK = None
        for c in cands:
            r = _solve(tgt_db, layout, fs, c)
            if bestK is None or r.cost < bestK.cost:
                bestK = r
        p = bestK.x
        if K >= Kmin:
            out[K] = (p.copy(), params_to_sos(p, layout, fs))
    return out


def errors_db(sos, tgt_db, fs, mask=EVAL_MASK):
    e = sos_db(sos, FGRID[mask], fs) - tgt_db[mask]
    return float(np.max(np.abs(e))), float(np.sqrt(np.mean(e ** 2)))


def stability(sos):
    """Max pole radius and max zero radius over sections (both < 1 => stable, min-phase)."""
    pr, zr = 0.0, 0.0
    for b0, b1, b2, a1, a2 in np.asarray(sos):
        pr = max(pr, float(np.max(np.abs(np.roots([1.0, a1, a2])))))
        zr = max(zr, float(np.max(np.abs(np.roots([b0, b1, b2])))) if abs(b0) > 1e-15 else 0.0)
    return pr, zr
