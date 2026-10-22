"""SL2: Surfaces mode in the Render loop. Fast design tests + slow render tests (-m slow).
Flat (2011) must stay bit-exact: the box proof (hash_scenes.py, pristine vs patched tree) is in
../proof/flat_bitexact.json; on Build day the existing golden test is the authority."""
import inspect
import math
import os
import numpy as np
import pytest
import _sl_harness as H
import surf_loop as SL
import surf_panels as P
import surf_target as ST
from early_field import LIVE_32
from fdn import FDN
from surface_colour import surfaces_hit_by_n

SR = 48000
ROOM = (6.0, 3.0, 8.0)
DELAYS = [int(x) for x in np.linspace(331, 2399, 32)]


def _spec(directional=True, anchor=1.8, room="real_default"):
    W, Hh, L, s, hum = H.room(room)
    spec = SL.make_spec(W, Hh, L, s, hum, anchor, directional=directional)
    return dict(spec, hits=[surfaces_hit_by_n(LIVE_32[i]) for i in range(32)])


@pytest.fixture(scope="module")
def surf_fdn():
    sp = _spec()
    f = FDN(DELAYS, g=1 / math.sqrt(32), room=ROOM, sr=SR, depth_per_axis=1.5, n=32, line_t60=1.8, surf=sp)
    return f, sp


def test_flat_fdn_has_no_sections_and_keeps_its_cuts():
    f = FDN(DELAYS, g=1 / math.sqrt(32), room=ROOM, sr=SR, depth_per_axis=1.5, n=32, line_t60=1.8)
    assert f._sl is None and f.peaking and int(f._use_peak.sum()) == 32


def test_lock_off_never_designs_sections():
    f = FDN(DELAYS, g=0.15, room=ROOM, sr=SR, depth_per_axis=1.5, n=32, line_t60=0.0, surf=_spec())
    assert f._sl is None


def test_sections_shape_and_stability(surf_fdn):
    f, sp = surf_fdn
    rep = sp["report"][-1]
    assert f._sl.shape == (32, 3, 5)
    assert rep["stab"]["max_loop_db"] < 0.0 and rep["stab"]["max_pole"] < 1.0
    assert rep["median_line_oct_pct"] < 15.0


def test_d_sl3_cuts_replaced_except_below_30_hz(surf_fdn):
    f, sp = surf_fdn
    # default room: X 28.6 Hz and Z 21.4 Hz cuts stay (folded into the fit); Y 57.2 Hz is replaced by panels
    kept_axes = {("X", "Y", "Z")[i % 3] for i in range(32) if f._use_peak[i]}
    assert kept_axes == {"X", "Z"} and sp["report"][-1]["kept_cuts"] == int(f._use_peak.sum())


def test_impulse_decays_and_stays_finite(surf_fdn):
    f, _ = surf_fdn
    inj = np.zeros((SR, 32)); inj[0, :] = 1.0
    y = f.process_block_poly(inj).sum(1)
    assert np.all(np.isfinite(y))
    e = [float(np.sum(y[a:a + 4800] ** 2)) for a in range(0, SR, 4800)]
    assert e[-1] < e[1] * 0.1


def test_directional_rates_keep_the_room_mean():
    W, Hh, L, s, hum = H.room("real_default")
    hits = [surfaces_hit_by_n(LIVE_32[i]) for i in range(32)]
    rd, T = SL.line_rates(DELAYS, SR, W, Hh, L, s, hum, SL.FIT_F, True, hits, 1.8)
    ra, _ = SL.line_rates(DELAYS, SR, W, Hh, L, s, hum, SL.FIT_F, False, hits, 1.8)
    tau = np.asarray(DELAYS, float) / SR
    mean_d = (tau[:, None] * rd).sum(0) / tau.sum()
    assert np.allclose(mean_d, ra[0], rtol=1e-9)              # kappa normalisation: same room T(f)
    assert np.std(rd[:, 30]) > 0.05 * np.mean(rd[:, 30])       # but lines really differ by direction


def test_scattering_floor_is_half():
    assert SL.S_MIN == 0.5


def test_t20_and_calibration_helpers():
    rng = np.random.default_rng(1)
    t = np.arange(int(2.5 * SR)) / SR
    ir = rng.standard_normal(len(t)) * 10 ** (-3 * t / 1.0)
    t20 = SL.t20_per_octave(ir, SR)
    assert np.all(np.abs(np.asarray(t20) - 1.0) < 0.12)
    assert SL.calibration_factors([2.0, 0.1, 1.1, 1, 1, 1, float("nan")], [1.0] * 7) == [1.6, 0.6, 1.1, 1.0, 1.0, 1.0, 1.0]


# ---------------------------------------------------------------- slow: real renders
def _render(**over):
    import _sl_render as R
    return R.render_body(**over)


@pytest.mark.slow
def test_ui_body_flat_explicit_equals_absent_bit_exact():
    a, _ = _render()
    b, _ = _render(decay_mode="flat", surf_treatment=P.room_shell_rows())
    assert a.tobytes() == b.tobytes()


@pytest.mark.slow
def test_flat_explicit_equals_absent_bit_exact():
    a, _ = _render(ir_length_ms=400)
    b, _ = _render(ir_length_ms=400, decay_mode="flat", surf_cal=[1.3] * 7,
                   surf_treatment=[dict(id="x", face="D", type="membrane", f0=125.0, q=2.0, amax=0.6, coverage=0.5)])
    assert a.tobytes() == b.tobytes()


@pytest.mark.slow
def test_surfaces_render_default_room_room_average_matches_prototype():
    import _sl_render as R
    ir, info = R.render_room("real_default", directional=False, anchor=1.8)
    assert np.all(np.isfinite(ir)) and np.max(np.abs(ir)) < 1.0
    assert all(b["stab"]["max_loop_db"] < 0 for b in info["surf"]["buses"])
    t20 = SL.t20_per_octave(ir.sum(1), SR)
    err = np.asarray(t20) / np.asarray(info["surf"]["target_T_oct"]) - 1
    # Room-average lines, before calibration. The box prototype (fold) measured -10 / -32 % at 125 / 250 Hz;
    # the prebuild run gave -12 / -33 %. This is why SL4 (directional + calibration) exists.
    assert -0.40 <= err[0] <= 0.0 and -0.40 <= err[1] <= 0.0, err
    assert np.max(np.abs(err[2:])) <= 0.15, err


@pytest.mark.slow
def test_surfaces_then_flat_leaves_no_state_behind():
    a, _ = _render(ir_length_ms=400)
    _render(ir_length_ms=400, decay_mode="surfaces")
    b, _ = _render(ir_length_ms=400)
    assert a.tobytes() == b.tobytes()
