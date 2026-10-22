"""Musical reflection-magnitude models fitted to √(1−α).

Target (amplitude reflection):
  R_db(f) = 20 * log10(√(max(1−α(f), 1e-6)))

α(f) is log-frequency interpolated between octave centres.
Depth is absolute (per bounce), not per metre.

Candidates
----------
A — dual_high_shelf          (two HF shelves; good for rising-α carpets/tiles)
B — low_shelf + high_shelf   (LF absorb for plywood / glass / curtain)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import numpy as np

from .materials import OCTAVE_HZ

FREQ_RANGE_HZ = (20.0, 16000.0)
N_FREQS = 192
PRESET_SCHEMA = "surfaces_fitter.material.v1"
ABSORB_BAND_HZ = tuple(OCTAVE_HZ)  # 125…8000 matching Desktop Surfaces cards

CANDIDATE_A = "dual_high_shelf"
CANDIDATE_B = "low_shelf_high_shelf"

PARAM_NAMES_A: Tuple[str, ...] = (
    "r0_db",
    "f0",
    "depth_db",
    "shelf_slope",
    "f0_hi",
    "depth_hi_db",
    "shelf_slope_hi",
)
PARAM_BOUNDS_A: Dict[str, Tuple[float, float]] = {
    "r0_db": (-30.0, 0.0),
    "f0": (200.0, 6000.0),
    "depth_db": (-40.0, 0.0),
    "shelf_slope": (0.6, 12.0),
    "f0_hi": (2000.0, 14000.0),
    "depth_hi_db": (-40.0, 0.0),
    "shelf_slope_hi": (0.6, 12.0),
}

PARAM_NAMES_B: Tuple[str, ...] = (
    "r0_db",
    "f_lo",
    "depth_lo_db",
    "shelf_slope_lo",
    "f0",
    "depth_db",
    "shelf_slope",
)
PARAM_BOUNDS_B: Dict[str, Tuple[float, float]] = {
    "r0_db": (-30.0, 0.0),
    "f_lo": (40.0, 800.0),
    "depth_lo_db": (-25.0, 0.0),
    "shelf_slope_lo": (0.6, 12.0),
    "f0": (400.0, 8000.0),
    "depth_db": (-40.0, 0.0),
    "shelf_slope": (0.6, 12.0),
}

CANDIDATE_MODELS = {
    "A": {
        "name": CANDIDATE_A,
        "param_names": PARAM_NAMES_A,
        "bounds": PARAM_BOUNDS_A,
    },
    "B": {
        "name": CANDIDATE_B,
        "param_names": PARAM_NAMES_B,
        "bounds": PARAM_BOUNDS_B,
    },
}


def high_shelf_db(
    freqs: np.ndarray,
    f0: float,
    depth_db: float,
    shelf_slope: float = 4.0,
) -> np.ndarray:
    """Smooth high-shelf gain in dB (log-sigmoid; same family as air/mic)."""
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(float(f0), 1.0))
    blend = 1.0 / (1.0 + np.exp(-float(shelf_slope) * x))
    return float(depth_db) * blend


def low_shelf_db(
    freqs: np.ndarray,
    f0: float,
    depth_db: float,
    shelf_slope: float = 4.0,
) -> np.ndarray:
    """Smooth low-shelf gain in dB (mirror of high_shelf)."""
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(float(f0), 1.0))
    blend = 1.0 / (1.0 + np.exp(float(shelf_slope) * x))  # 1 below f0, 0 above
    return float(depth_db) * blend


def alpha_at_freqs(
    freqs: np.ndarray,
    octave_hz: Sequence[float],
    alpha_octave: Sequence[float],
) -> np.ndarray:
    """Log-frequency interpolate α between octave centres; clamp outside."""
    f = np.asarray(freqs, dtype=float)
    hz = np.asarray(octave_hz, dtype=float)
    a = np.asarray(alpha_octave, dtype=float)
    log_hz = np.log10(np.maximum(hz, 1.0))
    log_f = np.log10(np.maximum(f, 1.0))
    return np.interp(log_f, log_hz, a)


def target_r_db(
    freqs: np.ndarray,
    octave_hz: Sequence[float],
    alpha_octave: Sequence[float],
) -> np.ndarray:
    """R_db(f) = 20*log10(√(max(1−α(f), 1e-6)))."""
    alpha = alpha_at_freqs(freqs, octave_hz, alpha_octave)
    one_minus = np.maximum(1.0 - alpha, 1e-6)
    return 20.0 * np.log10(np.sqrt(one_minus))


def absorb_bands_from_alpha(alpha_octave: Sequence[float]) -> list:
    """Export absorb[7] at Desktop Surfaces centres (already 7 bands)."""
    return [float(max(0.0, min(0.99, a))) for a in alpha_octave]


@dataclass
class SurfaceAbsModel:
    """Per-bounce reflection colour R_db(f) ≤ 0."""

    model: str = CANDIDATE_A
    r0_db: float = 0.0
    f0: float = 2000.0
    depth_db: float = -6.0
    shelf_slope: float = 4.0
    f0_hi: float = 8000.0
    depth_hi_db: float = -3.0
    shelf_slope_hi: float = 4.0
    f_lo: float = 200.0
    depth_lo_db: float = -3.0
    shelf_slope_lo: float = 4.0

    def params_dict(self) -> Dict[str, float]:
        key = {
            CANDIDATE_A: "A",
            CANDIDATE_B: "B",
        }[self.model]
        names = CANDIDATE_MODELS[key]["param_names"]
        return {k: float(getattr(self, k)) for k in names}

    @classmethod
    def from_vector(cls, model_key: str, x: Sequence[float]) -> "SurfaceAbsModel":
        meta = CANDIDATE_MODELS[model_key]
        kwargs = {n: float(v) for n, v in zip(meta["param_names"], x)}
        return cls(model=meta["name"], **kwargs)

    def r_db(self, freqs: np.ndarray) -> np.ndarray:
        """Model reflection magnitude in dB (≤ 0 for absorb-only shelves)."""
        f = np.asarray(freqs, dtype=float)
        if self.model == CANDIDATE_A:
            s1 = high_shelf_db(f, self.f0, self.depth_db, self.shelf_slope)
            s2 = high_shelf_db(f, self.f0_hi, self.depth_hi_db, self.shelf_slope_hi)
            return float(self.r0_db) + s1 + s2
        if self.model == CANDIDATE_B:
            lo = low_shelf_db(f, self.f_lo, self.depth_lo_db, self.shelf_slope_lo)
            hi = high_shelf_db(f, self.f0, self.depth_db, self.shelf_slope)
            return float(self.r0_db) + lo + hi
        raise ValueError(f"Unknown model {self.model!r}")

    def model_alpha(self, freqs: np.ndarray) -> np.ndarray:
        """Invert R_db → α = 1 − 10^(R_db/10)  (since |R|^2 = 1−α)."""
        r = self.r_db(freqs)
        r2 = np.power(10.0, r / 10.0)  # |R|^2
        return np.clip(1.0 - r2, 0.0, 0.99)


def fit_freqs(n: int = N_FREQS) -> np.ndarray:
    return np.geomspace(FREQ_RANGE_HZ[0], FREQ_RANGE_HZ[1], int(n))


def bounds_for(model_key: str) -> Tuple[np.ndarray, np.ndarray]:
    meta = CANDIDATE_MODELS[model_key]
    lo = np.array([meta["bounds"][n][0] for n in meta["param_names"]], dtype=float)
    hi = np.array([meta["bounds"][n][1] for n in meta["param_names"]], dtype=float)
    return lo, hi
