"""Mirror symmetry acceptance (MIRROR_ASYMMETRY_BRIEF.md, 1 Oct 2026).

Scene: Idle's 1 Oct 09:43 hall (57 x 34.2 x 97 m), stand on the room centre line, ORTF-style yaw +/-55,
SM57 sides, C muted, FDN only. Source A at x = 44.09, mirrored B at x = W - 44.09 = 12.91.
A's (L, R) output must equal B's (R, L) output. With the fix this is bit-exact on the box
(null below -2900 dB), so the tolerances below are float-noise margins, not engineering slack.

Status: XFAIL until the fix is in the tree (probe: mirror-symmetric LIVE_32 multiset AND a B-side FDN
colour map key 'fdn_b' in mic_colour/live_bank.py or render_pipeline.py). Once the probe finds it, the criteria must hold or FAIL.
Read-only on --sw.
"""
from __future__ import annotations
import os, sys
from collections import Counter
import numpy as np
import pytest

SR = 48000
W = 57.0
HALL = dict(W=W, H=34.2, L=97.0, sx=44.09, sz=34.89, sy=1.88, mcx=W / 2, mcz=24.25, my=1.90,
            space=0.0, hadamard_n=32, fdn_g=1.0, decay_lock=True, decay_s=0.71, ir_length_ms=1500.0,
            humidity=0.5, air_lp=0.25, air_shelf=1.0, mic_gain_l=1.0, mic_gain_c=0.0, mic_gain_r=1.0,
            direct_wet=0.0, early_wet=0.0, fdn_wet=1.0, dry_gain=0.0,
            mic_preset_l='ShureSM57', mic_preset_r='ShureSM57', mic_preset_c='ShureSM57',
            toe_half_deg=55.0, yaw_l_deg=-55.0, yaw_r_deg=55.0, yaw_c_deg=0.0,
            pattern_l='cardioid', pattern_r='cardioid', car_omni=1.0)
TOL = dict(null_db=-60.0, band_db=0.1, ild_db=0.1, ic=0.01, early_db=0.1, t30_pct=2.0)
FC3 = [f for f in (50 * 2 ** (k / 3) for k in range(29)) if f < 16500]


def _body(kind, **kw):
    b = dict(HALL)
    if kind == 'twoA': b.update(two_sources=True, mirror_b=True, source_balance=-1.0)
    elif kind == 'twoB': b.update(two_sources=True, mirror_b=True, source_balance=1.0)
    elif kind == 'twoC': b.update(two_sources=True, mirror_b=True, source_balance=0.0)
    elif kind == 'oneA': b.update(two_sources=False)
    elif kind == 'oneB': b.update(two_sources=False, sx=W - HALL['sx'])
    b.update(kw)
    return b


def _null(a, b):
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    return 10 * np.log10(max(float(np.sum((a - b) ** 2)), 1e-300) / max(float(np.sum(a ** 2)), 1e-300))


def mirror_metrics(A, B):
    """A (n,2) for source A, B (n,2) for mirrored B. Compares A with B swapped."""
    from analyze import t60_bands
    n = min(len(A), len(B)); A = A[:n]; Bs = B[:n, ::-1]
    f = np.fft.rfftfreq(n, 1 / SR)
    XA = [np.fft.rfft(A[:, c]) for c in (0, 1)]; XB = [np.fft.rfft(Bs[:, c]) for c in (0, 1)]
    band, ild, ic = [], [], []
    for fc in FC3:
        if fc < 100: continue
        m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        eA = [float(np.sum(np.abs(XA[c][m]) ** 2)) for c in (0, 1)]
        eB = [float(np.sum(np.abs(XB[c][m]) ** 2)) for c in (0, 1)]
        band.append(max(abs(10 * np.log10(eA[c] / eB[c])) for c in (0, 1)))
        ild.append(abs(10 * np.log10(eA[0] / eA[1]) - 10 * np.log10(eB[0] / eB[1])))
        icA = abs(np.sum(XA[0][m] * np.conj(XA[1][m]))) / np.sqrt(eA[0] * eA[1])
        icB = abs(np.sum(XB[0][m] * np.conj(XB[1][m]))) / np.sqrt(eB[0] * eB[1])
        ic.append(abs(icA - icB))
    e = np.abs(A).max(1); o = int(np.argmax(e > 1e-3 * e.max())); w = int(0.08 * SR)
    early = max(abs(10 * np.log10(np.sum(A[o:o + w, c] ** 2) / max(np.sum(Bs[o:o + w, c] ** 2), 1e-300))) for c in (0, 1))
    oc = [125, 250, 500, 1000, 2000, 4000, 8000]
    t30 = 0.0
    for c in (0, 1):
        ta, tb = t60_bands(A[:, c], SR, bands=oc), t60_bands(Bs[:, c], SR, bands=oc)
        t30 = max(t30, max(abs(ta[k] / tb[k] - 1) * 100 for k in oc))
    return dict(null_db=_null(A, Bs), band_db=max(band), ild_db=max(ild), ic=max(ic), early_db=early, t30_pct=t30)


