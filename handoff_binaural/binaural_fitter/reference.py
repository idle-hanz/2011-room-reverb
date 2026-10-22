"""Reference (pure Python) of the proposed binaural mic mapping, for Build and the tests.

Given head position/yaw, a binaural preset and an image (or source) position, returns what
each ear should get per image: delay (ms), level, grid node, colour record. This mirrors
BINAURAL_MODE_BRIEF.md; it is NOT wired into software/.

Engine conventions used (p5, VERIFIED): X right, Y up, Z forward, YAW_X_SIGN = +1,
c = 340 m/s, level = 1/r^2 (amplitude, engine lock).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .grid import ear_positions, engine_head_relative, lateral_angle, nearest_node

C_ENGINE = 340.0
PRESET_DIR = Path(__file__).resolve().parents[1] / "presets" / "binaural"
SUPPORTED_RATES = (44100, 48000)


def load_preset(preset_id: str, root: Path = PRESET_DIR) -> dict:
    return json.loads((root / f"{preset_id}.json").read_text())


def load_table(preset_id: str, sr: int, K: int | None = None, root: Path = PRESET_DIR) -> dict | None:
    if int(sr) not in SUPPORTED_RATES:
        return None
    name = f"{preset_id}.json" if (K is None or K == 6) else f"{preset_id}.K{K}.json"
    t = json.loads((root / "sos_tables" / str(int(sr)) / name).read_text())
    assert int(t["fit_fs"]) == int(sr)
    return t


def unsupported_rate_notice(sr) -> str:
    return (f"Binaural colour is OFF: the audio device runs at {int(sr) / 1000:g} kHz; "
            f"binaural HRTF tables exist for 44.1 and 48 kHz only.")


@dataclass
class EarTap:
    delay_ms: float
    level: float
    node: int
    record: int
    az: float
    el: float


def itd_correction_s(preset: dict, az: float, el: float) -> float:
    it = preset["itd"]
    th = math.degrees(float(lateral_angle(az, el)))
    return 1e-6 * float(np.interp(th, it["table_lateral_deg"], it["correction_us"]))


def image_to_ears(preset: dict, table: dict, head_xyz, head_yaw_deg: float, image_xyz,
                  level_from_head_centre: bool = True, c: float = C_ENGINE):
    """Per-ear tap for one image. Returns (left EarTap, right EarTap)."""
    s = float(preset["ear_spacing_m"])
    Lp, Rp = ear_positions(head_xyz, s, head_yaw_deg)
    dL = math.dist(Lp, image_xyz)
    dR = math.dist(Rp, image_xyz)
    az, el, r = engine_head_relative(head_xyz, image_xyz, head_yaw_deg)
    D = itd_correction_s(preset, az, el)
    tL = dL / c + max(-D, 0.0)
    tR = dR / c + max(D, 0.0)
    if level_from_head_centre:
        gL = gR = 1.0 / max(r, 1e-9) ** 2
    else:
        gL, gR = 1.0 / dL ** 2, 1.0 / dR ** 2
    n = int(nearest_node(table["nodes"], [az], [el])[0][0])
    recL = n
    recR = int(table["mirror"][n])  # R ear at node n = L record of mirror(n)
    return (EarTap(1e3 * tL, gL, n, recL, az, el), EarTap(1e3 * tR, gR, n, recR, az, el))


def record_sos(table: dict, record: int) -> np.ndarray:
    return np.asarray(table["sos"]["L"][record], dtype=np.float64)
