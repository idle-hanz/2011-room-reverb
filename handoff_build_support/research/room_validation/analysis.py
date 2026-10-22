"""Room-acoustic analysis helpers (ISO 3382-1 style), numpy/scipy only.
Band filters: Butterworth 6th-order band-pass (3rd-order prototype), forward filtering.
EDC: Schroeder backward integration with a simplified Lundeby truncation + noise compensation.
Onset: first sample within -20 dB of the absolute peak (ISO 3382-1 A.3.3)."""
import numpy as np
from scipy import signal

OCT = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)
THIRD = np.array([100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
                  2500, 3150, 4000, 5000, 6300, 8000, 10000], float)


def bandpass(x, fc, sr, frac=1):
    k = 2 ** (1 / (2 * frac))
    lo, hi = fc / k, min(fc * k, 0.45 * sr)
    sos = signal.butter(3, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfilt(sos, x)


def onset(x, thr_db=-20.0):
    a = np.abs(x)
    return int(np.argmax(a >= a.max() * 10 ** (thr_db / 20)))


def lundeby_trunc(h2, sr, win_ms=10.0):
    """Return (truncation index, noise power per sample). Simplified Lundeby (1995)."""
    n = len(h2)
    w = max(1, int(sr * win_ms / 1000))
    nb = n // w
    env = h2[: nb * w].reshape(nb, w).mean(1) + 1e-300
    noise = h2[int(0.9 * n):].mean() + 1e-300
    edb = 10 * np.log10(env)
    ndb = 10 * np.log10(noise)
    t = np.arange(nb) * w
    cross = n
    for _ in range(5):
        # regression from peak to noise+10 dB
        i0 = int(np.argmax(edb))
        above = np.where(edb[i0:] > ndb + 10)[0]
        if len(above) < 3:
            break
        i1 = i0 + above[-1]
        if i1 - i0 < 2:
            break
        p = np.polyfit(t[i0:i1 + 1], edb[i0:i1 + 1], 1)
        if p[0] >= 0:
            break
        cross = int(np.clip((ndb - p[1]) / p[0], 0, n))
        tail0 = int(min(n - 1, cross + sr * 0.05))
        if n - tail0 > 0.1 * n:
            noise = h2[tail0:].mean() + 1e-300
        else:
            noise = h2[int(0.9 * n):].mean() + 1e-300
        ndb = 10 * np.log10(noise)
    return int(min(cross, n)), float(noise)


def edc_db(x, sr, noise_comp=True):
    h2 = x.astype(np.float64) ** 2
    if noise_comp:
        cross, noise = lundeby_trunc(h2, sr)
        h2 = h2[:cross] - noise
        h2 = np.maximum(h2, 0)
    e = np.cumsum(h2[::-1])[::-1]
    e = e / (e[0] + 1e-300)
    return 10 * np.log10(e + 1e-300)


def decay_time(edc, sr, hi, lo):
    t = np.arange(len(edc)) / sr
    i = np.where((edc <= hi) & (edc >= lo))[0]
    if len(i) < 10 or edc.min() > lo:
        return np.nan
    p = np.polyfit(t[i], edc[i], 1)
    return -60.0 / p[0]


def params_band(x, sr, fc, frac=1, noise_comp=True):
    i0 = onset(x)
    y = bandpass(x, fc, sr, frac)[max(0, i0 - int(0.001 * sr)):]
    # restart at the broadband onset (1 ms pre-roll keeps the band-filter ramp)
    edc = edc_db(y, sr, noise_comp)
    e = y ** 2
    n50, n80 = int(0.050 * sr) + int(0.001 * sr), int(0.080 * sr) + int(0.001 * sr)
    tot = e.sum()
    return dict(EDT=decay_time(edc, sr, 0.0, -10.0), T20=decay_time(edc, sr, -5.0, -25.0),
                T30=decay_time(edc, sr, -5.0, -35.0),
                C50=10 * np.log10(e[:n50].sum() / max(e[n50:].sum(), 1e-300)),
                C80=10 * np.log10(e[:n80].sum() / max(e[n80:].sum(), 1e-300)),
                D50=e[:n50].sum() / tot, E=tot)


def all_params(x, sr, bands=OCT, frac=1, noise_comp=True):
    return {int(f): params_band(x, sr, f, frac, noise_comp) for f in bands}
