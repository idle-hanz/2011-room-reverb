"""Exact third-octave centres, 1000 * 2^(k/3).

This is the generator behind surf_loop.THIRD and the Room-result panel.
The ISO preferred names (31.5, 63, …) live on surface_colour.THIRD_OCTAVE_HZ.
Those are rounded labels, not this generator, so they stay there.
The page twin is RRBands.
"""
from __future__ import annotations

import numpy as np


def exact_third_centres(i0: int, i1: int):
    """Centres for integer k in [i0, i1). Same expression as the old arange lines."""
    return 1000.0 * 2.0 ** (np.arange(i0, i1) / 3.0)
