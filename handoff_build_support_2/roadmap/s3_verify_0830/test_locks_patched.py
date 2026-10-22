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


@pytest.mark.phase('LOCK')
def test_lock_unscaled_pm1_hadamard_play(sw, src):
    c = src('engine/live_stereo.c')
    m = re.search(r'static void fwht\(double \*a(?:,\s*int\s+n)?\)\s*\{', c)
    assert m, 'fwht() not found'
    body = c[m.end(): c.find('\n}\n', m.end())]
    assert 'u + v' in body and 'u - v' in body, 'fwht butterfly changed'
    assert not re.search(r'[*/]\s*(?:[0-9.]+|sqrt|inv|norm|scale)', body), 'fwht has a scale factor (must be unscaled +-1)'


@pytest.mark.phase('LOCK')
def test_lock_geometric_level_inverse_square(sw, app):
    import early_field as ef
    for d in (0.3, 1.0, 2.5, 7.0, 40.0):
        assert abs(ef.geometric_level(d) * d * d - 1.0) < 1e-12, f'geometric level at {d} m is not 1/r^2'


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
