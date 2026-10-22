"""Play peaking stays passive after the C b2 restore. No numerator scale.

The blob stores the float64 design as float32. live_stereo.c then sets
pb2 = 1 + pa1 + pa2 - pb0 - pb1 in double, which is unity DC for a cut-only
peaking filter. This checks that restored filter on the same grid the load
path uses. It does not scale the numerator and it does not lift Dffs.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "engine"
for p in (ROOT, ENGINE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import fdn  # noqa: E402
from early_field import SPEED_OF_SOUND_M_S  # noqa: E402

DEPTH = 1.5


def _f32(v: float) -> float:
    return float(np.float32(v))


def _grid(sr: float) -> np.ndarray:
    nyq = 0.5 * float(sr)
    hi = min(20000.0, nyq)
    low = np.linspace(0.01, 20.0, 400)
    dc = np.array([0.0], dtype=np.float64)
    sweep = np.geomspace(20.0, hi, 64)
    pts = np.concatenate([dc, low, sweep, np.array([nyq], dtype=np.float64)])
    pts = pts[(pts >= 0.0) & (pts <= nyq + 1e-9)]
    return np.unique(pts)


def _mag(b0, b1, b2, a1, a2, freq, sr) -> np.ndarray:
    w = 2.0 * math.pi * np.asarray(freq, dtype=np.float64) / float(sr)
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    num = b0 + b1 * z1 + b2 * z2
    den = 1.0 + a1 * z1 + a2 * z2
    return np.abs(num / den)


def _restored(bank, sr: float):
    """Float32 pack, then the C restore of b2. Returns (raw_dc, restored_peak)."""
    b0 = _f32(bank["b0"])
    b1 = _f32(bank["b1"])
    b2 = _f32(bank["b2"])
    a1 = _f32(bank["a1"])
    a2 = _f32(bank["a2"])
    raw_dc = float(_mag(b0, b1, b2, a1, a2, [0.0], sr)[0])
    b2r = 1.0 + a1 + a2 - b0 - b1
    peak = float(np.max(_mag(b0, b1, b2r, a1, a2, _grid(sr), sr)))
    return raw_dc, peak, b2r


def test_restored_b2_is_passive_on_every_bank():
    rooms = {
        "default": (6.0, 3.0, 8.0),
        "hall": (57.0, 34.2, 97.0),
        "hall_preset": (57.0, 34.241, 97.0),
    }
    for name, room in rooms.items():
        for sr in (44100, 48000):
            banks = fdn.live_peaking_banks(room, sr, SPEED_OF_SOUND_M_S, DEPTH)
            assert len(banks) == 3
            for ax, bank in zip(("X", "Y", "Z"), banks):
                assert bank["on"] is True
                raw_dc, peak, _b2 = _restored(bank, sr)
                assert peak <= 1.0 + 1e-9, f"{name} {sr} {ax} |H| {peak} (raw DC {raw_dc})"


def test_box_dc_figures():
    """Hall X at 48 kHz and default Z at 44.1 kHz are the posted float32 misses."""
    hall = fdn.live_peaking_banks((57.0, 34.2, 97.0), 48000, SPEED_OF_SOUND_M_S, DEPTH)
    raw_x, peak_x, _ = _restored(hall[0], 48000)
    assert raw_x > 1.4
    assert abs(peak_x - 1.0) < 1e-9 or peak_x <= 1.0 + 1e-9
    studio = fdn.live_peaking_banks((6.0, 3.0, 8.0), 44100, SPEED_OF_SOUND_M_S, DEPTH)
    raw_z, peak_z, _ = _restored(studio[2], 44100)
    assert raw_z > 1.0
    assert peak_z <= 1.0 + 1e-9


def test_no_diffusion_floor_and_scale_uncapped():
    assert not hasattr(fdn, "PLAY_DFFS_FLOOR")
    assert not hasattr(fdn, "play_dffs_from_taps")
    small = fdn.diffusion_scale_from_room((6.0, 3.0, 8.0))
    hall = fdn.diffusion_scale_from_room((57.0, 34.241, 97.0))
    assert hall > small
    assert abs(hall - 202.633) < 2.0
