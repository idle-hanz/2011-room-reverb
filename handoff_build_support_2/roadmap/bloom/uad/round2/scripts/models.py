# Scratch implementations of the CURRENT Bloom presets as written in compressor_presets.json (2026-10-19 13:08).
# Run as ordinary compressors (detector and gain on the same signal) so they can be compared with the UAD units.
# Per-sample loops are compiled with numba if present, else plain python (slow but fine for 6 s clips).
import numpy as np
from scipy.signal import butter, sosfilt
SR = 48000
try:
    from numba import njit
except Exception:
    def njit(*a, **k):
        def w(f): return f
        return w if not (a and callable(a[0])) else a[0]

@njit(cache=True)
def gc_soft(xdb, T, R, W, R2, K2):
    """Giannoulis Eq.4 soft knee, optional second segment (ratio R2 above T+K2). Returns positive GR dB."""
    n = len(xdb); gr = np.zeros(n)
    for i in range(n):
        x = xdb[i]; d = x - T
        if W > 0 and 2 * d < -W: y = x
        elif W > 0 and abs(2 * d) <= W: y = x + (1.0 / R - 1.0) * (d + W / 2) ** 2 / (2 * W)
        elif W <= 0 and d <= 0: y = x
        else: y = T + d / R
        if R2 > 0 and d > K2:
            y = T + K2 / R + (d - K2) / R2
        gr[i] = x - y
    return gr

def level_db(x, sc_hpf_hz=0.0):
    s = x
    if sc_hpf_hz > 0:
        s = sosfilt(butter(1, sc_hpf_hz, 'hp', fs=SR, output='sos'), x)
    return 20 * np.log10(np.abs(s) + 1e-12)

@njit(cache=True)
def opto_light_memory(tgt_db, a1, a2, wf, tm, tmd):
    """Natural: conductance-domain two-stage attack / two-decay release with light memory M."""
    n = len(tgt_db); out = np.zeros(n)
    u = 0.0; fa = 0.0; sa = 0.0; rf = 0.0; rs = 0.0; w = 0.0; mode = 0; M = 0.0
    ka1 = 1 - np.exp(-1.0 / (a1 * SR)); ka2 = 1 - np.exp(-1.0 / (a2 * SR))
    km = 1 - np.exp(-1.0 / (tm * SR)); kmd = 1 - np.exp(-1.0 / (tmd * SR))
    for i in range(n):
        T = 10 ** (tgt_db[i] / 20.0) - 1.0
        if T > u:
            if mode != 1: fa = u; sa = u; mode = 1
            fa += (T - fa) * ka1; sa += (T - sa) * ka2; u = wf * fa + (1 - wf) * sa
        else:
            if mode != 2:
                rf = u; rs = u; w = 0.12 + 0.11 * M; mode = 2
            tf = 0.032 + 0.045 * M
            rf += (T - rf) * (1 - np.exp(-1.0 / (tf * SR))); rs += (T - rs) * (1 - np.exp(-1.0 / (0.9 * SR)))
            u = (1 - w) * rf + w * rs
        if u > 0.06: M += (1 - M) * km      # compressing (> ~0.5 dB)
        else: M -= M * kmd
        out[i] = 20 * np.log10(1 + max(u, 0.0))
    return out

@njit(cache=True)
def series_two_section(tgt, tau_att, tau1, tau2, C1, C2):
    """Glue: SSL Auto. GR(dB) = v1 + v2; charging current i = (tgt - v)*Cs/tau_att only while tgt > v."""
    n = len(tgt); out = np.zeros(n); v1 = 0.0; v2 = 0.0; dt = 1.0 / SR
    Cs = C1 * C2 / (C1 + C2)
    for i in range(n):
        v = v1 + v2; cur = 0.0
        if tgt[i] > v: cur = (tgt[i] - v) * Cs / tau_att
        # exact-ish: semi-implicit Euler per section (dt << tau)
        v1 = (v1 + dt * cur / C1) / (1 + dt / tau1)
        v2 = (v2 + dt * cur / C2) / (1 + dt / tau2)
        out[i] = v1 + v2
    return out

@njit(cache=True)
def onepole_branch(tgt, ta, tr):
    n = len(tgt); out = np.zeros(n); g = 0.0
    ka = 1 - np.exp(-1.0 / (ta * SR)); kr = 1 - np.exp(-1.0 / (tr * SR))
    for i in range(n):
        if tgt[i] > g: g += (tgt[i] - g) * ka
        else: g += (tgt[i] - g) * kr
        out[i] = g
    return out

