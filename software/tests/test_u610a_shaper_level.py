"""610-A shaper level at Drive 0. PC0 ledger linears, PC1 pack."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW / "engine")]

import bloom_dsp as B  # noqa: E402

# Fit shaper input at 1 kHz. Not vc, and not the raw H1 level.
FIT_LEVEL = 161.466931945
SR = 48000.0


def _h1_mag(row) -> float:
    w = 2.0 * math.pi * 1000.0 / SR
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    b0, b1, b2, a1, a2 = row[15:20]
    return abs((b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2))


def test_u610a_drive0_shaper_level_and_unity():
    spec = {"pre": "u610a", "sr": SR, "pre_drive_db": 0.0}
    row = B.pack_pre(spec)
    play = B.pack_pre(spec, play=True)
    assert abs(_h1_mag(row) - FIT_LEVEL) < 1e-6
    assert abs(_h1_mag(play) - FIT_LEVEL) < 1e-6

    n = int(SR)
    t = np.arange(n, dtype=np.float64) / SR
    amp = 1.0e-6
    x = amp * np.sin(2.0 * math.pi * 1000.0 * t)
    y = B._pre_bus(x, row)
    tail = slice(n // 2, None)
    gain = float(np.sqrt(np.mean(y[tail] ** 2)) / np.sqrt(np.mean(x[tail] ** 2)))
    db = 20.0 * math.log10(gain)
    assert abs(db) < 0.01
