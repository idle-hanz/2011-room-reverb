"""Diffuse FDN tail with the head's measured interaural coherence (DECISION LOCKED 2026-09-30, item 1).

Method (reference for Build):
 1. Two near-uncorrelated tail signals from the existing loops (no loop change):
      A = sqrt(2) * sum of EVEN lines of the L-ear loop,  B = sqrt(2) * sum of ODD lines of the R-ear loop.
    (Play/Render already run one 32-line loop per bus, VERIFIED render_pipeline.render_fdn_ir; the full L and R
    loop sums are partly correlated at LF (0.35-0.64 below 200 Hz, VERIFIED), even/odd subsets are not.)
    Lines are uncoloured in this mode (the presets are diffuse-field equalised, so the diffuse average HRTF is flat).
 2. Frequency-dependent 2x2 mixer:  L = Hc*A + Hs*B,  R = Hs*A + Hc*B,
      Hc(f) = cos phi(f), Hs(f) = sin phi(f), sin(2 phi(f)) = IC_target(f)   (so Hc^2 + Hs^2 = 1: power kept)
    For uncorrelated, equal-power A, B the output coherence is exactly IC_target.
 3. Realised as two zero-phase (linear-phase) FIRs on mid/side, N taps:
      M = A + B, S = A - B;  L = (Hp*M + Hm*S)/2,  R = (Hp*M - Hm*S)/2,  Hp = Hc + Hs, Hm = Hc - Hs.
    Latency (N-1)/2 samples on the tail only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parents[1]


def target_ic(preset_id: str, path: Path | None = None):
    d = json.loads((path or ROOT / "reports" / "diffuse_field_coherence.json").read_text())[preset_id]
    return np.asarray(d["f_hz"], float), np.asarray(d["ic_real"], float)


def design_mixer(f_hz, ic, fs: int, ntaps: int = 513, window: str = "hann"):
    """Return (hp, hm) linear-phase FIRs (odd length) for M/S form, plus (hc, hs)."""
    assert ntaps % 2 == 1
    nfft = 1 << int(np.ceil(np.log2(8 * ntaps)))
    fb = np.fft.rfftfreq(nfft, 1.0 / fs)
    ic_b = np.interp(np.log(np.maximum(fb, 1.0)), np.log(f_hz), np.clip(ic, -0.999, 0.999),
                     left=float(ic[0]), right=0.0)
    phi = 0.5 * np.arcsin(ic_b)
    out = []
    for resp in (np.cos(phi), np.sin(phi)):
        h = np.fft.irfft(resp, nfft)
        h = np.roll(h, ntaps // 2)[:ntaps] * signal.get_window(window, ntaps, fftbins=False)
        out.append(h)
    hc, hs = out
    return hc + hs, hc - hs, hc, hs


def apply_mixer(A, B, hp, hm):
    M, S = A + B, A - B
    pm = signal.fftconvolve(M, hp)[: len(A)]
    sm = signal.fftconvolve(S, hm)[: len(A)]
    return 0.5 * (pm + sm), 0.5 * (pm - sm)


def designed_ic(hc, hs, fs, f_eval):
    w, Hc = signal.freqz(hc, worN=f_eval, fs=fs)
    _, Hs = signal.freqz(hs, worN=f_eval, fs=fs)
    num = 2 * np.real(Hc * np.conj(Hs))
    den = np.abs(Hc) ** 2 + np.abs(Hs) ** 2
    return num / den, 10 * np.log10(den)


def measure_ic(x, y, fs, nperseg=4096):
    f, Sxy = signal.csd(x, y, fs, nperseg=nperseg)
    _, Sxx = signal.welch(x, fs, nperseg=nperseg)
    _, Syy = signal.welch(y, fs, nperseg=nperseg)
    return f, np.real(Sxy) / np.sqrt(Sxx * Syy + 1e-300)


def band_ic(f, c, centres, frac=3.0):
    """Mean IC in 1/frac-octave bands around each centre (NaN if no bins)."""
    out = []
    for fc in centres:
        m = (f >= fc / 2 ** (0.5 / frac)) & (f < fc * 2 ** (0.5 / frac))
        out.append(float(np.mean(c[m])) if m.any() else float("nan"))
    return np.asarray(out)


THIRD_OCT = np.array([125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500,
                      3150, 4000, 5000, 6300, 8000], float)


def split_even_odd(poly_l, poly_r):
    """A = sqrt2 * sum(even lines of L loop), B = sqrt2 * sum(odd lines of R loop)."""
    return np.sqrt(2.0) * poly_l[:, 0::2].sum(1), np.sqrt(2.0) * poly_r[:, 1::2].sum(1)
