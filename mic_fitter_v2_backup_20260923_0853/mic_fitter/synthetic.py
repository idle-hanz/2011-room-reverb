"""ASSUMED DEMO DATA — synthetic off-axis curves mimicking published shapes.

These are NOT measured IRs. They approximate manufacturer / literature
off-axis behaviour: near-omni LF → directional HF shelf + mild LP darkening.
Clearly labelled ASSUMED everywhere they are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from .model import FREQ_RANGE_HZ, MicShelfModel, angle_weight


@dataclass
class SyntheticMicSpec:
    id: str
    display_name: str
    family: str  # dynamic_cardioid | sdc_cardioid | ldc_cardioid | fig8_ribbon
    honesty: str  # always ASSUMED for this module
    # "true" generator params (what we pretend the mic does) — then fit recovers them
    truth: MicShelfModel
    # optional polar-pattern level tilt (cardioid-ish) added to HF-weighted path
    pattern_null_db: float = -20.0  # level at 180° relative (broadband-ish)


def default_proxy_mics() -> List[SyntheticMicSpec]:
    """Six proxy mics spanning common studio types (v2 dual-shelf truths)."""
    return [
        SyntheticMicSpec(
            id="proxy_dynamic_cardioid",
            display_name="ASSUMED Dynamic Cardioid (SM57-ish)",
            family="dynamic_cardioid",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=3500.0, depth_max_db=-14.0, shelf_slope=4.5,
                f_lo=100.0, depth_lo_db=-1.5,
                res_hz=5500.0, lp_mix=0.30, fc_floor=2200.0, p=1.35,
            ),
            pattern_null_db=-22.0,
        ),
        SyntheticMicSpec(
            id="proxy_sdc_cardioid",
            display_name="ASSUMED SDC Cardioid (KM184-ish)",
            family="sdc_cardioid",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=5500.0, depth_max_db=-10.0, shelf_slope=5.0,
                f_lo=80.0, depth_lo_db=0.5,
                res_hz=9000.0, lp_mix=0.20, fc_floor=4000.0, p=1.1,
            ),
            pattern_null_db=-18.0,
        ),
        SyntheticMicSpec(
            id="proxy_ldc_cardioid",
            display_name="ASSUMED LDC Cardioid (U87-card-ish)",
            family="ldc_cardioid",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=4200.0, depth_max_db=-11.5, shelf_slope=4.0,
                f_lo=90.0, depth_lo_db=-0.8,
                res_hz=7000.0, lp_mix=0.25, fc_floor=2800.0, p=1.25,
            ),
            pattern_null_db=-16.0,
        ),
        SyntheticMicSpec(
            id="proxy_fig8_ribbon",
            display_name="ASSUMED Fig-8 Ribbon (Royer-ish)",
            family="fig8_ribbon",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=2800.0, depth_max_db=-8.0, shelf_slope=3.5,
                f_lo=70.0, depth_lo_db=1.0,
                res_hz=4500.0, lp_mix=0.35, fc_floor=1800.0, p=0.95,
            ),
            pattern_null_db=-6.0,
        ),
        SyntheticMicSpec(
            id="proxy_supercardioid_dynamic",
            display_name="ASSUMED Supercardioid Dynamic (Beta58-ish)",
            family="supercardioid",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=3800.0, depth_max_db=-16.0, shelf_slope=4.8,
                f_lo=110.0, depth_lo_db=-2.0,
                res_hz=6000.0, lp_mix=0.32, fc_floor=2000.0, p=1.55,
            ),
            pattern_null_db=-26.0,
        ),
        SyntheticMicSpec(
            id="proxy_omni_sdc",
            display_name="ASSUMED Omni SDC (measurement-ish)",
            family="omni",
            honesty="ASSUMED",
            truth=MicShelfModel(
                f0=8000.0, depth_max_db=-3.5, shelf_slope=3.0,
                f_lo=60.0, depth_lo_db=0.0,
                res_hz=12000.0, lp_mix=0.12, fc_floor=7000.0, p=1.0,
            ),
            pattern_null_db=-4.0,
        ),
    ]


def log_freqs(
    n: int = 64,
    f_lo: float = FREQ_RANGE_HZ[0],
    f_hi: float = FREQ_RANGE_HZ[1],
) -> np.ndarray:
    """Log-spaced analysis frequencies (v2 default: 20 Hz – 16 kHz)."""
    return np.geomspace(f_lo, f_hi, n)


def fig8_side_weight(theta_deg: np.ndarray) -> np.ndarray:
    """Extra HF darkening toward ±90° for fig-8 demo (ASSUMED)."""
    th = np.abs(((np.asarray(theta_deg, dtype=float) + 180.0) % 360.0) - 180.0)
    return np.sin(np.deg2rad(th)) ** 2


def generate_relative_db(
    spec: SyntheticMicSpec,
    freqs: np.ndarray,
    angles_deg: np.ndarray,
    noise_db: float = 0.15,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """
    Build ASSUMED relative magnitude H(θ)/H(0°) in dB.

    Returns array (n_angles, n_freqs).
    """
    rng = rng or np.random.default_rng(0)
    m = spec.truth
    base = m.relative_db(freqs, angles_deg)  # (n_th, n_f)

    # Mild pattern-level contribution that grows with frequency (directional HF)
    w = angle_weight(angles_deg, max(m.p * 0.85, 0.5))
    f_blend = 1.0 / (1.0 + np.exp(-3.0 * np.log10(np.maximum(freqs, 1.0) / 1500.0)))
    pattern = (spec.pattern_null_db * w[:, None]) * f_blend[None, :]

    if spec.family == "fig8_ribbon":
        side = fig8_side_weight(angles_deg)[:, None]
        pattern = pattern * 0.35 + (-18.0 * side) * f_blend[None, :]
        rear = (np.abs(angles_deg) > 135).astype(float)[:, None]
        pattern = pattern * (1.0 - 0.55 * rear)

    out = base + pattern
    if noise_db > 0:
        out = out + rng.normal(0.0, noise_db, size=out.shape)
    for i, a in enumerate(angles_deg):
        if abs(float(a)) < 1e-6:
            out[i, :] = 0.0
    return out


def build_dataset(
    angles_deg: np.ndarray | None = None,
    n_freq: int = 64,
    holdout_angles: List[float] | None = None,
) -> Dict[str, dict]:
    """
    Build train/holdout magnitude tables for all proxy mics.

    holdout defaults: 45°, 135° (typical mid/off angles).
    """
    if angles_deg is None:
        angles_deg = np.array([0, 15, 30, 45, 60, 90, 120, 135, 150, 180], dtype=float)
    if holdout_angles is None:
        holdout_angles = [45.0, 135.0]

    freqs = log_freqs(n_freq)
    hold = set(float(a) for a in holdout_angles)
    train_angles = np.array([a for a in angles_deg if float(a) not in hold], dtype=float)
    hold_angles = np.array([a for a in angles_deg if float(a) in hold], dtype=float)

    out: Dict[str, dict] = {}
    for i, spec in enumerate(default_proxy_mics()):
        rng = np.random.default_rng(1000 + i)
        all_db = generate_relative_db(spec, freqs, angles_deg, rng=rng)
        ang_to_idx = {float(a): j for j, a in enumerate(angles_deg)}
        train_db = np.stack([all_db[ang_to_idx[float(a)]] for a in train_angles])
        hold_db = (
            np.stack([all_db[ang_to_idx[float(a)]] for a in hold_angles])
            if len(hold_angles)
            else np.zeros((0, n_freq))
        )
        out[spec.id] = {
            "spec": spec,
            "freqs": freqs,
            "angles_all": angles_deg,
            "db_all": all_db,
            "train_angles": train_angles,
            "train_db": train_db,
            "holdout_angles": hold_angles,
            "holdout_db": hold_db,
            "honesty": "ASSUMED",
            "source": "synthetic_proxy_curves_mimicking_published_off_axis_shapes",
        }
    return out
