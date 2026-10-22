"""Tiny off-axis mic model v3: dual shelf (high+mild low) + soft one-pole.

Angle law unchanged: ½(1−cosθ)^p.
Shelves do the musical colour work; soft LP is a light residual darkener.
Optional manufacturer HPF is schema-only (not fitted from Zenodo).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

import numpy as np

# 9 free scalars — shelves-led colour + soft residual LP + angle exponent.
# Prefer ≤9; all kept with modest DE maxiter bump + lp_mix / depth_lo priors.
PARAM_NAMES: Tuple[str, ...] = (
    "f0",            # high-shelf corner Hz
    "depth_max_db",  # max high-shelf depth (typically ≤0) at 180°
    "shelf_slope",   # high-shelf steepness in log10-freq (was fixed ≈4)
    "f_lo",          # mild low-shelf corner Hz
    "depth_lo_db",   # mild low-shelf depth at 180° (soft prior → 0)
    "res_hz",        # soft one-pole knee Hz (on-axis reference)
    "lp_mix",        # 0..1 blend of soft LP into off-axis path (prior → ~0.25)
    "fc_floor",      # lowest effective LP cutoff Hz at extreme off-axis
    "p",             # angle-law exponent in ½(1−cosθ)^p
)

# (lo, hi) bounds for optimiser
PARAM_BOUNDS: Dict[str, Tuple[float, float]] = {
    "f0": (200.0, 12000.0),
    "depth_max_db": (-24.0, 0.0),
    "shelf_slope": (0.6, 12.0),
    "f_lo": (40.0, 400.0),
    "depth_lo_db": (-9.0, 9.0),
    "res_hz": (1500.0, 16000.0),
    "lp_mix": (0.0, 1.0),
    "fc_floor": (800.0, 8000.0),
    "p": (0.6, 3.5),
}

# Fixed mild steepness for the low shelf (keeps param count at 9).
# High shelf uses free `shelf_slope`; low shelf stays gentle.
LOW_SHELF_SLOPE: float = 2.5

MODEL_NAME = "dual_shelf_plus_soft_one_pole"
PRESET_SCHEMA = "mic_fitter.preset.v3"
FREQ_RANGE_HZ = (20.0, 16000.0)


def angle_weight(theta_deg: np.ndarray | float, p: float) -> np.ndarray:
    """½(1 − cos θ)^p with θ in degrees. 0 at on-axis, →1 toward 180°."""
    th = np.asarray(theta_deg, dtype=float)
    # fold to [0, 180] for magnitude symmetry of typical cardioids
    th = np.abs(((th + 180.0) % 360.0) - 180.0)
    cos_t = np.cos(np.deg2rad(th))
    w = 0.5 * (1.0 - cos_t)
    w = np.clip(w, 0.0, 1.0) ** float(p)
    return w


def high_shelf_db(
    freqs: np.ndarray,
    f0: float,
    depth_db: float,
    shelf_slope: float = 4.0,
) -> np.ndarray:
    """Smooth high-shelf gain in dB.

    `shelf_slope` is the sigmoid steepness in log10-frequency units:
    blend = 1 / (1 + exp(-shelf_slope * log10(f/f0))).
    Overnight v1 used a fixed slope of 4. Larger → sharper transition.
    """
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(f0, 1.0))
    blend = 1.0 / (1.0 + np.exp(-float(shelf_slope) * x))
    return depth_db * blend


def low_shelf_db(
    freqs: np.ndarray,
    f_lo: float,
    depth_db: float,
    slope: float = LOW_SHELF_SLOPE,
) -> np.ndarray:
    """Mild low-shelf gain in dB (active below f_lo).

    blend → 1 well below f_lo, → 0 well above. Same log-sigmoid family as
    the high shelf but mirrored.
    """
    f = np.asarray(freqs, dtype=float)
    x = np.log10(np.maximum(f, 1.0) / max(f_lo, 1.0))
    blend = 1.0 / (1.0 + np.exp(+float(slope) * x))
    return depth_db * blend


def soft_one_pole_db(freqs: np.ndarray, fc) -> np.ndarray:
    """Soft one-pole low-pass magnitude in dB (approx |1 / (1 + j f/fc)|).

    `fc` may be scalar or broadcastable to `freqs` (e.g. (n_theta, 1)).
    """
    f = np.asarray(freqs, dtype=float)
    fc_arr = np.asarray(fc, dtype=float)
    fc_arr = np.maximum(fc_arr, 1.0)
    mag = 1.0 / np.sqrt(1.0 + (f / fc_arr) ** 2)
    return 20.0 * np.log10(np.maximum(mag, 1e-12))


@dataclass
class MicShelfModel:
    """Relative off-axis response H(θ)/H(0°) in dB vs frequency (v2 dual-shelf)."""

    f0: float = 4000.0
    depth_max_db: float = -12.0
    shelf_slope: float = 4.0
    f_lo: float = 120.0
    depth_lo_db: float = 0.0
    res_hz: float = 6000.0
    lp_mix: float = 0.25
    fc_floor: float = 2500.0
    p: float = 1.2

    def params_dict(self) -> Dict[str, float]:
        return {k: float(getattr(self, k)) for k in PARAM_NAMES}

    @classmethod
    def from_vector(cls, x: Sequence[float]) -> "MicShelfModel":
        return cls(**{n: float(v) for n, v in zip(PARAM_NAMES, x)})

    def to_vector(self) -> np.ndarray:
        return np.array([getattr(self, n) for n in PARAM_NAMES], dtype=float)

    def relative_db(
        self,
        freqs: np.ndarray,
        theta_deg: float | np.ndarray,
    ) -> np.ndarray:
        """
        Model relative response in dB.

        Shape: if theta is scalar → (n_freq,); if array → (n_theta, n_freq).
        On-axis (θ=0) is identically 0 dB.
        """
        freqs = np.asarray(freqs, dtype=float)
        th = np.asarray(theta_deg, dtype=float)
        scalar = th.ndim == 0
        if scalar:
            th = th.reshape(1)

        w = angle_weight(th, self.p)  # (n_theta,)
        wcol = w[:, None]

        # High shelf: unit curve × angle-scaled depth
        hs_unit = high_shelf_db(freqs[None, :], self.f0, 1.0, self.shelf_slope)
        shelf_hi = hs_unit * (self.depth_max_db * wcol)

        # Mild low shelf: same angle weighting
        ls_unit = low_shelf_db(freqs[None, :], self.f_lo, 1.0)
        shelf_lo = ls_unit * (self.depth_lo_db * wcol)

        # Soft one-pole residual (encouraged mild via prior on lp_mix)
        fc = self.res_hz + (self.fc_floor - self.res_hz) * wcol
        lp = soft_one_pole_db(freqs[None, :], fc)
        lp0 = soft_one_pole_db(freqs, self.res_hz)
        lp_rel = (lp - lp0[None, :]) * self.lp_mix * wcol

        out = shelf_hi + shelf_lo + lp_rel
        if scalar:
            return out[0]
        return out


def bounds_array() -> Tuple[np.ndarray, np.ndarray]:
    lo = np.array([PARAM_BOUNDS[n][0] for n in PARAM_NAMES], dtype=float)
    hi = np.array([PARAM_BOUNDS[n][1] for n in PARAM_NAMES], dtype=float)
    return lo, hi


# ---------------------------------------------------------------------------
# Optional manufacturer HPF (NOT fitted from Zenodo — filters out of IR fit)
# ---------------------------------------------------------------------------

HPF_SLOPES = (6, 12, 18)  # dB/oct

# Documented manufacturer defaults (switchable in UI; plots default filter-out).
# Values are representative of common published switch positions — not fitted.
MANUFACTURER_HPF_DEFAULTS = {
    "NeumannU87AiCardioid": {"hpf_hz": 140.0, "hpf_slope": 12, "note": "U87 Ai LF roll-off switch ~140 Hz"},
    "NeumannU87AiOmni": {"hpf_hz": 140.0, "hpf_slope": 12, "note": "U87 Ai LF roll-off switch ~140 Hz"},
    "NeumannU87AiBidirect": {"hpf_hz": 140.0, "hpf_slope": 12, "note": "U87 Ai LF roll-off switch ~140 Hz"},
    "AKGC414Cardioid": {"hpf_hz": 160.0, "hpf_slope": 12, "note": "C414 XLII bass-cut options ~40/80/160 Hz; default doc 160"},
    "AKGC414Omni": {"hpf_hz": 160.0, "hpf_slope": 12, "note": "C414 XLII bass-cut options ~40/80/160 Hz"},
    "AKGC414Hyper": {"hpf_hz": 160.0, "hpf_slope": 12, "note": "C414 XLII bass-cut options ~40/80/160 Hz"},
    "AKGC414Bidirect": {"hpf_hz": 160.0, "hpf_slope": 12, "note": "C414 XLII bass-cut options ~40/80/160 Hz"},
    "ShureSM57": {"hpf_hz": None, "hpf_slope": 12, "note": "SM57 — no switchable HPF"},
    "ShureSM58": {"hpf_hz": None, "hpf_slope": 12, "note": "SM58 — no switchable HPF"},
    "ElectroVoiceRE20": {"hpf_hz": None, "hpf_slope": 12, "note": "RE20 Variable-D; no classic HPF switch in this schema"},
    "SennheiserMD441": {"hpf_hz": None, "hpf_slope": 12, "note": "MD 441 — brilliance/presence switches, not modelled as HPF here"},
    "RoyerR121": {"hpf_hz": None, "hpf_slope": 12, "note": "R-121 ribbon — no HPF switch"},
    "Coles4038": {"hpf_hz": None, "hpf_slope": 12, "note": "4038 ribbon — no HPF switch"},
    "DPA4006": {"hpf_hz": None, "hpf_slope": 12, "note": "4006A grid options; no fixed HPF in this schema"},
    "SchoepsCMC5UCardioid": {"hpf_hz": None, "hpf_slope": 12, "note": "CMC5+MK4 — optional CUT filters external; none in capsule IR"},
    "SchoepsCMC5UOmni": {"hpf_hz": None, "hpf_slope": 12, "note": "CMC5 omni — optional CUT external"},
    "SchoepsCMC5UBidirect": {"hpf_hz": None, "hpf_slope": 12, "note": "CMC5 fig-8 — optional CUT external"},
    "RodeNT2ACardioid": {"hpf_hz": 80.0, "hpf_slope": 12, "note": "NT2-A HPF switch flat/40/80 Hz; default doc 80"},
    "RodeNT2AOmni": {"hpf_hz": 80.0, "hpf_slope": 12, "note": "NT2-A HPF switch flat/40/80 Hz; default doc 80"},
    "RodeNT2ABidirect": {"hpf_hz": 80.0, "hpf_slope": 12, "note": "NT2-A HPF switch flat/40/80 Hz; default doc 80"},
}


def default_hpf_switches(mic_id: str) -> Dict:
    """Schema switches block; hpf_engaged defaults False (plots filter-out)."""
    meta = MANUFACTURER_HPF_DEFAULTS.get(mic_id, {"hpf_hz": None, "hpf_slope": 12, "note": ""})
    return {
        "hpf_hz": meta.get("hpf_hz"),
        "hpf_slope": int(meta.get("hpf_slope") or 12),
        "hpf_engaged": False,
        "manufacturer_note": meta.get("note", ""),
    }


def apply_hpf(
    db: np.ndarray,
    freqs: np.ndarray,
    hpf_hz: float | None,
    hpf_slope: int = 12,
    engaged: bool = False,
) -> np.ndarray:
    """Apply optional Butterworth-ish HPF magnitude in dB for future UI.

    Does nothing when engaged is False or hpf_hz is None.
    Slope must be 6, 12, or 18 dB/oct (1st / 2nd / 3rd order approx).
    Shape of `db` is preserved (…, n_freq) broadcasting over leading dims.
    """
    out = np.asarray(db, dtype=float).copy()
    if not engaged or hpf_hz is None or float(hpf_hz) <= 0:
        return out
    order = {6: 1, 12: 2, 18: 3}.get(int(hpf_slope), 2)
    f = np.asarray(freqs, dtype=float)
    # |H| = 1 / sqrt(1 + (fc/f)^{2n})  — high-pass
    ratio = (float(hpf_hz) / np.maximum(f, 1e-6)) ** (2 * order)
    mag_db = 20.0 * np.log10(np.maximum(1.0 / np.sqrt(1.0 + ratio), 1e-12))
    return out + mag_db
