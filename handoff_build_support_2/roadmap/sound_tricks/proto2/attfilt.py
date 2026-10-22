"""Per-line attenuation filter design (box prototype). Structures compared for accuracy vs Play CPU.
S1   = first-order low shelf x first-order high shelf, packed in 1 biquad (Jot-style 'one-pole + shelf')
S1P1 = S1 + 1 free peaking biquad (2 biquads)      S1P2 = S1 + 2 free peaking (3 biquads)
GEQ  = S1 + 8 fixed octave peaking 63 Hz-8 kHz (9 biquads; two-stage design after Valimaki, Prawda & Schlecht)
Fit target: per-pass loss so each line decays at its own rate; residual = relative T60 error (Schlecht & Habets 2017
note the nonlinear dB->T60 error propagation, so we fit T directly)."""
import math, numpy as np
from scipy.optimize import least_squares
FIT_F = np.geomspace(20.0, 20000.0, 56)
OCT = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)
THIRD = 1000.0 * 2.0 ** (np.arange(-10, 11) / 3.0)
NB = {"S1": 0, "S1P1": 1, "S1P2": 2, "GEQ": 8}
GEQ_FC = np.array([63, 125, 250, 500, 1000, 2000, 4000, 8000], float)

def shelf1(G_db, fc, sr, kind):
    G = 10.0 ** (G_db / 20.0); r = math.sqrt(G)
    w = 2.0 * sr * math.tan(math.pi * min(fc, 0.49 * sr) / sr); K = 2.0 * sr
    b0, b1, a0, a1 = ((1.0, r * w, 1.0, w / r) if kind == "lo" else (r, w, 1.0 / r, w))
    B0, B1, A0, A1 = b0 * K + b1, b1 - b0 * K, a0 * K + a1, a1 - a0 * K
    return B0 / A0, B1 / A0, A1 / A0

def peak(sr, f0, q, g_db):
    A = 10 ** (g_db / 40); w0 = 2 * math.pi * min(f0, 0.45 * sr) / sr; al = math.sin(w0) / (2 * q); c = math.cos(w0)
    b0, b1, b2, a0, a1, a2 = 1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

def sections(p, struct, sr):
    lb0, lb1, la1 = shelf1(p[0], math.exp(p[1]), sr, "lo"); hb0, hb1, ha1 = shelf1(p[2], math.exp(p[3]), sr, "hi")
    out = [(lb0 * hb0, lb0 * hb1 + lb1 * hb0, lb1 * hb1, la1 + ha1, la1 * ha1)]
    if struct == "GEQ":
        for fc, g in zip(GEQ_FC, p[4:]):
            out.append(peak(sr, fc, 1.2, g))
    else:
        for k in range(NB[struct]):
            g, lf, lq = p[4 + 3 * k: 7 + 3 * k]
            out.append(peak(sr, math.exp(lf), math.exp(lq), g))
    return out

def resp_db(secs, f, sr):
    z = np.exp(-1j * 2 * np.pi * f / sr); h = np.ones_like(z)
    for b0, b1, b2, a1, a2 in secs:
        h = h * (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20 * np.log10(np.abs(h) + 1e-300)

def design_line(tau, rate_fn, fixed_db_fn, sr, struct="S1P1"):
    """tau s; rate_fn(f) -> wanted loss dB/s (>0); fixed_db_fn(f) -> dB already in the loop (lg + peaks, <=0).
    Returns (sections, max octave T err, max third-octave T err)."""
    f = FIT_F; want = -tau * rate_fn(f); fixed = fixed_db_fn(f); tgt = want - fixed
    Tw = 60.0 / rate_fn(f)
    def Tgot(p, ff):
        tot = fixed_db_fn(ff) + resp_db(sections(p, struct, sr), ff, sr)
        return -60.0 * tau / np.minimum(tot, -1e-6)
    x0 = [float(tgt[0]), math.log(200.0), float(tgt[-1]), math.log(5000.0)]
    lo = [-40.0, math.log(30.0), -40.0, math.log(800.0)]; hi = [40.0, math.log(3000.0), 40.0, math.log(0.45 * sr)]
    if struct == "GEQ":
        x0 += [0.0] * 8; lo += [-24.0] * 8; hi += [24.0] * 8
    else:
        for k in range(NB[struct]):
            x0 += [0.0, math.log([700.0, 2500.0][k % 2]), math.log(0.8)]; lo += [-24.0, math.log(60.0), math.log(0.3)]; hi += [24.0, math.log(12000.0), math.log(4.0)]
    x0 = [min(max(v, l + 1e-6), h - 1e-6) for v, l, h in zip(x0, lo, hi)]
    dense = np.concatenate([[0.01], np.geomspace(2.0, 0.4999 * sr, 160)])   # incl. ~DC and Nyquist
    t_cap = 2.0 * float(np.max(60.0 / rate_fn(f)))           # fit aims tighter (2.0x) than the guard checks (3.0x)
    marg = np.full_like(dense, 60.0 * tau / t_cap)              # i.e. loop gain <= -60 tau / t_cap everywhere, DC..Nyquist
    def resid(p):
        tot = fixed_db_fn(dense) + resp_db(sections(p, struct, sr), dense, sr)
        pen = 50.0 * np.maximum(0.0, tot + np.maximum(marg, 1e-4))     # stability: loop gain must stay below 0 dB
        return np.concatenate([Tgot(p, f) / Tw - 1.0, pen])
    res = least_squares(resid, x0, bounds=(lo, hi), max_nfev=600)
    secs = sections(res.x, struct, sr)
    e_oct = float(np.max(np.abs(Tgot(res.x, OCT) / (60.0 / rate_fn(OCT)) - 1)))
    e_3rd = float(np.max(np.abs(Tgot(res.x, THIRD[(THIRD >= 100) & (THIRD <= 10000)]) / (60.0 / rate_fn(THIRD[(THIRD >= 100) & (THIRD <= 10000)])) - 1)))
    return secs, e_oct, e_3rd
