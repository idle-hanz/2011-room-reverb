"""Render helpers for the slow SL tests (Render path through app_server.params_from_body)."""
import inspect, os
import numpy as np
try:
    import _sl_harness as H  # loose folder (software/tests)
except ImportError:
    from tests import _sl_harness as H  # suite launched from software/
from render_pipeline import render
import surf_loop as SL

NOC = {"mic_gain_c": 0.0, "mic_gain_l": 1.0, "mic_gain_r": 1.0}   # as the box prototype (ORTF without C)


UI_BODY = H.fixture("fixture_ui_default_body.json")   # the UI's default scene (as posted by the app; box prototype base)


def render_body(base=None, **over):
    b = dict(UI_BODY if base is None else base); b.update(over)
    os.chdir(H.SW)
    try:
        p = H.A.params_from_body(b)
        dry = np.zeros(1); dry[0] = 1.0
        kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
        kw["desk"] = p
        yl, yr, info = render(dry, 48000, **kw)
    finally:
        os.chdir(H._cwd)
    return np.stack([np.asarray(yl, float), np.asarray(yr, float)], 1), info


def room_body(room, anchor, rows=None, **over):
    W, Hh, L, s, hum = H.room(room)
    surf = {k: {kk: vv for kk, vv in c.items() if kk in ("absorb", "absorb_hz", "diffusion", "material", "eq")} for k, c in s.items()}
    b = dict(NOC, surfaces=surf, decay_mode="surfaces", decay_lock=anchor is not None, decay_s=anchor or 1.8)
    if rows:
        b["surf_treatment"] = rows
    b.update(over)
    return b


def render_room(room, directional=True, anchor=None, rows=None, cal=None, **over):
    return render_body(**room_body(room, anchor, rows, surf_directional=directional, surf_cal=cal, **over))


def render_calibrated(room, directional=True, anchor=None, rows=None, **over):
    """D-SL4: render, measure T20 per octave, scale band losses by T20/T_target (0.6-1.6), render again."""
    ir0, info0 = render_room(room, directional, anchor, rows, **over)
    cal = SL.factors_for_calibrate(
        SL.t20_per_octave(ir0.sum(1)), info0["surf"]["target_T_oct"], directional)
    ir1, info1 = render_room(room, directional, anchor, rows, cal=cal, **over)
    return ir0, info0, ir1, info1, cal
