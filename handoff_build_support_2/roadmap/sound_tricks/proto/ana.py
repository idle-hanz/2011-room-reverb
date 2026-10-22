"""Analysis helpers: ISO 3382-style octave T30/EDT/C50/C80, Abel-Huang NED, tail IC per 1/3 octave,
and theoretical diffuse-field coherence of a two-mic array."""
import numpy as np, math
from scipy import signal
SR = 48000
OCT = (125, 250, 500, 1000, 2000, 4000, 8000)

def octave(x, fc, sr=SR, order=3):
    lo, hi = fc / 2 ** 0.5, min(fc * 2 ** 0.5, 0.45 * sr)
    sos = signal.butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x)

def edc_db(x):
    e = np.cumsum((x ** 2)[::-1])[::-1]
    e = e / max(e[0], 1e-300)
    return 10 * np.log10(np.maximum(e, 1e-30))

def t_fit(edc, lo, hi, sr=SR):
    i0 = np.argmax(edc <= lo); i1 = np.argmax(edc <= hi)
    if i1 <= i0 + 2:
        return float("nan")
    t = np.arange(i0, i1) / sr
    a, b = np.polyfit(t, edc[i0:i1], 1)
    return -60.0 / a

def onset(x):
    a = np.abs(x); return int(np.argmax(a >= 0.1 * a.max()))

def params(ir, sr=SR, bands=OCT):
    """ir: mono. Returns per-band T30, T20, EDT, C50, C80 (onset = first sample >= -20 dB of peak)."""
    out = {}
    n0 = onset(ir)
    for fc in bands:
        y = octave(ir, fc, sr)[n0:]
        e = edc_db(y)
        n50, n80 = int(0.05 * sr), int(0.08 * sr)
        E = y ** 2
        c50 = 10 * math.log10(E[:n50].sum() / max(E[n50:].sum(), 1e-300))
        c80 = 10 * math.log10(E[:n80].sum() / max(E[n80:].sum(), 1e-300))
        out[fc] = dict(T30=t_fit(e, -5, -35, sr), T20=t_fit(e, -5, -25, sr), EDT=t_fit(e, 0, -10, sr), C50=c50, C80=c80)
    return out

def ned(ir, sr=SR, win_ms=20.0):
    """Abel & Huang 2006 normalised echo density, Hann-weighted sliding window, per ms."""
    n = int(win_ms * 1e-3 * sr) | 1
    w = np.hanning(n); w /= w.sum()
    x = ir
    hop = int(1e-3 * sr)
    t, v = [], []
    for c in range(n // 2, len(x) - n // 2, hop):
        seg = x[c - n // 2:c + n // 2 + 1]
        sd = math.sqrt(max(float(np.sum(w * seg ** 2)), 1e-300))
        v.append(float(np.sum(w * (np.abs(seg) > sd))) / 0.3173)
        t.append(c / sr)
    return np.array(t), np.array(v)

def third_centres(lo=63, hi=12500):
    k = np.arange(-30, 30)
    f = 1000 * 2 ** (k / 3)
    return f[(f >= lo * 0.99) & (f <= hi * 1.01)]

def tail_ic(L, R, sr=SR, t0=0.08, t1=1.0):
    """Signed interchannel coherence Re{sum X Y*}/sqrt(sum|X|^2 sum|Y|^2) per 1/3 octave, tail window."""
    a, b = int(t0 * sr), int(t1 * sr)
    x, y = L[a:b], R[a:b]
    nf = 1 << int(math.ceil(math.log2(len(x))))
    X = np.fft.rfft(x, nf); Y = np.fft.rfft(y, nf)
    f = np.fft.rfftfreq(nf, 1 / sr)
    out = []
    for fc in third_centres():
        m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        num = np.real(np.sum(X[m] * np.conj(Y[m])))
        den = math.sqrt(np.sum(np.abs(X[m]) ** 2) * np.sum(np.abs(Y[m]) ** 2))
        out.append((float(fc), float(num / den) if den > 0 else float("nan")))
    return out

def fib_sphere(n=4000):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)

def diffuse_coherence(freqs, d_m, yaw1_deg, yaw2_deg, a1=0.5, a2=0.5, c=343.0):
    """Spherically isotropic field. Mics on the x axis at -d/2, +d/2, looking along yaw (0 = +y forward)
    in the horizontal plane. Pattern a + (1-a)cos(theta): a=1 omni, 0.5 cardioid, 0 fig-8."""
    u = fib_sphere()
    def look(yaw):
        r = math.radians(yaw); return np.array([math.sin(r), math.cos(r), 0.0])
    g1 = a1 + (1 - a1) * (u @ look(yaw1_deg)); g2 = a2 + (1 - a2) * (u @ look(yaw2_deg))
    proj = u[:, 0] * d_m
    out = []
    for f in freqs:
        k = 2 * math.pi * f / c
        num = np.mean(g1 * g2 * np.cos(k * proj))
        out.append(float(num / math.sqrt(np.mean(g1 ** 2) * np.mean(g2 ** 2))))
    return np.array(out)
