# Round 3: "new BLOOM" dynamics = round-2 scratch models + the Idle-approved timing fixes, parameterised for fitting.
import numpy as np, sys
sys.path.insert(0, '/workspace/uad2/scripts')
from models import gc_soft, level_db, opto_light_memory, series_two_section, onepole_branch, room_crush_det, fairchild_rc, njit, SR

@njit(cache=True)
def opto2(tgt_db, a1, a2, wf, tf0, tfm, w0, wm, ts, tm, tmd, heavy_db, kh):
    """Natural v3: as opto_light_memory, but the slow-release weight/time now FALL with heavy GR (H state)
    and rise with light long GR (M state).  H tracks GR above heavy_db."""
    n = len(tgt_db); out = np.zeros(n)
    u = 0.0; fa = 0.0; sa = 0.0; rf = 0.0; rs = 0.0; w = 0.0; mode = 0; M = 0.0; H = 0.0
    ka1 = 1 - np.exp(-1.0 / (a1 * SR)); ka2 = 1 - np.exp(-1.0 / (a2 * SR))
    km = 1 - np.exp(-1.0 / (tm * SR)); kmd = 1 - np.exp(-1.0 / (tmd * SR))
    ks = 1 - np.exp(-1.0 / (ts * SR)); kH = 1 - np.exp(-1.0 / (0.05 * SR))
    for i in range(n):
        T = 10 ** (tgt_db[i] / 20.0) - 1.0
        if T > u:
            if mode != 1: fa = u; sa = u; mode = 1
            fa += (T - fa) * ka1; sa += (T - sa) * ka2; u = wf * fa + (1 - wf) * sa
        else:
            if mode != 2:
                rf = u; rs = u; w = max(0.0, min(0.9, w0 + wm * M - kh * H)); mode = 2
            tf = tf0 + tfm * M
            rf += (T - rf) * (1 - np.exp(-1.0 / (tf * SR))); rs += (T - rs) * ks
            u = (1 - w) * rf + w * rs
        g = 20 * np.log10(1 + max(u, 0.0))
        if u > 0.06: M += (1 - M) * km
        else: M -= M * kmd
        if mode == 1:
            hv = 1.0 if g > heavy_db else 0.0
            H += (hv - H) * kH
        out[i] = g
    return out

@njit(cache=True)
def onepole_ar(tgt, ta, tr):
    n = len(tgt); out = np.zeros(n); g = 0.0
    ka = 1 - np.exp(-1.0 / (ta * SR)); kr = 1 - np.exp(-1.0 / (tr * SR))
    for i in range(n):
        if tgt[i] > g: g += (tgt[i] - g) * ka
        else: g += (tgt[i] - g) * kr
        out[i] = g
    return out

@njit(cache=True)
def nuke_det(tgt, ta, trf, trs, ws0, wsg, tg):
    """Nuke v3: one attack (both branches ~1 ms), dual release; slow share grows with time spent compressing."""
    n = len(tgt); out = np.zeros(n); f = 0.0; s = 0.0; G = 0.0
    ka = 1 - np.exp(-1.0 / (ta * SR)); kf = 1 - np.exp(-1.0 / (trf * SR)); ks = 1 - np.exp(-1.0 / (trs * SR)); kg = 1 - np.exp(-1.0 / (tg * SR))
    for i in range(n):
        t = tgt[i]
        if t > f: f += (t - f) * ka
        else: f += (t - f) * kf
        if t > s: s += (t - s) * ka
        else: s += (t - s) * ks
        if t > 0.5: G += (1 - G) * kg
        else: G -= G * kg * 0.25
        w = min(0.95, ws0 + wsg * G)
        out[i] = (1 - w) * f + w * s
    return out

