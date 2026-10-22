"""Distance-scalable air-absorption filter bank (musical, mic_fitter-style).

A_model(f, d) = d * H1(f)   with H1 in dB/m (≤ 0).

Candidates
----------
A — high shelf only
B — high shelf + soft one-pole (preferred if RMSE wins)
C — dual high shelf (if B still poor at 16 kHz)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import numpy as np

FREQ_RANGE_HZ = (20.0, 16000.0)
PRESET_SCHEMA = "air_fitter.preset.v1"
DISTANCES_M = (5.0, 10.0, 20.0, 40.0)
N_FREQS = 96  # log-spaced fit grid

# ASSUMED engine humidity shelf (software/engine/early_field.py) — compare only
ASSUMED_DB_PER_M = -0.15
ASSUMED_SHELF_RATIO = 0.35  # corner ≈ 0.35 * Nyquist
ASSUMED_SR = 44100.0


def high_shelf_db(
    freqs: np.ndarray,
    f0: float,
    depth_db: float,
    shelf_slope: float = 4.0,
) -> np.ndarray:
    """Smooth high-shelf gain in dB (same log-sigmoid as mic_fitter)."""
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(f0, 1.0))
    blend = 1.0 / (1.0 + np.exp(-float(shelf_slope) * x))
    return depth_db * blend


def soft_one_pole_db(freqs: np.ndarray, fc) -> np.ndarray:
    """Soft one-pole LP magnitude in dB: 20*log10(1/sqrt(1+(f/fc)^2))."""
    f = np.asarray(freqs, dtype=float)
    fc_arr = np.asarray(fc, dtype=float)
    fc_arr = np.maximum(fc_arr, 1.0)
    mag = 1.0 / np.sqrt(1.0 + (f / fc_arr) ** 2)
    return 20.0 * np.log10(np.maximum(mag, 1e-12))


def assumed_shelf_h1_db(
    freqs: np.ndarray,
    humidity: float = 0.5,
    sr: float = ASSUMED_SR,
) -> np.ndarray:
    """Engine ASSUMED humidity colour as H1(f) in dB/m (compare-only).

    gain_db_per_m = -0.15 * humidity, applied as a high shelf with corner
    ≈ 0.35 * Nyquist. Modelled with the same log-sigmoid family (slope≈8)
    so plots are fair against ISO α(f).
    """
    depth = ASSUMED_DB_PER_M * float(humidity)
    f0 = ASSUMED_SHELF_RATIO * (0.5 * float(sr))
    return high_shelf_db(freqs, f0, depth, shelf_slope=8.0)


# ---------------------------------------------------------------------------
# Candidate param layouts
# ---------------------------------------------------------------------------

CANDIDATE_A = "high_shelf"
CANDIDATE_B = "high_shelf_plus_soft_one_pole"
CANDIDATE_C = "dual_high_shelf"

PARAM_NAMES_A: Tuple[str, ...] = ("f0", "depth_db_per_m", "shelf_slope")
PARAM_BOUNDS_A: Dict[str, Tuple[float, float]] = {
    "f0": (500.0, 14000.0),
    "depth_db_per_m": (-0.25, 0.0),
    "shelf_slope": (0.6, 12.0),
}

PARAM_NAMES_B: Tuple[str, ...] = (
    "f0",
    "depth_db_per_m",
    "shelf_slope",
    "res_hz",
    "lp_mix",
)
PARAM_BOUNDS_B: Dict[str, Tuple[float, float]] = {
    "f0": (500.0, 14000.0),
    "depth_db_per_m": (-0.25, 0.0),
    "shelf_slope": (0.6, 12.0),
    "res_hz": (1500.0, 16000.0),
    "lp_mix": (0.0, 1.0),
}

PARAM_NAMES_C: Tuple[str, ...] = (
    "f0",
    "depth_db_per_m",
    "shelf_slope",
    "f0_hi",
    "depth_hi_db_per_m",
    "shelf_slope_hi",
)
PARAM_BOUNDS_C: Dict[str, Tuple[float, float]] = {
    "f0": (500.0, 8000.0),
    "depth_db_per_m": (-0.20, 0.0),
    "shelf_slope": (0.6, 12.0),
    "f0_hi": (4000.0, 16000.0),
    "depth_hi_db_per_m": (-0.30, 0.0),
    "shelf_slope_hi": (0.6, 12.0),
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
    "C": {
        "name": CANDIDATE_C,
        "param_names": PARAM_NAMES_C,
        "bounds": PARAM_BOUNDS_C,
    },
}


@dataclass
class AirAbsModel:
    """Per-metre colour H1(f) in dB/m; path loss = d * H1(f)."""

    model: str = CANDIDATE_B
    f0: float = 4000.0
    depth_db_per_m: float = -0.05
    shelf_slope: float = 4.0
    res_hz: float = 8000.0
    lp_mix: float = 0.3
    f0_hi: float = 10000.0
    depth_hi_db_per_m: float = -0.05
    shelf_slope_hi: float = 4.0

    def params_dict(self) -> Dict[str, float]:
        names = CANDIDATE_MODELS[
            {"high_shelf": "A", "high_shelf_plus_soft_one_pole": "B", "dual_high_shelf": "C"}[self.model]
        ]["param_names"]
        return {k: float(getattr(self, k)) for k in names}

    @classmethod
    def from_vector(cls, model_key: str, x: Sequence[float]) -> "AirAbsModel":
        meta = CANDIDATE_MODELS[model_key]
        kwargs = {n: float(v) for n, v in zip(meta["param_names"], x)}
        return cls(model=meta["name"], **kwargs)

    def h1_db_per_m(self, freqs: np.ndarray) -> np.ndarray:
        """H1(f) in dB/m (≤ 0)."""
        f = np.asarray(freqs, dtype=float)
        if self.model == CANDIDATE_A:
            return high_shelf_db(f, self.f0, self.depth_db_per_m, self.shelf_slope)
        if self.model == CANDIDATE_B:
            shelf = high_shelf_db(f, self.f0, self.depth_db_per_m, self.shelf_slope)
            lp = soft_one_pole_db(f, self.res_hz)
            return shelf + float(self.lp_mix) * lp
        if self.model == CANDIDATE_C:
            s1 = high_shelf_db(f, self.f0, self.depth_db_per_m, self.shelf_slope)
            s2 = high_shelf_db(f, self.f0_hi, self.depth_hi_db_per_m, self.shelf_slope_hi)
            return s1 + s2
        raise ValueError(f"Unknown model {self.model!r}")

    def path_loss_db(self, freqs: np.ndarray, distance_m: float) -> np.ndarray:
        return float(distance_m) * self.h1_db_per_m(freqs)


def fit_freqs(n: int = N_FREQS) -> np.ndarray:
    return np.geomspace(FREQ_RANGE_HZ[0], FREQ_RANGE_HZ[1], int(n))


def bounds_for(model_key: str) -> Tuple[np.ndarray, np.ndarray]:
    meta = CANDIDATE_MODELS[model_key]
    lo = np.array([meta["bounds"][n][0] for n in meta["param_names"]], dtype=float)
    hi = np.array([meta["bounds"][n][1] for n in meta["param_names"]], dtype=float)
    return lo, hi
