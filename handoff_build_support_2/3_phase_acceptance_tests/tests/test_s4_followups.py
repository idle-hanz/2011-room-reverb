"""S4 follow-ups (box, 2 Oct 11:40 verify): Surfaces Solo/Mute Play vs Render, and the two
diffusion layers measured on audio (not only on keys).

Window: early = 1.5-80 ms after the direct peak (direct excluded), FDN = after 50 ms.
Scene: the page's ORTF default room (std_lock18-like body with toe 55, space 0.17).
"""
from __future__ import annotations
import math
import numpy as np
import pytest
import probes as PR

SR = 48000
ORTF = {"decay_lock": True, "decay_s": 1.8, "humidity": 0.35, "early_wet": 1.0,
        "toe_half_deg": 55, "space": 0.17, "yaw_l_deg": -55, "yaw_r_deg": 55}
EARLY = {"fdn_wet": 0, "direct_wet": 1, "early_wet": 1}


def _e(x, a, b):
    return float(np.sum(x[max(a, 0):b] ** 2))


def _early_db(x, n0):
    return 10 * math.log10(_e(x, n0 + int(0.0015 * SR), n0 + int(0.080 * SR)) + 1e-30)


def _scene(extra):
    b = dict(ORTF); b.update(EARLY); b.update(extra); return b


def _pair(ctx, extra):
    body = _scene(extra)
    P = ctx.play_ir(body, {}, 0.5)
    R = ctx.render_ir(body, 500)
    return P, R


def _need_solo_mute(sw):
    PR.need(PR.solo_mute_track_b, sw)


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4_mute_all_render_early_silent(sw, ctx):
    """Mute A-F: the early bus loses every wall reflection in Render (as in Play), direct unchanged."""
    _need_solo_mute(sw)
    P0, R0 = _pair(ctx, {})
    Pm, Rm = _pair(ctx, {"surfaces_mute": list("ABCDEF")})
    n0 = int(np.argmax(np.abs(R0).sum(1)))
    d_r = _early_db(Rm, n0) - _early_db(R0, n0)
    assert d_r <= -20.0, f'Render early with all faces muted: {d_r:+.2f} dB vs none (Play drops them)'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4_mute_play_render_early_agree(sw, ctx):
    """Mute A, Mute E, Solo E and Solo A move the early energy the same way in Play and Render (within 3 dB:
    Play has 32 image lines and no per-hit EQ yet, Render has the full image set)."""
    _need_solo_mute(sw)
    P0, R0 = _pair(ctx, {})
    n0p = int(np.argmax(np.abs(P0).sum(1))); n0r = int(np.argmax(np.abs(R0).sum(1)))
    bad = {}
    for name, ov in (("mute_A", {"surfaces_mute": ["A"]}), ("mute_E", {"surfaces_mute": ["E"]}),
                     ("solo_E", {"surfaces_solo": "E"}), ("solo_A", {"surfaces_solo": "A"})):
        P, R = _pair(ctx, ov)
        dp = _early_db(P, n0p) - _early_db(P0, n0p)
        dr = _early_db(R, n0r) - _early_db(R0, n0r)
        if abs(dp - dr) > 3.0 or (dp < -0.5) != (dr < -0.5):
            bad[name] = (round(dp, 2), round(dr, 2))
    assert not bad, f'early dB vs none (Play, Render): {bad}'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4_solo_mute_direct_untouched(sw, ctx):
    """Direct window (+-1 ms) is unchanged with Mute A-F, in Play and Render (null <= -100 dB;
    Render's FFT noise floor sits near 1e-19)."""
    _need_solo_mute(sw)
    P0, R0 = _pair(ctx, {})
    Pm, Rm = _pair(ctx, {"surfaces_mute": list("ABCDEF")})
    for X0, Xm in ((P0, Pm), (R0, Rm)):
        n0 = int(np.argmax(np.abs(X0).sum(1))); a, b = n0 - SR // 1000, n0 + SR // 1000
        d = float(np.max(np.abs(X0[a:b] - Xm[a:b]))); pk = float(np.max(np.abs(X0[a:b])))
        assert d <= 1e-5 * pk, f'direct window changed under Mute: {20 * math.log10(d / pk + 1e-30):.1f} dB'


@pytest.mark.slow
@pytest.mark.phase('P0.3')
def test_s4_two_diffusion_layers_independent_on_audio(sw, ctx):
    """Smear (jitter_D) moves Render early timing and leaves Play's Dffs alone;
    Tail diffusion (structure_dif) changes Dffs and leaves the early bus bit-identical."""
    PR.need(PR.diffusion_split, sw)
    import json
    def surf(key, v):
        return {L: {key: v} for L in "ABCDEF"}
    base = _scene({})
    Rb = ctx.render_ir(base, 500)
    lb = json.load(open(ctx.params(base)))
    bj = _scene({"surfaces": surf("jitter_D", 0.9)})
    bs = _scene({"surfaces": surf("structure_dif", 0.9)})
    Rj = ctx.render_ir(bj, 500); Rs = ctx.render_ir(bs, 500)
    lj = json.load(open(ctx.params(bj))); ls = json.load(open(ctx.params(bs)))
    assert not np.array_equal(Rj, Rb), 'jitter_D did not move the Render early field'
    assert np.array_equal(Rs, Rb), 'structure_dif changed the early-only Render IR'
    for k in ('l', 'c', 'r'):
        assert lj['buses'][k]['dffs'] == lb['buses'][k]['dffs'], 'jitter_D changed Play Dffs'
        assert ls['buses'][k]['dffs'] != lb['buses'][k]['dffs'], 'structure_dif did not change Play Dffs'
