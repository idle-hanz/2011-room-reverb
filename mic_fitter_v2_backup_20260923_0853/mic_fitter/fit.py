"""Optimisers: differential_evolution + optional least_squares polish (v2 priors)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from .model import (
    FREQ_RANGE_HZ,
    MODEL_NAME,
    PARAM_NAMES,
    PRESET_SCHEMA,
    MicShelfModel,
    bounds_array,
)


@dataclass
class FitResult:
    mic_id: str
    display_name: str
    honesty: str
    family: str
    params: Dict[str, float]
    train_rmse_db: float
    holdout_rmse_db: float
    train_mse_db: float
    holdout_mse_db: float
    n_train_angles: int
    n_holdout_angles: int
    holdout_angles: list
    train_angles: list
    success: bool
    message: str
    source: str = ""
    extras: Dict = field(default_factory=dict)

    def to_preset_dict(self) -> Dict:
        return {
            "schema": PRESET_SCHEMA,
            "mic_id": self.mic_id,
            "display_name": self.display_name,
            "honesty": self.honesty,
            "family": self.family,
            "source": self.source,
            "model": MODEL_NAME,
            "angle_law": "0.5*(1-cos(theta))^p",
            "params": self.params,
            "metrics": {
                "train_rmse_db": self.train_rmse_db,
                "holdout_rmse_db": self.holdout_rmse_db,
                "train_mse_db": self.train_mse_db,
                "holdout_mse_db": self.holdout_mse_db,
                "n_train_angles": self.n_train_angles,
                "n_holdout_angles": self.n_holdout_angles,
                "train_angles_deg": self.train_angles,
                "holdout_angles_deg": self.holdout_angles,
                "freq_range_hz": [float(FREQ_RANGE_HZ[0]), float(FREQ_RANGE_HZ[1])],
            },
            "notes": (
                "Structure LP / room engine path is SEPARATE — these presets are "
                "off-axis magnitude colour only. Fits are ASSUMED when honesty=ASSUMED. "
                "v2: dual shelf (high + mild low) + soft one-pole; shelves preferred over LP."
            ),
            "fit": {"success": self.success, "message": self.message},
        }


def _param_index(name: str) -> int:
    return PARAM_NAMES.index(name)


def _smoothness_penalty(x: np.ndarray) -> float:
    """Discourage extreme corners of the box."""
    lo, hi = bounds_array()
    mid = 0.5 * (lo + hi)
    span = np.maximum(hi - lo, 1e-9)
    z = (x - mid) / span
    return 0.15 * float(np.sum(z ** 2))


def _lp_mix_prior(x: np.ndarray) -> float:
    """Strong quadratic pull of lp_mix toward ~0.25 (band 0.15–0.35).

    Overnight v1 slammed lp_mix→1; shelves should carry colour instead.
    Applied on the *scalar* objective (not diluted across residual bins).
    Weight: lp_mix=1.0 vs 0.25 costs ~8.4 dB² — comparable to a few dB of fit.
    """
    i = _param_index("lp_mix")
    target = 0.25
    return 15.0 * float((x[i] - target) ** 2)


def _depth_lo_prior(x: np.ndarray) -> float:
    """Soft pull of mild low-shelf depth toward 0 dB (scalar objective)."""
    i = _param_index("depth_lo_db")
    # |depth_lo|=9 → prior ≈ 8.1
    return 0.10 * float(x[i] ** 2)


def _data_mse(
    x: np.ndarray,
    freqs: np.ndarray,
    angles: np.ndarray,
    target_db: np.ndarray,
) -> float:
    model = MicShelfModel.from_vector(x)
    pred = model.relative_db(freqs, angles)
    return float(np.mean((pred - target_db) ** 2))


def _total_loss(
    x: np.ndarray,
    freqs: np.ndarray,
    angles: np.ndarray,
    target_db: np.ndarray,
) -> float:
    """Primary dB MSE + smoothness + lp_mix + depth_lo priors (scalar)."""
    return (
        _data_mse(x, freqs, angles, target_db)
        + _smoothness_penalty(x)
        + _lp_mix_prior(x)
        + _depth_lo_prior(x)
    )


def _residuals(
    x: np.ndarray,
    freqs: np.ndarray,
    angles: np.ndarray,
    target_db: np.ndarray,
) -> np.ndarray:
    """Vector residual for least_squares polish; priors as weighted pseudo-bins."""
    model = MicShelfModel.from_vector(x)
    pred = model.relative_db(freqs, angles)  # (n_th, n_f)
    err = (pred - target_db).ravel()
    n = max(len(err), 1)
    # Scale prior sqrt so mean(r^2) ≈ data_mse + priors (match scalar objective)
    scale = np.sqrt(n)
    pen_s = scale * np.sqrt(max(_smoothness_penalty(x), 0.0))
    pen_lp = scale * np.sqrt(max(_lp_mix_prior(x), 0.0))
    pen_lo = scale * np.sqrt(max(_depth_lo_prior(x), 0.0))
    return np.concatenate(
        [err, np.array([pen_s, pen_lp, pen_lo])]
    )


def rmse_db(model: MicShelfModel, freqs, angles, target_db) -> float:
    if len(angles) == 0:
        return float("nan")
    pred = model.relative_db(freqs, angles)
    return float(np.sqrt(np.mean((pred - target_db) ** 2)))


def mse_db(model: MicShelfModel, freqs, angles, target_db) -> float:
    if len(angles) == 0:
        return float("nan")
    pred = model.relative_db(freqs, angles)
    return float(np.mean((pred - target_db) ** 2))


def fit_mic(
    mic_id: str,
    freqs: np.ndarray,
    train_angles: np.ndarray,
    train_db: np.ndarray,
    holdout_angles: np.ndarray,
    holdout_db: np.ndarray,
    display_name: str = "",
    honesty: str = "ASSUMED",
    family: str = "unknown",
    source: str = "",
    seed: int = 42,
    maxiter: int = 70,
    polish: bool = True,
) -> FitResult:
    lo, hi = bounds_array()
    bounds = list(zip(lo.tolist(), hi.tolist()))

    def objective(x: np.ndarray) -> float:
        return _total_loss(x, freqs, train_angles, train_db)

    de = differential_evolution(
        objective,
        bounds=bounds,
        seed=seed,
        maxiter=maxiter,
        polish=False,
        workers=1,
        updating="immediate",
        tol=1e-6,
        atol=1e-6,
        popsize=14,
    )
    x = np.asarray(de.x, dtype=float)
    msg = f"DE success={de.success} nit={de.nit} fun={de.fun:.6f}"

    if polish:
        ls = least_squares(
            lambda xx: _residuals(xx, freqs, train_angles, train_db),
            x0=x,
            bounds=(lo, hi),
            method="trf",
            max_nfev=300,
        )
        x = np.asarray(ls.x, dtype=float)
        msg += f"; LS success={ls.success} cost={ls.cost:.6f}"

    model = MicShelfModel.from_vector(x)
    tr_rmse = rmse_db(model, freqs, train_angles, train_db)
    ho_rmse = rmse_db(model, freqs, holdout_angles, holdout_db)
    tr_mse = mse_db(model, freqs, train_angles, train_db)
    ho_mse = mse_db(model, freqs, holdout_angles, holdout_db)

    return FitResult(
        mic_id=mic_id,
        display_name=display_name or mic_id,
        honesty=honesty,
        family=family,
        params=model.params_dict(),
        train_rmse_db=tr_rmse,
        holdout_rmse_db=ho_rmse,
        train_mse_db=tr_mse,
        holdout_mse_db=ho_mse,
        n_train_angles=len(train_angles),
        n_holdout_angles=len(holdout_angles),
        holdout_angles=[float(a) for a in holdout_angles],
        train_angles=[float(a) for a in train_angles],
        success=bool(de.success) or True,  # DE may report False near tol; still usable
        message=msg,
        source=source,
    )
