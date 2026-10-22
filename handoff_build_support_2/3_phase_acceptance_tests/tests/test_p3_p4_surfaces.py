"""P3A materials, P3B Solo/Mute, P4 per-hit cascade + the serial-cascade lock."""
from __future__ import annotations
import inspect
import numpy as np
import pytest
import probes as PR

SR = 48000.0


def _cards():
    import surface_colour as sc
    s = sc.default_surfaces()
    # make two panels clearly different so order/serial-vs-parallel is observable
    s['A'] = dict(s['A'], absorb=[0.1, 0.3, 0.6, 0.8, 0.5, 0.2][:len(s['A'].get('absorb') or [0] * 6)],
                  eq={'low_shelf_db': 3.0, 'low_shelf_hz': 200.0, 'peak_db': -4.0, 'peak_hz': 1500.0, 'peak_q': 1.2, 'high_shelf_db': -2.0, 'high_shelf_hz': 6000.0})
    s['B'] = dict(s['B'], absorb=[0.5, 0.4, 0.2, 0.1, 0.3, 0.7][:len(s['B'].get('absorb') or [0] * 6)],
                  eq={'low_shelf_db': -2.0, 'low_shelf_hz': 150.0, 'peak_db': 5.0, 'peak_hz': 3000.0, 'peak_q': 0.8, 'high_shelf_db': 1.5, 'high_shelf_hz': 8000.0})
    return s


@pytest.mark.phase('LOCK')
def test_lock_per_hit_cascade_is_serial_render(sw, app):
    """Render: an image hitting A then B gets stages(A) + stages(B) in hit order, and its response is the PRODUCT
    of the per-hit responses (serial cascade), not a sum/average."""
    import surface_colour as sc
    s = _cards()
    sa, sb, sab = (sc.surface_filter_stages(s, l, SR) for l in (['A'], ['B'], ['A', 'B']))
    assert sa and sb, 'test cards produced no stages'
    assert sab == sa + sb, 'stages for [A, B] are not stages(A) followed by stages(B)'
    x = np.zeros(8192); x[0] = 1.0
    ha = np.fft.rfft(sc.apply_surface_to_buffer(x, s, ['A'], SR))
    hb = np.fft.rfft(sc.apply_surface_to_buffer(x, s, ['B'], SR))
    hab = np.fft.rfft(sc.apply_surface_to_buffer(x, s, ['A', 'B'], SR))
    assert np.allclose(hab, ha * hb, rtol=1e-6, atol=1e-9), 'two-hit response != product of single-hit responses'


@pytest.mark.phase('LOCK')
def test_lock_render_passes_every_hit(sw, app):
    import render_pipeline as rp
    s = inspect.getsource(rp.render_early_ir)
    assert 'surfaces_hit_by_n(' in s and 'apply_surface_to_buffer(bl, surfaces, hit' in s, \
        'render_early_ir must cascade all hit letters of each image'


@pytest.mark.phase('P3A')
def test_p3a_curtain_wall_only_real_materials(sw):
    """Product lock: real materials only; curtains never on floor/ceiling. Checked against the Track A role table."""
    PR.need(PR.materials_track_a, sw)
    import surface_colour as sc
    table = getattr(sc, 'MATERIALS', None) or getattr(sc, 'MATERIAL_PRESETS', None)
    if table is None:
        pytest.xfail('Track A present but no MATERIALS/MATERIAL_PRESETS table exposed; adapt this test to the real interface')
    for name, m in table.items():
        if 'curtain' in name.lower():
            roles = set(m.get('roles') or m.get('allowed_roles') or [])
            assert roles <= {'wall'}, f'{name} allowed on {roles}'


@pytest.mark.phase('P3B')
def test_p3b_mute_all_panels_leaves_direct_and_fdn(sw, app):
    """Mute keeps the tap. Render early colour is identity. Direct gain stays 1.
    A wall hit reflects ×0. Play solo_mute is all 0, and the direct image still injects.
    Play early shares that inject (no separate Play surface-EQ cascade in this phase)."""
    PR.need(PR.solo_mute_track_b, sw)
    import surface_colour as sc
    import render_pipeline as rp

    p = app.params_from_body({"surfaces_mute": list("ABCDEF")})
    live = rp.live_fdn_params(p)
    assert live["solo_mute"] == [0.0] * 6
    di = int(live["direct_index"])
    assert abs(float(live["buses"]["l"]["inject"][di])) > 1e-8

    raw = sc.default_surfaces()
    eff = sc.effective_surfaces(raw, None, list("ABCDEF"))
    assert rp.tap_reflect_gain((0, 0, 0), eff) == 1.0
    assert rp.tap_reflect_gain((1, 0, 0), eff) == 0.0
    assert sc.surfaces_hit_by_n((1, 0, 0)) == ["C"]
    assert sc.surface_filter_stages(eff, ["A"], SR) == []
    x = np.zeros(128)
    x[0] = 1.0
    y = sc.apply_surface_to_buffer(x.copy(), eff, ["A", "E"], SR)
    assert np.allclose(y, x)
    assert not np.allclose(sc.apply_surface_to_buffer(x.copy(), raw, ["A"], SR), x)

    solo = sc.effective_surfaces(raw, "E", [])
    assert sc.surface_filter_stages(solo, ["E"], SR)
    assert sc.surface_filter_stages(solo, ["A"], SR) == []
    assert rp.tap_reflect_gain((1, 0, 0), solo) == 0.0
    assert rp.tap_reflect_gain((0, -1, 0), solo) != 0.0
    assert sc.effective_surfaces(raw, None, {}) is raw
    assert sc.solo_mute_gates(None, None) == [1.0] * 6


@pytest.mark.slow
@pytest.mark.phase('P4')
def test_p4_play_render_parity_narrowed(sw, ctx):
    """D-S5c-4. |dPlay − dRender| ≤ 0.3 dB on the narrowed windows.

    Gated: tail 80 ms+ of default (shaped − flat), face-A HS+6 and all-faces
    HS+6 (each case − default); full-mix 0–80 ms of default and face-A HS+6.
    All-faces full-mix 0–80 ms, and every early-bus row, are printed and not gated.
    """
    PR.need(PR.play_cascade, sw)
    import sys
    sys.path.insert(0, str(sw / "tests"))
    import test_s5_surf_tail as s5
    s5.assert_surf_parity(ctx, extras=False)


@pytest.mark.phase('P4')
def test_p4_flat_cards_bit_exact_bypass(sw):
    PR.need(PR.play_cascade, sw)
    pytest.xfail('P4 present: all-flat cards -> Play output bit-identical to cascade-off')


@pytest.mark.phase('P4')
def test_p4_cpu_budget(sw):
    PR.need(PR.play_cascade, sw)
    pytest.xfail('P4 present: CPU <= +0.15 ms/block with 1 source (ASSUMED budget) via wasm_run.js bench')
