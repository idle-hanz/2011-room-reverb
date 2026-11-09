"""Capsule fold stays linear. Old strip keys stay off the live dict."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from fdn import apply_capsule_weights  # noqa: E402

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"
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
    "bloom_attack_scale": 2,
    "bloom_release_scale": 2,
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


def test_fold_is_linear_so_the_buses_stay_separable():
    rng = np.random.default_rng(0)
    L, C, R = (rng.normal(size=64) for _ in range(3))
    w = {"ll": 0.7, "lr": 0.2, "cl": 0.5, "cr": 0.5, "rl": 0.1, "rr": 0.8}
    full_l, full_r = apply_capsule_weights(L, C, R, w)
    array_l, array_r = apply_capsule_weights(L, np.zeros_like(C), R, w)
    room_l, room_r = apply_capsule_weights(np.zeros_like(L), C, np.zeros_like(R), w)
    assert np.max(np.abs(full_l - (array_l + room_l))) < 1e-12
    assert np.max(np.abs(full_r - (array_r + room_r))) < 1e-12


def test_off_body_keeps_the_empty_md5():
    blob = _blob({})
    assert _md5({}) == EMPTY
    assert "bloom" not in blob
    assert "side" not in blob
    assert "pre_colour" not in blob
    assert "predelay_n" not in blob


def test_armed_strip_keys_stay_out_of_the_live_dict():
    body = dict(ARMED)
    body["place_c"] = "room"
    blob = _blob(body)
    assert "side" not in blob
    assert "bloom" not in blob
    assert "pre_colour" not in blob
    assert "predelay_n" not in blob
    assert "array_preset" not in blob
    assert "room_preset" not in blob
    assert "place_c" not in blob
    assert _md5(body) == EMPTY
