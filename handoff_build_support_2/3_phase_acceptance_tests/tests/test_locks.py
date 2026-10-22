"""Product locks that must hold in every phase (always runnable)."""
from __future__ import annotations
import json, re
import numpy as np
import pytest
import probes as PR


@pytest.mark.phase('LOCK')
def test_lock_unscaled_pm1_hadamard_render(sw, app):
    import fdn
    H = fdn.unscaled_hadamard_matrix(32)
    assert set(np.unique(H)) == {-1.0, 1.0}, 'Hadamard entries must be exactly +-1 (unscaled)'
    assert np.array_equal(H @ H.T, 32 * np.eye(32)), 'not a Hadamard matrix'


def _c_macro(c, header_re):
    """A #define whose lines end in a backslash, including the last line."""
    m = re.search(r'(?m)^' + header_re + r'[^\n]*', c)
    if not m:
        return ''
    end = m.end()
    line = m.group(0)
    while line.rstrip('\r').endswith('\\'):
        nl = c.find('\n', end)
        if nl < 0:
            break
        nxt = c.find('\n', nl + 1)
        if nxt < 0:
            nxt = len(c)
        end = nxt
        line = c[nl + 1:nxt]
    return c[m.start():end]


@pytest.mark.phase('LOCK')
def test_lock_unscaled_pm1_hadamard_play(sw, src):
    """Play calls constant-size fwht8/16/32. Each one is the unscaled +-1 butterfly."""
    c = src('engine/live_stereo.c')
    body = _c_macro(c, r'#define\s+FWHT_BODY\(NFIX\)')
    assert body, 'FWHT_BODY not found'
    assert 'u + v' in body and 'u - v' in body, 'fwht butterfly changed'
    assert not re.search(r'[*/]\s*(?:[0-9.]+|sqrt|inv|norm|scale)', body), 'fwht has a scale factor (must be unscaled +-1)'
    for n in (8, 16):
        needle = f'static void fwht{n}(double *a) {{ FWHT_BODY({n}); }}'
        assert needle in c, f'fwht{n} is not the constant-size unscaled body'
    # S4b: fwht32 multiplies by the ±1 column table, then the same unscaled butterfly.
    fw = re.search(r'static void fwht32\(double \*a\) \{.*?\n\}', c, re.S)
    assert fw and 'FWHT_BODY(32)' in fw.group(0), 'fwht32 is not the unscaled butterfly'
    assert 'g_csignTab' in fw.group(0) and not re.search(
        r'[*/]\s*(?:[0-9.]+|sqrt|inv|norm|scale)', fw.group(0)), 'fwht32 scales the butterfly'
    # Box 2 Oct 16:5x (S4b verify): the column table itself must be +-1 (a 0.5 entry would pass the
    # checks above), must match Render's fdn.LOOP_COLUMN_D, and parity must switch it off (plain H).
    tb = re.search(r'static const double CSIGN_D\[32\]\s*=\s*\{([^}]*)\}', c)
    assert tb, 'CSIGN_D[32] table not found'
    d = [float(v) for v in re.findall(r'[-+]?\d+(?:\.\d*)?', tb.group(1))]
    assert len(d) == 32 and all(v in (1.0, -1.0) for v in d), f'CSIGN_D is not 32 x +-1: {d}'
    import sys as _sys
    _sys.path[:0] = [str(sw), str(sw / 'engine')]
    import fdn as _fdn
    assert [float(v) for v in _fdn.LOOP_COLUMN_D] == d, 'Play CSIGN_D != Render fdn.LOOP_COLUMN_D'
    H = _fdn.unscaled_hadamard_matrix(32)
    assert (_fdn.loop_hadamard(32, parity=True) == H).all(), 'reaktor_parity must keep plain H'
    assert (_fdn.loop_hadamard(32) == H * _fdn.LOOP_COLUMN_D[None, :]).all(), 'Render n=32 must be H*D'
    assert re.search(r'g_csign\s*=\s*st->plainH\s*\?\s*0\s*:\s*1', c), 'Play parity (plainH) must switch the signs off'


@pytest.mark.phase('LOCK')
def test_lock_geometric_level_inverse_distance(sw, app):
    """D-TLAW 2026-10-10. Software amplitude is 1/r.

    The Structure Air Abs graph stays 1/r² (shot 256).
    """
    import early_field as ef
    for d in (0.3, 1.0, 2.5, 7.0, 40.0):
        assert abs(ef.geometric_level(d) * d - 1.0) < 1e-12, f'geometric level at {d} m is not 1/r'
    assert ef.geometric_level(0.0) == 0.0


@pytest.mark.phase('LOCK')
def test_lock_early_images_excite_fdn(sw, ctx):
    """Every one of the 32 early images injects into its FDN line (Play params, all three buses)."""
    P = json.loads(open(ctx.params('std_lock18')).read())
    for ch in 'lcr':
        inj = np.asarray(P['buses'][ch]['inject'], float)
        assert len(inj) == 32 and np.all(np.abs(inj) > 0), f'bus {ch}: lines with zero inject {np.where(inj == 0)[0].tolist()}'


@pytest.mark.phase('LOCK')
def test_lock_two_diffusion_layers_separate_keys(sw):
    """Lock: Surfaces delta-d jitter and Structure Dffs are driven by separate keys (today both read card 'diffusion')."""
    PR.need(PR.diffusion_split, sw)
