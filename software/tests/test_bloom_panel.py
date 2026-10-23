"""Bloom panel keys reach Render. Off stays off the live dict. No audio render."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import bloom_dsp as B  # noqa: E402

EMPTY = "b20cf5dc675f613992aa6a31c2cd74f4"

# Page Room Crush at the bloom_listen/room_crush.wav settings.
# The report records amount 100 and glue_colour false.
# The other keys are the engine defaults.
PAGE = {
    "bloom_preset": "room_crush",
    "bloom_amount": 100,
    "bloom_colour": False,
    "glue_colour": False,
    "pre_colour": "off",
    "pre_drive_db": 0.0,
    "predelay_ms": 0.0,
    "bloom_attack_scale": 1.0,
    "bloom_release_scale": 1.0,
}
LISTEN = {
    "bloom_preset": "room_crush",
    "bloom_amount": 100,
    "glue_colour": False,
}


def _md5(body: dict) -> tuple[str, bool]:
    p = A.params_from_body(body)
    blob = A.live_fdn_params(p)
    digest = hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()
    return digest, "bloom" in blob


def test_off_body_keeps_the_empty_md5():
    digest, on = _md5({})
    assert digest == EMPTY
    assert on is False
    assert A._bloom_render_kw(A.params_from_body({})) == {}


def test_room_crush_page_matches_listen_design():
    p = A.params_from_body(PAGE)
    kw = A._bloom_render_kw(p)
    assert kw["bloom_preset"] == "room_crush"
    assert kw["bloom_amount"] == 100.0
    assert kw["glue_colour"] is False
    assert kw["bloom_colour"] is False
    assert kw["pre_colour"] == "off"
    assert B.design(kw, 48000) == B.design(LISTEN, 48000)
    digest, on = _md5(PAGE)
    assert on is True
    assert digest != EMPTY
