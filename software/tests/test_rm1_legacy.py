"""RM1. Armed old preamp and compressor keys do not move Render or the Play blob.

Same default scene on both sides. ir_length_ms is 80 before params_from_body.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from render_pipeline import render  # noqa: E402

EMPTY = "06bb1aaa0f59d67402b160224e155089"
SR = 48000
ARMED = {
    "route_array_pre": "neve1073",
    "route_array_drive": 12,
    "route_array_comp": "glue",
    "route_array_amount": 100,
    "route_room_pre": "u610a",
    "route_room_drive": 9,
    "route_room_comp": "room_crush",
    "route_room_amount": 80,
    "route_master_pre": "neve1073",
    "route_master_drive": 6,
    "route_master_comp": "nuke",
    "route_master_amount": 100,
    "bloom_on": True,
    "bloom_menu": "room_crush",
    "bloom_amount_ui": 100,
    "bloom_colour_ui": True,
    "glue_colour_ui": True,
    "pre_drive_ui": 12,
    "predelay_ui": 40,
    "bloom_attack_ui": 2,
    "bloom_release_ui": 2,
    "bloom_preset": "nuke",
    "bloom_amount": 100,
    "bloom_colour": True,
    "glue_colour": True,
    "pre_colour": "u610a",
    "pre_drive_db": 12,
    "predelay_ms": 40,
    "bloom_attack_scale": 2.0,
    "bloom_release_scale": 2.0,
    "array_preset": "glue",
    "array_amount": 100,
    "array_pre": "neve1073",
    "array_drive_db": 6,
    "room_preset": "room_crush",
    "room_amount": 100,
    "room_pre": "u610a",
    "room_drive_db": 6,
}


def _blob(body: dict) -> dict:
    return A.live_fdn_params(A.params_from_body(body))


def _md5(body: dict) -> str:
    return hashlib.md5(json.dumps(_blob(body), sort_keys=True, default=str).encode()).hexdigest()


def _stereo(body: dict) -> np.ndarray:
    p = A.params_from_body(dict(body))
    dry = np.zeros(32, dtype=np.float64)
    dry[0] = 1.0
    sig = inspect.signature(render)
    kw = {n: p[n] for n in sig.parameters if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    kw["ir_length_ms"] = 80
    left, right, _info = render(dry, SR, **kw)
    return np.stack(
        [np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)],
        1,
    )


def test_armed_keys_keep_the_empty_md5_and_the_same_blob():
    assert _md5({}) == EMPTY
    assert _md5(ARMED) == EMPTY
    short = {"ir_length_ms": 80}
    armed = dict(short)
    armed.update(ARMED)
    base = _blob(short)
    stuck = _blob(armed)
    assert json.dumps(base, sort_keys=True, default=str) == json.dumps(
        stuck, sort_keys=True, default=str
    )
    assert "bloom" not in base
    assert "side" not in base
    assert "pre_colour" not in base
    assert "predelay_n" not in base


def test_armed_keys_do_not_move_a_render_sample():
    short = {"ir_length_ms": 80}
    armed = dict(short)
    armed.update(ARMED)
    base = _stereo(short)
    stuck = _stereo(armed)
    assert base.shape == stuck.shape
    assert float(np.max(np.abs(base - stuck))) == 0.0
