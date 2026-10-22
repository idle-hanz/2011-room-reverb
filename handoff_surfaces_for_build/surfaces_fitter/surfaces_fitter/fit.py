"""Fit dual_high_shelf / low_shelf+high_shelf to textbook √(1−α) targets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from .materials import Material, OCTAVE_HZ, list_materials
from .model import (
    ABSORB_BAND_HZ,
    CANDIDATE_MODELS,
    FREQ_RANGE_HZ,
    PRESET_SCHEMA,
    SurfaceAbsModel,
    absorb_bands_from_alpha,
    alpha_at_freqs,
    bounds_for,
    fit_freqs,
    target_r_db,
)

# Prefer B (LF shelf) when it improves RMSE by more than this (dB),
# or when material is known to need LF absorb.
LF_NEED_IDS = {
    "plywood_panel",
    "glass_window",
    "heavy_curtain",
    "gypsum_painted",
    "carpet_on_foam",
    "absorber_panel_2in",
    "acoustic_ceiling_tile",
}
B_IMPROVEMENT_THRESHOLD = 0.15  # dB RMSE


@dataclass
class FitResult:
    material_id: str
    display_name: str
    honesty: str
    roles: List[str]
    banned_on: List[str]
    source_note: str
    absorb_hz: List[float]
    absorb: List[float]
    alpha_octave: List[float]
    candidate: str  # A / B
    model: str
    params: Dict[str, float]
    rmse_r_db: float
    absorb_l1: float
    candidate_rmse: Dict[str, float]
    freq_range_hz: Tuple[float, float]
    success: bool
    message: str
    extras: Dict = field(default_factory=dict)

    def to_preset_dict(self) -> Dict:
        return {
            "schema": PRESET_SCHEMA,
            "id": self.material_id,
            "display_name": self.display_name,
            "honesty": self.honesty,
            "roles": list(self.roles),
            "banned_on": list(self.banned_on),
            "absorb_hz": list(self.absorb_hz),
            "absorb": list(self.absorb),
            "alpha_octave": list(self.alpha_octave),
            "model": self.model,
            "candidate": self.candidate,
            "params": self.params,
            "rmse_r_db": self.rmse_r_db,
            "absorb_l1": self.absorb_l1,
            "candidate_rmse_r_db": self.candidate_rmse,
            "freq_range_hz": [float(self.freq_range_hz[0]), float(self.freq_range_hz[1])],
            "source_note": self.source_note,
            "usage": (
                "One bounce: apply R(f); multi-bounce: cascade product along hit list. "
                "Do not put curtain/carpet roles on illegal faces."
            ),
            "fit": {"success": self.success, "message": self.message},
            "locks": {
                "live_software": "do not import into live software/ engine in this pack",
                "honesty": "ASSUMED_TEXTBOOK — not Structure VERIFIED",
                "depth": "absolute per bounce (not per metre)",
            },
        }


def _residuals(x: np.ndarray, model_key: str, freqs: np.ndarray, target: np.ndarray) -> np.ndarray:
    model = SurfaceAbsModel.from_vector(model_key, x)
    return model.r_db(freqs) - target


def _rmse(x: np.ndarray, model_key: str, freqs: np.ndarray, target: np.ndarray) -> float:
    r = _residuals(x, model_key, freqs, target)
    return float(np.sqrt(np.mean(r ** 2)))


def _fit_candidate(
    model_key: str,
    freqs: np.ndarray,
    target: np.ndarray,
    maxiter: int = 60,
) -> Tuple[np.ndarray, float, str]:
    lo, hi = bounds_for(model_key)
    bounds = list(zip(lo.tolist(), hi.tolist()))

    def obj(x: np.ndarray) -> float:
        return _rmse(x, model_key, freqs, target)

    de = differential_evolution(
        obj,
        bounds=bounds,
        maxiter=maxiter,
        polish=False,
        seed=42,
        tol=1e-6,
        updating="immediate",
        workers=1,
    )
    x0 = de.x

    ls = least_squares(
        lambda x: _residuals(x, model_key, freqs, target),
        x0,
        bounds=(lo, hi),
        max_nfev=400,
        ftol=1e-10,
        xtol=1e-10,
    )
    x_best = ls.x
    rmse = _rmse(x_best, model_key, freqs, target)
    msg = f"DE success={de.success}; LS success={ls.success} cost={ls.cost:.4g}"
    return x_best, rmse, msg


def _absorb_l1(model: SurfaceAbsModel, alpha_octave: Sequence[float]) -> float:
    """L1 error of model α vs textbook α at the 7 absorb centres."""
    hz = np.asarray(ABSORB_BAND_HZ, dtype=float)
    target_a = np.asarray(alpha_octave, dtype=float)
    pred_a = model.model_alpha(hz)
    return float(np.mean(np.abs(pred_a - target_a)))


def fit_material(mat: Material, maxiter: int = 60) -> FitResult:
    freqs = fit_freqs()
    target = target_r_db(freqs, OCTAVE_HZ, mat.alpha_octave)
    absorb = absorb_bands_from_alpha(mat.alpha_octave)

    candidate_rmse: Dict[str, float] = {}
    fitted: Dict[str, Tuple[np.ndarray, float, str]] = {}

    for key in ("A", "B"):
        x, rmse, msg = _fit_candidate(key, freqs, target, maxiter=maxiter)
        fitted[key] = (x, rmse, msg)
        candidate_rmse[key] = rmse

    rmse_a = candidate_rmse["A"]
    rmse_b = candidate_rmse["B"]

    prefer_b = mat.id in LF_NEED_IDS or (rmse_a - rmse_b) > B_IMPROVEMENT_THRESHOLD
    if prefer_b and rmse_b <= rmse_a + 0.05:
        winner = "B"
    elif rmse_b < rmse_a - B_IMPROVEMENT_THRESHOLD:
        winner = "B"
    else:
        winner = "A"

    x_w, rmse_w, msg_w = fitted[winner]
    model = SurfaceAbsModel.from_vector(winner, x_w)
    l1 = _absorb_l1(model, mat.alpha_octave)

    return FitResult(
        material_id=mat.id,
        display_name=mat.display_name,
        honesty=mat.honesty,
        roles=list(mat.roles),
        banned_on=mat.banned_on(),
        source_note=mat.source_note,
        absorb_hz=list(ABSORB_BAND_HZ),
        absorb=absorb,
        alpha_octave=list(mat.alpha_octave),
        candidate=winner,
        model=model.model,
        params=model.params_dict(),
        rmse_r_db=rmse_w,
        absorb_l1=l1,
        candidate_rmse=candidate_rmse,
        freq_range_hz=FREQ_RANGE_HZ,
        success=True,
        message=msg_w,
        extras={
            "notes": mat.notes,
            "prefer_lf_candidate": mat.id in LF_NEED_IDS,
        },
    )


def fit_all(maxiter: int = 60) -> List[FitResult]:
    return [fit_material(m, maxiter=maxiter) for m in list_materials()]
