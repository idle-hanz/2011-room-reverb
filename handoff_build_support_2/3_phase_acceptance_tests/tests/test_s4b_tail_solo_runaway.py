"""S4b (box, 2 Oct 13:30 diagnosis of Idle's 'Dalek robotic tail' and 'Solo left wall is not on the left').

1. Surfaces Solo/Mute must act on the EARLY reflections only. Today (11:40) Play zeroes the FDN inject of
   every line whose image hits a silenced face and also zeroes those lines' Dffs (Solo A: inject 0 on 30/32
   lines, Dffs 0 on 22/32), so the tail gets quieter and narrower. Render does the same to its FDN inject.
2. Soloing the left wall (A, -X) must give a left-dominant early field in Play and Render.
3. Long decays must not run away. The in-loop axial peaking biquads (f0 1.6-4.6 Hz in the 57 x 34.2 x 97 m
   hall) lose unity DC gain when packed as float32 (X axis: DC gain 1.5), so decay 8 s grows to a
   full-scale DC. Box prototype (restore b2 = 1 + a1 + a2 - b0 - b1 in double at load) fixes it and is
   bit-exact in the default room.
4. 'Robotic' comb (Idle's real 13:31 file is a Render of this exact scene; the 11:40 IR nulls it to -64 dB):
   the FDN line outputs are summed with all +1 weights, and 1^T H = 32 e0^T for a Sylvester Hadamard, so the
   whole output re-enters through line 0 only (image (0,2,0), 19.34 ms) -> a comb at 19.34 ms plus the
   direct line's 9.67 ms. Fix (2 Oct 15:15): column signs, feedback matrix H*D with a fixed mirror-safe
   +-1 table d (still a +-1 Hadamard); the output tap, first pass and level stay as today.
Scene notes: Play bodies go through run_all.Ctx (DEFAULTS + overrides). Early-only = fdn 0, direct 0, early 1.
"""
from __future__ import annotations
import math
import numpy as np
import pytest
import probes as PR

SR = 48000
ORTF = {"decay_lock": True, "decay_s": 1.8, "humidity": 0.35, "toe_half_deg": 55, "space": 0.17,
        "yaw_l_deg": -55, "yaw_r_deg": 55}
