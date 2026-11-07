"""RBJ biquad designers shared by the early field and the surface cards.

Returns un-normalised (b0, b1, b2, a0, a1, a2). source_radiation.rbj_high_shelf
stays separate: it clamps f0 to 0.45*fs and returns a0-normalised coefficients.
"""

from __future__ import annotations

import math
from typing import Tuple

Biquad = Tuple[float, float, float, float, float, float]


def rbj_peaking(sr: float, f0: float, q: float, gain_db: float) -> Biquad:
    """RBJ peaking EQ. gain_db negative = cut."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q) if q > 1e-9 else 0.0
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cosw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha / A
    return b0, b1, b2, a0, a1, a2


def rbj_highshelf(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    """RBJ high-shelf. gain_db negative = HF cut."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw)
    a2 = (A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2


def rbj_lowshelf(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    """RBJ low-shelf."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw)
    a2 = (A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2
