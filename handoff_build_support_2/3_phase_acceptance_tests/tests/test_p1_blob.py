"""P1 - parameter blob header / version hygiene (BUILD_ROADMAP.md §2, P1.1)."""
from __future__ import annotations
import json, re
import numpy as np
import pytest
import probes as PR
from conftest import call_harness


def _ver(src):
    m = re.search(r'var\s+WORKLET_VER\s*=\s*(\d+)', src('static/js/live_fdn.js'))
    assert m, 'WORKLET_VER not found in live_fdn.js'
    return int(m.group(1))


@pytest.mark.phase('P1')
def test_p1_worklet_ver_consistent_everywhere(sw, src):
    """One version: live_fdn.js WORKLET_VER == index.html ?v= for live_fdn.js == the value the repo tests pin."""
    v = _ver(src)
    page = re.search(r'live_fdn\.js\?v=(\d+)', src('static/index.html'))
    assert page and int(page.group(1)) == v, f'index.html live_fdn.js?v={page and page.group(1)} vs WORKLET_VER {v}'
    for t in ('tests/test_live_stereo.py', 'tests/test_mic_colour_relative.py'):
        pins = set(int(x) for x in re.findall(r'WORKLET_VER = (\d+)', src(t)))
        assert pins <= {v}, f'{t} pins WORKLET_VER {pins}, code has {v}'


@pytest.mark.phase('P1')
def test_p1_blob_len_matches_packer(sw, ctx, RA):
    """Python packer (harness port of packRoom) == BLOB_LEN in fdn_worklet.js, and the default room packs byte-exactly (run_all t01)."""
    call_harness(RA, RA.t01_pack_matches_worklet, ctx)


@pytest.mark.phase('P1')
def test_p1_wasm_matches_source(sw, ctx, RA):
    """Shipped live_stereo.wasm behaves like live_stereo.c rebuilt with zig (run_all t02). Skips without zig/gcc."""
    call_harness(RA, RA.t02_wasm_matches_source, ctx)


@pytest.mark.phase('P1')
def test_p1_blob_v2_header_and_sections(sw, app):
    PR.need(PR.blob_v2, sw)
    import render_pipeline as rp
    p = app.params_from_body({})
    blob = np.asarray(rp.pack_blob_v2(app.live_fdn_params(p)), dtype=np.float64)
    assert blob[0] == 2 and blob[1] == 2, f'magic/major {blob[:2]} (want 2, 2)'
    n_sec, total = int(blob[3]), int(blob[4])
    assert total == len(blob), f'total_len {total} vs {len(blob)}'
    spans = []
    for s in range(n_sec):
        sid, off, ln, sver = blob[5 + 4 * s: 9 + 4 * s]
        assert 0 < off and off + ln <= total, f'section {sid} out of range'
        spans.append((int(off), int(off + ln)))
    spans.sort()
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), f'overlapping sections {spans}'


@pytest.mark.phase('P1')
def test_p1_max_blob_raised(sw, src):
    PR.need(PR.blob_v2, sw)
    m = re.search(r'MAX_BLOB\s*=\s*(\d+)', src('engine/live_stereo.c'))
    assert m and int(m.group(1)) >= 16384, f'MAX_BLOB {m and m.group(1)} < 16384'


@pytest.mark.phase('P1')
def test_p1_old_wasm_silent_on_v2_blob(sw):
    PR.need(PR.blob_v2, sw)
    pytest.xfail('needs the pre-P1 wasm as a fixture: keep a copy of static/wasm/live_stereo.wasm from before P1 '
                 'and play a v2 blob through it with harness/lib/wasm_run.js (WASM=<old>) -> expect all-zero output')
