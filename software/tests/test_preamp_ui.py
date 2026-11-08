"""PREAMP-UI1. An off preamp and compressor leaves the default render bit-exact."""
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

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"
SR = 48000

# Keys a stuck Off post would still send. The page omits them. Both must match.
OFF = {
    "pre_colour": "off",
    "pre_drive_db": 0.0,
    "bloom_preset": "natural",
    "bloom_amount": 0.0,
    "bloom_colour": False,
    "glue_colour": False,
    "predelay_ms": 0.0,
    "bloom_attack_scale": 1.0,
    "bloom_release_scale": 1.0,
    "array_pre": "off",
    "array_drive_db": 0.0,
    "array_preset": "natural",
    "array_amount": 0.0,
    "room_pre": "off",
    "room_drive_db": 0.0,
    "room_preset": "natural",
    "room_amount": 0.0,
}


def _md5(body: dict) -> str:
    blob = A.live_fdn_params(A.params_from_body(body))
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _ir(extra: dict) -> np.ndarray:
    p = A.params_from_body(dict(extra))
    dry = np.zeros(32, dtype=np.float64)
    dry[0] = 1.0
    sig = inspect.signature(render)
    kw = {n: p[n] for n in sig.parameters if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    kw.update(A._bloom_render_kw(p))
    kw.update(A._routing_render_kw(p))
    left, right, _info = render(dry, SR, **kw)
    return np.stack([np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64)], 1)


def test_default_and_explicit_off_keep_the_empty_md5():
    assert _md5({}) == EMPTY
    assert _md5(OFF) == EMPTY
    assert A._bloom_render_kw(A.params_from_body({})) == {}
    assert A._routing_render_kw(A.params_from_body({})) == {}
    assert A._bloom_render_kw(A.params_from_body(OFF))["pre_colour"] == "off"
    assert A._bloom_render_kw(A.params_from_body(OFF))["bloom_amount"] == 0.0


def test_off_again_render_matches_the_default_scene():
    short = {"ir_length_ms": 80}
    base = _ir(short)
    stuck = _ir(dict(short, **OFF))
    assert base.shape == stuck.shape
    assert float(np.max(np.abs(base - stuck))) == 0.0
