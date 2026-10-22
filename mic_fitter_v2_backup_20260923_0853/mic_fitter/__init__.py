"""Mic off-axis magnitude fitter — dual shelf + soft one-pole (v2)."""

__version__ = "0.2.0"

from .model import (
    FREQ_RANGE_HZ,
    MODEL_NAME,
    PARAM_BOUNDS,
    PARAM_NAMES,
    PRESET_SCHEMA,
    MicShelfModel,
)
from .fit import FitResult, fit_mic

__all__ = [
    "MicShelfModel",
    "PARAM_NAMES",
    "PARAM_BOUNDS",
    "FREQ_RANGE_HZ",
    "MODEL_NAME",
    "PRESET_SCHEMA",
    "fit_mic",
    "FitResult",
    "__version__",
]