@njit(cache=True)
def room_crush_det(tgt, ta1, ta2, wa, lag_s, tr):
    """Room Crush: onset lag at the start of each compression episode (GR fully released), two-stage attack
    (wa*fast + (1-wa)*slow; the weight is OUR assumption, the JSON gives only the two times), one-pole release."""
    n = len(tgt); out = np.zeros(n); f = 0.0; s = 0.0; g = 0.0; cnt = 0; idle = True; quiet = 0
    nq = int(0.020 * SR)  # 20 ms below threshold with GR released = new episode (our assumption)
    k1 = 1 - np.exp(-1.0 / (ta1 * SR)); k2 = 1 - np.exp(-1.0 / (ta2 * SR)); kr = 1 - np.exp(-1.0 / (tr * SR))
    nl = int(lag_s * SR)
    for i in range(n):
        if idle and tgt[i] > 0.0:
            cnt += 1
            if cnt > nl: idle = False
        if tgt[i] > g and not idle:
            f += (tgt[i] - f) * k1; s += (tgt[i] - s) * k2
            g = max(g, wa * f + (1 - wa) * s)
        elif tgt[i] <= g:
            g += (tgt[i] - g) * kr; f = min(f, g); s = min(s, g)
        quiet = quiet + 1 if tgt[i] <= 0.0 else 0
        if g < 0.05 and quiet > nq:
            idle = True; cnt = 0
        out[i] = g
    return out

@njit(cache=True)
def fairchild_rc(Vt, tau_att, CT, RT, RU, CU, RV, CV, use_v):
    """Swell: Fairchild pos5 (pos6 if use_v) release network in detector volts. Charging only while Vt > vCT."""
    n = len(Vt); out = np.zeros(n); vc = 0.0; vu = 0.0; vv = 0.0; dt = 1.0 / SR
    Ratt = tau_att / CT
    for i in range(n):
        cur = (Vt[i] - vc) / Ratt if Vt[i] > vc else 0.0
        iu = (vc - vu) / RU; iv = (vc - vv) / RV if use_v else 0.0
        vc += dt * (cur - vc / RT - iu - iv) / CT
        vu += dt * iu / CU
        if use_v: vv += dt * iv / CV
        out[i] = vc
    return out

def run_preset(name, x, T, makeup_db=0.0):
    """x: mono input; T: threshold dBFS (fitted). Returns (y, gr_db positive)."""
    if name == "natural":
        L = level_db(x)
        tgt = gc_soft(L, T, 5.0, 8.0, 4.0, 20.0)
        gr = opto_light_memory(tgt, 0.002, 0.16, 0.8, 0.3, 0.3)
    elif name == "glue":
        L = level_db(x)
        tgt = gc_soft(L, T, 4.0, 12.0, 0.0, 0.0)
        gr = series_two_section(tgt, 0.010, 0.0428, 5.1, 0.47e-6, 6.8e-6)
    elif name == "room_crush":
        L = level_db(x)
        tgt = gc_soft(L, T, 16.0, 9.0, 0.0, 0.0)
        gr = room_crush_det(tgt, 0.0004, 0.003, 0.7, 0.002, 0.300)
    elif name == "nuke":
        L = level_db(x, 100.0)
        tgt = gc_soft(L, T, 1e6, 0.0, 0.0, 0.0)
        fast = onepole_branch(tgt, 0.0025, 0.060); slow = onepole_branch(tgt, 0.350, 0.550)
        gr = 0.68 * fast + 0.32 * slow
    elif name == "swell":
        L = level_db(x, 100.0)
        tgt = np.minimum(gc_soft(L, T, 1.6, 10.0, 6.0, 10.0), 10.0)
        Vt = 8.06 * (np.exp(tgt / 18.1) - 1)
        V = fairchild_rc(Vt, 0.025, 4e-6, 220e3, 100e3, 8e-6, 100e3, 20e-6, False)
        gr = np.minimum(18.1 * np.log1p(np.maximum(V, 0) / 8.06), 10.0)
    else:
        raise ValueError(name)
    y = x * 10 ** ((makeup_db - gr) / 20.0)
    return y, gr

PRESET_UNIT = {"natural": "la2as_pr50", "glue": "ssl_4_auto", "room_crush": "fet_all", "nuke": "dis_nuke_room", "swell": "fc_t5"}
