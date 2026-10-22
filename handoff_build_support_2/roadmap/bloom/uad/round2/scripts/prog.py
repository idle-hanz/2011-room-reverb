# Synthetic, royalty-free program material for round 2 (deterministic). All mono 48 kHz, peak-normalised to 1.0.
import numpy as np
from scipy.signal import butter, sosfilt, lfilter
SR = 48000
def _env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))
def _hp(x, fc, o=2): return sosfilt(butter(o, fc, 'hp', fs=SR, output='sos'), x)
def _lp(x, fc, o=2): return sosfilt(butter(o, fc, 'lp', fs=SR, output='sos'), x)
def _bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'bp', fs=SR, output='sos'), x)
def _add(buf, sig, t):
    i = int(round(t * SR)); j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i]

def kick(rng, vel=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035); ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * _env(n, 0.16)
    click = _hp(rng.standard_normal(n), 2500) * _env(n, 0.0025) * 0.35
    return vel * (body + click)

def snare(rng, vel=1.0):
    n = int(0.4 * SR); t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 185 * t) + 0.6 * np.sin(2 * np.pi * 330 * t)) * _env(n, 0.06) * 0.5
    nz = _bp(rng.standard_normal(n), 1200, 9000) * _env(n, 0.13)
    att = _hp(rng.standard_normal(n), 3000) * _env(n, 0.004) * 0.6
    return vel * (tone + nz + att) * 0.8

def hat(rng, vel=1.0, open_=False):
    n = int((0.35 if open_ else 0.08) * SR)
    nz = _hp(rng.standard_normal(n), 7000, 4) * _env(n, 0.12 if open_ else 0.022)
    return vel * nz * 0.35

def drums(T=6.0, bpm=120.0, seed=11):
    rng = np.random.default_rng(seed); buf = np.zeros(int(T * SR)); beat = 60.0 / bpm
    nb = int(T / beat)
    for b in range(nb):
        t = b * beat
        if b % 4 in (0, 2) or (b % 8 == 7): _add(buf, kick(rng, 0.9 + 0.1 * rng.random()), t + 0.004 * rng.standard_normal())
        if b % 8 == 2: _add(buf, kick(rng, 0.7), t + beat * 0.5)
        if b % 4 in (1, 3): _add(buf, snare(rng, 0.85 + 0.15 * rng.random()), t + 0.003 * rng.standard_normal())
        for h in range(2):
            _add(buf, hat(rng, (0.9 if h == 0 else 0.55) * (0.8 + 0.2 * rng.random()), open_=(b % 8 == 6 and h == 1)), t + h * beat / 2)
    return buf

def vocal(T=6.0, seed=12):
    rng = np.random.default_rng(seed); n = int(T * SR); t = np.arange(n) / SR
    notes = [(0.15, 1.05, 220.0, 'a'), (1.15, 1.9, 246.9, 'e'), (2.0, 2.9, 261.6, 'o'), (3.15, 3.75, 293.7, 'i'),
             (3.8, 4.7, 261.6, 'a'), (4.8, 5.85, 220.0, 'u')]
    F = {'a': (800, 1150, 2900), 'e': (400, 1700, 2600), 'i': (300, 2300, 3000), 'o': (450, 800, 2830), 'u': (325, 700, 2530)}
    out = np.zeros(n)
    for (a, b, f0, v) in notes:
        i0, i1 = int(a * SR), int(b * SR); m = i1 - i0; tt = np.arange(m) / SR
        vib = 1 + 0.017 * np.sin(2 * np.pi * 5.5 * tt) * np.clip(tt / 0.3, 0, 1)
        scoop = 1 - 0.03 * np.exp(-tt / 0.06)
        f = f0 * vib * scoop * (1 + 0.003 * rng.standard_normal(m).cumsum() / np.sqrt(np.arange(1, m + 1)))
        ph = np.cumsum(f) / SR; frac = ph % 1.0
        src = np.where(frac < 0.6, 0.5 - 0.5 * np.cos(np.pi * frac / 0.6), np.cos(np.pi * (frac - 0.6) / 0.8)) - 0.25
        src = np.diff(np.concatenate([[0], src]))  # glottal flow derivative
        src += 0.004 * rng.standard_normal(m)  # aspiration
        y = np.zeros(m)
        for k, (fc, bw) in enumerate(zip(F[v], (80, 90, 120))):
            r = np.exp(-np.pi * bw / SR); w = 2 * np.pi * fc / SR
            y += (1.0 / (k + 1)) * lfilter([1 - r], [1, -2 * r * np.cos(w), r * r], src)
        env = np.clip(tt / 0.04, 0, 1) * np.clip((m / SR - tt) / 0.08, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.7 * tt + rng.random()))
        out[i0:i1] += y * env
    return out

