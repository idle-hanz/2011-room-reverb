"""Fit candidate filter banks to ISO 9613-1 α(f)·d over several distances."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from .iso9613 import Climate, alpha_db_per_m, path_loss_db
from .model import (
    CANDIDATE_MODELS,
    DISTANCES_M,
    FREQ_RANGE_HZ,
    PRESET_SCHEMA,
    AirAbsModel,
    assumed_shelf_h1_db,
    bounds_for,
    fit_freqs,
)

# Climate presets to fit (PRIMARY first)
CLIMATE_PRESETS: List[Dict] = [
    {
        "id": "studio_20C_50RH",
        "label": "Studio 20 °C / 50 % RH (PRIMARY)",
        "temperature_c": 20.0,
        "relative_humidity_pct": 50.0,
        "pressure_kpa": 101.325,
        "primary": True,
    },
    {
        "id": "dry_20C_20RH",
        "label": "Dry 20 °C / 20 % RH",
        "temperature_c": 20.0,
        "relative_humidity_pct": 20.0,
        "pressure_kpa": 101.325,
        "primary": False,
    },
    {
        "id": "humid_20C_80RH",
        "label": "Humid 20 °C / 80 % RH",
        "temperature_c": 20.0,
        "relative_humidity_pct": 80.0,
        "pressure_kpa": 101.325,
        "primary": False,
    },
    {
        "id": "warm_22C_40RH",
        "label": "Warm 22 °C / 40 % RH",
        "temperature_c": 22.0,
        "relative_humidity_pct": 40.0,
        "pressure_kpa": 101.325,
        "primary": False,
    },
]

HF_WEIGHT = 1.5
HF_BAND_HZ = (4000.0, 16000.0)
# Prefer B unless C improves joint RMSE by more than this (dB)
C_IMPROVEMENT_THRESHOLD = 0.002


@dataclass
class FitResult:
    climate_id: str
    label: str
    honesty: str
    conditions: Dict
    candidate: str  # A / B / C
    model: str
    params: Dict[str, float]
    joint_rmse_db: float
    per_distance_rmse_db: Dict[str, float]
    candidate_rmse: Dict[str, float]
    flat_rmse_db: float
    assumed_rmse: Dict[str, float]
    freq_range_hz: Tuple[float, float]
    distances_m: List[float]
    success: bool
    message: str
    alpha_check: Dict = field(default_factory=dict)
    extras: Dict = field(default_factory=dict)

    def to_preset_dict(self) -> Dict:
        return {
            "schema": PRESET_SCHEMA,
            "id": self.climate_id,
            "honesty": self.honesty,
            "conditions": self.conditions,
            "model": self.model,
            "candidate": self.candidate,
            "params": self.params,
            "usage": (
                "A_db(f,d) = d * H1(f); apply as magnitude 10^(A_db/20) once per path "
                "(early) or inject distance (FDN). Do not put on feedback return. "
                "Do not replace geometric 1/r^2."
            ),
            "rmse": {
                "joint_db": self.joint_rmse_db,
                "per_distance_db": self.per_distance_rmse_db,
                "flat_naive_db": self.flat_rmse_db,
                "assumed_shelf": self.assumed_rmse,
                "all_candidates_joint_db": self.candidate_rmse,
            },
            "freq_range_hz": [float(self.freq_range_hz[0]), float(self.freq_range_hz[1])],
            "distances_m": list(self.distances_m),
            "locks": {
                "geometric_1_over_r2": "stays — this only replaces ASSUMED high-shelf colour",
                "structure_1pole_wet_dis": "separate musical control — not replaced",
                "placement": "once on early + FDN inject; not Direct; not feedback",
                "live_software": "do not import into live software/ engine in this pack",
            },
            "fit": {"success": self.success, "message": self.message},
            "alpha_check": self.alpha_check,
        }


def _freq_weights(freqs: np.ndarray) -> np.ndarray:
    w = np.ones_like(freqs, dtype=float)
    w[(freqs >= HF_BAND_HZ[0]) & (freqs <= HF_BAND_HZ[1])] = HF_WEIGHT
    return w


def _joint_residuals(
    x: np.ndarray,
    model_key: str,
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,  # (n_d, n_f) path loss ≤ 0
) -> np.ndarray:
    model = AirAbsModel.from_vector(model_key, x)
    w = _freq_weights(freqs)
    errs = []
    for i, d in enumerate(distances):
        pred = model.path_loss_db(freqs, d)
        errs.append((pred - targets[i]) * np.sqrt(w))
    return np.concatenate(errs)


def _joint_mse(
    x: np.ndarray,
    model_key: str,
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
) -> float:
    r = _joint_residuals(x, model_key, freqs, distances, targets)
    return float(np.mean(r ** 2))


def rmse_joint(
    model: AirAbsModel,
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
    weighted: bool = True,
) -> float:
    w = _freq_weights(freqs) if weighted else np.ones_like(freqs)
    errs = []
    for i, d in enumerate(distances):
        pred = model.path_loss_db(freqs, d)
        errs.append(((pred - targets[i]) ** 2) * w)
    return float(np.sqrt(np.mean(np.concatenate(errs))))


def rmse_per_distance(
    model: AirAbsModel,
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
) -> Dict[str, float]:
    out = {}
    for i, d in enumerate(distances):
        pred = model.path_loss_db(freqs, d)
        out[f"{d:g}m"] = float(np.sqrt(np.mean((pred - targets[i]) ** 2)))
    return out


def flat_naive_rmse(
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
    climate: Climate,
) -> float:
    """Single number ᾱ (mean ISO α over fit band) × d vs ISO — naive flat shelf."""
    alpha = alpha_db_per_m(freqs, climate)
    a_bar = float(np.mean(alpha))
    errs = []
    w = _freq_weights(freqs)
    for i, d in enumerate(distances):
        pred = -a_bar * float(d) * np.ones_like(freqs)
        errs.append(((pred - targets[i]) ** 2) * w)
    return float(np.sqrt(np.mean(np.concatenate(errs))))


def assumed_shelf_rmse(
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
    humidity: float,
) -> float:
    h1 = assumed_shelf_h1_db(freqs, humidity=humidity)
    errs = []
    w = _freq_weights(freqs)
    for i, d in enumerate(distances):
        pred = float(d) * h1
        errs.append(((pred - targets[i]) ** 2) * w)
    return float(np.sqrt(np.mean(np.concatenate(errs))))


def _fit_one_candidate(
    model_key: str,
    freqs: np.ndarray,
    distances: Sequence[float],
    targets: np.ndarray,
    seed: int = 42,
    maxiter: int = 80,
) -> Tuple[AirAbsModel, float, str]:
    lo, hi = bounds_for(model_key)
    bounds = list(zip(lo.tolist(), hi.tolist()))

    def objective(x: np.ndarray) -> float:
        return _joint_mse(x, model_key, freqs, distances, targets)

    de = differential_evolution(
        objective,
        bounds=bounds,
        seed=seed,
        maxiter=maxiter,
        polish=False,
        workers=1,
        updating="immediate",
        tol=1e-8,
        atol=1e-8,
        popsize=15,
    )
    x0 = de.x.copy()

    def resid(x: np.ndarray) -> np.ndarray:
        return _joint_residuals(x, model_key, freqs, distances, targets)

    ls = least_squares(resid, x0, bounds=(lo, hi), max_nfev=400)
    x_best = ls.x
    model = AirAbsModel.from_vector(model_key, x_best)
    rmse = rmse_joint(model, freqs, distances, targets, weighted=True)
    msg = (
        f"DE success={de.success} nit={de.nit} fun={de.fun:.6g}; "
        f"LS success={ls.success} cost={ls.cost:.6g}"
    )
    return model, rmse, msg


def _alpha_sanity(climate: Climate) -> Dict:
    """Validate rough table-order points (20 °C 50 % RH style)."""
    checks = {}
    for f in (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0):
        a = float(alpha_db_per_m(f, climate))
        checks[f"{int(f)}Hz"] = a
    return checks


def fit_climate(
    preset: Dict,
    distances: Sequence[float] = DISTANCES_M,
    n_freqs: int = 96,
    seed: int = 42,
    maxiter: int = 80,
    prefer_order: Sequence[str] = ("A", "B", "C"),
) -> FitResult:
    climate = Climate(
        temperature_c=preset["temperature_c"],
        relative_humidity_pct=preset["relative_humidity_pct"],
        pressure_kpa=preset.get("pressure_kpa", 101.325),
    )
    freqs = fit_freqs(n_freqs)
    distances = list(distances)
    targets = np.stack([path_loss_db(freqs, d, climate) for d in distances], axis=0)

    candidate_rmse: Dict[str, float] = {}
    candidate_models: Dict[str, AirAbsModel] = {}
    candidate_msgs: Dict[str, str] = {}

    for key in prefer_order:
        model, rmse, msg = _fit_one_candidate(
            key, freqs, distances, targets, seed=seed, maxiter=maxiter
        )
        candidate_rmse[key] = rmse
        candidate_models[key] = model
        candidate_msgs[key] = msg

    # Selection: try A, then B, then C if B still poor at 16 kHz / RMSE gap
    best_key = "A"
    best_rmse = candidate_rmse["A"]
    if candidate_rmse.get("B", 1e9) < best_rmse:
        best_key = "B"
        best_rmse = candidate_rmse["B"]
    # Prefer B over A even if close when B wins — already handled.
    # Take C only if it clearly beats B (and B exists)
    if "C" in candidate_rmse and "B" in candidate_rmse:
        if candidate_rmse["C"] < candidate_rmse["B"] - C_IMPROVEMENT_THRESHOLD:
            # Also check absolute error at 16 kHz for B vs ISO
            b_model = candidate_models["B"]
            alpha16 = float(alpha_db_per_m(16000.0, climate))
            h1_16 = float(b_model.h1_db_per_m(np.array([16000.0]))[0])
            err16 = abs((-alpha16) - h1_16)
            if err16 > 0.01 or candidate_rmse["C"] < best_rmse:
                best_key = "C"
                best_rmse = candidate_rmse["C"]
    elif "C" in candidate_rmse and candidate_rmse["C"] < best_rmse - C_IMPROVEMENT_THRESHOLD:
        best_key = "C"
        best_rmse = candidate_rmse["C"]

    # Default preference: if B is within 5% of best and better than A, keep B
    if "B" in candidate_rmse and best_key == "A":
        if candidate_rmse["B"] <= candidate_rmse["A"] * 1.05:
            best_key = "B"
            best_rmse = candidate_rmse["B"]

    winner = candidate_models[best_key]
    flat_r = flat_naive_rmse(freqs, distances, targets, climate)
    assumed = {
        "humidity_0.5_joint_db": assumed_shelf_rmse(freqs, distances, targets, 0.5),
        "humidity_1.0_joint_db": assumed_shelf_rmse(freqs, distances, targets, 1.0),
        "note": (
            "ASSUMED engine: gain = -0.15 * d * humidity, high-shelf corner "
            "~0.35*Nyquist @ 44.1 kHz (≈7718 Hz). Not fitted — compare only."
        ),
    }

    return FitResult(
        climate_id=preset["id"],
        label=preset["label"],
        honesty="FITTED_TO_ISO_9613_1",
        conditions={
            "temperature_c": climate.temperature_c,
            "relative_humidity_pct": climate.relative_humidity_pct,
            "pressure_kpa": climate.pressure_kpa,
        },
        candidate=best_key,
        model=winner.model,
        params=winner.params_dict(),
        joint_rmse_db=rmse_joint(winner, freqs, distances, targets, weighted=True),
        per_distance_rmse_db=rmse_per_distance(winner, freqs, distances, targets),
        candidate_rmse={k: float(v) for k, v in candidate_rmse.items()},
        flat_rmse_db=flat_r,
        assumed_rmse=assumed,
        freq_range_hz=FREQ_RANGE_HZ,
        distances_m=distances,
        success=True,
        message=f"winner={best_key} ({winner.model}); " + candidate_msgs[best_key],
        alpha_check=_alpha_sanity(climate),
        extras={
            "hf_weight": HF_WEIGHT,
            "hf_band_hz": list(HF_BAND_HZ),
            "all_candidate_params": {
                k: candidate_models[k].params_dict() for k in candidate_models
            },
        },
    )
