"""Old preamp and compressor keys stay off the live dict. Empty MD5 holds."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402

EMPTY = "06bb1aaa0f59d67402b160224e155089"
ARMED = {
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


def test_absent_and_armed_keep_the_empty_md5():
    empty = _blob({})
    assert _md5({}) == EMPTY
    assert "bloom" not in empty
    assert "side" not in empty
    assert "pre_colour" not in empty
    armed = _blob(ARMED)
    assert _md5(ARMED) == EMPTY
    assert "bloom" not in armed
    assert "side" not in armed
    assert "pre_colour" not in armed
    assert "predelay_n" not in armed
