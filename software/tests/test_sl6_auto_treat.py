"""SL6: Auto-treat suggests rows (D-SL5), axis-balanced broadband + <= 4 tuned panels; EBU preset (D-SL9)."""
import copy
import numpy as np
import pytest
try:
    import _sl_harness as H
except ImportError:
    from tests import _sl_harness as H
import surf_autotreat as AT
import surf_panels as P
import surf_target as ST

BOX = H.fixture("fixture_box_plan.json")


@pytest.fixture(scope="module")
def plan():
    W, Hh, L, s, hum = H.room("real_default")
    s0 = copy.deepcopy(s)
    r = AT.auto_treat(W, Hh, L, s, hum, 0.8)
    assert s == s0                                       # the scene is never modified
    return W, Hh, L, s, hum, r


def test_reproduces_the_box_plan(plan):
    *_, r = plan
    got = [(x["face"], x["type"], x.get("f0"), x["coverage"]) for x in r["suggested"]]
    want = [tuple(x) for x in BOX["rows"]]
    assert got == want
    assert r["porous"] == "absorber_panel_4in_gap4in"
    assert r["coverage"] == BOX["coverage"]
    assert r["n_within_10pct"] == 20 and r["n_bands"] == 24        # model 20/24. PC: factors off 6/23, octave cal 12/23, bass hold 15/23, through-500 hold 16/23


def test_only_suggests(plan):
    W, Hh, L, s, hum, r = plan
    assert all(x["suggested"] for x in r["suggested"])
    T_sug = ST.room_target(W, Hh, L, P.cards_with_treatment(s, r["suggested"]), hum, ST.BANDS)
    assert np.allclose(T_sug, ST.room_target(W, Hh, L, s, hum, ST.BANDS))
    acc = [dict(x, suggested=False) for x in r["suggested"]]
    T_acc = ST.room_target(W, Hh, L, P.cards_with_treatment(s, acc), hum, np.array([500.0, 1000.0, 2000.0]))
    assert np.mean(T_acc) == pytest.approx(0.8, rel=0.08)


def test_limits(plan):
    *_, r = plan
    assert max(r["coverage"].values()) <= 0.9 + 1e-9
    assert sum(x["type"] in ("membrane", "helmholtz") for x in r["suggested"]) <= 4
    assert not P.validate_rows([dict(x, suggested=False) for x in r["suggested"]])


def test_existing_tuned_rows_share_the_budget_of_four():
    W, Hh, L, s, hum = H.room("real_default")
    have = [dict(P.design_membrane(62.5), id="mine", face="F", coverage=0.2, on=True) for _ in range(1)]
    r = AT.auto_treat(W, Hh, L, s, hum, 0.8, existing_rows=have)
    assert sum(x["type"] in ("membrane", "helmholtz") for x in r["suggested"]) <= 3


def test_ebu_preset_and_make_it_a_panel():
    assert AT.ebu_preset_t_mid(6.0, 3.0, 8.0) == pytest.approx(0.2823, abs=1e-4)
    p = AT.make_it_a_panel(57.2, 6.0, 3.0, 8.0)
    assert p["type"] == "membrane" and p["suggested"] and p["face"] in ("F", "A", "C")
    assert AT.make_it_a_panel(600.0, 6.0, 3.0, 8.0) is None          # above 500 Hz stays a decay cut


def test_api_suggests_and_leaves_the_scene_alone():
    body = {"t_mid": 0.8, "surf_treatment": []}
    out = H.A.api_auto_treat(body)
    assert out["ok"] is True
    assert body["surf_treatment"] == []
    assert out["suggested"] and all(r["suggested"] for r in out["suggested"])
    assert max(out["coverage"].values()) <= 0.9 + 1e-9


def test_target_longer_than_room_fits_shape_only():
    """Treatment only adds absorption. Asking for more than the room's own mid T gives no porous rows
    (no 0 % rows), shape_only=True, and the panels fit the Makivirta shape at the room's own T."""
    W, Hh, L, s, hum = H.room("real_default")
    t_room = float(np.mean(ST.room_target(W, Hh, L, s, hum, ST.THIRD_40_8K)[(ST.THIRD_40_8K >= 500) & (ST.THIRD_40_8K <= 2000)]))
    r = AT.auto_treat(W, Hh, L, s, hum, t_room * 1.5)
    assert r["shape_only"] and r["t_fit"] < t_room * 1.5
    assert all(x["type"] != "porous" for x in r["suggested"])
    assert all(x["coverage"] >= 0.005 for x in r["suggested"])
