"""610-A shaper level at Drive 0. PC1 pack, then the PC3 −39 dB trim."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW / "engine")]

import bloom_dsp as B  # noqa: E402

# Fit shaper level at 1 kHz, before the PC3 trim. Not vc, and not u after /vc.
FIT_LEVEL = 161.466931945
TRIM = 10.0 ** (-39.0 / 20.0)
# PC2 model THD at −57 dBFS, harmonics 2–15, settled half, exact-bin rfft.
PC2_THD_M57 = 40.1063
SR = 48000.0


def _h1_mag(row) -> float:
    w = 2.0 * math.pi * 1000.0 / SR
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    b0, b1, b2, a1, a2 = row[15:20]
    return abs((b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2))


def _thd_h2_h15(y: np.ndarray) -> float:
    """Settled half, exact-bin rfft, harmonics 2–15, no window."""
    z = np.asarray(y[len(y) // 2 :], dtype=np.float64)
    per = int(SR // 1000.0)
    n = (z.size // per) * per
    z = z[:n]
    spec = np.fft.rfft(z)
    scale = 2.0 / n

    def amp(k: int) -> float:
        return abs(spec[k * 1000 * n // int(SR)]) * scale

    fundamental = amp(1)
    harm = sum(amp(k) ** 2 for k in range(2, 16))
    return 100.0 * math.sqrt(harm) / fundamental


def test_u610a_drive0_shaper_level_and_unity():
    spec = {"pre": "u610a", "sr": SR, "pre_drive_db": 0.0}
    row = B.pack_pre(spec)
    play = B.pack_pre(spec, play=True)
    expect = FIT_LEVEL * TRIM
    assert abs(_h1_mag(row) - expect) < 1e-6
    assert abs(_h1_mag(play) - expect) < 1e-6

    n = int(SR)
    t = np.arange(n, dtype=np.float64) / SR
    quiet = 1.0e-6 * np.sin(2.0 * math.pi * 1000.0 * t)
    y = B._pre_bus(quiet, row)
    tail = slice(n // 2, None)
    gain = float(np.sqrt(np.mean(y[tail] ** 2)) / np.sqrt(np.mean(quiet[tail] ** 2)))
    db = 20.0 * math.log10(gain)
    assert abs(db) < 0.01

    hot = (10.0 ** (-18.0 / 20.0)) * np.sin(2.0 * math.pi * 1000.0 * t)
    thd = _thd_h2_h15(B._pre_bus(hot, row))
    assert abs(thd / PC2_THD_M57 - 1.0) < 0.02
