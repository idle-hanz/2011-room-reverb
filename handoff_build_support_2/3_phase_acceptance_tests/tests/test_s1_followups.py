"""S1 follow-ups found on the 1 Oct 22:10 snapshot (box, read-only on --sw).

* The realised Play/Render air filter (two RBJ shelves, slope 1) vs ISO 9613-1, not only the analytic fit
  that Build's test_p2_iso_air_fit_within_tolerance checks. Box 1 Oct: max 0.37 dB / RMSE 0.13 dB at 30 m.
* Packaging: engine/air_iso.py reads ../air_fitter/presets. Without that sibling folder any room with
  humidity > 0 (client default 0.35) raises FileNotFoundError in live_params (VERIFIED on a copy, 1 Oct).
* /api/defaults and parameters.csv should list the new keys (air_climate, air_iso).
"""
from __future__ import annotations
import sys
import numpy as np
import pytest


@pytest.mark.phase('P2')
def test_p2_realised_rbj_pair_close_to_iso(sw, app):
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    try:
        import air_iso, early_field as ef
    except ImportError:
        pytest.xfail('P2 ISO air not in tree')
    sr = 48000
    f = np.geomspace(100.0, 16000.0, 200)
    z = np.exp(-2j * np.pi * f / sr)
    for d in (1.0, 5.0, 10.0, 30.0):
        lo, hi = ef.iso_shelf_pair(d, sr, 1.0, 'studio_20C_50RH')
        r = np.zeros_like(f)
        for c in (lo, hi):
            if c is None:
                continue
            b0, b1, b2, a0, a1, a2 = c if len(c) == 6 else (c[0], c[1], c[2], 1.0, c[3], c[4])
            r += 20 * np.log10(np.abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)))
        iso = air_iso.iso_path_loss_db(f, d, 'studio_20C_50RH')
        err = r - iso
        rmse = float(np.sqrt(np.mean(err ** 2)))
        assert np.max(np.abs(err)) <= 0.5 and rmse <= 0.25, (d, float(np.max(np.abs(err))), rmse)


@pytest.mark.phase('P2')
def test_gap_air_presets_vendored_in_software(sw):
    src = (sw / 'engine' / 'air_iso.py')
    if not src.exists():
        pytest.xfail('P2 ISO air not in tree')
    local = any(sw.rglob('studio_20C_50RH.json'))
    if not local:
        pytest.xfail('S1 gap: ISO air presets not vendored in software/ (engine/air_iso.py reads ../air_fitter/presets)')


@pytest.mark.phase('P0.5')
def test_gap_new_air_keys_in_defaults_and_parameters(sw, app):
    ok_def = 'air_climate' in app.DEFAULTS and 'air_iso' in app.DEFAULTS
    csv = (sw / 'parameters.csv').read_text(encoding='utf-8') if (sw / 'parameters.csv').exists() else ''
    ok_csv = 'air_climate' in csv
    if not (ok_def and ok_csv):
        pytest.xfail(f'S1 gap: air_climate/air_iso missing from DEFAULTS ({ok_def}) or parameters.csv ({ok_csv})')


def _pair_db(pair, f, sr):
    z = np.exp(-2j * np.pi * f / sr)
    r = np.zeros_like(f, dtype=float)
    for c in pair:
        if c is None:
            continue
        b0, b1, b2, a0, a1, a2 = c if len(c) == 6 else (c[0], c[1], c[2], 1.0, c[3], c[4])
        r += 20.0 * np.log10(np.abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)))
    return r


