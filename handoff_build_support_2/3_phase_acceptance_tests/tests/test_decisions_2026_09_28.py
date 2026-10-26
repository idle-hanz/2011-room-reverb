"""Idle's locked decisions of 28 Sep 2026 (build_support_2/DECISIONS_LOCKED_2026-09-28.md).
A decision that is not in the tree yet gives XFAIL with the measured numbers (same semantics as the phase
suite: XFAIL = not landed). Once the probe finds it, the criterion must hold or the test FAILs."""
from __future__ import annotations
import json, re
import numpy as np
import pytest
from pathlib import Path
from conftest import call_harness

SR = 48000

# app.js MIC_PRESETS (lines 6-55); C capsule off for the two-capsule setups, on for MS.
K1_PRESETS = {
    'xy_90':  dict(space=0.01, toe_half_deg=45, pattern_l='cardioid', pattern_c='cardioid', pattern_r='cardioid', yaw_l_deg=-45, yaw_r_deg=45, mic_gain_c=0),
    'xy_120': dict(space=0.01, toe_half_deg=60, pattern_l='cardioid', pattern_c='cardioid', pattern_r='cardioid', yaw_l_deg=-60, yaw_r_deg=60, mic_gain_c=0),
    'ortf':   dict(space=0.17, toe_half_deg=55, pattern_l='cardioid', pattern_c='cardioid', pattern_r='cardioid', yaw_l_deg=-55, yaw_r_deg=55, mic_gain_c=0),
    'nos':    dict(space=0.30, toe_half_deg=45, pattern_l='cardioid', pattern_c='cardioid', pattern_r='cardioid', yaw_l_deg=-45, yaw_r_deg=45, mic_gain_c=0),
    'din':    dict(space=0.20, toe_half_deg=45, pattern_l='cardioid', pattern_c='cardioid', pattern_r='cardioid', yaw_l_deg=-45, yaw_r_deg=45, mic_gain_c=0),
    'ms':     dict(space=0.05, toe_half_deg=90, pattern_l='cardioid', pattern_c='omni', pattern_r='cardioid', yaw_l_deg=-90, yaw_r_deg=90, mic_gain_c=1),
}
SPACED = {'ortf', 'nos', 'din'}
# Source well to the LEFT of the stand (x = 1 m, stand at x = 3 m in a 6 m wide room): about 32 deg left.
K1_BASE = dict(W=6, H=3, L=8, sx=1.0, sy=1.5, sz=4.75, mcx=3, mcz=1.5, my=1.5, yaw_c_deg=0, car_omni=1,
               humidity=0.0, decay_lock=True, decay_s=1.8, colour_mode='MEASURED_SHELF')


def _k1_landed(src):
    return 'YAW_X_SIGN' in src('engine/maths_look.py') and 'YAW_X_SIGN' in src('static/js/maths_look.js')


def _lr(ir):
    eL, eR = float(np.sum(ir[:, 0] ** 2)), float(np.sum(ir[:, 1] ** 2))
    arr = [int(np.argmax(np.abs(ir[:, ch]) > 0.1 * np.max(np.abs(ir[:, ch])))) for ch in (0, 1)]
    return 10 * np.log10(eL / eR), arr


# ------------------------------------------------------------------ K1
@pytest.mark.phase('K1')
def test_k1_single_yaw_convention(sw, src):
    """Decision 1: ONE convention constant (Python maths_look.YAW_X_SIGN == JS RRLook.YAW_X_SIGN == +1);
    no per-preset sign edits and no second hard-coded look formula."""
    if not _k1_landed(src):
        pytest.xfail('K1 not landed: no YAW_X_SIGN in engine/maths_look.py / static/js/maths_look.js')
    py = re.search(r'^YAW_X_SIGN\s*=\s*([-+]?[0-9.]+)', src('engine/maths_look.py'), re.M)
    js = re.search(r'YAW_X_SIGN\s*=\s*([-+]?[0-9.]+)', src('static/js/maths_look.js'))
    assert py and js and float(py.group(1)) == 1.0 and float(js.group(1)) == 1.0, (py, js)
    left = []
    for rel in ('engine/early_field.py', 'polar_field.py', 'mic_display.py'):
        if re.search(r'\(\s*-\s*math\.sin\(\s*yaw', src(rel)): left.append(rel)
    if re.search(r'x:\s*-\s*Math\.sin\(\s*yawRad', src('static/js/room_math.js')): left.append('room_math.js')
    assert not left, f'hard-coded old look formula left in {left}'
    # presets keep their stored numbers (L negative, R positive): no per-preset edits
    assert re.search(r'ortf:\s*\{[^}]*yaw_l_deg:\s*-55[^}]*yaw_r_deg:\s*55', src('static/js/app.js'), re.S)


