# Round-3 compressor hybrid prototype: new-BLOOM dynamics (fitted) + static colour shaper (+GR depth law) + fixed EQ.
import numpy as np, json, os, sys
sys.path.insert(0, '/workspace/uad3'); sys.path.insert(0, '/workspace/uad2/scripts')
import dyn3
from numba import njit
from scipy.signal import resample_poly
SR = 48000
SIDE = {'natural': 'out', 'room_crush': 'out', 'nuke': 'out', 'swell': 'in', 'glue': 'none'}
def dyn_params(p):
    P = dict(dyn3.DEF[p]); f = '/workspace/uad3/fit_%s.json' % p
    if os.path.exists(f): P.update(json.load(open(f))['params'])
    return P
@njit(cache=True)
def shape(v, d, fam, vr, a2, a3, b):
    """distortion part only (y = v + out). fam 0 poly: vr*d*(a2 u^2 + a3 u^3), u=v/vr.
    fam 1 biased tanh: vr*d*((tanh(u+b)-tanh b)/sech^2 b - u).  d = per-sample depth."""
    n = len(v); o = np.empty(n); tb = np.tanh(b); s2 = 1 - tb * tb
    for i in range(n):
        u = v[i] / vr
        if fam == 0: o[i] = vr * d[i] * (a2 * u * u + a3 * u * u * u)
        else: o[i] = vr * d[i] * ((np.tanh(u + b) - tb) / s2 - u)
    return o
@njit(cache=True)
def shape_adaa(v, d, vr, a2, a3):
    """first-order ADAA of the poly shaper (fam 0) with slowly varying depth."""
    n = len(v); o = np.empty(n); xp = 0.0; Fp = 0.0
    for i in range(n):
        u = v[i] / vr; F = a2 * u ** 3 / 3 + a3 * u ** 4 / 4; du = u - xp
        if abs(du) > 1e-7: g = (F - Fp) / du
        else:
            m = 0.5 * (u + xp); g = a2 * m * m + a3 * m ** 3
        o[i] = vr * d[i] * g; xp = u; Fp = F
    return o
@njit(cache=True)
def dcblock(x, R):
    y = np.empty_like(x); xp = 0.0; yp = 0.0
    for i in range(len(x)):
        yp = x[i] - xp + R * yp; xp = x[i]; y[i] = yp
    return y
def depth(gr, C):
    if C.get('law', 'gr') == 'const': return np.ones_like(gr)
    return C['d0'] + (1 - C['d0']) * np.clip(gr / C['Gs'], 0, 1)
def colour(v, gr, C, os_=1, adaa=False):
    if C is None or C.get('off'): return v
    d = depth(gr, C); vr = 10 ** (C['vr_db'] / 20)
    if os_ > 1:
        vu = resample_poly(v, os_, 1); du = np.repeat(d, os_)[:len(vu)]
        o = shape(vu, du, C['fam'], vr, C.get('a2', 0.0), C.get('a3', 0.0), C.get('b', 0.0))
        o = resample_poly(o, 1, os_)[:len(v)]
    elif adaa and C['fam'] == 0:
        o = shape_adaa(v, d, vr, C.get('a2', 0.0), C.get('a3', 0.0))
    else:
        o = shape(v, d, C['fam'], vr, C.get('a2', 0.0), C.get('a3', 0.0), C.get('b', 0.0))
    if C.get('fc', 0) > 0:   # memory term: one-pole LP on the distortion component only
        from scipy.signal import lfilter
        al = np.exp(-2 * np.pi * C['fc'] / SR); o = lfilter([1 - al], [1, -al], o)
    o = dcblock(o, np.exp(-2 * np.pi * 5.0 / SR))
    return v + o
def run(p, x, P=None, C=None, os_=1, adaa=False):
    """returns y (no EQ), gr.  Output-side: colour(g*x); input-side: g*colour(x)."""
    P = P or dyn_params(p); gr = dyn3.gr_of(p, x, P); g = 10 ** (-gr / 20)
    if SIDE[p] == 'in' and C is not None: return g * colour(x, np.zeros_like(gr), C, os_, adaa), gr
    if SIDE[p] == 'out' and C is not None: return colour(g * x, gr, C, os_, adaa), gr
    return g * x, gr
