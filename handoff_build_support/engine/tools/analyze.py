"""Shared acoustic metrics for the harnesses/tests (numpy+scipy)."""
import numpy as np
from scipy.signal import butter, sosfiltfilt, sosfilt

BANDS = [125, 250, 500, 1000, 2000, 4000, 8000, 11000]

def load_f32_stereo(path):
    x = np.fromfile(path, dtype=np.float32).reshape(-1, 2)
    return x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)

def band(x, sr, fc):
    lo, hi = fc / 2 ** 0.5, min(fc * 2 ** 0.5, 0.45 * sr)
    sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    return sosfiltfilt(sos, x)

def schroeder_db(x):
    e = np.cumsum((x ** 2)[::-1])[::-1]
    e = e / max(e[0], 1e-300)
    return 10 * np.log10(np.maximum(e, 1e-300))

def t60_from_edc(edc, sr, hi=-5.0, lo=-35.0):
    """Line fit of the EDC between hi and lo dB, extrapolated to -60 (T30 when -5..-35)."""
    i0 = np.argmax(edc <= hi); i1 = np.argmax(edc <= lo)
    if i1 <= i0 + 10 or edc[-1] > lo:
        return float('nan')
    t = np.arange(i0, i1) / sr
    k, _ = np.polyfit(t, edc[i0:i1], 1)
    return -60.0 / k if k < 0 else float('inf')

def t60_bands(x, sr, bands=BANDS, hi=-5.0, lo=-35.0):
    out = {}
    for fc in bands:
        if fc * 2 ** -0.5 >= 0.45 * sr:
            continue
        out[fc] = t60_from_edc(schroeder_db(band(x, sr, fc)), sr, hi, lo)
    out['broadband'] = t60_from_edc(schroeder_db(x), sr, hi, lo)
    return out

def late_t60(x, sr, fc, t_start, t_len):
    """Slope of the band energy envelope (dB/s) between t_start..t_start+t_len -> T60 (s)."""
    y = band(x, sr, fc) if fc else x
    hop = int(0.05 * sr)
    seg = y[int(t_start * sr): int((t_start + t_len) * sr)]
    n = len(seg) // hop
    if n < 4:
        return float('nan')
    e = 10 * np.log10(np.maximum(np.mean(seg[: n * hop].reshape(n, hop) ** 2, axis=1), 1e-300))
    k, _ = np.polyfit(np.arange(n) * hop / sr, e, 1)
    return -60.0 / k if k < 0 else float('inf')

def peak_freqs(x, sr, n=5, fmin=200):
    w = np.hanning(len(x))
    S = np.abs(np.fft.rfft(x * w)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / sr)
    S[f < fmin] = 0
    # smooth to 20 Hz and pick peaks
    k = max(1, int(20 / (f[1] - f[0])))
    Ss = np.convolve(S, np.ones(k) / k, mode='same')
    idx = []
    order = np.argsort(-Ss)
    for i in order:
        if all(abs(f[i] - f[j]) > 300 for j in idx):
            idx.append(i)
        if len(idx) >= n:
            break
    tot = Ss.sum()
    return [(round(float(f[i])), round(float(10 * np.log10(Ss[i] / (tot / len(Ss)))), 1)) for i in idx]

def rms_db(x):
    return 10 * np.log10(max(float(np.mean(np.asarray(x) ** 2)), 1e-300))