@pytest.mark.phase('K1')
@pytest.mark.parametrize('preset', list(K1_PRESETS))
def test_k1_left_source_L_louder_and_earlier_play(sw, ctx, src, preset):
    """Decision 1: source at the left -> L louder AND earlier (real Play path, MEASURED_SHELF colour).
    Louder: direct bus L-R >= +2 dB and early bus L-R >= +1 dB. Earlier: direct arrival L <= R
    (strictly earlier for the spaced pairs ORTF/NOS/DIN)."""
    body = dict(K1_BASE, **K1_PRESETS[preset])
    d_db, arr = _lr(call_harness_ir(ctx, dict(body, direct_wet=1, early_wet=0, fdn_wet=0)))
    e_db, _ = _lr(call_harness_ir(ctx, dict(body, direct_wet=0, early_wet=1, fdn_wet=0)))
    res = f'{preset}: direct L-R {d_db:+.2f} dB, early L-R {e_db:+.2f} dB, arrival L/R {arr} samples'
    ok = d_db >= 2.0 and e_db >= 1.0 and (arr[0] < arr[1] if preset in SPACED else arr[0] <= arr[1])
    if not ok and not _k1_landed(src):
        pytest.xfail('K1 not landed (capsules crossed): ' + res)
    assert ok, res


def call_harness_ir(ctx, body, secs=0.3):
    try:
        return ctx.play_ir(body, {}, secs)
    except Exception as e:
        if 'node not found' in str(e): pytest.skip('node not found')
        raise


@pytest.mark.slow
@pytest.mark.phase('K1')
@pytest.mark.parametrize('preset', ['ortf', 'xy_90', 'ms'])
def test_k1_left_source_L_louder_and_earlier_render(sw, ctx, src, preset):
    """Decision 1, Render path: direct-only IR, L-R >= +2 dB and L arrives no later than R."""
    body = dict(K1_BASE, **K1_PRESETS[preset], direct_wet=1, early_wet=0, fdn_wet=0)
    d_db, arr = _lr(ctx.render_ir(body, 300))
    res = f'{preset} Render: direct L-R {d_db:+.2f} dB, arrival L/R {arr}'
    ok = d_db >= 2.0 and (arr[0] < arr[1] if preset in SPACED else arr[0] <= arr[1])
    if not ok and not _k1_landed(src):
        pytest.xfail('K1 not landed (capsules crossed): ' + res)
    assert ok, res


# ------------------------------------------------------------------ K2 / K3 / K4 defaults
@pytest.mark.phase('K2')
def test_k2_air_1pole_default_zero(sw, app, src):
    """Decision 2: Structure air 1-pole code stays, default mix 0 (server, client state, slider)."""
    srv = app.params_from_body({})['air_lp']
    js = re.search(r'air_lp:\s*([0-9.]+)', src('static/js/app.js'))
    html = re.search(r'id="air_lp"[^>]*value="([0-9.]+)"', src('static/index.html'))
    vals = {'server': srv, 'app.js': float(js.group(1)) if js else None, 'index.html': float(html.group(1)) if html else None}
    if any(v != 0.0 for v in vals.values()):
        pytest.xfail(f'K2 default not landed: {vals}')
    assert 'air_lp' in src('engine/live_stereo.c') or 'airZ' in src('engine/live_stereo.c'), '1-pole code must stay'


