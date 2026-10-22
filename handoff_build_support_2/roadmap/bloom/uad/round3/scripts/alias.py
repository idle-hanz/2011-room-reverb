import numpy as np
from scipy.signal import windows, stft
SR = 48000
def tone_alias(y, f0, nh=40):
    """Two independent measures on a steady tone segment (last 0.5 s).
    M1: spectral peak picking at the exact folded positions of harmonics k*f0 > Nyquist (Blackman-Harris 4-term).
    M2: time-domain LS removal of DC + every true harmonic below Nyquist, then the strongest residual line and total residual.
    Returns dict in dBFS (sine-peak units) and dBc."""
    y = np.asarray(y, float)[-SR // 2:]; n = len(y); w = windows.blackmanharris(n); cg = w.sum() / 2
    Y = np.abs(np.fft.rfft(y * w)) / cg; fr = np.fft.rfftfreq(n, 1 / SR); df = fr[1]
    def pk(f, b=3):
        i = int(round(f / df)); return Y[max(0, i - b):i + b + 1].max()
    fund = pk(f0)
    true_bins = [k * f0 for k in range(1, nh) if k * f0 < SR / 2]
    al = []
    for k in range(2, nh):
        fk = k * f0
        if fk < SR / 2: continue
        fa = abs(((fk + SR / 2) % SR) - SR / 2)
        if min(abs(fa - t) for t in true_bins) < 30 or fa < 20: continue
        al.append((k, fa, pk(fa)))
    m1 = max(al, key=lambda z: z[2]) if al else (0, 0, 1e-15)
    # M2
    t = np.arange(n) / SR; cols = [np.ones(n)]
    for f in true_bins: cols += [np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t)]
    A = np.stack(cols, 1); c, *_ = np.linalg.lstsq(A, y, rcond=None); r = y - A @ c
    R = np.abs(np.fft.rfft(r * w)) / cg; band = (fr > 20) & (fr < 23900)
    i2 = np.argmax(R * band); 
    for f_ in true_bins: band &= np.abs(fr - f_) > 60
    b16 = band & (fr < 16000); i3 = np.argmax(R * b16); tot = np.sqrt(np.sum((np.abs(np.fft.rfft(r * w)) ** 2)[band]) / np.sum(w ** 2) * 2 / n) if False else np.sqrt(np.mean(r ** 2)) * np.sqrt(2)
    db = lambda v: 20 * np.log10(max(v, 1e-15))
    return dict(fund_dbfs=db(fund), m1_worst_alias_dbfs=db(m1[2]), m1_worst_k=m1[0], m1_worst_f=round(m1[1]), m1_dbc=db(m1[2]) - db(fund),
                m2_peak_resid_dbfs=db(R[i2]), m2_peak_f=round(fr[i2]), m2_dbc=db(R[i2]) - db(fund), m2_resid_total_dbc=db(tot) - db(fund), m2_peak_below16k_dbfs=db(R[i3]), m2_peak_below16k_f=round(fr[i3]))
def sweep_alias(y, f1=2000., f2=20000., T=4.0, nh=12):
    """Sweep method: STFT, mask +-2 bins around every true harmonic track k*f(t) below Nyquist; report the worst
    non-harmonic bin per frame (dBFS) relative to the fundamental, and its max over the sweep above f=5 kHz."""
    y = np.asarray(y, float)[:int(T * SR)]; L = T / np.log(f2 / f1)
    f, tt, Z = stft(y, SR, window='blackmanharris', nperseg=4096, noverlap=3072, boundary=None)
    A = np.abs(Z) * 2 / windows.blackmanharris(4096).sum() * 4096 / 4096
    out = []
    for j, tc in enumerate(tt):
        fi = f1 * np.exp(tc / L)
        if fi > f2 * 0.98 or tc < 0.05: continue
        m = (f > 20) & (f < 20500)
        for k in range(1, nh):
            if k * fi < SR / 2: m &= np.abs(f - k * fi) > 4 * fi / L * 4096 / SR / 2 + 60
        fund = A[np.argmin(np.abs(f - fi)), j]
        out.append((fi, 20 * np.log10(A[m, j].max() + 1e-15), 20 * np.log10(fund + 1e-15)))
    return np.array(out)