def bass(T=6.0, bpm=120.0, seed=13):
    rng = np.random.default_rng(seed); buf = np.zeros(int(T * SR)); e8 = 30.0 / bpm
    roots = [55.0, 55.0, 65.4, 73.4, 55.0, 49.0, 55.0, 82.4]
    k = 0; t = 0.0
    while t < T - 0.3:
        f0 = roots[(k // 4) % len(roots)] * (2.0 if k % 8 == 7 else 1.0)
        n = int(e8 * 0.95 * SR); tt = np.arange(n) / SR
        ph = (f0 * tt) % 1.0; saw = 2 * ph - 1
        y = _lp(saw, 300 + 1400 * np.exp(-0)) * (np.exp(-tt / 0.25)) * np.clip(tt / 0.003, 0, 1) * np.clip((n / SR - tt) / 0.01, 0, 1)
        _add(buf, y * (0.85 + 0.15 * rng.random()), t); k += 1; t += e8
    return _lp(buf, 1200)

def tail_bursts(T=6.0, seed=14, rt60=1.8, period=1.5):
    """Reverb-tail-like decaying noise bursts: HF decays faster (two bands), soft onset."""
    rng = np.random.default_rng(seed); buf = np.zeros(int(T * SR))
    t = 0.05
    while t < T - 0.2:
        n = int(min(rt60 * 1.3, T - t) * SR); tt = np.arange(n) / SR
        lo = _lp(rng.standard_normal(n), 2000) * np.exp(-6.91 * tt / rt60)
        hi = _hp(rng.standard_normal(n), 2000) * np.exp(-6.91 * tt / (0.55 * rt60)) * 0.6
        on = np.clip(tt / 0.012, 0, 1)
        _add(buf, (lo + hi) * on * (0.7 + 0.3 * rng.random()), t); t += period * (0.8 + 0.4 * rng.random())
    return buf

def synth_ir(rt60=1.8, T=2.5, seed=15):
    rng = np.random.default_rng(seed); n = int(T * SR); tt = np.arange(n) / SR
    lo = _lp(rng.standard_normal(n), 3000) * np.exp(-6.91 * tt / rt60)
    hi = _hp(rng.standard_normal(n), 3000) * np.exp(-6.91 * tt / (0.5 * rt60)) * 0.5
    ir = (lo + hi) * np.clip(tt / 0.02, 0, 1); ir[0] = 0
    return ir / np.sqrt(np.sum(ir ** 2))

def norm(x): return (x / np.max(np.abs(x))).astype(np.float32)

def all_programs(T=6.0):
    d = drums(T); v = vocal(T); b = bass(T); tl = tail_bursts(T)
    mix = norm(d) * 0.55 + norm(b) * 0.45 + norm(v) * 0.5
    ir = synth_ir()
    wet = np.convolve(mix, ir)[:len(mix)]
    return {"drums": norm(d), "vocal": norm(v), "bass": norm(b), "tail": norm(tl), "mix": norm(mix), "wetmix": norm(wet)}
