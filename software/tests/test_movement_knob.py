"""Movement knob. Default 0 stays off. Knob 100 is 0.15 ms on Play and Render.

Play packs section 8 from movement_ms. Render passes the same percent into
movement_peak_ms. Parity, flat cards, mirror/null, and a direct-only body stay 0.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import render_pipeline as rp  # noqa: E402


def _section_ids(blob):
    n = int(blob[3])
    directory = blob[5:5 + 4 * n]
    return [directory[i] for i in range(0, len(directory), 4)]


def _section_payload(blob, sid):
    n = int(blob[3])
    directory = blob[5:5 + 4 * n]
    for i in range(0, len(directory), 4):
        if directory[i] == sid:
            off = int(directory[i + 1])
            ln = int(directory[i + 2])
            return blob[off:off + ln]
    return None


def test_flag_is_off_and_curve_holds():
    assert rp.MOVEMENT_FORCED_OFF is False
    assert rp.movement_peak_ms({}) == 0.0
    assert rp.movement_peak_ms({"movement": 0}) == 0.0
    assert rp.movement_peak_ms({"movement": 50}) == pytest.approx(0.10)
    assert rp.movement_peak_ms({"movement": 100}) == pytest.approx(0.15)
    assert rp.movement_peak_ms({"movement": 100, "reaktor_parity": True}) == 0.0
    assert rp.movement_peak_ms({"movement": 100, "mirror_null": True}) == 0.0
    assert rp.movement_peak_ms({"movement": 100, "fdn_wet": 0.0, "early_wet": 0.0}) == 0.0


def test_play_packs_knob_and_default_omits_section_8():
    off = A.live_fdn_params(A.params_from_body({}))
    assert float(off.get("movement_ms") or 0.0) == 0.0
    assert 8.0 not in _section_ids(rp.pack_blob_v2(off))
    on = A.live_fdn_params(A.params_from_body({"movement": 100}))
    assert on["movement_ms"] == pytest.approx(0.15)
    assert _section_payload(rp.pack_blob_v2(on), 8.0) == pytest.approx([0.15])


def test_render_takes_the_same_knob():
    assert "movement" in inspect.signature(rp._render_core).parameters
    text = (SW / "render_pipeline.py").read_text(encoding="utf-8")
    assert '"movement": movement,' in text
    server = (SW / "app_server.py").read_text(encoding="utf-8")
    assert 'movement=float(p.get("movement") or 0.0)' in server
    assert rp.movement_peak_ms(
        {"reaktor_parity": False, "movement": 100, "fdn_wet": 1.0, "early_wet": 1.0},
        None,
    ) == pytest.approx(0.15)
    assert rp.movement_peak_ms(
        {"reaktor_parity": False, "movement": 0, "fdn_wet": 1.0, "early_wet": 1.0},
        None,
    ) == 0.0


def test_knob_is_visible_and_defaults_to_zero():
    page = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="movementRow" hidden' not in page
    assert 'id="movement" min="0" max="100" step="1" value="0"' in page
    app = (SW / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "movement: 0" in app
