"""dB and linear amplitude. 20 log10, so 6.0206 dB is about ×2.

The page twin is RRDb. Callers that clamp, mute, or format a fader stay
in the caller. This module is only the conversion.
"""
from __future__ import annotations

import math


def db_to_lin(db: float) -> float:
    """10^(dB/20)."""
    return 10.0 ** (float(db) / 20.0)


def lin_to_db(lin: float) -> float:
    """20 log10(amplitude). The caller rejects a non-positive value."""
    return 20.0 * math.log10(float(lin))
