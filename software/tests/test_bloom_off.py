"""Bloom off stays off the live dict. Amount 0 is not a 0 dB multiply."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import bloom_dsp as B  # noqa: E402

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"


def _md5(body: dict) -> tuple[str, bool]:
    p = A.params_from_body(body)
    blob = A.live_fdn_params(p)
    digest = hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()
    return digest, "bloom" in blob


def test_absent_matches_explicit_off():
    empty, empty_on = _md5({})
    assert empty == EMPTY
    assert empty_on is False
    off, off_on = _md5({
        "bloom_preset": "swell",
        "bloom_amount": 0,
        "bloom_colour": True,
        "glue_colour": True,
        "pre_colour": "off",
        "pre_drive_db": 6,
        "predelay_ms": 0,
    })
    assert off == EMPTY
    assert off_on is False
    assert B.design({"bloom_amount": 0, "bloom_colour": True, "pre_drive_db": 3}, 48000) is None


def test_nuke_tone_gr_is_finite_and_clamped():
    c = B.design({"bloom_amount": 100, "bloom_preset": "nuke"}, 48000)
    assert c is not None
    assert c["max_duck_db"] == 24.0
    st = B.DetState()
    sr = 48000
    gr_max = 0.0
    for n in range(sr // 2):
        x = 0.25 * math.sin(2.0 * math.pi * 1000.0 * n / sr)
        gr = B.step_gr(st, x, c)
        assert math.isfinite(gr)
        assert gr >= -1e-9
        if gr > gr_max:
            gr_max = gr
        g = B.wet_gain_db(c["amount_db"], gr, c["max_duck_db"])
        assert -c["max_duck_db"] - 1e-9 <= g <= c["amount_db"] + 1e-9
    assert gr_max > 1.0
