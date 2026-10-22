# Generalised Hammerstein (diagonal Volterra / Farina-Novak) identification by multi-record frequency-domain LS,
# and a short-memory full Volterra (orders 1..3) time-domain LS fit.
import numpy as np
from scipy.signal import resample_poly, fftconvolve
SR = 48000; PRE = 64
def powers(x, N, os_=4):
    """x^n, n=1..N, computed at os_ x rate and band-limited back (as an oversampled plug-in would)."""
    out = [np.asarray(x, float)]
    if N > 1:
        xu = resample_poly(x, os_, 1)
        for n in range(2, N + 1):
            out.append(resample_poly(xu ** n, 1, os_)[:len(x)])
    return out
def fit_hammerstein(records, N=5, M=2048, reg=1e-8, os_=4):
    L = max(len(x) for x, y in records); nfft = 1 << int(np.ceil(np.log2(L + M)))
    nb = nfft // 2 + 1
    AtA = np.zeros((nb, N, N), complex); Aty = np.zeros((nb, N), complex)
    for x, y in records:
        X = np.stack([np.fft.rfft(p, nfft) for p in powers(x, N, os_)], axis=1)
        Y = np.fft.rfft(y, nfft)
        AtA += X.conj()[:, :, None] * X[:, None, :]; Aty += X.conj() * Y[:, None]
    d = np.einsum('bii->bi', AtA).real
    lam = reg * d.mean(axis=0)[None, :] + 1e-30            # per-order ridge
    for i in range(N): AtA[:, i, i] += lam[0, i]
    H = np.linalg.solve(AtA, Aty[..., None])[..., 0].T
    h = np.fft.irfft(H, nfft, axis=1)
    k = np.concatenate([h[:, -PRE:], h[:, :M]], axis=1)    # compact: PRE acausal taps + M causal
    w = np.ones(PRE + M); w[:PRE // 2] = np.hanning(PRE)[:PRE // 2]; w[-M // 8:] = np.hanning(M // 4)[M // 8:]
    return k * w[None]
def apply_hammerstein(x, k, os_=4):
    P = powers(x, k.shape[0], os_); y = np.zeros(len(x))
    for n in range(k.shape[0]):
        y += fftconvolve(P[n], k[n])[PRE:PRE + len(x)]
    return y
def nmse_db(y, yhat, sl=slice(None)):
    return float(10 * np.log10(np.sum((y[sl] - yhat[sl]) ** 2) / np.sum(y[sl] ** 2)))
def _lags(x, m):
    n = len(x); return [np.concatenate([np.zeros(k), x[:n - k]]) for k in range(m)]
def volterra_features(x, M2=10, M3=5):
    X = _lags(x, max(M2, M3)); cols = []
    for i in range(M2):
        for j in range(i, M2): cols.append(X[i] * X[j])
    for i in range(M3):
        for j in range(i, M3):
            for l in range(j, M3): cols.append(X[i] * X[j] * X[l])
    return np.stack(cols, axis=1)
def fit_volterra_resid(records, base, M2=10, M3=5, reg=1e-6, step=3):
    """Full 2nd+3rd-order short-memory Volterra fitted to the residual left by base(x)."""
    A = []; b = []
    for x, y in records:
        r = y - base(x)
        F = volterra_features(x, M2, M3)
        A.append(F[::step]); b.append(r[::step])
    A = np.concatenate(A); b = np.concatenate(b)
    G = A.T @ A; G += reg * np.trace(G) / len(G) * np.eye(len(G))
    return np.linalg.solve(G, A.T @ b)
def apply_volterra_resid(x, base, c, M2=10, M3=5):
    return base(x) + volterra_features(x, M2, M3) @ c