@njit(cache=True)
def rc_det2(tgt, ta1, ta2, wa, lag_s, tr, beta):
    """Room Crush v3: as room_crush_det, but release time scales with depth: tr_eff = tr*(max(g,0.5)/10)^beta."""
    n = len(tgt); out = np.zeros(n); f = 0.0; s = 0.0; g = 0.0; cnt = 0; idle = True; quiet = 0
    nq = int(0.020 * SR)
    k1 = 1 - np.exp(-1.0 / (ta1 * SR)); k2 = 1 - np.exp(-1.0 / (ta2 * SR))
    nl = int(lag_s * SR)
    for i in range(n):
        if idle and tgt[i] > 0.0:
            cnt += 1
            if cnt > nl: idle = False
        if tgt[i] > g and not idle:
            f += (tgt[i] - f) * k1; s += (tgt[i] - s) * k2
            g = max(g, wa * f + (1 - wa) * s)
        elif tgt[i] <= g:
            te = tr * (max(g, 0.5) / 10.0) ** beta
            g += (tgt[i] - g) * (1 - np.exp(-1.0 / (te * SR))); f = min(f, g); s = min(s, g)
        quiet = quiet + 1 if tgt[i] <= 0.0 else 0
        if g < 0.05 and quiet > nq:
            idle = True; cnt = 0
        out[i] = g
    return out

DEF = {
 'glue':       dict(T=-28.3, R=4.0, W=6.0, ta=0.0065, t1=0.0428, t2=5.1),
 'natural':    dict(T=-25.6, a1=0.0006, a2=0.16, wf=0.8, tf0=0.032, tfm=0.045, w0=0.12, wm=0.11, ts=0.9, tm=0.3, tmd=0.3, heavy_db=12.0, kh=0.1),
 'room_crush': dict(T=-37.9, R=16.0, W=9.0, ta1=0.0004, ta2=0.003, wa=0.7, lag=0.002, tr=0.025, beta=0.0),
 'nuke':       dict(T=-24.0, ta=0.001, trf=0.060, trs=0.55, ws0=0.32, wsg=0.0, tg=0.5),
 'swell':      dict(T=-24.0, R=1.6, W=10.0, R2=6.0, K2=10.0, ta=0.0035, CT=4e-6, RT=220e3, RU=100e3, CU=8e-6),
}
def gr_of(name, x, P):
    if name == 'glue':
        return series_two_section(gc_soft(level_db(x), P['T'], P['R'], P['W'], 0.0, 0.0), P['ta'], P.get('t1', 0.0428), P.get('t2', 5.1), 0.47e-6, 6.8e-6)
    if name == 'natural':
        tgt = gc_soft(level_db(x), P['T'], 5.0, 8.0, 4.0, 20.0)
        return opto2(tgt, P['a1'], P['a2'], P['wf'], P['tf0'], P['tfm'], P['w0'], P['wm'], P['ts'], P['tm'], P['tmd'], P['heavy_db'], P['kh'])
    if name == 'room_crush':
        tgt = gc_soft(level_db(x), P['T'], P['R'], P['W'], 0.0, 0.0)
        return rc_det2(tgt, P['ta1'], P['ta2'], P['wa'], P['lag'], P['tr'], P.get('beta', 0.0))
    if name == 'nuke':
        tgt = gc_soft(level_db(x, 100.0), P['T'], 1e6, 0.0, 0.0, 0.0)
        return nuke_det(tgt, P['ta'], P['trf'], P['trs'], P['ws0'], P['wsg'], P['tg'])
    if name == 'swell':
        tgt = gc_soft(level_db(x, 100.0), P['T'], P['R'], P['W'], P['R2'], P['K2'])
        Vt = 8.06 * (np.exp(tgt / 18.1) - 1)
        V = fairchild_rc(Vt, P['ta'], P['CT'], P['RT'], P['RU'], P['CU'], 100e3, 20e-6, False)
        return 18.1 * np.log1p(np.maximum(V, 0) / 8.06)
def run(name, x, P=None):
    P = P or DEF[name]; gr = gr_of(name, x, P); return x * 10 ** (-gr / 20.0), gr
