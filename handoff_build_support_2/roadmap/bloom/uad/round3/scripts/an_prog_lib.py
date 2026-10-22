# Program material: UAD vs our current preset models (scratch re-implementation of compressor_presets.json).
import numpy as np, json, csv, sys
import os; ROOT=os.environ.get('UADROOT','/workspace'); sys.path.insert(0, ROOT+'/uad2/scripts')
import io2, models as Mo, volterra as V
from scipy.signal import fftconvolve, welch
SR = 48000; B = 48                         # 1 ms blocks for GR traces
FIT = json.load(open(ROOT+'/uad2/an/static_fit.json'))
def g_ss(unit):
    x, y = io2.rec('c1k_' + unit); seg = y[:24000]
    return np.sqrt(2 * np.mean(seg ** 2)) / 10 ** (-45 / 20)
_H1 = {}
def h1(unit):
    if unit not in _H1:
        x, y = io2.rec('cess_%s_-30' % unit)
        k = V.fit_hammerstein([(x, y)], N=1, M=4096)[0]
        K = np.fft.rfft(np.roll(np.pad(k, (0, 8192 - len(k))), -V.PRE)); fr = np.fft.rfftfreq(8192, 1 / SR)
        sel = (fr > 300) & (fr < 3000) & ((fr < 800) | (fr > 1250))
        k = k * g_ss(unit) / np.median(np.abs(K[sel]))
        _H1[unit] = k
    return _H1[unit]
def lin(x, k): return fftconvolve(x, k)[V.PRE:V.PRE + len(x)]
def block_gain(ref, y, B=B, W=240):
    """LS gain over a W-sample window every B samples (W=5 ms keeps LF material from blowing up near zero crossings)."""
    c1 = np.concatenate([[0], np.cumsum(ref * y)]); c2 = np.concatenate([[0], np.cumsum(ref * ref)])
    centers = np.arange(B // 2, len(ref), B); a = np.clip(centers - W // 2, 0, len(ref)); b = np.clip(centers + W // 2, 0, len(ref))
    num = c1[b] - c1[a]; den = c2[b] - c2[a]
    c3 = np.concatenate([[0], np.cumsum(y * y)]); yy = c3[b] - c3[a]
    block_gain.rho = num / np.sqrt(np.maximum(den * yy, 1e-60))
    return num / np.maximum(den, 1e-30), 10 * np.log10(np.maximum(den / np.maximum(b - a, 1), 1e-30))
def env_db(y, w=480):
    n = len(y) // w * w; return 10 * np.log10(np.maximum(np.mean(y[:n].reshape(-1, w) ** 2, axis=1), 1e-20))
def third_oct(y):
    f, P = welch(y, SR, nperseg=8192); c = 1000 * 2.0 ** (np.arange(-15, 15) / 3)
    out = []
    for fc in c:
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6)); out.append(10 * np.log10(np.mean(P[m]) + 1e-30))
    return c, np.array(out)
from scipy.signal import butter, sosfiltfilt
_BP = butter(6, [20.0, 19000.0], 'bandpass', fs=SR, output='sos')
def null_db(y, yh):
    """Null depth inside 20 Hz-19 kHz (the ESS used for the UAD linear response stops at 20 kHz)."""
    y = sosfiltfilt(_BP, y); yh = sosfiltfilt(_BP, yh)
    c = np.dot(y, yh) / np.dot(yh, yh); return 10 * np.log10(np.sum((y - c * yh) ** 2) / np.sum(y ** 2)), c
def compare(preset, unit, pk, ab):
    id_ = 'prog_%s_%s_%s' % (unit, pk, ab); x, y = io2.rec(id_)
    T = FIT[preset]['T']; k = h1(unit)
    ym, grm = Mo.run_preset(preset, x, T)
    hx = lin(x, k)
    gu, ex = block_gain(hx, y); rho = block_gain.rho.copy(); gm, exm = block_gain(x, ym)
    act = (ex > max(-60.0, ex.max() - 40)) & (rho > 0.95) & (exm > max(-60.0, exm.max() - 40))    # windows where a pure gain explains UAD's output
    GRu = -20 * np.log10(np.maximum(np.abs(gu), 1e-6)); GRm = -20 * np.log10(np.maximum(np.abs(gm), 1e-6))
    d = (GRm - GRu)[act]
    nl_raw, c_raw = null_db(y, ym); ymh = lin(ym, k) / g_ss(unit)   # ours + UAD's linear frequency response
    nl_lin, c_lin = null_db(y, ymh)
    eu = env_db(y); em = env_db(c_lin * ymh); ea = eu > eu.max() - 40
    fu, su = third_oct(y); _, sm = third_oct(c_lin * ymh); _, sm0 = third_oct(c_raw * ym)
    band = (fu > 30) & (fu < 16500)
    tb = (np.arange(len(gu)) + 0.5) * B
    gi = np.interp(np.arange(len(x)), tb[act], gu[act]); yo = gi * hx
    nl_or, _ = null_db(y, yo)
    q = ex < ex.max() - 55
    off = float(np.median(GRu[q & (ex > -150)])) if (q & (ex > -150)).sum() > 20 else float('nan')
    r = dict(preset=preset, unit=unit, program=pk, level=('base' if ab == 'a' else '+8 dB'),
             uad_gr_mean_db=round(float(np.mean(GRu[act])), 2), uad_gr_p99_db=round(float(np.percentile(GRu[act], 99)), 2),
             ours_gr_mean_db=round(float(np.mean(GRm[act])), 2), frac_windows_used=round(float(act.sum() / max(1, (ex > max(-60.0, ex.max() - 40)).sum())), 3),
             gr_err_bias_db=round(float(np.mean(d)), 2), gr_err_rms_db=round(float(np.sqrt(np.mean(d ** 2))), 2),
             gr_err_p99_db=round(float(np.percentile(np.abs(d), 99)), 2), gr_err_max_db=round(float(np.max(np.abs(d))), 2),
             env_err_rms_db=round(float(np.sqrt(np.mean((em - eu)[ea] ** 2))), 2),
             spec_diff_rms_db=round(float(np.sqrt(np.mean((sm - su)[band] ** 2))), 2), spec_diff_max_db=round(float(np.max(np.abs(sm - su)[band])), 2),
             spec_diff_rms_noFR_db=round(float(np.sqrt(np.mean((sm0 - su)[band] ** 2))), 2),
             null_raw_db=round(float(nl_raw), 1), null_withUADfr_db=round(float(nl_lin), 1), null_oracle_gain_db=round(float(nl_or), 1))
    return r, dict(x=x, y=y, ym=c_lin * ymh, yo=yo, GRu=GRu, GRm=GRm, act=act, gu=gu, hx=hx)
