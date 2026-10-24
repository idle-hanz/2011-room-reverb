"""Box Mirror L/R. Off keeps the live MD5. On copies left onto right."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from render_pipeline import live_fdn_params  # noqa: E402
from surface_colour import parse_surfaces  # noqa: E402

EMPTY = "b20cf5dc675f613992aa6a31c2cd74f4"
CENTRE = "ba1bbc6d386ed75bf484156f08043f37"
# Default splay live dict before this toggle. Equal A and C must not move it.
SPLAY = "06d91ff57c4006fdaec8f6d9b418c147"


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _split():
    return {
        "A": {"absorb": [0.91, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22]},
        "C": {"absorb": [0.11, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22]},
        "B": {"absorb": [0.33, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22]},
    }


def test_default_mirror_on_stays_bit_exact():
    assert _md5(live_fdn_params(A.params_from_body({"mirror_lr": True}))) == EMPTY
    assert _md5(live_fdn_params(A.params_from_body({
        "third_mic": "centre", "mic_gain_c": 1.0, "mirror_lr": True,
    }))) == CENTRE


def test_box_off_is_bit_exact():
    assert _md5(live_fdn_params(A.params_from_body({}))) == EMPTY
    assert _md5(live_fdn_params(A.params_from_body({"mirror_lr": False}))) == EMPTY
    assert _md5(live_fdn_params(A.params_from_body({
        "third_mic": "centre", "mic_gain_c": 1.0,
    }))) == CENTRE
    assert _md5(live_fdn_params(A.params_from_body({
        "third_mic": "centre", "mic_gain_c": 1.0, "mirror_lr": False,
    }))) == CENTRE
    assert _md5(live_fdn_params(A.params_from_body({"room_shape": "splay"}))) == SPLAY
    assert _md5(live_fdn_params(A.params_from_body({
        "room_shape": "splay", "mirror_lr": False,
    }))) == SPLAY


def test_toggle_copies_left_onto_right_only():
    off = A.params_from_body({"mirror_lr": False, "surfaces": _split(), "room_shape": "box"})
    assert off["surfaces"]["A"]["absorb"][0] == 0.91
    assert off["surfaces"]["C"]["absorb"][0] == 0.11
    assert off["surfaces"]["B"]["absorb"][0] == 0.33
    assert off["surfaces"]["C"]["letter"] == "C"
    on = A.params_from_body({"mirror_lr": True, "surfaces": _split(), "room_shape": "box"})
    assert on["surfaces"]["C"]["absorb"][0] == 0.91
    assert on["surfaces"]["A"]["absorb"][0] == 0.91
    assert on["surfaces"]["B"]["absorb"][0] == 0.33
    assert on["surfaces"]["D"]["absorb"][0] == parse_surfaces(None)["D"]["absorb"][0]
    assert on["surfaces"]["E"]["absorb"] == parse_surfaces(None)["E"]["absorb"]
    assert on["surfaces"]["F"]["absorb"] == parse_surfaces(None)["F"]["absorb"]
    assert on["surfaces"]["C"]["letter"] == "C"
    assert "mirror_lr" not in live_fdn_params(on)


def test_splay_mirrors_without_the_toggle():
    body = {"room_shape": "splay", "surfaces": _split()}
    got = A.params_from_body(body)
    assert got["surfaces"]["C"]["absorb"][0] == 0.91
    assert got["surfaces"]["B"]["absorb"][0] == 0.33
    lede = A.params_from_body({"room_shape": "lede", "surfaces": _split()})
    assert lede["surfaces"]["C"]["absorb"][0] == 0.11
