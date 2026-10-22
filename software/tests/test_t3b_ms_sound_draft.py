"""T3b (D18 + D19, locked 4 Oct 2026 16:43).

D18: MS presets decode at unity (S:M = 1, virtual pair +-63 deg) with a -3 dB trim on M and S.
D19: with one source, when any strip is on route s, the direct sound uses the pattern spikes
     (direct_capsule_spikes, hottest capsule = 1) in Render AND Play (buses[ch]["direct_gain"]).
     Every other setup keeps (1, 1, 1): the ORTF golden must not move.
"""
from __future__ import annotations
import pytest
try:
    import _harness as H
except ModuleNotFoundError:
    from tests import _harness as H
from render_pipeline import live_fdn_params

TRIM = 10 ** (-3 / 20)
FRONT = dict(sx=3.0, sz=4.75)


def test_d18_unity_decode_minus3_weights():
    w = H.weights(H.ms(m_gain=TRIM, mic_gain_l=TRIM))
    assert w["ll"] == pytest.approx(TRIM) and w["lr"] == pytest.approx(-TRIM)
    assert w["cl"] == pytest.approx(TRIM) and w["cr"] == pytest.approx(TRIM)
    assert abs(w["ll"]) == pytest.approx(w["cl"])            # S:M = 1 -> +-63 deg


def test_d19_ortf_has_no_direct_gain_today_and_after():
    live = live_fdn_params(H.A.params_from_body(H.ortf(**FRONT)))
    assert "direct_gain" not in live["buses"]["l"]           # one source, no route s: unchanged


def test_d19_render_ms_direct_centred_for_front_source():
    ir = H.render_body(H.ms(fdn_wet=0.0, early_wet=0.0, direct_wet=1.0, **FRONT))
    assert abs(H.lr_db(ir)) < 1.0


def test_d19_play_ms_side_direct_gain_follows_pattern():
    live = live_fdn_params(H.A.params_from_body(H.ms(**FRONT)))
    s_gain = live["buses"]["l"].get("direct_gain", 1.0)      # fig-8 side, source in front
    m_gain = live["buses"]["c"].get("direct_gain", 1.0)
    assert m_gain == pytest.approx(1.0) and abs(s_gain) < 0.2
