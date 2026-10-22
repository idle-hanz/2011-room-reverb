"""ITD: measured (LF cross-correlation and onset), free-field geometry, Woodworth model.

Sign: ITD = t_R - t_L (seconds). Positive = left ear leads (source on the left).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, resample_poly, sosfiltfilt

from .grid import lateral_angle

UPS = 8


def measured_itd(ir: np.ndarray, fs: int, method: str = "xcorr", lp_hz: float = 1500.0, max_ms: float = 1.0):
    """ir: (M, 2, N). Returns (M,) ITD seconds."""
    up = resample_poly(ir, UPS, 1, axis=-1)
    fu = fs * UPS
    if method == "xcorr":
        sos = butter(4, lp_hz, fs=fu, output="sos")
        x = sosfiltfilt(sos, up, axis=-1)
        L, R = x[:, 0, :], x[:, 1, :]
        n = L.shape[-1]
        nf = 1 << int(np.ceil(np.log2(2 * n)))
        C = np.fft.irfft(np.fft.rfft(R, nf) * np.conj(np.fft.rfft(L, nf)), nf)  # lag>0: R later
        maxlag = int(max_ms * 1e-3 * fu)
        lags = np.concatenate([np.arange(0, maxlag + 1), np.arange(-maxlag, 0)])
        Cw = np.concatenate([C[:, :maxlag + 1], C[:, -maxlag:]], axis=1)
        k = np.argmax(Cw, axis=1)
        return lags[k] / fu
    # onset: first sample above -20 dB re each ear's peak
    a = np.abs(up)
    thr = a.max(axis=-1, keepdims=True) * 10 ** (-20 / 20)
    on = np.argmax(a >= thr, axis=-1) / fu
    return on[:, 1] - on[:, 0]


def geometric_itd(az_deg, el_deg, spacing_m, r_m, c):
    """Exact free-field path difference for two points at +-spacing/2 on the interaural axis."""
    th = lateral_angle(az_deg, el_deg)
    h = spacing_m / 2
    # source at distance r, lateral component r*sin(th)
    x_lat = r_m * np.sin(th)
    rest = r_m * np.cos(th)
    dL = np.sqrt((x_lat - h) ** 2 + rest ** 2)
    dR = np.sqrt((x_lat + h) ** 2 + rest ** 2)
    return (dR - dL) / c


def woodworth(theta_lat, k_s):
    """ITD = k (theta + sin theta), k = a/c seconds."""
    return k_s * (theta_lat + np.sin(theta_lat))


def fit_woodworth(az, el, itd, el_max=60.0):
    th = lateral_angle(az, el)
    m = np.abs(el) <= el_max
    g = th[m] + np.sin(th[m])
    return float(np.sum(g * itd[m]) / np.sum(g * g))


def correction_s(theta_lat, k_s, spacing_m, c_engine):
    """Signed ITD correction D = Woodworth - far-field geometry (seconds).

    Apply causally: t_R += max(D, 0); t_L += max(-D, 0). For a left source (theta > 0)
    D > 0 whenever a_eff > spacing/2, i.e. the far (right) ear is delayed further.
    """
    return woodworth(theta_lat, k_s) - (spacing_m / c_engine) * np.sin(theta_lat)
