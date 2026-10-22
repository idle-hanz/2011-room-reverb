"""Shaper-only alias and Room Crush EQ gain. Does not change product code.

Compares the shipped colour block (no compressor makeup) with a polyphase
FIR47 that matches round3 bench2.c. Writes nothing except stdout.
"""
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


def eq_mag_db(preset: str, freq: float) -> float:
    spec = bloom_dsp.design(
        {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True,
         "glue_colour": True},
        SR,
    )
    pack = bloom_dsp.pack_coeffs(spec)
    n = (len(pack) - 40) // 5
    w = 2.0 * math.pi * freq / SR
    z = complex(math.cos(w), math.sin(w))
    h = 1.0 + 0.0j
    for s in range(n):
        b0, b1, b2, a1, a2 = pack[40 + 5 * s: 45 + 5 * s]
        num = b0 + b1 / z + b2 / z / z
        den = 1.0 + a1 / z + a2 / z / z
        h *= num / den
    return 20.0 * math.log10(abs(h)), n, [round(v, 5) for v in pack[26:40]]


class Poly:
    """bench2.c up2/down2, K=12. Even taps are skipped. Centre path is 0.5."""

    def __init__(self) -> None:
        self.hs = []
        k_n = 12
        for k in range(k_n):
            n = 2 * k + 1
            s = math.sin(math.pi * n / 2.0) / (math.pi * n)
            i = (4 * k_n - 1) // 2 + n
            w = (
                0.42
                - 0.5 * math.cos(2.0 * math.pi * i / (4 * k_n - 2))
                + 0.08 * math.cos(4.0 * math.pi * i / (4 * k_n - 2))
            )
            self.hs.append(s * w)
        self.bu = [0.0] * (4 * k_n)
        self.pu = 0
        self.bd = [0.0] * (4 * k_n)
        self.pd = 0
        self.d0 = [0.0] * (2 * k_n)
        self.p0 = 0
        self.k = k_n

    def up(self, x: float):
        k = self.k
        self.bu[self.pu] = x
        self.bu[self.pu + 2 * k] = x
        b = self.pu + 1
        acc = 0.0
        for i in range(k):
            acc += self.hs[i] * (self.bu[b + k - 1 - i] + self.bu[b + k + i])
        self.pu = (self.pu + 1) % (2 * k)
        o0 = self.bu[(self.pu + k - 1) % (2 * k)]
        return o0, 2.0 * acc

    def down(self, e: float, od: float) -> float:
        k = self.k
        self.bd[self.pd] = od
        self.bd[self.pd + 2 * k] = od
        b = self.pd + 1
        acc = 0.0
        for i in range(k):
            acc += self.hs[i] * (self.bd[b + k - 1 - i] + self.bd[b + k + i])
        self.d0[self.p0] = e
        ed = self.d0[(self.p0 + k) % (2 * k)]
        self.p0 = (self.p0 + 1) % (2 * k)
        self.pd = (self.pd + 1) % (2 * k)
        return 0.5 * ed + acc


def shaper_only(preset: str, freq: float, level_db: float, kind: str) -> dict:
    body = {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True}
    if preset == "glue":
        body["glue_colour"] = True
    spec = bloom_dsp.design(body, SR)
    pack = bloom_dsp.pack_coeffs(spec)
    n = SR
    t = np.arange(n) / SR
    x = (10.0 ** (level_db / 20.0)) * np.sin(2.0 * math.pi * freq * t)
    st = bloom_dsp._Colour(pack)
    y = np.empty(n)
    if kind == "ship":
        for i, v in enumerate(x):
            y[i] = st.shape(float(v), 0.0, 1.0)
    elif kind == "poly":
        # Same distortion law as the shipped sample, polyphase FIR around it.
        poly = Poly()
        depth = pack[32]
        for i, v in enumerate(x):
            a, b = poly.up(float(v))
            y0 = st._dist(a, depth)
            y1 = st._dist(b, depth)
            dist = poly.down(y0, y1)
            y[i] = float(v) + dist
    else:
        raise SystemExit(kind)
    m = tone_alias(y, freq)
    return {
        "m1": round(m["m1_worst_alias_dbfs"], 2),
        "m2": round(m["m2_peak_below16k_dbfs"], 2),
        "fund": round(m["fund_dbfs"], 2),
        "k": m["m1_worst_k"],
        "f": m["m1_worst_f"],
    }


def main() -> None:
    for preset in ("natural", "glue", "room_crush", "nuke", "swell"):
        db, n, slots = eq_mag_db(preset, 1000.0)
        print("EQ1K", preset, "biquads", n, "mag_db", round(db, 4), "slots", slots, flush=True)
    rows = [
        ("natural", 9000, -12),
        ("natural", 13000, 0),
        ("natural", 17000, 0),
        ("glue", 9000, -12),
        ("glue", 17000, 0),
        ("room_crush", 13000, 0),
        ("room_crush", 9000, 0),
        ("nuke", 9000, -12),
        ("swell", 9000, 0),
        ("swell", 13000, -12),
    ]
    for preset, freq, level in rows:
        a = shaper_only(preset, freq, level, "ship")
        print("SHIP", preset, freq, level, a, flush=True)
        if preset in ("natural", "swell"):
            b = shaper_only(preset, freq, level, "poly")
            print("POLY", preset, freq, level, b, flush=True)


if __name__ == "__main__":
    main()
