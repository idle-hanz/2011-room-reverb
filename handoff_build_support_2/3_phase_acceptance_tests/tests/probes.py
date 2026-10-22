"""Feature probes: is a roadmap feature present in the tree?  Each returns (present: bool, evidence: str).
Probes read source text only (cheap, no execution) so a missing feature gives a clean XFAIL with a reason."""
from __future__ import annotations
import re
from pathlib import Path


def _t(sw: Path, rel: str) -> str:
    f = sw / rel
    return f.read_text(encoding='utf-8', errors='replace') if f.exists() else ''


def f1_denormal_guard(sw):
    c = _t(sw, 'engine/live_stereo.c')
    ok = ('LS_DC' in c or 'ls_flush' in c or re.search(r'1e-1[5-9]|1e-20', c) is not None)
    return ok, 'live_stereo.c has LS_DC / ls_flush / tiny-value flush' if ok else 'no denormal guard in live_stereo.c'


def f2_line_absorption(sw):
    c, f, r = _t(sw, 'engine/live_stereo.c'), _t(sw, 'engine/fdn.py'), _t(sw, 'render_pipeline.py')
    ok = ('line_t60' in c or 'lineT60' in c) and 'line_t60' in f and 'line_t60' in r
    return ok, 'line_t60 in live_stereo.c, fdn.py and render_pipeline.py' if ok else 'F2 (per-line loss, line_t60) not in tree (P0.2)'


def f5_same_sample_play(sw):
    import re as _re
    c = _t(sw, 'engine/live_stereo.c')
    # Comments do not count: S4 added "Reserve 1 is loop_semantics (unused)" to a comment.
    c = _re.sub(r'/\*.*?\*/', '', c, flags=_re.S)
    c = _re.sub(r'//[^\n]*', '', c)
    fdn = _t(sw, 'engine/fdn.py')
    z1 = 'LOOP_SEMANTICS = "z1_both"' in fdn or "LOOP_SEMANTICS = 'z1_both'" in fdn
    ok = z1 or 'build_mix' in c or 'loop_semantics' in c or 'loop_mix' in _t(sw, 'static/js/fdn_worklet.js')
    if z1:
        return True, 'Render loop is z^-1 in both (LOOP_SEMANTICS z1_both); Play already was'
    return ok, 'Play consumes loop M / loop_semantics' if ok else 'P0.4 loop semantics not decided/landed (no build_mix / loop_semantics / packed loop_mix) - F5 is DECISION FOR IDLE'


def diffusion_split(sw):
    s, a = _t(sw, 'surface_colour.py'), _t(sw, 'app_server.py')
    ok = ('jitter_D' in s or 'jitter_d' in s) and ('structure_dif' in a or 'structure_dif' in _t(sw, 'render_pipeline.py'))
    return ok, 'jitter_D + structure_dif keys present' if ok else 'P0.3 diffusion key split not in tree (card "diffusion" still feeds both layers)'


def client_reads_defaults(sw):
    ok = '/api/defaults' in _t(sw, 'static/js/app.js')
    return ok, 'app.js fetches /api/defaults' if ok else 'P0.5b: client does not load /api/defaults (hard-coded state in app.js)'


def blob_v2(sw):
    ok = 'pack_blob_v2' in _t(sw, 'render_pipeline.py')
    return ok, 'pack_blob_v2 present' if ok else 'P1 blob v2 header/section table not in tree (magic 1 only)'


def iso_air(sw):
    ok = (sw / 'engine' / 'air_iso.py').exists() or 'air_climate' in _t(sw, 'app_server.py')
    return ok, 'ISO 9613-1 air present' if ok else 'P2 ISO 9613-1 air not in tree (no engine/air_iso.py, no air_climate)'


def materials_track_a(sw):
    ok = 'heavy_curtain' in _t(sw, 'surface_colour.py') or (sw / 'presets' / 'surfaces').exists()
    return ok, 'Track A materials present' if ok else 'P3A Track A materials/role bans not in tree'


def solo_mute_track_b(sw):
    ok = 'surfaces_solo' in _t(sw, 'app_server.py') or 'effective_surfaces' in _t(sw, 'surface_colour.py')
    return ok, 'Track B solo/mute present' if ok else 'P3B surfaces Solo/Mute not in tree'


def play_cascade(sw):
    c = _t(sw, 'engine/live_stereo.c')
    ok = re.search(r'\bSURF\b|surf_casc|surfCasc|SEC_SURF', c) is not None
    return ok, 'Play per-hit cascade section present' if ok else 'P4 Play per-hit surface cascade not in tree'


def scattering(sw):
    ok = (sw / 'engine' / 'scatter.py').exists()
    return ok, 'engine/scatter.py present' if ok else 'P5 scattering (Track C) not in tree'


def source_radiation(sw):
    ok = (sw / 'engine' / 'source_radiation.py').exists() or 'src_rad' in _t(sw, 'app_server.py')
    return ok, 'source radiation present' if ok else 'P6 source radiation not in tree'


def sos_colour(sw):
    ok = (sw / 'mic_colour' / 'sos_table.py').exists()
    return ok, 'mic_colour/sos_table.py present' if ok else 'IIR (SOS) colour not in tree'


def need(probe, sw):
    """XFAIL the calling test cleanly when the feature is not in the tree."""
    import pytest
    ok, why = probe(sw)
    if not ok:
        pytest.xfail(why)
    return why
