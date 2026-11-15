"""The copy button is a Surfaces click. Empty and splay live hashes stay put."""
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

EMPTY = "06bb1aaa0f59d67402b160224e155089"
SPLAY = "6d996c03137772aaca9cebecab3358ac"


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def test_empty_and_splay_live_hash_hold():
    empty = live_fdn_params(A.params_from_body({}))
    splay = live_fdn_params(A.params_from_body({"room_shape": "splay"}))
    assert _md5(empty) == EMPTY
    assert _md5(splay) == SPLAY
