"""Yaw and look. One convention for Python and the page.

Yaw 0 looks toward +Z. look = (YAW_X_SIGN·sin yaw, 0, cos yaw).
Positive yaw rotates that look toward +X (the UI's right).
L capsule (smaller X) aims outward toward −X, so its yaw is negative
(ORTF −55°, MS −90°). R aims outward toward +X (ORTF +55°, MS +90°).

K1 (Idle, 28 Sep 2026): the old sign was −1, which aimed every
L-negative/R-positive preset inward. Stored yaw numbers did not change.
The page twin is RRLook in static/js/maths_look.js. Keep both equal.
"""
from __future__ import annotations

import math
from typing import Tuple

YAW_X_SIGN = 1.0
Vec3 = Tuple[float, float, float]


def look_vector(yaw_rad: float) -> Vec3:
    """Horizontal aim. Yaw 0 looks toward +Z. No tilt."""
    return (YAW_X_SIGN * math.sin(yaw_rad), 0.0, math.cos(yaw_rad))


def look_xz(yaw_rad: float) -> Tuple[float, float]:
    """The same aim with the height dropped. yaw 0 is +Z."""
    x, _y, z = look_vector(yaw_rad)
    return (x, z)
