"""Treatment sets decay. The switch is off unless the post says so.

Flat stays the empty-body live MD5. Surfaces with the switch on uses the
500 Hz / 1 kHz material mean Render already arms when the lock is off.
"""
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

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"


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


def test_flat_switch_keeps_the_empty_live_md5():
    import app_server as A
    assert A.params_from_body({})["treat_sets_decay"] is False
    assert A.params_from_body({"treat_sets_decay": True})["treat_sets_decay"] is True
    assert _md5(A.live_fdn_params(A.params_from_body({}))) == EMPTY
    assert _md5(A.live_fdn_params(A.params_from_body({"treat_sets_decay": True}))) == EMPTY


def test_surfaces_switch_uses_the_material_mean_and_amount_shortens_it():
    W, Hh, L, surfaces, hum = H.room("real_default")
    bare = _mid(W, Hh, L, surfaces, hum, [])
    plan = AT.auto_treat(W, Hh, L, surfaces, hum, 0.8)
    rows = [dict(r, suggested=False, on=True) for r in plan["suggested"]]
    full = _mid(W, Hh, L, surfaces, hum, rows)
    assert bare > full
    off = _live(surfaces, [])
    assert off["line_t60"] == 0.0
    assert "surf_on" not in off or not off.get("surf_on")
    on = _live(surfaces, [], treat_sets_decay=True)
    assert abs(on["line_t60"] - bare) < 1e-6
    assert abs(on["decay_s"] - bare) < 1e-6
    assert on.get("surf_on") == 1
    treated = _live(surfaces, rows, treat_sets_decay=True)
    assert abs(treated["line_t60"] - full) < 1e-6
    assert treated["line_t60"] < on["line_t60"]