@pytest.mark.phase('K3')
def test_k3_default_source_29_distinct_delays(sw, app):
    """Decision 3: default source x 2.6 m, height 1.2 m; every bus gets >= 29 distinct delays (of 32)."""
    d = app.DEFAULTS
    p = app.params_from_body(dict(d, sample_rate=SR))
    out = app.live_fdn_params(p)
    n = {ch: len(set(round(v * SR / 1000.0) for v in out['buses'][ch]['delay_ms'])) for ch in 'lcr'}
    if (d.get('sx'), d.get('sy')) != (2.6, 1.2):
        pytest.xfail(f"K3 default not landed: sx {d.get('sx')} sy {d.get('sy')}, distinct delays {n}")
    assert min(n.values()) >= 29, n
    e = app.params_from_body({})  # API caller sending nothing gets the same source
    assert (e['sx'], e['sy']) == (2.6, 1.2), (e['sx'], e['sy'])


@pytest.mark.phase('K3')
def test_k3_client_default_matches(sw, src):
    js = src('static/js/app.js')
    m = re.search(r'\bsx:\s*([0-9.]+),[^\n]*\bsy:\s*([0-9.]+)', js)
    html = re.search(r'id="sy"[^>]*value="([0-9.]+)"', src('static/index.html'))
    got = (float(m.group(1)), float(m.group(2))) if m else None
    if got != (2.6, 1.2):
        pytest.xfail(f'K3 client default not landed: app.js sx/sy {got}')
    assert html and float(html.group(1)) == 1.2


@pytest.mark.phase('K4')
def test_k4_fdn_first_defaults(sw, src):
    """Decision 4: FDN fader on (0.5 = 0 dB), direct and early faders 0, early_wet 1.0 (bus enable x fader)."""
    js, html = src('static/js/app.js'), src('static/index.html')
    g = lambda k: (lambda m: float(m.group(1)) if m else None)(re.search(r'\b' + k + r':\s*([0-9.]+)', js))
    vals = {k: g(k) for k in ('fader_fdn', 'fader_direct', 'fader_early', 'early_wet')}
    want = {'fader_fdn': 0.5, 'fader_direct': 0.0, 'fader_early': 0.0, 'early_wet': 1.0}
    if vals != want:
        pytest.xfail(f'K4 defaults not landed: {vals} (want {want})')
    hd = re.search(r'id="fader_direct"[^>]*value="([0-9.]+)"', html)
    assert hd and float(hd.group(1)) == 0.0, 'index.html fader_direct must start at 0'
    # early send must be (enable x fader), so early_wet 1.0 does not make early audible at fader 0
    assert re.search(r'o\.early_wet\s*=\s*\w+\s*\*\s*stripLinear\(src,\s*"early"\)', js), 'early send must be early_wet x fader'


@pytest.mark.phase('K4')
def test_k4_raise_early_fader_no_stale_replay(sw, ctx, RA, src):
    """Decision 4 fix: lowering the early fader must not freeze old input in the early lane.
    Noise 0-2 s; early off at 1.0 s; early back on at 2.5 s (input silent since 2 s).
    From 2.5 s the output must equal an early-always-on run (null <= -100 dB). Before the fix the early
    lane was not written while off, so raising the fader replayed noise captured before 1.0 s."""
    p = ctx.params('std_lock18')
    outs = {}
    for tag, sched in (('switch', [[1.0, {'early_wet': 0.0}], [2.5, {'early_wet': 1.0}]]),
                       ('ref', [[1.0, {'early_wet': 1.0}], [2.5, {'early_wet': 1.0}]])):
        f = ctx.work / f'k4_{tag}.f32'
        try:
            ctx.play(p, {'early_wet': 1.0}, 'switch', 2.0, 3.5, f, json.dumps(sched))
        except RA.SkipTest as e:
            pytest.skip(str(e))
        outs[tag] = np.fromfile(f, np.float32).reshape(-1, 2).astype(np.float64)
    i0 = int(2.5 * SR)
    a, b = outs['switch'][i0:], outs['ref'][i0:]
    nd = RA.null_db(b, a)
    burst = float(np.max(np.abs(a - b)))
    fixed = 'K4 stale-early fix' in src('engine/live_stereo.c')
    msg = f'after re-enable: null {nd:.1f} dB vs early-always-on, max diff {burst:.3g}'
    if nd > -100.0 and not fixed:
        pytest.xfail('K4 stale early replay present (fix not landed): ' + msg)
    assert nd <= -100.0, msg


