import numpy as np
SR = 48000
def hfit(seg, f0, nh=5):
    """Least-squares sinusoid fit at exact harmonics. Returns amp[k], phase[k] (sin reference), k=1..nh."""
    n = len(seg); t = np.arange(n) / SR; w = np.hanning(n)
    cols = []
    for k in range(1, nh + 1):
        cols += [np.sin(2 * np.pi * k * f0 * t), np.cos(2 * np.pi * k * f0 * t)]
    cols.append(np.ones(n)); A = np.stack(cols, 1)
    c, *_ = np.linalg.lstsq(A * w[:, None], seg * w, rcond=None)
    s, co = c[0:2 * nh:2], c[1:2 * nh:2]
    return np.hypot(s, co), np.arctan2(co, s)
def rel_phase(seg, f0, nh=5):
    a, ph = hfit(seg, f0, nh)
    th = np.array([(ph[k - 1] - k * ph[0] + np.pi) % (2 * np.pi) - np.pi for k in range(1, nh + 1)])
    return 20 * np.log10(np.maximum(a / a[0], 1e-12)), np.degrees(th)
