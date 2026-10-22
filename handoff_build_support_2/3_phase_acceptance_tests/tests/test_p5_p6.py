"""P5 scattering and P6 source radiation, plus the 'no scattering inside the FDN loop' lock."""
from __future__ import annotations
import inspect, re, sys
import pytest
import probes as PR
from conftest import call_harness


@pytest.mark.phase('LOCK')
def test_lock_no_scattering_inside_fdn_loop(sw, src):
    """Scatter/cluster code must never appear in the FDN loop (Play diffuse/read_peaked/fwht, Render FDN class).
    Passes trivially while scattering does not exist; it is a guard for P5.
    Play sizes the loop with fwht8/16/32 and diffuse8/16/32."""
    c = src('engine/live_stereo.c')
    def macro(header_re):
        mm = re.search(r'(?m)^' + header_re + r'[^\n]*', c)
        assert mm, header_re
        end = mm.end()
        line = mm.group(0)
        while line.rstrip('\r').endswith('\\'):
            nl = c.find('\n', end)
            if nl < 0:
                break
            nxt = c.find('\n', nl + 1)
            if nxt < 0:
                nxt = len(c)
            end = nxt
            line = c[nl + 1:nxt]
        return c[mm.start():end]

    chunks = []
    m = re.search(r'static[^{;]*\bread_peaked\([^)]*\)\s*\{', c)
    assert m, 'read_peaked() not found in live_stereo.c'
    chunks.append(('read_peaked', c[m.end(): c.find('\n}\n', m.end())]))
    chunks.append(('fwht', macro(r'#define\s+FWHT_BODY\(NFIX\)')))
    chunks.append(('diffuse', macro(r'#define\s+DIFFUSE_FN\(name,\s*HN,\s*FW\)')))
    for n in (8, 16):
        assert f'static void fwht{n}(double *a) {{ FWHT_BODY({n}); }}' in c, f'fwht{n} missing'
        assert f'DIFFUSE_FN(diffuse{n}, {n}, fwht{n})' in c, f'diffuse{n} missing'
    # fwht32 is the same butterfly after the ±1 column multiply (S4b). Still no scatter.
    fw = re.search(r'static void fwht32\(double \*a\) \{.*?\n\}', c, re.S)
    assert fw and 'FWHT_BODY(32)' in fw.group(0), 'fwht32 missing'
    assert 'scat' not in fw.group(0).lower() and 'cluster' not in fw.group(0).lower()
    assert 'DIFFUSE_FN(diffuse32, 32, fwht32)' in c, 'diffuse32 missing'
    for name, body in chunks:
        assert not re.search(r'scat|cluster', body, re.I), f'scattering inside {name}()'
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    import fdn
    s = inspect.getsource(fdn.FDN)
    assert not re.search(r'scat|cluster', s, re.I), 'scattering inside engine/fdn.py FDN class'


@pytest.mark.phase('P5')
def test_p5_scatter_zero_is_bit_identical(sw, ctx, RA):
    PR.need(PR.scattering, sw)
    call_harness(RA, RA.t06_scattering_zero_identity, ctx)


@pytest.mark.phase('P5')
def test_p5_scatter_after_air(sw, app):
    PR.need(PR.scattering, sw)
    import render_pipeline as rp
    s = inspect.getsource(rp.render_early_ir)
    i_air, i_sc = s.find('apply_air_absorption('), s.find('scatter')
    assert 0 <= i_air < i_sc, 'roadmap §1 override: scatter goes AFTER air (not right after _apply_ir_at as Track C says)'


@pytest.mark.phase('P5')
def test_p5_energy_and_feed_forward(sw):
    PR.need(PR.scattering, sw)
    pytest.xfail('P5 present: energy +-0.5 dB vs s=0 and feed-forward proof (Track C brief tests) - wire to scatter.py')


@pytest.mark.phase('P6')
def test_p6_omni_source_bit_identical(sw, ctx, RA):
    PR.need(PR.source_radiation, sw)
    call_harness(RA, RA.t05_omni_source_identity, ctx)


@pytest.mark.phase('P6')
def test_p6_tail_invariant_to_source_yaw(sw, ctx, RA):
    PR.need(PR.source_radiation, sw)
    call_harness(RA, RA.t07_tail_yaw_invariance, ctx)


@pytest.mark.phase('P6')
def test_p6_two_source_cpu(sw, ctx, RA):
    """Two directional sources. Shared off ceiling 2.40 ms; shared on 2.133 ms (D-S5c-2)."""
    PR.need(PR.source_radiation, sw)
    call_harness(RA, RA.t19_two_source_radiation_cpu, ctx)
