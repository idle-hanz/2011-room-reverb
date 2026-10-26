"""First-order polar a and the desk slider map.

a=1 omni, a=0.5 cardioid, a=SUPER_A supercardioid. ASSUMED continuum.
A hypercardioid name is HYPER_A (0.25), so 0° / 90° / 180° read 1 / 0.25 / −0.5.
polar 1 with no hyper name stays SUPER_A (0.37). The page twin is RRPattern.
"""
from __future__ import annotations

import math

SUPER_A = 0.37
HYPER_A = 0.25


def _hyper_name(pattern) -> bool:
    if pattern is None:
        return False
    p = str(pattern).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    return p in ("hypercardioid", "hyper")


def polar_a_from_slider(polar: float, pattern=None) -> float:
    """Map Omni(0) → Cardioid(0.5) → Super(1) onto first-order a.

    a=1 omni, a=0.5 cardioid, a=SUPER_A supercardioid. ASSUMED continuum.
    A hypercardioid name is HYPER_A. polar 1 with no name stays SUPER_A.
    """
    if _hyper_name(pattern):
        return HYPER_A
    d = max(0.0, min(1.0, float(polar)))
    if d <= 0.5:
        return 1.0 - d
    return 0.5 - (d - 0.5) * (0.5 - SUPER_A) / 0.5


def first_order_gain(theta: float, a: float, *, signed: bool = True) -> float:
    """a + (1−a) cos θ. Unsigned gain is the absolute value."""
    g = float(a) + (1.0 - float(a)) * math.cos(theta)
    if not signed:
        return abs(g)
    return g
