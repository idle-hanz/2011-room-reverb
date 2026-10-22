"""P2 - air (ISO 9613-1) and the air-placement locks (BUILD_ROADMAP.md §1, P2)."""
from __future__ import annotations
import ast, inspect, re, textwrap
import numpy as np
import pytest
import probes as PR

SR = 48000


def _null(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    return 10 * np.log10(max(float(np.sum((a - b) ** 2)), 1e-300) / max(float(np.sum(a ** 2)), 1e-300))


@pytest.mark.phase('LOCK')
def test_lock_direct_is_air_free_play(sw, ctx):
    """Direct path only (early/FDN off) is bit-identical for humidity 0 vs 1 in Play."""
    over = {"colour_on": False, "early_wet": 0, "fdn_wet": 0, "direct_wet": 1}
    a = ctx.play_ir('std_lock18', over, 0.3, extra={'humidity': 0.0})
    b = ctx.play_ir('std_lock18', over, 0.3, extra={'humidity': 1.0})
    assert np.max(np.abs(a)) > 0, 'direct-only Play IR is silent'
    assert np.array_equal(a, b), f'direct changes with humidity (null {_null(a, b):.1f} dB) - lock: direct is air-free'


@pytest.mark.slow
@pytest.mark.phase('LOCK')
def test_lock_direct_is_air_free_render(sw, ctx):
    body = {"decay_lock": True, "decay_s": 1.8, "early_wet": 0, "fdn_wet": 0, "direct_wet": 1, "colour_mode": "BYPASS"}
    a = ctx.render_ir(dict(body, humidity=0.0), 200)
    b = ctx.render_ir(dict(body, humidity=1.0), 200)
    assert np.max(np.abs(a)) > 0
    assert _null(a, b) < -200, f'Render direct changes with humidity ({_null(a, b):.1f} dB)'


@pytest.mark.phase('LOCK')
def test_lock_no_air_on_fdn_return_play(sw, src):
    """Every tint() (air 1-pole + shelf) call in live_stereo.c acts on an inject value (x*inj), never on a line read."""
    c = src('engine/live_stereo.c')
    calls = re.findall(r'(?<![\w])tint\(\s*([^;]*?)\)\s*[;+)]', c)
    calls = [k for k in calls if not k.startswith('Line *')]
    assert calls, 'no tint() calls found'
    bad = [k for k in calls if 'inj' not in k]
    assert not bad, f'tint() applied to something other than an inject: {bad}'
    m = re.search(r'static[^{;]*\bread_peaked\([^)]*\)\s*\{', c)
    assert m, 'read_peaked() not found'
    body = c[m.end(): c.find('\n}\n', m.end())]
    assert 'tint(' not in body and 'air' not in body.lower(), 'air inside read_peaked() (FDN return/loop)'
    dstart = re.search(r'(?m)^#define\s+DIFFUSE_FN\(name,\s*HN,\s*FW\)[^\n]*', c)
    assert dstart, 'DIFFUSE_FN not found'
    end = dstart.end()
    line = dstart.group(0)
    while line.rstrip('\r').endswith('\\'):
        nl = c.find('\n', end)
        if nl < 0:
            break
        nxt = c.find('\n', nl + 1)
        if nxt < 0:
            nxt = len(c)
        end = nxt
        line = c[nl + 1:nxt]
    db = c[dstart.start():end]
    assert 'tint(' not in db and 'air' not in db.lower(), 'air inside diffuse() (FDN return/loop)'
    for n in (8, 16, 32):
        assert f'DIFFUSE_FN(diffuse{n}, {n}, fwht{n})' in c, f'diffuse{n} missing'


@pytest.mark.phase('LOCK')
def test_lock_no_air_on_fdn_return_render(sw, app):
    import render_pipeline as rp
    s = inspect.getsource(rp.render_fdn_ir)
    assert 'apply_air_absorption' not in s, 'render_fdn_ir applies air outside the inject builder'
    import fdn
    s2 = inspect.getsource(fdn.build_inject_from_taps)
    assert 'apply_air_absorption' in s2, 'air expected on the FDN inject (build_inject_from_taps)'
    for name in ('process_block_poly', 'process_block'):
        if hasattr(fdn.FDN, name):
            assert 'air' not in inspect.getsource(getattr(fdn.FDN, name)).lower(), f'air inside FDN.{name}'


@pytest.mark.phase('LOCK')
def test_lock_humidity_one_pole_separate_from_shelf(sw, app):
    """Structure humidity 1-pole and the ASSUMED high shelf are two separable stages: combined == serial product."""
    import early_field as ef
    x = np.zeros(4096); x[0] = 1.0
    def H(lp, sh):
        y = ef.apply_air_absorption(x.copy(), 5.0, SR, 0.6, air_lp=lp, air_shelf=sh)
        return np.fft.rfft(y)
    lp_only, sh_only, both, none = H(0.25, 0.0), H(0.0, 1.0), H(0.25, 1.0), H(0.0, 0.0)
    assert np.allclose(none, 1.0, atol=1e-12), 'air_lp=0 & air_shelf=0 must be identity'
    assert not np.allclose(lp_only, 1.0) and not np.allclose(sh_only, 1.0), 'each stage must act on its own'
    assert np.allclose(both, lp_only * sh_only, rtol=1e-6, atol=1e-9), 'combined air != 1-pole x shelf'


@pytest.mark.phase('LOCK')
def test_lock_render_stage_order(sw, app):
    """Per image in Render: image/allpass -> air -> surface cascade -> mic colour (roadmap §1)."""
    import render_pipeline as rp
    s = inspect.getsource(rp.render_early_ir)
    idx = {k: s.find(k + '(') for k in ('_apply_ir_at', 'apply_air_absorption', 'apply_surface_to_buffer', '_colour_apply')}
    assert all(v >= 0 for v in idx.values()), f'missing stage call in render_early_ir: {idx}'
    order = sorted(idx, key=idx.get)
    assert order == ['_apply_ir_at', 'apply_air_absorption', 'apply_surface_to_buffer', '_colour_apply'], f'stage order {order}'


@pytest.mark.phase('P2')
def test_p2_iso_air_fit_within_tolerance(sw, app):
    """Analytic dual-shelf vs ISO 9613-1. Bound is the vendored preset's per-distance RMSE, scaled by distance."""
    PR.need(PR.iso_air, sw)
    import json
    import air_iso
    preset = json.loads((sw / 'engine' / 'presets' / 'air' / 'studio_20C_50RH.json').read_text(encoding='utf-8'))
    tol5 = float(preset['rmse']['per_distance_db']['5m'])
    freqs = np.geomspace(20.0, 16000.0, 96)
    for d in (1.0, 5.0, 10.0, 30.0):
        model = air_iso.model_path_loss_db(freqs, d, 'studio_20C_50RH')
        iso = air_iso.iso_path_loss_db(freqs, d, 'studio_20C_50RH')
        rmse = float(np.sqrt(np.mean((model - iso) ** 2)))
        limit = tol5 * (d / 5.0) * 1.05
        assert rmse <= limit, f'{d:.0f} m RMSE {rmse:.5f} dB > {limit:.5f}'


@pytest.mark.phase('P2')
def test_p2_air_shelf_zero_nulls_iso_off(sw, app):
    """Early-only: air_shelf=0 matches air_iso False (the shelf is off either way)."""
    PR.need(PR.iso_air, sw)
    from render_pipeline import render
    dry = np.zeros(1)
    dry[0] = 1.0
    common = dict(
        W=6.0, H=3.0, L=8.0, sox=0.5, soz=0.4, mz=6.5, my=1.5, sy=1.5,
        sx=3.0, sz=4.1, mcz=1.5, space=0.17, diverg=1.0, car_omni=1.0,
        early_wet=1.0, fdn_wet=0.0, direct_wet=0.0, dry_gain=0.0, fdn_g=1.0,
        humidity=0.6, air_lp=0.25, ir_length_ms=80.0, path_on=False,
        colour_mode='BYPASS', hadamard_n=32,
    )
    aL, aR, _ia = render(dry, 48000, air_shelf=0.0, air_iso=True, **common)
    bL, bR, _ib = render(dry, 48000, air_shelf=1.0, air_iso=False, **common)
    assert np.array_equal(aL, bL) and np.array_equal(aR, bR)


@pytest.mark.phase('P2.2')
def test_p2_play_render_early_null(sw):
    PR.need(PR.iso_air, sw)
    PR.need(PR.play_cascade, sw)
    pytest.xfail('needs the P4 per-hit cascade in Play before an early-only null <= -60 dB is possible')
