"""Binaural mode: Play-side proofs + the gaps left after Build's 1 Oct build (box, 1 Oct 2026).

Build's acceptance file (handoff_binaural/tests/test_binaural_mode_acceptance.py) proves the Python/Render side
(22/22 on the 1 Oct 15:50 snapshot). These tests add what it does not cover:
  * Play (real fdn_worklet.js + live_stereo.wasm in node): tail IC vs the head target, direct ILD/ITD sign,
    mirror symmetry of the direct path.
  * The open items of BINAURAL_MODE_BRIEF.md §2.2 / packaging, as XFAIL probes (they PASS once built).
Needs: node, handoff_binaural/ and mic_fitter/ next to software/ (as the app does today).
Read-only on --sw.
"""
from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / 'harness' / 'lib'
SR = 48000
BASE = {"decay_lock": True, "decay_s": 1.8, "humidity": 0.5, "early_wet": 1.0, "mic_setup": "binaural",
        "binaural_preset": "SADIE2_KU100"}


def _pack(sw):
    p = Path(sw).parent / 'handoff_binaural'
    if not (p / 'binaural_fitter' / 'tail_ic.py').exists():
        pytest.skip('handoff_binaural/ (with binaural_fitter) is not next to software/')
    return p


def _play(sw, pytestconfig, body, over, secs, tmp):
    py = pytestconfig.getoption('--app-python')
    pj = Path(tmp) / 'p.json'
    out = Path(tmp) / 'o.f32'
    subprocess.run([py, str(LIB / 'dump_params.py'), str(sw), json.dumps(body), str(pj), str(SR)],
                   check=True, capture_output=True)
    subprocess.run([pytestconfig.getoption('--node'), str(LIB / 'wasm_run.js'), str(sw), str(pj), json.dumps(over),
                    'ir', str(secs), str(out)], check=True, capture_output=True)
    return json.load(open(pj)), np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)


def _band_db(x, f0):
    n = 1 << 17
    X = np.fft.rfft(x, n); f = np.fft.rfftfreq(n, 1 / SR)
    m = (f > f0 / 2 ** 0.5) & (f < f0 * 2 ** 0.5)
    return 10 * np.log10(np.mean(np.abs(X[m]) ** 2) + 1e-30)


@pytest.mark.phase('BINAURAL')
def test_binaural_play_tail_coherence_matches_head(sw, pytestconfig):
    """Play FDN tail (early/direct off), 8 s decay so the estimator noise is like the Render test's 4 s g=0.999 tail.
    Same tolerance as the locked Render test, plus the H·D tail: max |dIC| <= 0.16, RMS <= 0.06
    (1/3 oct 125 Hz - 8 kHz). Plain H was inside 0.15. Column signs land at 0.151.
    Box 1 Oct: 0.118 / 0.052 (no IC mixer: 0.54 / 0.20 at 1.8 s)."""
    pack = _pack(sw)
    sys.path.insert(0, str(pack))
    from binaural_fitter import tail_ic as T
    with tempfile.TemporaryDirectory() as tmp:
        P, x = _play(sw, pytestconfig, dict(BASE, decay_s=8.0), {"early_wet": 0, "direct_wet": 0}, 4.6, tmp)
    assert P.get('ic_hp') and len(P['ic_hp']) % 2 == 1, 'live_params sends no IC mixer FIRs'
    a0 = int(0.1 * SR) + 256
    f, c = T.measure_ic(x[a0:, 0], x[a0:, 1], SR)
    got = T.band_ic(f, c, T.THIRD_OCT)
    ft, ict = T.target_ic('SADIE2_KU100')
    want = np.interp(np.log(T.THIRD_OCT), np.log(ft), ict)
    d = got - want
    mx = float(np.max(np.abs(d)))
    rms = float(np.sqrt(np.mean(d ** 2)))
    assert mx <= 0.16 and rms <= 0.06, (round(mx, 3), round(rms, 3), np.round(got, 2), np.round(want, 2))


@pytest.mark.slow
@pytest.mark.phase('BINAURAL')
def test_binaural_play_tail_coherence_ensemble(sw, pytestconfig):
    """Box 2 Oct (S4b verify, gate audit). The single-scene max |dIC| is one draw of a scene-dependent
    quantity: on six scenes plain H spans 0.115-0.168 and H.D 0.069-0.193 (the 0.151 of the main test is
    the signs at that one scene, unchanged with a 9 s IR). The ensemble is what must not regress:
    mean of max |dIC| <= 0.15, every scene <= 0.20, mean RMS <= 0.06 (16:30 H.D: 0.133 / 0.193 / 0.050;
    plain H: 0.132 / 0.168 / 0.053)."""
    pack = _pack(sw)
    sys.path.insert(0, str(pack))
    from binaural_fitter import tail_ic as T
    ft, ict = T.target_ic('SADIE2_KU100')
    want = np.interp(np.log(T.THIRD_OCT), np.log(ft), ict)
    scenes = [{}, {'sx': 2.0}, {'sz': 5.0}, {'mcx': 2.5}, {'two_sources': True}, {'decay_s': 6.0}]
    mxs, rmss = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for ov in scenes:
            body = dict(BASE, decay_s=8.0); body.update(ov)
            _, x = _play(sw, pytestconfig, body, {"early_wet": 0, "direct_wet": 0}, 4.6, tmp)
            a0 = int(0.1 * SR) + 256
            f, c = T.measure_ic(x[a0:, 0], x[a0:, 1], SR)
            d = T.band_ic(f, c, T.THIRD_OCT) - want
            mxs.append(float(np.max(np.abs(d)))); rmss.append(float(np.sqrt(np.mean(d ** 2))))
    assert np.mean(mxs) <= 0.15 and max(mxs) <= 0.20 and np.mean(rmss) <= 0.06, (np.round(mxs, 3), np.round(rmss, 3))


