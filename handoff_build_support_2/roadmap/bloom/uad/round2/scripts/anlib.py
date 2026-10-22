import json, os, numpy as np
SR = 48000
OUT = "/workspace/uad2/out"
def load(id_, d=OUT):
    m = json.load(open(os.path.join(d, id_ + ".json"))); y = np.load(os.path.join(d, id_ + ".npz"))["y"].astype(np.float64)
    return m, y
def db(x): return 20 * np.log10(np.maximum(np.abs(x), 1e-30))

def seg_spec(seg):
    n = len(seg); w = np.hanning(n); sp = np.fft.rfft(seg * w) * 2 / np.sum(w)
    return sp, np.fft.rfftfreq(n, 1 / SR)

def amp_at(sp, fr, f, df=None):
    b = f * len(fr) * 2 / SR if False else f / (fr[1] - fr[0]); i = int(round(b))
    lo, hi = max(i - 2, 0), min(i + 3, len(sp))
    return float(np.max(np.abs(sp[lo:hi])))

def harm(seg, f0, nh=10):
    sp, fr = seg_spec(seg)
    hs = [h for h in range(1, nh + 1) if f0 * h < 23500]
    a = np.array([amp_at(sp, fr, f0 * h) for h in hs])
    fund = a[0]
    # noise+distortion residual: everything outside +-6 bins of the fundamental, 15 Hz .. 22 kHz
    df = fr[1] - fr[0]; mask = (fr > 15) & (fr < 22000); b0 = int(round(f0 / df)); mask[max(b0 - 6, 0):b0 + 7] = False
    resid = np.sqrt(np.sum(np.abs(sp[mask]) ** 2) / 1.5)
    return {"fund": fund, "h_dbc": list(db(a[1:] / fund)), "thd_pct": float(100 * np.sqrt(np.sum(a[1:] ** 2)) / fund),
            "thdn_pct": float(100 * resid / fund), "hs": hs[1:],
            "h_abs_db": list(db(a[1:]))}

def stair_segments(y, keep):
    out = []; p = 0
    for a, b in keep:
        n = b - a; out.append(y[..., p:p + n]); p += n
    return out

def imd_smpte(seg):
    sp, fr = seg_spec(seg)
    a60 = amp_at(sp, fr, 60.0); a7 = amp_at(sp, fr, 7000.0)
    sb = [amp_at(sp, fr, 7000.0 + s * k * 60.0) for k in (1, 2, 3, 4) for s in (-1, 1)]
    return {"a60": a60, "a7k": a7, "imd_pct": float(100 * np.sqrt(np.sum(np.square(sb))) / a7),
            "sb1_dbc": float(db((sb[0] + sb[1]) / 2 / a7)), "sb2_dbc": float(db((sb[2] + sb[3]) / 2 / a7))}

def imd_ccif(seg):
    sp, fr = seg_spec(seg)
    a19 = amp_at(sp, fr, 19000.0); a20 = amp_at(sp, fr, 20000.0)
    d2 = amp_at(sp, fr, 1000.0); d3a = amp_at(sp, fr, 18000.0); d3b = amp_at(sp, fr, 21000.0)
    ref = (a19 + a20) / 2
    return {"a19": a19, "a20": a20, "d2_dbc": float(db(d2 / ref)), "d3_dbc": float(db(np.sqrt(d3a ** 2 + d3b ** 2) / ref)),
            "imd_pct": float(100 * np.sqrt(d2 ** 2 + d3a ** 2 + d3b ** 2) / ref)}

def inv_ess(T, f1=20.0, f2=20000.0, fade_s=0.02):
    import siglib as S
    x, L = S.ess(T, f1, f2, fade_s)
    t = np.arange(len(x)) / SR
    inv = x[::-1] * np.exp(-t / L)        # Farina inverse: time reverse + 6 dB/oct amplitude correction
    # normalise so that x * inv = delta (scale at mid band)
    X = np.fft.rfft(x, 2 * len(x)); IV = np.fft.rfft(inv, 2 * len(x)); fr = np.fft.rfftfreq(2 * len(x), 1 / SR)
    sel = (fr > 200) & (fr < 10000)
    k = 1.0 / np.median(np.abs(X[sel] * IV[sel]))
    return x, inv * k, L

def deconv(y, inv):
    n = len(y) + len(inv); nf = 1 << int(np.ceil(np.log2(n)))
    return np.fft.irfft(np.fft.rfft(y, nf) * np.fft.rfft(inv, nf), nf)[:n]
