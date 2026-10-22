"""SL1: Room result model (read-only). Must match the box model to <= 1 % on the 3 rooms."""
import math
import numpy as np
import pytest
import _sl_harness as H
import surf_target as ST

FX = H.fixture("fixture_box_targets.json")["targets"]


@pytest.mark.parametrize("name,room,anchor", [("g4_studio_dir", "studio_panelled", None),
                                              ("g4_brick_dir", "bare_brick_plaster", None),
                                              ("g3_dir", "real_default", 1.8)])
def test_matches_box_model_within_1pct(name, room, anchor):
    W, Hh, L, s, hum = H.room(room)
    T = ST.anchored_target(W, Hh, L, s, hum, ST.BANDS, anchor)
    assert np.max(np.abs(T / np.asarray(FX[name]) - 1)) <= 0.01


def test_face_eq_boost_never_enters_the_loop_but_a_cut_does():
    W, Hh, L, s, hum = H.room("real_default")
    T0 = ST.room_target(W, Hh, L, s, hum, ST.BANDS)
    boost = {k: dict(c, eq={"peak_hz": 1000, "peak_db": 6.0, "peak_q": 1}) for k, c in s.items()}
    cut = {k: dict(c, eq={"peak_hz": 1000, "peak_db": -6.0, "peak_q": 1}) for k, c in s.items()}
    assert np.allclose(ST.room_target(W, Hh, L, boost, hum, ST.BANDS), T0)
    assert ST.room_target(W, Hh, L, cut, hum, ST.BANDS)[3] < 0.8 * T0[3]


def test_air_shortens_only_the_top():
    W, Hh, L, s, hum = H.room("real_default")
    with_air = ST.room_target(W, Hh, L, s, hum, ST.BANDS)
    no_air = ST.room_target(W, Hh, L, s, hum, ST.BANDS, include_air=False)
    assert abs(with_air[0] / no_air[0] - 1) < 0.02 and with_air[-1] < 0.7 * no_air[-1]


def test_yardsticks():
    assert ST.ebu_tm(144.0) == pytest.approx(0.2823, abs=1e-4)
    assert ST.schroeder_hz(2.65, 144.0) == pytest.approx(271.3, abs=0.5)
    ax = [m for m in ST.modes(6.0, 3.0, 8.0, 60.0) if m[2] == "axial"]
    assert [round(m[0], 1) for m in ax][:3] == [21.4, 28.6, 42.9]
    assert any(m[1] == (0, 1, 0) and round(m[0], 1) == 57.2 for m in ax)
    t = ST.makivirta_target(np.array([50.0, 300.0, 1000.0]), 0.8)
    assert list(np.round(t, 3)) == [1.0, 0.8, 0.8]


def test_room_result_payload():
    W, Hh, L, s, hum = H.room("real_default")
    r = ST.room_result(W, Hh, L, s, hum, decay_s=1.8, decay_lock=True)
    n = len(r["f"])
    assert n == 25 and all(len(r[k]) == n for k in ("T_faces", "T_faces_air", "target", "within_10pct", "ebu_pass"))
    m = [t for f, t in zip(r["f"], r["T_faces_air"]) if 500 <= f <= 1000]
    assert np.mean(m) == pytest.approx(1.8, rel=0.02)          # lock on: anchored to the dial
    r2 = ST.room_result(W, Hh, L, s, hum, decay_s=1.8, decay_lock=False)
    assert r2["anchor_s"] is None and r2["T_absolute_mid"] > 2.0  # untreated plaster room, absolute