def _fails(m):
    bad = [k for k in TOL if (m[k] > TOL[k])]
    return bad, ', '.join(f'{k} {m[k]:.3g} (tol {TOL[k]})' for k in TOL)


def _imgs(sw, n=32):
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    old = os.getcwd(); os.chdir(sw)
    try:
        import importlib
        ef = importlib.import_module('early_field')
        return list(ef.build_image_indices(n))
    finally:
        os.chdir(old)


def _multiset_ok(imgs):
    c = Counter(imgs); m = Counter((-a, b, z) for a, b, z in imgs)
    return [n for n in c if c[n] != m[n]]


def _landed(sw, src):
    return not _multiset_ok(_imgs(sw)) and any('fdn_b' in src(f) for f in ('mic_colour/live_bank.py', 'render_pipeline.py'))


def _judge(sw, src, m, what):
    bad, txt = _fails(m)
    if not bad: return
    if not _landed(sw, src):
        pytest.xfail(f'MIRROR fix not in tree: {what}: {txt}')
    raise AssertionError(f'{what}: mirror asymmetry {txt}')


@pytest.mark.phase('MIRROR')
def test_mirror_image_set_is_mirror_symmetric(sw, src):
    imgs = _imgs(sw)
    bad = _multiset_ok(imgs)
    if bad and not _landed(sw, src):
        pytest.xfail(f'LIVE_32 is not X-mirror symmetric: unpaired {bad}')
    assert not bad, f'unpaired images {bad}'


@pytest.mark.phase('MIRROR')
def test_mirror_play_one_source(sw, src, ctx):
    A = ctx.play_ir(_body('oneA'), {}, 3.0); B = ctx.play_ir(_body('oneB'), {}, 3.0)
    _judge(sw, src, mirror_metrics(A, B), 'Play one source A vs B at mirrored position')


@pytest.mark.phase('MIRROR')
@pytest.mark.parametrize('colour', ['MEASURED_SHELF', 'BYPASS'])
@pytest.mark.parametrize('lanes', ['fdn', 'early', 'direct'])
def test_mirror_play_two_sources_hard(sw, src, ctx, colour, lanes):
    ov = dict(colour_mode=colour, fdn_wet=float(lanes == 'fdn'), early_wet=float(lanes == 'early'),
              direct_wet=float(lanes == 'direct'))
    A = ctx.play_ir(_body('twoA', **ov), {}, 3.0); B = ctx.play_ir(_body('twoB', **ov), {}, 3.0)
    _judge(sw, src, mirror_metrics(A, B), f'Play two sources balance A vs B ({lanes}, {colour})')


@pytest.mark.phase('MIRROR')
def test_mirror_play_two_sources_centre_is_self_mirror(sw, src, ctx):
    """Balance centre, same impulse on both inputs: the output must be its own mirror (L == R)."""
    X = ctx.play_ir(_body('twoC', early_wet=1.0, direct_wet=1.0), {}, 3.0)
    _judge(sw, src, mirror_metrics(X, X), 'Play two sources, balance centre, L vs R')


@pytest.mark.slow
@pytest.mark.phase('MIRROR')
def test_mirror_render_one_source(sw, src, ctx):
    A = ctx.render_ir(_body('oneA'), 2500); B = ctx.render_ir(_body('oneB'), 2500)
    _judge(sw, src, mirror_metrics(A, B), 'Render one source A vs B at mirrored position')
