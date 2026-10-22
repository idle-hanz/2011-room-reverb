"""Parametric s(f) model, per-hit specular/scatter split, Lambert cluster envelope, velvet cluster, shelf fit."""
import math
import numpy as np
from scipy.optimize import least_squares

# ---------------------------------------------------------------- s(f) model
def s_logistic(f, s_lo, s_hi, fc, k):
    """Logistic in log2-frequency. s_lo floor, s_hi ceiling, fc midpoint (Hz), k slope per octave."""
    f = np.asarray(f, dtype=float)
    return s_lo + (s_hi - s_lo) / (1.0 + np.exp(-k * np.log2(f / fc)))


def fit_logistic(f, s, fixed=None, x0=None):
    """Least-squares fit. fixed: dict of params held constant (e.g. {'k':1.2,'s_lo':0.05})."""
    f = np.asarray(f, float); s = np.clip(np.asarray(s, float), 0.0, 1.0)
    names = ["s_lo", "s_hi", "fc", "k"]
    fixed = dict(fixed or {})
    lo = dict(s_lo=0.0, s_hi=0.0, fc=80.0, k=0.4)
    hi = dict(s_lo=0.3, s_hi=1.0, fc=20000.0, k=6.0)
    guess = dict(s_lo=float(min(s.min(), 0.29)), s_hi=float(max(s.max(), 0.01)),
                 fc=float(np.exp(np.mean(np.log(f)))), k=1.5)
    if x0: guess.update(x0)
    free = [n for n in names if n not in fixed]

    def unpack(x):
        d = dict(fixed); d.update({n: v for n, v in zip(free, x)}); return d

    def resid(x):
        d = unpack(x)
        pen = max(0.0, d["s_lo"] - d["s_hi"]) * 10.0  # keep monotone rising
        return np.append(s_logistic(f, **d) - s, pen)

    x0v = [min(max(guess[n], lo[n] + 1e-6), hi[n] - 1e-6) for n in free]
    best = None
    for fc0 in ([x0v[free.index("fc")]] if "fc" in free else [None]) + ([300.0, 1000.0, 3000.0, 8000.0] if "fc" in free else []):
        xs = list(x0v)
        if fc0 is not None: xs[free.index("fc")] = fc0
        r = least_squares(resid, xs, bounds=([lo[n] for n in free], [hi[n] for n in free]))
        if best is None or r.cost < best.cost: best = r
    d = unpack(best.x)
    rmse = float(np.sqrt(np.mean((s_logistic(f, **d) - s) ** 2)))
    return d, rmse


# ---------------------------------------------------------------- per-hit energy split
def specular_fraction(s_list_per_hit):
    """Energy fraction that stays specular after the serial hit list: prod(1 - s_h). Arrays over bands."""
    S = np.ones_like(np.asarray(s_list_per_hit[0], float)) if s_list_per_hit else None
    if S is None: return None
    for s in s_list_per_hit: S = S * (1.0 - np.clip(np.asarray(s, float), 0.0, 1.0))
    return S


# ---------------------------------------------------------------- Lambert cluster envelope (DERIVED)
def lambert_energy_cdf(x):
    """DERIVED: first-order Lambert reflection from an infinite plane, source & receiver at equal height h.
    Energy vs normalised arrival time x = t / t_spec (x>=1):  density ∝ x^-5,  CDF = 1 - x^-4.
    (Lambert cos·cos / r1²r2² integrated over annuli; see research memo §5.)"""
    x = np.maximum(np.asarray(x, float), 1.0)
    return 1.0 - x ** -4


def cluster_window_ms(t_spec_ms, x_max=10 ** 0.25, w_min_ms=1.0, w_max_ms=30.0):
    """Width of the cluster that holds ~90 % of Lambert energy (x_max=10^0.25 → 90 %). Grows with path length
    (and therefore with image order). Clamped for CPU. Returns ms."""
    return float(min(w_max_ms, max(w_min_ms, (x_max - 1.0) * t_spec_ms)))


def velvet_cluster(t_spec_ms, sr, n_pulses=16, seed=0, x_max=10 ** 0.25, w_max_ms=30.0):
    """Sparse velvet-style cluster: n_pulses ±1 pulses, one per equal-energy slot of the Lambert CDF on
    [t_spec, t_spec*x_max] (so pulse *density* follows the energy law and all pulses have equal |a|),
    jittered inside each slot, random sign. Unit total energy (sum a^2 = 1).
    Returns offsets (samples, relative to the specular arrival, >=1) and amplitudes."""
    rng = np.random.default_rng(seed)
    w_ms = cluster_window_ms(t_spec_ms, x_max=x_max, w_max_ms=w_max_ms)
    x_hi = 1.0 + w_ms / max(t_spec_ms, 1e-6)
    c_hi = lambert_energy_cdf(x_hi)
    edges = np.linspace(0.0, c_hi, n_pulses + 1)
    u = edges[:-1] + rng.random(n_pulses) * (edges[1:] - edges[:-1])
    x = (1.0 - u) ** -0.25                    # inverse CDF
    off = np.maximum(1, np.round((x - 1.0) * t_spec_ms * 1e-3 * sr)).astype(int)
    # merge collisions deterministically
    off = np.maximum.accumulate(off + np.arange(n_pulses) * 0)  # keep order
    for i in range(1, n_pulses):
        if off[i] <= off[i - 1]: off[i] = off[i - 1] + 1
    sign = np.where(rng.random(n_pulses) < 0.5, -1.0, 1.0)
    amp = sign / math.sqrt(n_pulses)
    return off, amp, w_ms


# ---------------------------------------------------------------- RBJ shelf used for spec / scatter filters
def rbj_high_shelf(sr, f0, gain_db, S=1.0):
    A = 10 ** (gain_db / 40.0); w0 = 2 * math.pi * f0 / sr
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / 2 * math.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    b0 = A * ((A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * alpha
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def biquad_mag(b, a, f, sr):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f, float) / sr)
    return np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))


F0_GRID = np.geomspace(150.0, 10000.0, 24)


def fit_gain_shelf(target_mag, bands, sr, floor=1e-3):
    """Fit  g_lo · HighShelf(f0, g_hi/g_lo)  to a 7-band magnitude target (control-rate, grid over f0,
    closed-form LS for g_lo/g_hi in dB). Returns (b, a, rms_err_db). Cheap enough to run per tap on param change."""
    t_db = 20 * np.log10(np.maximum(np.asarray(target_mag, float), floor))
    best = None
    for f0 in F0_GRID:
        for gd in np.linspace(-40, 40, 81):
            b, a = rbj_high_shelf(sr, f0, gd)
            m_db = 20 * np.log10(biquad_mag(b, a, bands, sr))
            off = float(np.mean(t_db - m_db))
            err = float(np.sqrt(np.mean((t_db - (m_db + off)) ** 2)))
            if best is None or err < best[0]: best = (err, f0, gd, off)
    err, f0, gd, off = best
    b, a = rbj_high_shelf(sr, f0, gd)
    return b * 10 ** (off / 20), a, err, dict(f0=float(f0), shelf_db=float(gd), trim_db=float(off))