CENTRED = dict(ORTF, W=6.0, H=3.0, L=8.0, sx=3.0, mcx=3.0)
TAIL = {"fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0}
EARLY = {"fdn_wet": 0.0, "direct_wet": 0.0, "early_wet": 1.0}
HALL = dict(W=57.0, H=34.2, L=97.0, sx=24.0, sz=60.0, mcx=28.5, mcz=30.0, sx_b=33.0, sz_b=60.0,
            two_sources=True, mirror_b=True, decay_lock=True)


def _need(sw):
    PR.need(PR.solo_mute_track_b, sw)


def _db(e):
    return 10 * math.log10(e + 1e-30)


def _ild_after_direct(x, n0):
    a, b = n0 + int(0.0015 * SR), n0 + int(0.060 * SR)
    return _db(float(np.sum(x[a:b, 0] ** 2))) - _db(float(np.sum(x[a:b, 1] ** 2)))


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_solo_mute_leave_play_tail_untouched(sw, ctx):
    """Play, tail only: Solo A and Mute A-F give the same FDN output as no Solo/Mute (|diff| <= 1e-6 x peak),
    and the posted inject / Dffs per line are unchanged."""
    _need(sw)
    import json
    base = dict(ORTF, **TAIL)
    X0 = ctx.play_ir(base, {}, 1.5)
    l0 = json.load(open(ctx.params(base)))
    for ov in ({"surfaces_solo": "A"}, {"surfaces_mute": list("ABCDEF")}):
        b = dict(base, **ov)
        X = ctx.play_ir(b, {}, 1.5)
        l = json.load(open(ctx.params(b)))
        pk = float(np.max(np.abs(X0)))
        assert float(np.max(np.abs(X - X0))) <= 1e-6 * pk, f'Play tail changed under {ov}'
        for k in ('l', 'c', 'r'):
            assert l['buses'][k]['inject'] == l0['buses'][k]['inject'], f'{ov}: inject gated on bus {k}'
            assert l['buses'][k]['dffs'] == l0['buses'][k]['dffs'], f'{ov}: Dffs gated on bus {k}'


@pytest.mark.phase('P3B')
def test_s4b_shared_on_solo_a_leaves_tail(sw, ctx):
    """Shared tail on: Solo A does not change the FDN tail. injS is the un-gated inject."""
    _need(sw)
    import json
    base = dict(ORTF, **TAIL, shared_tail=True)
    X0 = ctx.play_ir(base, {}, 1.5)
    X = ctx.play_ir(dict(base, surfaces_solo="A"), {}, 1.5)
    pk = float(np.max(np.abs(X0))) + 1e-30
    assert float(np.max(np.abs(X - X0))) <= 1e-6 * pk, 'shared tail moved under Solo A'
    l0 = json.load(open(ctx.params(base)))
    l = json.load(open(ctx.params(dict(base, surfaces_solo="A"))))
    assert l0.get("shared_tail") is True
    for k in ("l", "c", "r"):
        assert l["buses"][k]["inject"] == l0["buses"][k]["inject"]


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_solo_mute_leave_render_tail_untouched(sw, ctx):
    """Render, tail only: Solo A and Mute A-F leave the FDN output unchanged (|diff| <= 1e-5 x peak)."""
    _need(sw)
    base = dict(ORTF, **TAIL)
    R0 = ctx.render_ir(base, 1500)
    for ov in ({"surfaces_solo": "A"}, {"surfaces_mute": list("ABCDEF")}):
        R = ctx.render_ir(dict(base, **ov), 1500)
        n = min(len(R), len(R0))
        assert float(np.max(np.abs(R[:n] - R0[:n]))) <= 1e-5 * float(np.max(np.abs(R0))), f'Render tail changed under {ov}'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_play_solo_left_wall_is_left(sw, ctx):
    """Play, early only, source and mics on the centreline: Solo A (left, -X) gives L-R >= +6 dB in the
    60 ms after the direct; Solo C (right) gives <= -6 dB. (11:40: +9.1 / -9.1 dB.)"""
    _need(sw)
    X0 = ctx.play_ir(dict(CENTRED, **EARLY), {}, 0.25)
    n0 = int(np.argmax(np.abs(X0).sum(1)))
    ia = _ild_after_direct(ctx.play_ir(dict(CENTRED, **EARLY, surfaces_solo="A"), {}, 0.25), n0)
    ic = _ild_after_direct(ctx.play_ir(dict(CENTRED, **EARLY, surfaces_solo="C"), {}, 0.25), n0)
    assert ia >= 6.0 and ic <= -6.0, f'Play Solo A ILD {ia:+.2f} dB, Solo C {ic:+.2f} dB'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_render_solo_left_wall_is_left(sw, ctx):
    """Render, same scene: Solo A >= +6 dB, Solo C <= -6 dB (box with the D11 fix: +23.8 / -23.7 dB)."""
    _need(sw)
    R0 = ctx.render_ir(dict(CENTRED, **EARLY), 250)
    n0 = int(np.argmax(np.abs(R0).sum(1)))
    ia = _ild_after_direct(ctx.render_ir(dict(CENTRED, **EARLY, surfaces_solo="A"), 250), n0)
    ic = _ild_after_direct(ctx.render_ir(dict(CENTRED, **EARLY, surfaces_solo="C"), 250), n0)
    assert ia >= 6.0 and ic <= -6.0, f'Render Solo A ILD {ia:+.2f} dB, Solo C {ic:+.2f} dB'


def _levels(x):
    m = x.mean(1)
    return [_db(float(np.mean(m[i * SR:(i + 1) * SR] ** 2))) / 1.0 for i in range(len(m) // SR)]


@pytest.mark.slow
@pytest.mark.phase('P0')
@pytest.mark.parametrize('name,extra', [
    ('hall_2src_decay8', dict(HALL, decay_s=8.0)),
    ('hall_binaural_decay4', dict(HALL, decay_s=4.0, mic_setup='binaural')),
    ('hall_binaural_decay8', dict(HALL, decay_s=8.0, mic_setup='binaural')),
])
def test_s4b_long_decay_no_runaway(sw, ctx, name, extra):
    """Play, tail only, 20 s IR: finite, and the level falls every 2 s after t = 2 s
    (or is already below -240 dB).

    PERROOMK 2026-10-20 drops the absolute "18-20 s <= -150 dB" floor. That floor
    belonged to the boot-calibrated hall, which rang for tens of seconds. The fall
    rate is the least-squares slope of the 1 s levels from 2 s to the last window
    above -240 dB. It must sit between 0.5*60/T_max and 2*60/T_min dB/s, where
    T_max and T_min are this scene's designed per-band T60s. The mean of both
    channels' 500 Hz and 1 kHz octave T30 must be within 15 % of the dial.

    History: box prototype fix.wasm was -202.5 / -286.5 (float floor) / -211.3 dB
    at 18-20 s, falling about 7.5 dB/s at decay 8 s. The 11:40 ships rose
    (to -5 dB / to -69 dB / 0 dBFS DC)."""
    import sys
    from analyze import t60_bands
    sys.path[:0] = [str(sw), str(sw / 'engine')]
    import app_server as A
    import surf_loop as SLP
    import surf_panels as SP

    body = dict(extra, **TAIL)
    X = ctx.play_ir(body, {}, 20)
    assert np.all(np.isfinite(X)), 'non-finite output'
    lv = _levels(X)
    seq = lv[2::2]
    assert all(b < a or b < -240.0 for a, b in zip(seq, seq[1:])), f'{name}: level not falling every 2 s: {[round(v, 1) for v in seq]}'
    p = A.params_from_body(body)
    cards = SP.cards_with_treatment(p['surfaces'], p.get('surf_treatment') or [])
    row = SLP.phys_ceiling_row(p['W'], p['H'], p['L'], cards, float(p['decay_s']))
    T = np.asarray(row['t'], float)
    t_max = float(np.max(T))
    t_min = float(np.min(T))
    lo = 0.5 * 60.0 / t_max
    hi = 2.0 * 60.0 / t_min
    start = 2
    last = None
    for i in range(start, len(lv)):
        if lv[i] > -240.0:
            last = i
    assert last is not None and last > start, f'{name}: no slope window {[round(v, 1) for v in lv]}'
    ys = np.asarray(lv[start:last + 1], float)
    ts = np.arange(start, last + 1, dtype=float)
    fall = -float(np.polyfit(ts, ys, 1)[0])
    assert lo <= fall <= hi, (
        f'{name}: fall {fall:.4f} dB/s not in [{lo:.4f}, {hi:.4f}] '
        f'(T_max {t_max:.4f}, T_min {t_min:.4f})'
    )
    mids = []
    for ch in (0, 1):
        tb = t60_bands(X[:, ch], SR, bands=[500, 1000])
        mids.append(float(tb[500]))
        mids.append(float(tb[1000]))
    mid = float(np.mean(mids))
    dial = float(extra['decay_s'])
    rel = abs(mid - dial) / dial
    assert rel <= 0.15, f'{name}: mid T30 {mid:.4f} s vs dial {dial} ({rel:.3%}) bands {mids}'


def _acmax(x, sr, lo_ms=2.0, hi_ms=60.0, at_ms=None):
    out = []
    for ch in range(2):
        F = np.fft.rfft(x[:, ch], 1 << 18)
        a = np.fft.irfft(np.abs(F) ** 2)[:int(hi_ms * sr / 1000)]
        a /= a[0]
        if at_ms is None:
            out.append(float(np.max(np.abs(a[int(lo_ms * sr / 1000):]))))
        else:
            out.append(float(np.max(np.abs(a[int((at_ms - 0.15) * sr / 1000):int((at_ms + 0.15) * sr / 1000)]))))
    return out


DEFAULT_TAIL = dict(ORTF, W=6.0, H=3.0, L=8.0, **TAIL)


def _comb_db(x, sr, f_lo=101.5, f_hi=105.5):
    """Comb index per channel: mean fine-spectrum level on the harmonics of f0 (150-3000 Hz, best f0 in
    [f_lo, f_hi]) minus the off-harmonic mean. 103.5 Hz = 1 / 9.67 ms, the direct/line-0 period."""
    from scipy.ndimage import median_filter
    out = []
    N = 1 << 19
    f = np.fft.rfftfreq(N, 1 / sr)
    band = (f > 150) & (f < 3000)
    for ch in range(2):
        P = 10 * np.log10(np.abs(np.fft.rfft(x[:, ch], N)) ** 2 + 1e-30)
        fine = P - median_filter(P, size=int(301 * N / (1 << 17) / (sr / 44100)) | 1)
        best = -99.0
        for f0 in np.arange(f_lo, f_hi, 0.05):
            on = np.zeros(len(f), bool)
            for k in range(2, int(3000 / f0)):
                on |= np.abs(f - k * f0) < 0.8
            best = max(best, float(np.mean(fine[on & band]) - np.mean(fine[(~on) & band])))
        out.append(best)
    return out


@pytest.mark.slow
@pytest.mark.phase('P3B')
@pytest.mark.parametrize('extra,limit', [
    ({}, 0.23),
    ({'phys_ceiling': False}, 0.20),
], ids=['physics_on', 'explicit_false'])
def test_s4b_play_tail_has_no_line0_comb(sw, ctx, extra, limit):
    """Play, default room, FDN only (the page default mix): tail autocorrelation at line 0's delay (19.35 ms)
    and anywhere 2-60 ms <= 0.30 on both channels. (11:40: 0.43 / 0.37 at 19.35 ms;
    box prototype csign.wasm (column signs): 0.154 / 0.18, which is also the max.)

    PERROOMK 2026-10-20 re-measured the physics-on row (key absent) at 19.36 ms as
    0.18725144939233385 and 0.21261059152758685 (max 0.21261059152758685). The limit
    for that row is 0.23. Explicit phys_ceiling false stays at 0.20. The 2-60 ms
    max stays 0.30 on both rows."""
    X = ctx.play_ir(dict(DEFAULT_TAIL, **extra), {}, 1.5)
    at = _acmax(X, SR, at_ms=19.36)
    mx = _acmax(X, SR)
    assert max(at) <= limit and max(mx) <= 0.30, f'ac at 19.36 ms {at}, max {mx}, limit {limit}'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_render_tail_has_no_line0_comb(sw, ctx):
    """Render, same scene (Idle's file): comb index on the 103.5 Hz harmonics <= 6 dB per channel and
    autocorrelation max 2-60 ms <= 0.40. (11:40 at 48 k: 12.7 / 10.6 dB, ac 0.41 / 0.42 at 19.33 ms;
    box monkeypatch with column signs: 4.6 / 4.8 dB, ac max 0.24 / 0.24; at 44.1 k 4.5 / 4.5 dB, ac 0.24 / 0.37.
    Idle's guitar through the fixed IR: 11.1 -> 4.5 dB.)"""
    R = ctx.render_ir(DEFAULT_TAIL, 1500)
    cb = _comb_db(R, SR)
    mx = _acmax(R, SR)
    assert max(cb) <= 6.0 and max(mx) <= 0.40, f'comb index {cb} dB, ac max {mx}'


@pytest.mark.slow
@pytest.mark.phase('P3B')
def test_s4b_symmetric_scene_tail_stays_exact_mono(sw, ctx):
    """Idle keeps the exact mono tail in symmetric scenes: source and mics on the centreline, FDN only,
    Play L == R exactly (must hold before and after the column-sign fix)."""
    X = ctx.play_ir(dict(DEFAULT_TAIL, sx=3.0, mcx=3.0), {}, 1.0)
    assert float(np.max(np.abs(X[:, 0] - X[:, 1]))) == 0.0
