"""Quick pin tier. Reads and hashes only. Does not render and does not rebuild wasm.

From software\\:
software\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_pins.py -q -p no:cacheprovider
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
GOLDEN = (
    ROOT
    / "handoff_build_support_2"
    / "3_phase_acceptance_tests"
    / "harness"
    / "golden"
)
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from early_field import geometric_level  # noqa: E402

pytestmark = pytest.mark.quick

TLAW_SHA1 = {
    "play_std_lock18_byp.f32": "d011bafca80f4e46ae768db40becd762e78dcada",
    "play_std_lock18_col.f32": "80d86ec23022d09fdb0653298ad322ca539e5bb5",
    "play_std_unlocked_byp.f32": "91738c70220b4edce512aebe3548dfdbd894cc41",
    "play_std_unlocked_col.f32": "171a1450978742a7fc1f3cb77739d202d80f48a9",
    "render_std_unlocked_byp.f32": "2a806e334e06cc475868d4c3da3fc78431c9a0aa",
}
GOLDEN_META_SHA1 = "52bfce749715e335d8fa2418a16e8593e9a54040"
EMPTY_MD5 = "b20cf5dc675f613992aa6a31c2cd74f4"
CENTRE_MD5 = "ba1bbc6d386ed75bf484156f08043f37"
DISTANCES = (0.3, 1.0, 2.5, 7.0, 40.0)


def test_tlaw_golden_sha1s():
    for name, expect in TLAW_SHA1.items():
        digest = hashlib.sha1((GOLDEN / name).read_bytes()).hexdigest()
        assert digest == expect, (name, digest)


def test_golden_meta_sha1():
    digest = hashlib.sha1((GOLDEN / "GOLDEN_META.json").read_bytes()).hexdigest()
    assert digest == GOLDEN_META_SHA1


def test_live_md5s_match_a7():
    """Same calls as test_a7_default_live_hash_unchanged."""
    body = {}
    p = A.params_from_body(body)
    blob = A.live_fdn_params(p)
    digest = hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()
    assert digest == EMPTY_MD5
    kept = A.params_from_body({"third_mic": "centre", "mic_gain_c": 1.0})
    kept_blob = A.live_fdn_params(kept)
    kept_digest = hashlib.md5(
        json.dumps(kept_blob, sort_keys=True, default=str).encode()
    ).hexdigest()
    assert kept_digest == CENTRE_MD5


def test_cache_pins():
    live = (SW / "static" / "js" / "live_fdn.js").read_text(encoding="utf-8")
    page = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert "WORKLET_VER = 63" in live
    assert "live_fdn.js?v=64" in page
    assert "app.js?v=89" in page


def test_geometric_level_is_inverse_distance():
    for d in DISTANCES:
        assert abs(geometric_level(d) * d - 1.0) < 1e-12, d