# ------------------------------------------------------------------ 6 headroom
@pytest.mark.phase('HEADROOM')
def test_headroom_trim_table(sw, src):
    """Decision 6: fixed loop trims as a named table, one row per loop change (F2, F3 now; F5 row reserved),
    per path (play/render), applied to the FDN send only."""
    if 'LOOP_LEVEL_TRIM_DB' not in src('engine/fdn.py'):
        pytest.xfail('headroom trim table not in tree (engine/fdn.py LOOP_LEVEL_TRIM_DB)')
    import fdn
    t = fdn.LOOP_LEVEL_TRIM_DB
    assert {'f2_line_absorption', 'f3_play_rate_delays', 'f5_same_sample'} <= set(t), t
    assert all(r['play'] <= 0.0 and r['render'] <= 0.0 for r in t.values()), 'trims may only reduce level (0 dBFS clip risk)'
    assert abs(fdn.loop_level_trim_db('play', True) - sum(r['play'] for r in t.values())) < 1e-12
    assert abs(fdn.loop_level_trim_db('play', False) - sum(r['play'] for r in t.values() if r['when'] != 'lock')) < 1e-12
    rp = src('render_pipeline.py')
    assert 'loop_level_trim_lin("render"' in rp and 'loop_level_trim_lin("play"' in rp, 'both paths must apply the trim'


@pytest.mark.phase('HEADROOM')
def test_headroom_t14_fdn_level_matches_pre_f2(sw, ctx, RA, src):
    """Decision 6 / run_all t14: peak < 0.95 and the FDN bus within +-0.5 dB of T14_REF.

    D-SRC-DIST-LEVEL re-pinned fdn_rms_db to -24.55. The pre-freeze tree was
    -24.78. The 28 Sep figure -27.18 is the older reference.
    """
    if 'LOOP_LEVEL_TRIM_DB' not in src('engine/fdn.py'):
        r = None
        try:
            r = RA.t14_level_sanity(ctx)
        except AssertionError as e:
            pytest.xfail(f'headroom trim not landed: {e}')
        pytest.xfail(f'headroom trim not landed (t14 {r})')
    call_harness(RA, RA.t14_level_sanity, ctx)


@pytest.mark.phase('HEADROOM')
def test_headroom_t14_whole_mix_informational(sw, ctx, RA):
    """Whole t14 mix (direct + early + FDN at unity) vs the pre-F2 reference (peak 0.512, RMS -16.37 dB at T14_PIN).
    Not trimmed on purpose: F3 removed a fractional-delay loss on Play direct/early (Play direct now equals
    Render direct). XFAIL (with numbers) when outside +-0.5 dB, so Idle can decide whether to trim those buses too."""
    import re as _re
    if not _re.search(r'LOOP_LEVEL_TRIM_DB', (Path(sw) / 'engine' / 'fdn.py').read_text(encoding='utf-8')):
        pytest.xfail('headroom trim table not in tree (engine/fdn.py LOOP_LEVEL_TRIM_DB); whole-mix check needs it')
    r = call_harness(RA, RA.t14_level_sanity, ctx)
    d = r['pinned_mix_delta_db']
    if abs(d) > 0.5:
        pytest.xfail(f"whole mix {d:+.2f} dB vs pre-F2 (peak {r['pinned_mix_peak']} vs {RA.T14_REF['mix_peak']}): direct/early not trimmed - DECISION")