@pytest.mark.phase('P2')
def test_d8_humidity_sets_iso_rh(sw, app):
    """D8: right is drier, and that is more 8–16 kHz loss down to the peak.

    Humidity 0 is the unchanged bypass. 0.35 is the climate preset's RH.
    The dry preset is past the treble-loss peak, so its 0.35 detent stays
    on the peak. 1.0 is that peak. Two humidities above 0 differ, and the
    higher slider is the darker one.
    """
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    try:
        import air_iso
        import early_field as ef
        import render_pipeline as rp
    except ImportError:
        pytest.xfail('P2 ISO air not in tree')
    sr = 48000
    f = np.geomspace(100.0, 16000.0, 200)
    band = (f >= 8000.0) & (f <= 16000.0)
    x = np.zeros(32, dtype=float)
    x[0] = 1.0
    y = ef.apply_air_absorption(x, 30.0, sr, 0.0, air_lp=1.0, air_shelf=1.0)
    assert y is x and float(x[0]) == 1.0

    peak_20 = air_iso.peak_rh_pct(20.0)
    peak_22 = air_iso.peak_rh_pct(22.0)
    assert abs(peak_20 - 21.7) < 1e-9 and abs(peak_22 - 19.2) < 1e-9
    for climate in ('studio_20C_50RH', 'dry_20C_20RH', 'humid_20C_80RH', 'warm_22C_40RH'):
        assert air_iso.rh_pct_from_slider(0.0, climate) is None
    assert abs(air_iso.rh_pct_from_slider(0.35, 'studio_20C_50RH') - 50.0) < 1e-9
    assert abs(air_iso.rh_pct_from_slider(0.35, 'humid_20C_80RH') - 80.0) < 1e-9
    assert abs(air_iso.rh_pct_from_slider(0.35, 'warm_22C_40RH') - 40.0) < 1e-9
    assert abs(air_iso.rh_pct_from_slider(0.35, 'dry_20C_20RH') - peak_20) < 1e-9
    assert abs(air_iso.rh_pct_from_slider(1.0, 'studio_20C_50RH') - peak_20) < 1e-9
    assert abs(air_iso.rh_pct_from_slider(1.0, 'warm_22C_40RH') - peak_22) < 1e-9
    assert air_iso.rh_pct_from_slider(0.01, 'studio_20C_50RH') > 85.0

    rh_lo = air_iso.rh_pct_from_slider(0.2, 'studio_20C_50RH')
    rh_mid = air_iso.rh_pct_from_slider(0.35, 'studio_20C_50RH')
    rh_hi = air_iso.rh_pct_from_slider(1.0, 'studio_20C_50RH')
    assert rh_hi < rh_mid < rh_lo, (rh_lo, rh_mid, rh_hi)
    low = _pair_db(ef.iso_shelf_pair(30.0, sr, 1.0, 'studio_20C_50RH', 0.2), f, sr)
    high = _pair_db(ef.iso_shelf_pair(30.0, sr, 1.0, 'studio_20C_50RH', 0.8), f, sr)
    delta = float(high[band].mean() - low[band].mean())
    assert delta < -0.02, delta

    for humidity, climate in ((0.2, 'studio_20C_50RH'), (1.0, 'studio_20C_50RH'), (0.8, 'warm_22C_40RH')):
        rh = air_iso.rh_pct_from_slider(humidity, climate)
        for d in (1.0, 5.0, 10.0, 30.0):
            got = _pair_db(ef.iso_shelf_pair(d, sr, 1.0, climate, humidity), f, sr)
            iso = air_iso.iso_path_loss_db(f, d, climate, rh)
            err = got - iso
            mx = float(np.max(np.abs(err)))
            rmse = float(np.sqrt(np.mean(err ** 2)))
            assert mx <= 0.5 and rmse <= 0.25, (climate, humidity, d, mx, rmse)
        live = _live_shelf_db(rp, 30.0, sr, humidity, climate, f)
        render = _pair_db(ef.iso_shelf_pair(30.0, sr, 1.0, climate, humidity), f, sr)
        assert np.max(np.abs(live - render)) < 1e-4

    off_g, _lp, off_a, off_b = rp._live_air_for_distance(30.0, sr, 0.0, 0.0, 1.0, 'studio_20C_50RH', True)
    assert off_g == 0.0 and off_a['on'] is False and off_b['on'] is False

    html = (sw / 'static' / 'index.html').read_text(encoding='utf-8')
    js = (sw / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    assert 'Air amount (humidity)' in html
    assert 'Right is drier' in html
    assert 'Relative humidity' in html
    assert 'var AIR_RH_NOMINAL = 0.35' in js
    assert 'var AIR_RH_WET = 90' in js
    assert '20: 21.7' in js and '22: 19.2' in js
    for climate, preset_rh in (
        ('studio_20C_50RH', 50),
        ('dry_20C_20RH', 20),
        ('humid_20C_80RH', 80),
        ('warm_22C_40RH', 40),
    ):
        assert f'{climate}: {preset_rh}' in js
        assert int(air_iso.climate_record(climate)['conditions']['relative_humidity_pct']) == preset_rh
    assert 'Math.max(preset, peak)' in js
    assert 'AIR_RH_WET + (h / AIR_RH_NOMINAL) * (anchor - AIR_RH_WET)' in js
    assert '((h - AIR_RH_NOMINAL) / (1 - AIR_RH_NOMINAL)) * (peak - anchor)' in js


def _live_shelf_db(rp, dist, sr, humidity, climate, f):
    _g, _lp, shelf, shelf2 = rp._live_air_for_distance(dist, sr, humidity, 0.0, 1.0, climate, True)
    z = np.exp(-2j * np.pi * f / sr)
    r = np.zeros_like(f, dtype=float)
    for sh in (shelf, shelf2):
        if not sh.get('on'):
            continue
        b0, b1, b2, a1, a2 = sh['b0'], sh['b1'], sh['b2'], sh['a1'], sh['a2']
        r += 20.0 * np.log10(np.abs((b0 + b1 * z + b2 * z * z) / (1.0 + a1 * z + a2 * z * z)))
    return r


# ---------------------------------------------------------------------------
# Added by the box on 2 Oct (D8 verification, snapshot 06:15 BST).
# ISO 9613-1:1993 Table 1(g), 10 degC, 101.325 kPa, dB/km (official iTeh preview).
# Frequencies are the exact midband values the table uses.
_ISO_T1_10C = {
    # f_exact: {RH%: dB/km}
    1000.0: {10: 21.6, 50: 4.26, 90: 3.54},
    3981.07: {10: 57.3, 50: 46.7, 90: 25.7},
    7943.28: {10: 69.4, 50: 155.0, 90: 92.4},
}


@pytest.mark.phase('P2')
def test_iso_alpha_matches_iso9613_table1(sw, app):
    """air_iso's ISO 9613-1 alpha must match the standard's own Table 1 (2 % tol).

    ISO 9613-1 note 3: the molar concentration h is a PERCENTAGE. Using a fraction
    (RH/100 * psat/p) makes h 100x too small: 8 kHz at 10 degC / 50 % comes out
    ~12 dB/km instead of 155 dB/km, and the RH direction at 8-16 kHz is inverted.
    """
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    try:
        import air_iso
    except ImportError:
        pytest.xfail('P2 ISO air not in tree')
    fn = getattr(air_iso, '_iso_alpha_db_per_m', None)
    if fn is None:
        pytest.xfail('no _iso_alpha_db_per_m in air_iso')
    bad = []
    for f, row in _ISO_T1_10C.items():
        for rh, want in row.items():
            got = 1000.0 * float(fn(np.array([f]), 10.0, float(rh), 101.325)[0])
            if abs(got - want) > 0.02 * want:
                bad.append((f, rh, round(got, 2), want))
    assert not bad, f'(f, RH, engine dB/km, ISO Table 1 dB/km): {bad}'


@pytest.mark.phase('P2')
def test_d8_treble_loss_monotonic_across_slider(sw, app):
    """D8: moving the air slider right never reduces 8-16 kHz loss (realised Play/Render pair, 30 m).

    Checked on the realised dual-RBJ shelves at 20 slider values 0.05..1.0, studio climate,
    8-16 kHz mean in dB. Allowed wobble 0.02 dB per step.
    """
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    try:
        import early_field as ef
    except ImportError:
        pytest.xfail('P2 ISO air not in tree')
    sr = 48000
    f = np.geomspace(100.0, 16000.0, 400)
    band = f >= 8000.0
    hs = np.linspace(0.05, 1.0, 20)
    try:
        vals = [float(_pair_db(ef.iso_shelf_pair(30.0, sr, 1.0, 'studio_20C_50RH', h), f, sr)[band].mean()) for h in hs]
    except TypeError:
        pytest.xfail('iso_shelf_pair has no humidity argument (D8 not in tree)')
    up = [(round(float(hs[i]), 3), round(vals[i], 3), round(vals[i + 1], 3)) for i in range(len(vals) - 1) if vals[i + 1] > vals[i] + 0.02]
    assert not up, f'less treble loss when moving right (h, loss_db, next_loss_db): {up}'
