"""Treatment sets decay. The switch is off unless the post says so.

Flat stays the empty-body live MD5. Surfaces with the lock off uses the
500 Hz / 1 kHz material mean on Play and on Render. The switch is one way
the page turns that lock off. A locked dial stays the dial.
"""
import inspect
import pytest
import hashlib
import json

import numpy as np

try:
    import _sl_harness as H
except ImportError:
    from tests import _sl_harness as H
import surf_autotreat as AT
import surf_panels as P
import surf_target as ST
from render_pipeline import live_fdn_params

EMPTY = "06bb1aaa0f59d67402b160224e155089"


def _md5(blob):
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _mid(W, Hh, L, surfaces, hum, rows):
    cards = P.cards_with_treatment(surfaces, rows)
    return float(np.mean(ST.room_target(
        W, Hh, L, cards, hum, np.array([500.0, 1000.0]),
    )))


def _live(surfaces, rows, **extra):
    body = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "decay_s": 1.8, "decay_lock": False,
        "decay_mode": "surfaces", "phys_ceiling": True,
        "surfaces": surfaces, "surf_treatment": rows,
    }
    body.update(extra)
    return live_fdn_params(body)


@pytest.mark.slow
def test_flat_switch_keeps_the_empty_live_md5():
    import app_server as A
    assert A.params_from_body({})["treat_sets_decay"] is False
    assert A.params_from_body({"treat_sets_decay": True})["treat_sets_decay"] is True
    assert _md5(A.live_fdn_params(A.params_from_body({}))) == EMPTY
    assert _md5(A.live_fdn_params(A.params_from_body({"treat_sets_decay": True}))) == EMPTY


@pytest.mark.slow
def test_surfaces_switch_uses_the_material_mean_and_amount_shortens_it():
    W, Hh, L, surfaces, hum = H.room("real_default")
    bare = _mid(W, Hh, L, surfaces, hum, [])
    plan = AT.auto_treat(W, Hh, L, surfaces, hum, 0.8)
    rows = [dict(r, suggested=False, on=True) for r in plan["suggested"]]
    full = _mid(W, Hh, L, surfaces, hum, rows)
    assert bare > full
    held = _live(surfaces, [], decay_lock=True, decay_s=1.8)
    assert abs(held["line_t60"] - 1.8) < 1e-6
    off = _live(surfaces, [])
    assert abs(off["line_t60"] - bare) < 1e-6
    assert abs(off["decay_s"] - bare) < 1e-6
    assert off.get("surf_on") == 1
    on = _live(surfaces, [], treat_sets_decay=True)
    assert abs(on["line_t60"] - bare) < 1e-6
    assert abs(on["decay_s"] - bare) < 1e-6
    assert on.get("surf_on") == 1
    treated = _live(surfaces, rows, treat_sets_decay=True)
    assert abs(treated["line_t60"] - full) < 1e-6
    assert treated["line_t60"] < on["line_t60"]
    import app_server as A
    from render_pipeline import render
    body = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0,
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "decay_s": 1.8, "decay_lock": False, "treat_sets_decay": False,
        "decay_mode": "surfaces", "phys_ceiling": True,
        "surfaces": surfaces, "surf_treatment": [],
        "ir_length_ms": 400,
    }
    p = A.params_from_body(body)
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    yl, yr, info = render(dry, 48000, **kw)
    ir = np.stack([np.asarray(yl, float), np.asarray(yr, float)], 1)
    assert np.max(np.abs(ir)) < 1.0
    assert abs(float(info["surf"]["decay_s_used"]) - off["line_t60"]) < 1e-4
