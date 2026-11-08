"""Surfaces step 0. Flat lock-off stays on the slider. The air card no longer
points at a one-pole control that the page does not have.
"""
from pathlib import Path

import app_server as A
from render_pipeline import live_fdn_params

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"


def test_flat_lock_off_stays_on_the_slider():
    p = A.params_from_body({"decay_lock": False, "fdn_g": 0.5, "decay_mode": "flat"})
    live = live_fdn_params(p)
    assert live["line_t60"] == 0.0
    assert not live.get("surf_on")


def test_air_card_does_not_mention_the_removed_one_pole():
    html = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert "one-pole is under Advanced" not in html
    assert 'id="air_lp"' not in html
    assert "ISO depth is the shelf mix" in html
