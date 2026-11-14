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
from maths_distance import geometric_level  # noqa: E402

pytestmark = pytest.mark.quick

TLAW_SHA1 = {
    "play_std_lock18_byp.f32": "f5e9ebce2759262bc63a6fa67f30caecee2375ff",
    "play_std_lock18_col.f32": "a3a796a516436c682e9af71deaf77081a5509939",
    "play_std_unlocked_byp.f32": "778a241ce39842a3252e37617cb3a8f196f547eb",
    "play_std_unlocked_col.f32": "c2a74eec10c0a12c1747ceabd7993f0db93a5e12",
    "render_std_unlocked_byp.f32": "135c41ce546c390ef048a28713338259db07bd0a",
}
GOLDEN_META_SHA1 = "fd356749d18eacb7e4768ea798061f5b1b8ec030"
EMPTY_MD5 = "06bb1aaa0f59d67402b160224e155089"
CENTRE_MD5 = "64f8319d8bf4e33353f8681ec31140de"
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
    "app.css": 54,
    "sl_room_result.css": 3,
    "rr_controls.css": 1,
    "room_shape.js": 10,
    "maths_look.js": 2,
    "maths_pattern.js": 2,
    "maths_distance.js": 1,
    "maths_db.js": 2,
    "maths_bands.js": 1,
    "maths_image.js": 2,
    "room_math.js": 23,
    "spectrum_colors.js": 1,
    "freq_palette.js": 2,
    "room_view_pose.js": 1,
    "room_draw.js": 10,
    "room_3d.js": 29,
    "room_editor.js": 34,
    "image_views.js": 27,
    "colour_surfaces.js": 11,
    "polar_field.js": 19,
    "polar_views.js": 12,
    "mic_desk.js": 30,
    "source_desk.js": 7,
    "pack_room.js": 56,
    "live_fdn.js": 68,
    "lr_buttons.js": 1,
    "ms_presets.js": 3,
    "pair_mode.js": 2,
    "drag_model.js": 2,
    "room_window_math.js": 1,
    "settings_boot.js": 1,
    "rr_state.js": 12,
    "rr_mic.js": 1,
    "rr_mix.js": 12,
    "rr_room.js": 8,
    "rr_source.js": 2,
    "rr_space.js": 7,
    "rr_polar.js": 3,
    "rr_transport.js": 14,
    "rr_settings.js": 5,
    "app.js": 115,
    "sl_room_result.js": 13,
    "rr_controls.js": 1,
    "rr_controls_boot.js": 1,
}


def test_cache_pins():
    live = (SW / "static" / "js" / "live_fdn.js").read_text(encoding="utf-8")
    assert "WORKLET_VER = 65" in live


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
