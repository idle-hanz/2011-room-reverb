"""Real-wall polarity. Missing or false keeps today's early-tap signs.

The tick forces every early tap positive on the shoebox and the polygon.
The Hadamard and its column signs stay. The capsule pattern stays.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from fdn import LOOP_COLUMN_D, loop_hadamard  # noqa: E402
from render_pipeline import live_fdn_params, play_listen_scene  # noqa: E402

EMPTY_MD5 = "06bb1aaa0f59d67402b160224e155089"
_SIGNED = (
    "level_l", "level_r", "level_c",
    "press_l", "press_r", "press_c",
    "grad_l", "grad_r", "grad_c",
)


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _signs_match(off, on) -> None:
    assert len(off) == len(on) and len(off) > 0
    neg = 0
    for a, b in zip(off, on):
        assert a.n == b.n
        assert a.order == b.order
        assert a.cardio_l == b.cardio_l
        assert a.cardio_r == b.cardio_r
        assert a.cardio_c == b.cardio_c
        assert a.delay_ms_l == b.delay_ms_l
        assert a.delay_ms_r == b.delay_ms_r
        if int(a.polarity) < 0:
            neg += 1
            assert int(b.polarity) == 1
            for name in _SIGNED:
                assert getattr(b, name) == -getattr(a, name)
        else:
            assert int(b.polarity) == int(a.polarity)
            for name in _SIGNED:
                assert getattr(b, name) == getattr(a, name)
    assert neg >= 1


def test_missing_and_false_stay_off_and_bit_exact():
    missing = A.params_from_body({})
    explicit = A.params_from_body({"real_wall_polarity": False})
    assert missing["real_wall_polarity"] is False
    assert explicit["real_wall_polarity"] is False
    assert A.params_from_body({"real_wall_polarity": True})["real_wall_polarity"] is True
    off = live_fdn_params(missing)
    assert "real_wall_polarity" not in off
    assert _md5(off) == EMPTY_MD5
    assert _md5(live_fdn_params(explicit)) == EMPTY_MD5
    on = live_fdn_params(A.params_from_body({"real_wall_polarity": True}))
    assert "real_wall_polarity" not in on
    assert _md5(on) != EMPTY_MD5


def test_tick_makes_shoebox_and_polygon_taps_positive():
    hadamard = loop_hadamard(32, parity=False).copy()
    columns = LOOP_COLUMN_D.copy()
    box_off = play_listen_scene(A.params_from_body({}))["taps"]
    box_on = play_listen_scene(A.params_from_body({"real_wall_polarity": True}))["taps"]
    _signs_match(box_off, box_on)
    splay_off = play_listen_scene(A.params_from_body({"room_shape": "splay"}))["taps"]
    splay_on = play_listen_scene(A.params_from_body({
        "room_shape": "splay",
        "real_wall_polarity": True,
    }))["taps"]
    _signs_match(splay_off, splay_on)
    assert np.array_equal(loop_hadamard(32, parity=False), hadamard)
    assert np.array_equal(LOOP_COLUMN_D, columns)
