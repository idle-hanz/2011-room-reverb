"""Fitter relative_db, loaded from mic_fitter/mic_fitter/model.py alone.

The package ``mic_fitter/__init__`` imports the fit module, which imports
SciPy. This loader never imports that package.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MOD = None


def repo_root() -> Path:
    """Directory that contains both software/ and mic_fitter/.

    Not Path(__file__).parents[1]: that is software/ when this file lives
    in software/mic_colour/.
    """
    here = Path(__file__).resolve()
    for p in here.parents:
        model = p / "mic_fitter" / "mic_fitter" / "model.py"
        if (p / "software").is_dir() and model.is_file():
            return p
    raise RuntimeError("repo root with software/ and mic_fitter/ not found")


def fitter_model():
    """The fitter model module. Executes model.py only."""
    global _MOD
    if _MOD is not None:
        return _MOD
    path = repo_root() / "mic_fitter" / "mic_fitter" / "model.py"
    spec = importlib.util.spec_from_file_location("mic_colour_fitter_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can see the module (Py 3.14).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _MOD = mod
    return mod


def _m():
    return fitter_model()


def relative_db(model, freqs, theta_deg):
    """H_db(θ, f) from the fitter. On-axis is 0 dB. The soft pole stays inside."""
    return model.relative_db(freqs, theta_deg)


def angle_weight(theta_deg, p):
    return _m().angle_weight(theta_deg, p)


def high_shelf_db(freqs, f0, depth_db, shelf_slope=4.0):
    return _m().high_shelf_db(freqs, f0, depth_db, shelf_slope)


def low_shelf_db(freqs, f_lo, depth_db, slope=None):
    if slope is None:
        return _m().low_shelf_db(freqs, f_lo, depth_db)
    return _m().low_shelf_db(freqs, f_lo, depth_db, slope)


def soft_one_pole_db(freqs, fc):
    return _m().soft_one_pole_db(freqs, fc)


def apply_hpf(db, freqs, hpf_hz, hpf_slope=12, engaged=False):
    return _m().apply_hpf(db, freqs, hpf_hz, hpf_slope, engaged)


def model_from_params(params: dict):
    names = _m().PARAM_NAMES
    return _m().MicShelfModel(**{k: float(params[k]) for k in names})


def param_names():
    return tuple(_m().PARAM_NAMES)


def model_name() -> str:
    return str(_m().MODEL_NAME)
