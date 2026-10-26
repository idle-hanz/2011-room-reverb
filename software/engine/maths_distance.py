"""Software distance law. The page twin is RRDistance.

Software amplitude is 1/r (Idle, 2026-10-10). The Structure Air Abs graph
is still 1/r² (shot 256: Dis×Dis then 1/x). Idle chose 1/r for the whole
software path, Play and Render: AGC balance, close mics too loud, and the
physical pressure law (about 6 dB per doubling). Distances 1/x stays 1/340
(delay), not this gain.
"""
from __future__ import annotations


def geometric_level(distance: float) -> float:
    """Amplitude 1/r. A non-positive distance is silence."""
    if distance <= 1e-9:
        return 0.0
    return 1.0 / distance
