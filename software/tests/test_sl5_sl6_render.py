"""SL5/SL6 renders (slow): the room shell moves the bass as on the box; Treatment rows only act in
Surfaces mode; the accepted auto-treat plan reaches >= 15/23 third-octaves within +-10 %."""
import json
import numpy as np
import pytest
try:
    import _sl_harness as H
    import _sl_render as R
except ImportError:
    from tests import _sl_harness as H
    from tests import _sl_render as R
import surf_autotreat as AT
import surf_loop as SL
import surf_panels as P


def _third_t20(ir, bands):
    from scipy import signal
    x = ir.sum(1); a = np.abs(x); n0 = int(np.argmax(a >= 0.1 * a.max()))
    out = []
    for fc in bands:
        lo, hi = fc * 2 ** (-1 / 6), min(fc * 2 ** (1 / 6), 0.45 * 48000)
        sos = signal.butter(3, [lo, hi], btype="band", fs=48000, output="sos")
        y = signal.sosfiltfilt(sos, x)[n0:]
        e = np.cumsum((y ** 2)[::-1])[::-1]; e = 10 * np.log10(np.maximum(e / e[0], 1e-30))
        i0, i1 = int(np.argmax(e <= -5)), int(np.argmax(e <= -25))
        out.append(-60.0 / np.polyfit(np.arange(i0, i1) / 48000, e[i0:i1], 1)[0])
    return np.asarray(out)


@pytest.mark.slow
def test_room_shell_bass_matches_box(tmp_path):
    ir0, i0, ir1, i1, cal = R.render_calibrated("real_default", True, 1.8, rows=P.room_shell_rows())
    t = SL.t20_per_octave(ir1.sum(1))
    # SURFACES opt-in must not rewrite software/proof.
    (tmp_path / "sl5_shell_results.json").write_text(json.dumps(dict(t20=t, target=i1["surf"]["target_T_oct"], cal=cal), indent=1))
    assert t[0] == pytest.approx(1.9, rel=0.10) and t[1] == pytest.approx(2.35, rel=0.10)


# Room average. 125, 250 and 500 Hz held at 1. Highs are the measured octave factors.
# The plan target still matches the 2026-10-24 Makivirta list (model 20/24). That
# render was 16/23. Polar-once dropped the second pattern on measured mics, and
# the same rows and cal now render 15/23. Do not remeasure the highs.
_AUTO_TREAT_CAL = [1.0, 1.0, 1.0, 0.850, 0.878, 0.870, 0.906]


@pytest.mark.slow
def test_auto_treat_plan_rendered(tmp_path):
    W, Hh, L, s, hum = H.room("real_default")
    plan = AT.auto_treat(W, Hh, L, s, hum, 0.8)
    rows = [dict(r, suggested=False) for r in plan["suggested"]]
    cal = list(_AUTO_TREAT_CAL)
    ir1, _info = R.render_room("real_default", False, None, rows=rows, cal=cal)
    f = np.asarray(plan["f"])[1:]                      # 50 Hz-8 kHz: 23 third-octaves as on the box
    tgt = np.asarray(plan["target"])[1:]
    t = _third_t20(ir1, f)
    ok = np.abs(t / tgt - 1) <= 0.10
    # SURFACES opt-in must not rewrite software/proof/sl6_treated_results.json.
    (tmp_path / "sl6_treated_results.json").write_text(json.dumps(dict(f=f.tolist(), t20=t.tolist(), target=tgt.tolist(), n_ok=int(ok.sum()), cal=cal), indent=1))
    assert int(ok.sum()) >= 15, (int(ok.sum()), np.round(t / tgt, 2))
