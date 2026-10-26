"""Play solo match. Held while materials change. Render does not apply it."""
from __future__ import annotations

import inspect
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from render_pipeline import render  # noqa: E402
from solo_match import (  # noqa: E402
    CAP_LIN,
    attach_solo_match,
    match_lin,
    measure_lin,
    play_early_energy,
    resolve_gain,
)
from surface_colour import default_surfaces  # noqa: E402

# 10*log10((1-0.9)/(1-0.02)). Flat bands, one hit of the soloed panel.
ABSORB_DROP_DB = 10.0 * math.log10((1.0 - 0.9) / (1.0 - 0.02))


def test_no_solo_is_unity():
    p = A.params_from_body({})
    live = {"ok": True}
    attach_solo_match(live, p, True, None, None)
    assert live["solo_match_lin"] == 1.0
    assert live["solo_match_letter"] is None


def test_switch_off_is_unity_and_does_not_measure():
    p = A.params_from_body({"surfaces_solo": "A"})
    calls = {"n": 0}

    def measure():
        calls["n"] += 1
        return 4.0

    assert resolve_gain("A", False, None, None, measure) == 1.0
    assert resolve_gain(None, True, None, None, measure) == 1.0
    assert calls["n"] == 0
    live = {"ok": True}
    attach_solo_match(live, p, False, None, None)
    assert live["solo_match_lin"] == 1.0


def test_cap_holds():
    assert match_lin(1.0, 1.0) == 1.0
    assert match_lin(1.0, 0.0) == CAP_LIN
    assert match_lin(1.0e12, 1.0) == CAP_LIN
    assert resolve_gain("A", True, "A", 100.0, lambda: 1.0) == CAP_LIN


def test_hold_skips_a_second_measure():
    calls = {"n": 0}

    def measure():
        calls["n"] += 1
        return 3.0

    assert resolve_gain("A", True, None, None, measure) == 3.0
    assert resolve_gain("A", True, "A", 3.0, measure) == 3.0
    assert calls["n"] == 1
    assert resolve_gain("B", True, "A", 3.0, measure) == 3.0
    assert calls["n"] == 2


def _render_impulse(body):
    p = A.params_from_body(body)
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    sig = inspect.signature(render).parameters
    assert "match_solo_level" not in sig
    assert "solo_match_gain" not in sig
    kw = {n: p[n] for n in sig if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    left, right, _info = render(dry, 48000, **kw)
    return np.stack([np.asarray(left, np.float64), np.asarray(right, np.float64)], 1)


def test_render_ignores_the_switch():
    common = {
        "surfaces_solo": "A",
        "ir_length_ms": 200.0,
        "decay_s": 0.12,
        "decay_lock": True,
    }
    on = _render_impulse(dict(common, match_solo_level=True, solo_match_gain=8.0))
    off = _render_impulse(dict(common, match_solo_level=False, solo_match_gain=1.0))
    assert on.shape == off.shape
    assert np.array_equal(on, off)


def _panel(letter, alpha):
    surfaces = default_surfaces()
    surfaces[letter]["absorb"] = [float(alpha)] * len(surfaces[letter]["absorb"])
    return surfaces


def _monitored(body):
    p = A.params_from_body(body)
    calls = {"n": 0}
    solo = p.get("surfaces_solo")

    def measure():
        calls["n"] += 1
        return measure_lin(p, solo)

    enabled = True if "match_solo_level" not in body else bool(body.get("match_solo_level"))
    gain = resolve_gain(
        solo,
        enabled,
        body.get("solo_match_letter"),
        body.get("solo_match_gain"),
        measure,
    )
    energy = play_early_energy(p) * gain * gain
    return gain, energy, calls["n"]


def test_solo_absorb_drop_stays_about_9_9_db():
    """0.02 to 0.9 on a soloed panel. Held gain, switch on. Play early falls ~9.9 dB."""
    low = {
        "surfaces_solo": "A",
        "match_solo_level": True,
        "surfaces": _panel("A", 0.02),
    }
    gain_lo, energy_lo, measured = _monitored(low)
    assert measured == 1
    assert gain_lo > 0.0
    high = {
        "surfaces_solo": "A",
        "match_solo_level": True,
        "surfaces": _panel("A", 0.9),
        "solo_match_letter": "A",
        "solo_match_gain": gain_lo,
    }
    gain_hi, energy_hi, measured_again = _monitored(high)
    assert measured_again == 0
    assert gain_hi == pytest.approx(gain_lo, abs=1e-12)
    db = 10.0 * math.log10(energy_hi / energy_lo)
    assert db == pytest.approx(ABSORB_DROP_DB, abs=0.5)
