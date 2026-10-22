"""Settled gain vs alias. Does not change product code."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
R3 = ROOT / "handoff_build_support_2" / "roadmap" / "bloom" / "uad" / "round3"
sys.path[:0] = [str(SW), str(SW / "engine"), str(R3 / "scripts")]

import bloom_dsp  # noqa: E402
from alias import tone_alias  # noqa: E402

SR = 48000


def tone(freq: float, level_db: float, n: int = SR) -> np.ndarray:
    t = np.arange(n) / SR
    return (10.0 ** (level_db / 20.0)) * np.sin(2.0 * math.pi * freq * t)


def measure(preset: str, freq: float, level: float) -> None:
    body = {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True}
    if preset == "glue":
        body["glue_colour"] = True
    spec = bloom_dsp.design(body, SR)
    pack = bloom_dsp.pack_coeffs(spec)
    x = tone(freq, level)
    g, gr = bloom_dsp._gain_env(x, spec)
    g_db = 20.0 * np.log10(np.maximum(g[-SR // 2 :], 1e-12))
    gr_s = gr[-SR // 2 :]
    # attenuation only, the prototype's g = 10^(-GR/20), then the shipped shaper
    att = 10.0 ** (-np.maximum(gr, 0.0) / 20.0)
    st = bloom_dsp._Colour(pack)
    y_att = np.empty_like(x)
    y_ship = np.empty_like(x)
    swell = pack[38] > 0.5 and pack[26] > 0.5
    for i, v in enumerate(x):
        if swell:
            y_att[i] = st.shape(float(v), float(gr[i]), 1.0) * float(att[i])
        else:
            y_att[i] = st.shape(float(v) * float(att[i]), float(gr[i]), 1.0)
    st2 = bloom_dsp._Colour(pack)
    for i, v in enumerate(x):
        if swell:
            z = st2.shape(float(v), float(gr[i]), 1.0)
            y_ship[i] = z * float(g[i])
        else:
            z = float(v) * float(g[i])
            y_ship[i] = st2.shape(z, float(gr[i]), 1.0)
    a = tone_alias(y_att, freq)
    b = tone_alias(y_ship, freq)
    print(
        preset, freq, level,
        "gr", round(float(np.median(gr_s)), 2),
        "g_db", round(float(np.median(g_db)), 2),
        "att_m1", round(float(a["m1_worst_alias_dbfs"]), 1),
        "ship_m1", round(float(b["m1_worst_alias_dbfs"]), 1),
        "ship_fund", round(float(b["fund_dbfs"]), 1),
        flush=True,
    )


def main() -> None:
    rows = [
        ("natural", 13000, 0),
        ("natural", 9000, -12),
        ("natural", 7000, -24),
        ("room_crush", 13000, 0),
        ("room_crush", 13000, -12),
        ("room_crush", 9000, 0),
        ("glue", 17000, 0),
        ("glue", 9000, -12),
        ("nuke", 9000, -12),
        ("nuke", 13000, 0),
        ("swell", 9000, 0),
        ("swell", 13000, -12),
    ]
    for row in rows:
        measure(*row)


if __name__ == "__main__":
    main()
