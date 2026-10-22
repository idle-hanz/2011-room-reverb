"""Room-acoustic metrics for compare_ref.py (numpy + scipy only).

All functions take mono float64 arrays at sample rate sr whose t=0 is the impulse instant.
Band filtering: zero-phase FFT octave filter with raised-cosine skirts (same as
engine/tests/lib/analyze.py band()) so numbers line up with the engine test pack.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares

OCT = [125, 250, 500, 1000, 2000, 4000, 8000, 11000]
BAL_BANDS = [125, 250, 500, 1000, 2000, 4000, 8000, 16000]


def band(x, sr, fc, width_oct=1.0):
    x = np.asarray(x, dtype=np.float64)
    n = 1 << int(np.ceil(np.log2(max(len(x), 2))))
    X = np.fft.rfft(x, n)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    lo, hi = fc / 2 ** (width_oct / 2), fc * 2 ** (width_oct / 2)
    sk = 2 ** (1 / 12)
    lf = np.log2(np.maximum(f, 1e-9))
    def ramp(a, b):
        t = np.clip((lf - np.log2(a)) / (np.log2(b) - np.log2(a)), 0, 1)
        return 0.5 - 0.5 * np.cos(np.pi * t)
    w = ramp(lo / sk, lo * sk)
    if hi * sk < 0.5 * sr:
        w = w * (1 - ramp(hi / sk, hi * sk))
    return np.fft.irfft(X * w, n)[: len(x)]


def bandpass_hz(x, sr, f_lo, f_hi):
    n = 1 << int(np.ceil(np.log2(max(len(x), 2))))
    X = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1.0 / sr)
    return np.fft.irfft(X * ((f >= f_lo) & (f < f_hi)), n)[: len(x)]


def noise_floor_db(x, frac=0.05):
    """Mean energy (dB re peak energy) of the last `frac` of the IR. -inf-ish for clean float IRs."""
    e = x ** 2
    k = max(16, int(len(e) * frac))
    tail = float(np.mean(e[-k:])); pk = float(np.max(e)) + 1e-300
    return 10 * np.log10(max(tail, 1e-300) / pk)


def schroeder(x, trunc_noise=True):
    """Backward-integrated EDC in dB (0 dB at t=0). If a flat noise floor is detected
    (> -120 dB re peak), subtract its expected contribution (Chu method) before integrating."""
    e = np.asarray(x, dtype=np.float64) ** 2
    if trunc_noise:
        k = max(16, int(len(e) * 0.05))
        nf = float(np.mean(e[-k:]))
        if nf > 1e-12 * float(np.max(e)):
            e = np.maximum(e - nf, 0.0)
    c = np.cumsum(e[::-1])[::-1]
    c = c / max(c[0], 1e-300)
    return 10 * np.log10(np.maximum(c, 1e-300))


def t_from_edc(edc, sr, hi, lo):
    i0 = int(np.argmax(edc <= hi)); i1 = int(np.argmax(edc <= lo))
    if edc[-1] > lo or i1 <= i0 + 10:
        return float('nan')
    t = np.arange(i0, i1) / sr
    k, _ = np.polyfit(t, edc[i0:i1], 1)
    return -60.0 / k if k < 0 else float('inf')


def two_slope_fit(edc, sr, floor_db=-65.0):
    """Fit EDC(t) = 10log10(A1·10^(-6t/T1) + A2·10^(-6t/T2)) (Xiang-style multi-slope model,
    two terms, no noise term: the EDC here is already noise-compensated) over 0 dB .. floor.
    Returns dict: T1 (early), T2 (late), knee_db (EDC level where the terms are equal),
    rms1 (single-slope residual dB), rms2 (two-slope residual dB), two_stage (bool)."""
    lo = max(floor_db, float(edc[-1]) + 3.0)
    i1 = int(np.argmax(edc <= lo)) if np.any(edc <= lo) else len(edc) - 1
    i0 = int(np.argmax(edc <= -1.0))
    if i1 - i0 < 50:
        return dict(T1=np.nan, T2=np.nan, knee_db=np.nan, rms1=np.nan, rms2=np.nan, two_stage=False, fit_to_db=lo)
    step = max(1, (i1 - i0) // 2000)
    idx = np.arange(i0, i1, step)
    t = idx / sr; y = edc[idx]
    # single slope
    k1, b1 = np.polyfit(t, y, 1)
    rms1 = float(np.sqrt(np.mean((y - (k1 * t + b1)) ** 2)))
    Tsingle = -60.0 / k1 if k1 < 0 else np.inf
    def model(p, tt):
        a1, a2, T1, T2 = p
        return 10 * np.log10(10 ** a1 * 10 ** (-6 * tt / T1) + 10 ** a2 * 10 ** (-6 * tt / T2) + 1e-300)
    # initial guesses: early slope from 0..-15, late from last third
    Te = t_from_edc(edc, sr, -1, -15) if np.any(edc <= -15) else Tsingle
    j = len(idx) * 2 // 3
    kl, bl = np.polyfit(t[j:], y[j:], 1) if len(idx) - j > 5 else (k1, b1)
    Tl = -60.0 / kl if kl < 0 else 10 * Tsingle
    Te = float(np.clip(Te if np.isfinite(Te) else Tsingle, 0.02, 60)); Tl = float(np.clip(Tl, 0.03, 120))
    if Tl <= Te * 1.05:
        Tl = Te * 1.5
    p0 = [0.0, float(np.clip(bl / 10, -8, 0)), Te, Tl]
    try:
        r = least_squares(lambda p: model(p, t) - y, p0,
                          bounds=([-3, -12, 0.01, 0.01], [1, 1, 200, 400]))
        a1, a2, T1, T2 = r.x
        if T1 > T2:
            a1, a2, T1, T2 = a2, a1, T2, T1
        rms2 = float(np.sqrt(np.mean(r.fun ** 2)))
    except Exception:
        return dict(T1=Tsingle, T2=Tsingle, knee_db=np.nan, rms1=rms1, rms2=rms1, two_stage=False, fit_to_db=lo)
    # knee: time where the two components are equal
    knee_db = np.nan
    if T2 > T1 * 1.01:
        # a1 - 6t/T1 = a2 - 6t/T2  (in log10 units ×10 → dB)
        tk = (10 * (a1 - a2)) / (60 / T1 - 60 / T2)
        if 0 < tk < t[-1] * 1.5:
            knee_db = float(model([a1, a2, T1, T2], np.array([tk]))[0])
    two = bool(np.isfinite(knee_db) and T2 / T1 >= 1.5 and rms2 < 0.6 * rms1 and knee_db > lo + 3 and rms1 > 0.5)
    return dict(T1=float(T1), T2=float(T2), knee_db=knee_db, rms1=rms1, rms2=rms2, two_stage=two,
                T_single=float(Tsingle), fit_to_db=float(lo))


def envelope_late_t60(x, sr, t_start, t_len, hop_s=0.05):
    hop = int(hop_s * sr)
    seg = x[int(t_start * sr): int((t_start + t_len) * sr)]
    n = len(seg) // hop
    if n < 4:
        return float('nan')
    e = 10 * np.log10(np.maximum(np.mean(seg[: n * hop].reshape(n, hop) ** 2, axis=1), 1e-300))
    k, _ = np.polyfit(np.arange(n) * hop / sr, e, 1)
    return -60.0 / k if k < 0 else float('inf')


def first_arrival(x, sr, skip_s=0.0003, search_s=0.15):
    """Direct-sound index = largest |x| in [skip_s, search_s]. The first 0.3 ms is skipped because a
    Schroeder allpass line (Dffs != 0) emits its feed-forward term -Dffs*x at t = 0 (rebuild AND,
    by structure, the 2011 Diffuser Delay), which is not the direct sound."""
    a0 = int(skip_s * sr)
    a = np.abs(x[a0: int(search_s * sr)])
    if a.size == 0 or a.max() <= 0:
        return a0
    return a0 + int(np.argmax(a))


def direct_energy(x, sr, i0):
    a = max(0, i0 - int(0.0005 * sr)); b = i0 + int(0.002 * sr)
    return float(np.sum(x[a:b] ** 2))


def band_energy_db(x, sr, fc):
    return 10 * np.log10(max(float(np.sum(band(x, sr, fc) ** 2)), 1e-300))


def spectral_balance(x, sr, t0, t1=None):
    """Octave energies (dB) re the 1 kHz octave, in window [t0, t1)."""
    seg = x[int(t0 * sr): (int(t1 * sr) if t1 else None)]
    if len(seg) < 64:
        return {}
    ref = band_energy_db(seg, sr, 1000)
    return {fc: band_energy_db(seg, sr, fc) - ref for fc in BAL_BANDS if fc * 2 ** 0.5 < 0.5 * sr * 1.02}


def hf_residue(x, sr, t_after):
    """Late HF residue metrics, measured after time t_after (s):
    - late T60 (envelope slope, 1.5 s window) at 1k, 9k, 11k
    - nyq_db: energy 0.85·Nyq..0.99·Nyq re 1–4 kHz energy (dB), late window
    - nyq_t60: late T60 of that near-Nyquist band."""
    nyq = sr / 2
    seg = x[int(t_after * sr):]
    out = {}
    for fc in (1000, 9000, 11000):
        out[f'late_t60_{fc}'] = envelope_late_t60(band(x, sr, fc), sr, t_after, 1.5)
    if len(seg) > 1024:
        hi = bandpass_hz(seg, sr, 0.85 * nyq, 0.99 * nyq)
        mid = bandpass_hz(seg, sr, 1000, 4000)
        out['nyq_db'] = 10 * np.log10(max(np.sum(hi ** 2), 1e-300) / max(np.sum(mid ** 2), 1e-300))
        out['nyq_t60'] = envelope_late_t60(bandpass_hz(x, sr, 0.85 * nyq, 0.99 * nyq), sr, t_after, 1.5)
    else:
        out['nyq_db'] = float('nan'); out['nyq_t60'] = float('nan')
    return out


def stereo_corr(L, R, sr, t0, t1):
    a = L[int(t0 * sr): int(t1 * sr)]; b = R[int(t0 * sr): int(t1 * sr)]
    if len(a) < 256:
        return dict(corr0=np.nan, iacc=np.nan)
    den = np.sqrt(np.sum(a ** 2) * np.sum(b ** 2)) + 1e-300
    c0 = float(np.sum(a * b) / den)
    m = int(0.001 * sr)
    n = 1 << int(np.ceil(np.log2(2 * len(a))))
    xc = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    lags = np.concatenate([xc[: m + 1], xc[-m:]])
    return dict(corr0=c0, iacc=float(np.max(np.abs(lags)) / den))


def analyse(L, R, sr, label=''):
    """Full metric dict for one stereo IR (t=0 = impulse)."""
    M = 0.5 * (L + R)
    res = {'label': label, 'n': int(len(L)), 'secs': len(L) / sr}
    i0 = first_arrival(M, sr)
    res['first_arrival_ms'] = 1000 * i0 / sr
    ed = direct_energy(M, sr, i0)
    res['zero_time_db_re_direct'] = 10 * np.log10(max(float(np.sum(M[: int(0.0003 * sr)] ** 2)), 1e-300) / max(ed, 1e-300))
    tail_e = float(np.sum(M[i0 + int(0.08 * sr):] ** 2))
    res['tail_vs_direct_db'] = 10 * np.log10(max(tail_e, 1e-300) / max(ed, 1e-300))
    e = M ** 2; c80 = int(i0 + 0.08 * sr)
    res['C80_db'] = 10 * np.log10(max(float(np.sum(e[:c80])), 1e-300) / max(float(np.sum(e[c80:])), 1e-300))
    res['noise_floor_db'] = noise_floor_db(M)
    bands = {}
    for fc in OCT + ['bb']:
        if fc != 'bb' and fc * 2 ** -0.5 >= 0.45 * sr:
            continue
        y = M if fc == 'bb' else band(M, sr, fc)
        edc = schroeder(y)
        d = dict(T20=t_from_edc(edc, sr, -5, -25), T30=t_from_edc(edc, sr, -5, -35),
                 EDT=t_from_edc(edc, sr, 0, -10), T_late_edc=t_from_edc(edc, sr, -35, -55))
        d.update(two_slope_fit(edc, sr))
        bands[str(fc)] = d
    res['bands'] = bands
    edc_bb = schroeder(M)
    t30db = int(np.argmax(edc_bb <= -30)) / sr if np.any(edc_bb <= -30) else 0.5 * len(M) / sr
    t20db = int(np.argmax(edc_bb <= -20)) / sr if np.any(edc_bb <= -20) else 0.3 * len(M) / sr
    t40db = int(np.argmax(edc_bb <= -40)) / sr if np.any(edc_bb <= -40) else len(M) / sr
    res['t_edc_-20_s'] = t20db; res['t_edc_-30_s'] = t30db
    res['balance_early'] = spectral_balance(M, sr, i0 / sr, i0 / sr + 0.08)
    res['balance_tail'] = spectral_balance(M, sr, i0 / sr + 0.08)
    res['hf'] = hf_residue(M, sr, t20db)
    res['stereo'] = stereo_corr(L, R, sr, i0 / sr + 0.08, max(t40db, i0 / sr + 0.3))
    res['stereo_bands'] = {str(fc): stereo_corr(band(L, sr, fc), band(R, sr, fc), sr, i0 / sr + 0.08,
                                                 max(t40db, i0 / sr + 0.3))['corr0'] for fc in (250, 1000, 4000)}
    return res


def edc_curves(L, R, sr, bands=(None, 250, 1000, 4000, 8000), decim=240):
    M = 0.5 * (L + R)
    out = {}
    for fc in bands:
        y = M if fc is None else band(M, sr, fc)
        edc = schroeder(y)
        out['bb' if fc is None else str(fc)] = (np.arange(0, len(edc), decim) / sr, edc[::decim])
    return out


def fine_timing(ref, var, sr, i_dir, w1_ms=30.0, w2=(0.040, 0.150), maxlag=3):
    """Sample-level timing test for the loop-timing question (b).
    W1 = [direct, direct + w1_ms]: first-pass images (no loop trip yet). If the geometry/delays match,
    the normalised cross-correlation c1 at lag1 ~ 0 is high.  W2 = 40..150 ms: dominated by 1..4 loop
    trips.  A z^-1 loop delays every trip by one sample, so against a same-sample variant the
    reference correlates best at lag +1..+k, and against a matching variant at lag 0.
    Returns c1, lag1, c2_0 (at lag1), lag2 (best), c2_best."""
    def nxc(a, b, lags):
        out = []
        for L in lags:
            if L >= 0:
                aa, bb = a[L:], b[: len(b) - L]
            else:
                aa, bb = a[: len(a) + L], b[-L:]
            den = np.sqrt(np.sum(aa ** 2) * np.sum(bb ** 2)) + 1e-300
            out.append(float(np.sum(aa * bb) / den))
        return np.array(out)
    lags = np.arange(-maxlag, maxlag + 1)
    a0, a1 = i_dir + int(0.001 * sr), i_dir + int(w1_ms * 1e-3 * sr)   # skip the direct spike itself
    n = min(len(ref), len(var))
    if a1 >= n:
        return dict(c1=np.nan, lag1=0, c2_0=np.nan, lag2=0, c2_best=np.nan)
    c1s = nxc(ref[a0:a1], var[a0:a1], lags); k1 = int(np.argmax(c1s))
    b0, b1 = int(w2[0] * sr), min(n, int(w2[1] * sr))
    c2s = nxc(ref[b0:b1], var[b0:b1], lags); k2 = int(np.argmax(c2s))
    c2_0 = float(c2s[list(lags).index(lags[k1])])
    return dict(c1=float(c1s[k1]), lag1=int(lags[k1]), c2_0=c2_0, lag2=int(lags[k2]), c2_best=float(c2s[k2]),
                null2_db=float(10 * np.log10(max(1 - c2_0 ** 2, 1e-12))))
