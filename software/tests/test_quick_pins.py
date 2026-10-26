"""Quick pin tier. Reads and hashes only. Does not render and does not rebuild wasm.

From software\\:
software\\.venv\\Scripts\\python.exe -m pytest tests\\test_quick_pins.py -q -p no:cacheprovider
"""
from __future__ import annotations

import hashlib
import json
import re
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
EMPTY_MD5 = "067adbca1930efcd3f7c83bdd1d4c359"
CENTRE_MD5 = "35db578a18557d5729c0450e26f24a9d"
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


# Cache query on each file index.html loads. One table, one check.
PIN_TABLE = {
    "app.css": 42,
    "sl_room_result.css": 2,
    "rr_controls.css": 1,
    "room_shape.js": 7,
    "room_math.js": 21,
    "spectrum_colors.js": 1,
    "freq_palette.js": 2,
    "room_view_pose.js": 1,
    "room_draw.js": 5,
    "room_3d.js": 25,
    "room_editor.js": 26,
    "image_views.js": 21,
    "colour_surfaces.js": 9,
    "polar_field.js": 15,
    "polar_views.js": 6,
    "mic_desk.js": 25,
    "source_desk.js": 4,
    "pack_room.js": 55,
    "live_fdn.js": 64,
    "lr_buttons.js": 1,
    "ms_presets.js": 3,
    "pair_mode.js": 2,
    "drag_model.js": 2,
    "room_window_math.js": 1,
    "routing_scene.js": 3,
    "rr_state.js": 1,
    "rr_mic.js": 1,
    "rr_mix.js": 1,
    "rr_room.js": 1,
    "rr_source.js": 1,
    "rr_space.js": 1,
    "rr_polar.js": 1,
    "rr_transport.js": 1,
    "rr_settings.js": 1,
    "app.js": 104,
    "sl_room_result.js": 8,
    "rr_controls.js": 1,
    "rr_controls_boot.js": 1,
}


def test_cache_pins():
    live = (SW / "static" / "js" / "live_fdn.js").read_text(encoding="utf-8")
    assert "WORKLET_VER = 63" in live


def test_index_versions_match_pin_table():
    page = (SW / "static" / "index.html").read_text(encoding="utf-8")
    found = re.findall(r'(?:href|src)="[^"]*?([^"/?]+)\?v=(\d+)"', page)
    assert found, "index.html has no cache queries"
    got = {}
    for name, ver in found:
        assert name not in got or got[name] == int(ver), name
        got[name] = int(ver)
    assert got == PIN_TABLE


def test_geometric_level_is_inverse_distance():
    for d in DISTANCES:
        assert abs(geometric_level(d) * d - 1.0) < 1e-12, d
