# Round-2 signal library (shared by the PC input generator and the box analysis). 48 kHz, float64 math, saved float32.
import numpy as np
SR = 48000
def db2a(d): return 10.0 ** (d / 20.0)

def stair(f, levels, step_s):
    """Continuous-phase sine staircase; level = dBFS peak."""
    n = int(round(step_s * SR)); N = n * len(levels); t = np.arange(N) / SR
    amp = np.repeat([db2a(L) for L in levels], n)
    return amp * np.sin(2 * np.pi * f * t)

def stair_keep(levels, step_s, keep_s=0.5):
    n = int(round(step_s * SR)); k = int(round(keep_s * SR))
    return [[(i + 1) * n - k, (i + 1) * n] for i in range(len(levels))]

def twotone_stair(f1, f2, r12, levels, step_s):
    """Two tones, amplitude ratio a1:a2 = r12:1, composite peak (a1+a2) = level dBFS."""
    n = int(round(step_s * SR)); N = n * len(levels); t = np.arange(N) / SR
    pk = np.repeat([db2a(L) for L in levels], n)
    a1 = pk * r12 / (r12 + 1.0); a2 = pk / (r12 + 1.0)
    return a1 * np.sin(2 * np.pi * f1 * t) + a2 * np.sin(2 * np.pi * f2 * t)

def ess(T, f1=20.0, f2=20000.0, fade_s=0.02):
    """Farina exponential sweep, unit peak, with raised-cosine fades. Returns x and L."""
    n = int(round(T * SR)); t = np.arange(n) / SR
    L = T / np.log(f2 / f1)
    x = np.sin(2 * np.pi * f1 * L * (np.exp(t / L) - 1.0))
    fd = int(fade_s * SR); w = np.ones(n)
    w[:fd] = 0.5 - 0.5 * np.cos(np.pi * np.arange(fd) / fd); w[-fd:] = w[:fd][::-1]
    return x * w, L

def tone_sweep_stair(levels, settle_s=1.5, sweep_s=1.0, tail_s=0.3, rel_db=-30.0, f0=1000.0, with_sweep=True):
    """Per step: 1 kHz tone at level; after settle_s a small ESS (rel_db below the tone) is added."""
    sw, _ = ess(sweep_s, 20.0, 20000.0, 0.005)
    n_set = int(round(settle_s * SR)); n_sw = len(sw); n_t = int(round(tail_s * SR)); n = n_set + n_sw + n_t
    N = n * len(levels); t = np.arange(N) / SR
    amp = np.repeat([db2a(L) for L in levels], n)
    x = amp * np.sin(2 * np.pi * f0 * t)
    keep = []
    for i, L in enumerate(levels):
        a = i * n + n_set
        if with_sweep: x[a:a + n_sw] += db2a(L + rel_db) * sw
        keep.append([a, a + n_sw + n_t])
    return x, keep

def quad_step(fc, lo_db, hi_db, t_step=0.5, t_hi=0.3, t_after=0.7, phase=0.0):
    """Carrier step (phase-continuous) for sample-accurate attack via sin/cos quadrature pair."""
    N = int(round((t_step + t_hi + t_after) * SR)); t = np.arange(N) / SR
    a = np.full(N, db2a(lo_db)); i0 = int(round(t_step * SR)); i1 = i0 + int(round(t_hi * SR))
    a[i0:i1] = db2a(hi_db)
    return a * np.sin(2 * np.pi * fc * t + phase), i0, i1

def freq_stair(freqs, level_db, step_s):
    segs = []
    for f in freqs:
        n = int(round(step_s * SR)); t = np.arange(n) / SR
        segs.append(db2a(level_db) * np.sin(2 * np.pi * f * t))
    return np.concatenate(segs)

def bandnoise(T, level_rms_db, seed=1, f_lo=20.0, f_hi=20000.0):
    rng = np.random.default_rng(seed); n = int(round(T * SR))
    X = np.fft.rfft(rng.standard_normal(n)); fr = np.fft.rfftfreq(n, 1 / SR)
    X[(fr < f_lo) | (fr > f_hi)] = 0; x = np.fft.irfft(X, n)
    fd = int(0.02 * SR); w = np.ones(n); w[:fd] = np.linspace(0, 1, fd); w[-fd:] = w[:fd][::-1]
    x *= w
    return x * db2a(level_rms_db) / np.sqrt(np.mean(x ** 2))