@pytest.mark.phase('BINAURAL')
def test_binaural_play_direct_left_source_left_ear_first_and_louder(sw, pytestconfig):
    """Source left of the head (sx 1.0, head at mcx 3.0): L ear earlier and louder at 4 kHz. Box 1 Oct: +15.4 dB, 271 us."""
    _pack(sw)
    with tempfile.TemporaryDirectory() as tmp:
        _, x = _play(sw, pytestconfig, dict(BASE, sx=1.0, mcx=3.0), {"early_wet": 0, "fdn_wet": 0}, 0.2, tmp)
    assert _band_db(x[:, 0], 4000) - _band_db(x[:, 1], 4000) > 6.0
    assert np.argmax(np.abs(x[:, 0])) < np.argmax(np.abs(x[:, 1]))


@pytest.mark.phase('BINAURAL')
def test_binaural_play_direct_is_mirror_exact(sw, pytestconfig):
    """Direct only: source at mcx - 2 vs mcx + 2 gives (L, R) == (R, L). Box 1 Oct: bit-exact."""
    _pack(sw)
    with tempfile.TemporaryDirectory() as tmp:
        _, a = _play(sw, pytestconfig, dict(BASE, sx=1.0, mcx=3.0), {"early_wet": 0, "fdn_wet": 0}, 0.2, tmp)
    with tempfile.TemporaryDirectory() as tmp:
        _, b = _play(sw, pytestconfig, dict(BASE, sx=5.0, mcx=3.0), {"early_wet": 0, "fdn_wet": 0}, 0.2, tmp)
    err = np.sum((a - b[:, ::-1]) ** 2) / max(np.sum(a ** 2), 1e-30)
    assert err <= 1e-6


# ---- gaps (XFAIL until built; FAIL never expected) ----

def _gap(cond, reason):
    if not cond:
        pytest.xfail(reason)


@pytest.mark.phase('BINAURAL')
def test_gap_hrtf_tables_vendored_in_software(sw):
    """Today the app reads ../handoff_binaural/presets/binaural (engine/early_field.py binaural_pack_dir). Without that
    folder, live_params raises FileNotFoundError (VERIFIED on a copy, 1 Oct). Ship the tables + licence notices in software/."""
    loc = sw / 'mic_colour' / 'presets' / 'binaural'
    ok = all((loc / n).exists() for n in ('SADIE2_KU100.json', 'sos_tables/48000/SADIE2_KU100.json',
                                          'sos_tables/44100/SADIE2_KU100.json', 'tail_ic/SADIE2_KU100.json'))
    lic = any((sw / p).exists() for p in ('LICENSES/NOTICE_SADIE_II.txt', 'mic_colour/presets/binaural/LICENSES/NOTICE_SADIE_II.txt'))
    _gap(ok and lic, 'BINAURAL gap: HRTF tables/licences not vendored in software/ (depends on ../handoff_binaural)')


@pytest.mark.phase('BINAURAL')
def test_gap_floor_head_rotate_handle(src):
    """Brief §2.1: head yaw slider (done) AND a rotate handle on the Floor view (a drag kind for head yaw)."""
    js = src('static/js/room_editor.js')
    _gap('head_yaw' in js, 'BINAURAL gap: no head-yaw rotate handle on the Floor view (only a look arrow)')


@pytest.mark.phase('BINAURAL')
def test_gap_head_with_ears_drawing_and_3d(src):
    """Brief §2.2: head with ears in the top, side and 3D views."""
    ok = 'binaural' in src('static/js/room_3d.js') and 'binaural' in src('static/js/mic_desk.js')
    _gap(ok, 'BINAURAL gap: no head-with-ears drawing (room_3d.js / mic_desk.js have no binaural branch)')


@pytest.mark.phase('BINAURAL')
def test_gap_hrtf_polar_and_ild_panel(src):
    """Brief §2.2: capsule polar replaced by an HRTF polar (500/2k/4k/8k per ear) + ILD-vs-azimuth panel from the SOS."""
    blob = src('static/js/mic_desk.js') + src('static/js/polar_field.js') + src('static/js/app.js') + src('app_server.py')
    import re
    low = blob.lower()
    _gap(re.search(r'hrtf[_ -]?polar', low) is not None and re.search(r'\bild\b', low) is not None,
         'BINAURAL gap: no HRTF polar / ILD panel')


@pytest.mark.phase('BINAURAL')
def test_gap_play_shows_unsupported_rate_notice(src):
    """Brief §2.2/§4: the notice is in Render's status (app_server) and in live_params ('colour_notice'),
    but the Play page never shows it."""
    _gap('colour_notice' in src('static/js/app.js') or 'colour_notice' in src('static/js/live_fdn.js'),
         'BINAURAL gap: Play does not display colour_notice (e.g. 96 kHz device: colour OFF silently)')
