"""Air absorption fitter — ISO 9613-1:1993 α(f) → distance-scalable musical filter."""

__version__ = "0.1.0"

from .iso9613 import alpha_db_per_m, Climate
from .model import (
    FREQ_RANGE_HZ,
    PRESET_SCHEMA,
    high_shelf_db,
    soft_one_pole_db,
    AirAbsModel,
    CANDIDATE_MODELS,
)
from .fit import FitResult, fit_climate, CLIMATE_PRESETS

__all__ = [
    "alpha_db_per_m",
    "Climate",
    "FREQ_RANGE_HZ",
    "PRESET_SCHEMA",
    "high_shelf_db",
    "soft_one_pole_db",
    "AirAbsModel",
    "CANDIDATE_MODELS",
    "FitResult",
    "fit_climate",
    "CLIMATE_PRESETS",
    "__version__",
]
