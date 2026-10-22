"""SOFA loading, magnitude spectra, fractional-octave smoothing, diffuse-field EQ.

Coordinates (SOFA SimpleFreeFieldHRIR, VERIFIED in the files): azimuth deg CCW from
front (+90 = left), elevation deg up, receiver 0 = LEFT ear (louder at az 90, VERIFIED).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

NFFT = 8192
# Storage / fit frequency grid (Hz). Eval band for metrics is 100 Hz .. 16 kHz.
FGRID = np.geomspace(40.0, 20000.0, 300)
EVAL_LO, EVAL_HI = 100.0, 16000.0
EVAL_MASK = (FGRID >= EVAL_LO) & (FGRID <= EVAL_HI)


@dataclass
class Sofa:
    path: str
    ir: np.ndarray          # (M, 2, N) float64
    fs: int
    az: np.ndarray          # (M,) deg, SOFA convention, wrapped to (-180, 180]
    el: np.ndarray          # (M,) deg
    r: np.ndarray           # (M,) m
    receivers: np.ndarray   # (2, 3) m
    attrs: dict = field(default_factory=dict)

    @property
    def ear_spacing_m(self) -> float:
        return float(np.linalg.norm(self.receivers[0] - self.receivers[1]))

    def unit_vectors(self) -> np.ndarray:
        return sph_to_vec(self.az, self.el)


def load_sofa(path) -> Sofa:
    import netCDF4
    d = netCDF4.Dataset(str(path))
    try:
        ir = np.asarray(d["Data.IR"][:], dtype=np.float64)
        fs = int(round(float(np.asarray(d["Data.SamplingRate"][:]).reshape(-1)[0])))
        sp = np.asarray(d["SourcePosition"][:], dtype=np.float64)
        rp = np.asarray(d["ReceiverPosition"][:], dtype=np.float64).reshape(2, 3)
        typ = str(d["SourcePosition"].getncattr("Type"))
        if "spherical" not in typ:
            raise ValueError(f"expected spherical SourcePosition, got {typ}")
        delay = np.asarray(d["Data.Delay"][:], dtype=np.float64)
        if np.any(np.abs(delay) > 0):
            raise ValueError("non-zero Data.Delay not handled")
        attrs = {a: str(d.getncattr(a)) for a in d.ncattrs()}
    finally:
        d.close()
    az = (sp[:, 0] + 180.0) % 360.0 - 180.0
    az[az == -180.0] = 180.0
    return Sofa(str(path), ir, fs, az, sp[:, 1], sp[:, 2], rp, attrs)


def sph_to_vec(az_deg, el_deg) -> np.ndarray:
    """SOFA: x front, y left, z up."""
    a = np.radians(np.asarray(az_deg, dtype=np.float64))
    e = np.radians(np.asarray(el_deg, dtype=np.float64))
    return np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], axis=-1)


def nearest_index(sofa: Sofa, az, el):
    v = sph_to_vec(az, el)
    U = sofa.unit_vectors()
    dots = U @ np.atleast_2d(v).T
    idx = np.argmax(dots, axis=0)
    ang = np.degrees(np.arccos(np.clip(dots[idx, np.arange(dots.shape[1])], -1, 1)))
    return idx, ang


def sphere_weights(sofa: Sofa, n_ref: int = 60000) -> np.ndarray:
    """Area weights by nearest-neighbour counting on a Fibonacci sphere (works for any grid).

    Directions with no reference point nearby (e.g. a missing polar cap) get no weight,
    so the diffuse-field average covers only the measured part of the sphere.
    """
    from scipy.spatial import cKDTree
    i = np.arange(n_ref) + 0.5
    z = 1 - 2 * i / n_ref
    phi = np.pi * (1 + 5 ** 0.5) * i
    ref = np.stack([np.sqrt(1 - z * z) * np.cos(phi), np.sqrt(1 - z * z) * np.sin(phi), z], axis=1)
    U = sofa.unit_vectors()
    dist, idx = cKDTree(U).query(ref)
    # Reject reference points far from any measurement (> 6 deg chord ~ 0.105)
    ok = dist < 0.105
    w = np.bincount(idx[ok], minlength=len(U)).astype(np.float64)
    return w / w.sum()


def power_spectra(ir: np.ndarray, fs: int, nfft: int = NFFT):
    """|H|^2 on rfft bins. ir: (..., N)."""
    H = np.fft.rfft(ir, n=nfft, axis=-1)
    f = np.fft.rfftfreq(nfft, 1.0 / fs)
    return f, (H.real ** 2 + H.imag ** 2)


def complex_spectra(ir, fs, nfft=NFFT):
    return np.fft.rfftfreq(nfft, 1.0 / fs), np.fft.rfft(ir, n=nfft, axis=-1)


_SMAT = {}


def smoothing_matrix(fbins: np.ndarray, fgrid: np.ndarray = FGRID, frac: float = 6.0) -> np.ndarray:
    """Rows: rectangular 1/frac-octave power average around each fgrid point."""
    key = (len(fbins), float(fbins[1]), len(fgrid), float(fgrid[0]), float(fgrid[-1]), frac)
    if key in _SMAT:
        return _SMAT[key]
    half = 0.5 / frac
    S = np.zeros((len(fgrid), len(fbins)))
    for i, fc in enumerate(fgrid):
        lo, hi = fc * 2 ** -half, fc * 2 ** half
        m = (fbins >= lo) & (fbins <= hi)
        if m.sum() >= 2:
            S[i, m] = 1.0 / m.sum()
        else:  # linear interpolation fallback
            j = np.searchsorted(fbins, fc)
            j = min(max(j, 1), len(fbins) - 1)
            t = (fc - fbins[j - 1]) / (fbins[j] - fbins[j - 1])
            S[i, j - 1], S[i, j] = 1 - t, t
    _SMAT[key] = S
    return S


def smoothed_db(power: np.ndarray, fbins: np.ndarray, frac: float = 6.0, fgrid=FGRID) -> np.ndarray:
    S = smoothing_matrix(fbins, fgrid, frac)
    p = power @ S.T
    return 10 * np.log10(np.maximum(p, 1e-20))


def diffuse_field_db(sofa: Sofa, w: np.ndarray | None = None, frac: float = 3.0):
    """Diffuse-field (random-incidence) power average of both ears, 1/3-oct smoothed, on FGRID."""
    if w is None:
        w = sphere_weights(sofa)
    f, P = power_spectra(sofa.ir, sofa.fs)
    pdf = np.einsum("m,mef->f", w, P) / 2.0
    return smoothed_db(pdf[None, :], f, frac)[0], w


class HrtfSet:
    """Diffuse-field-equalised, 1/6-oct smoothed magnitude (dB on FGRID) on demand."""

    def __init__(self, sofa: Sofa, frac: float = 6.0, df_eq: bool = True):
        self.sofa = sofa
        self.frac = frac
        self.df_db, self.w = diffuse_field_db(sofa)
        self.df_eq = df_eq
        self._f, _ = power_spectra(sofa.ir[:1], sofa.fs)

    def mag_db(self, idx) -> np.ndarray:
        """(len(idx), 2, len(FGRID)) dB."""
        idx = np.atleast_1d(idx)
        f, P = power_spectra(self.sofa.ir[idx], self.sofa.fs)
        db = smoothed_db(P, f, self.frac)
        if self.df_eq:
            db = db - self.df_db[None, None, :]
        return db

    def raw_mag_db(self, idx) -> np.ndarray:
        """Unsmoothed (zero-padded FFT interpolated to FGRID), DF-equalised."""
        idx = np.atleast_1d(idx)
        f, P = power_spectra(self.sofa.ir[idx], self.sofa.fs)
        db = 10 * np.log10(np.maximum(P, 1e-20))
        out = np.stack([[np.interp(FGRID, f, db[i, e]) for e in range(2)] for i in range(len(idx))])
        if self.df_eq:
            out = out - self.df_db[None, None, :]
        return out
