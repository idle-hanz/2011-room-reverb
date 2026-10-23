"""SL5: treatment physics against textbook values (Cox & D'Antonio ch. 5/7, Everest, Miki 1990)."""
import math
import numpy as np
import pytest
try:
    import _sl_harness as H
except ImportError:
    from tests import _sl_harness as H
import surf_panels as P

F_OCT = np.array([125, 250, 500, 1000, 2000, 4000, 8000.0])


def test_membrane_formula_constants_follow_from_physics():
    # f0 = (1/2pi) sqrt(rho c^2/(m d)): 60/sqrt(md) empty (adiabatic), ~50/sqrt(md) with wool (isothermal)
    for m, d in [(2.7, 0.059), (5.4, 0.119), (13.5, 0.2)]:
        assert P.membrane_f0_physical(m, d, False) == pytest.approx(P.membrane_f0(m, d, False), rel=0.005)
        assert P.membrane_f0_physical(m, d, True) == pytest.approx(P.membrane_f0(m, d, True), rel=0.02)


@pytest.mark.parametrize("m,d", [(2.7, 0.059), (5.4, 0.119), (9.0, 0.1)])
def test_membrane_impedance_peak_matches_design_formula(m, d):
    f = np.geomspace(20, 1000, 4000)
    pk = P.fit_resonance(f, P.membrane_alpha_physical(f, m, d, fill=1.0))
    assert pk["f0"] == pytest.approx(P.membrane_f0(m, d, True), rel=0.06)
    assert 1.5 <= pk["q"] <= 5.0


def test_helmholtz_matches_everest_inch_formula():
    # Everest, Master Handbook of Acoustics: f0 = 200 sqrt(p / (d t')), p = % open, d, t' in inches
    eps, t, a, d = 0.023, 0.012, 0.003, 0.10
    tp_in = (t + 2 * 0.85 * a) / 0.0254
    everest = 200.0 * math.sqrt((eps * 100) / ((d / 0.0254) * tp_in))
    assert P.helmholtz_f0(eps, t, a, d) == pytest.approx(everest, rel=0.08)


@pytest.mark.parametrize("eps,d", [(0.023, 0.10), (0.014, 0.10), (0.05, 0.15)])
def test_perforate_impedance_peak_near_formula(eps, d):
    f = np.geomspace(20, 1000, 4000)
    pk = P.fit_resonance(f, P.perforated_alpha_physical(f, eps, 0.012, 0.003, d, fill_thick=0.025))
    assert pk["f0"] == pytest.approx(P.helmholtz_f0(eps, 0.012, 0.003, d), rel=0.12)
    assert pk["f0"] < P.helmholtz_f0(eps, 0.012, 0.003, d)        # wool behind the holes adds mass: lower


@pytest.mark.parametrize("mid,thick,gap", [("absorber_panel_4in_gap4in", 0.1016, 0.1016),
                                           ("absorber_panel_2in_gap2in", 0.05, 0.05),
                                           ("absorber_panel_1in_gap1in", 0.0254, 0.0254)])
def test_miki_paris_reproduces_the_library_porous_presets(mid, thick, gap):
    lib = P.load_material(mid, H.SW / "presets" / "surfaces")
    a = P.porous_alpha(F_OCT, 15000.0, thick, gap, "random")
    assert np.max(np.abs(a - np.asarray(lib["absorb"]))) <= 0.012
    on_rigid = P.porous_alpha(F_OCT, 15000.0, thick, 0.0, "random")
    assert np.max(np.abs(on_rigid - np.asarray(lib["on_rigid_absorb"]))) <= 0.012


def test_air_gap_extends_the_low_end_and_miki_tends_to_air():
    a0 = P.porous_alpha(F_OCT, 15000.0, 0.05, 0.0)
    a1 = P.porous_alpha(F_OCT, 15000.0, 0.05, 0.05)
    assert a1[0] > a0[0] and a1[1] > a0[1]
    Zc, k = P.miki(np.array([1e6]), 1000.0)
    assert abs(Zc[0] / P.Z0 - 1) < 0.01


def test_resonant_curve_shape():
    f0, q, amax = 125.0, 2.0, 0.6
    assert P.resonant_alpha(f0, f0, q, amax) == pytest.approx(amax)
    f = np.geomspace(20, 1000, 20000)
    pk = P.fit_resonance(f, P.resonant_alpha(f, f0, q, amax))
    assert pk["q"] == pytest.approx(q, rel=0.03)


def test_designs_match_the_box_plan():
    m = P.design_membrane(125.0)
    assert m["build"].startswith("3 mm hardboard") and round(m["d"] * 1000) == 59 and m["f0"] == 125.0
    m = P.design_membrane(62.5)
    assert m["build"].startswith("9 mm plywood") and round(m["d"] * 1000) == 119
    h = P.design_helmholtz(198.4)
    assert round(h["eps"] * 100, 1) == 2.3 and h["d"] == 0.10
    assert P.design_panel(57.0)["type"] == "membrane" and P.design_panel(250.0)["type"] == "helmholtz"


def test_rows_alpha_and_validation():
    card = {"absorb_hz": list(F_OCT), "absorb": [0.02] * 7}
    assert np.allclose(P.alpha_fn(card, [])(F_OCT), 0.02)
    row = dict(id="m", face="D", type="membrane", f0=125.0, q=2.0, amax=0.6, coverage=0.5, on=True)
    a = P.alpha_fn(card, [row])(np.array([125.0, 1000.0]))
    assert a[0] == pytest.approx(0.5 * 0.02 + 0.5 * 0.6, abs=1e-6) and a[1] < 0.1
    sug = P.cards_with_treatment({"D": card}, [dict(row, suggested=True)])
    assert "absorb_fn" not in sug["D"]                     # a suggestion changes nothing until accepted
    off = P.cards_with_treatment({"D": card}, [dict(row, on=False)])
    assert "absorb_fn" not in off["D"]
    assert P.validate_rows([dict(row, coverage=0.5), dict(row, id="n", coverage=0.5)])     # 100 % > 90 %
    assert not P.validate_rows([row])
    sh = P.room_shell_rows()
    assert len(sh) == 4 and all(r["f0"] == 90.0 and r["coverage"] == 0.3 and r["assumed"] for r in sh)
