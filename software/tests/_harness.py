"""Shared harness for the Thursday test drafts. Copy next to the tests in software/tests/.
Mirrors tests/test_b5_mono.py: post a body through app_server.params_from_body and render."""
from __future__ import annotations
import inspect, math, os, sys
from pathlib import Path
import numpy as np

SW = Path(os.environ.get("RR_SOFTWARE", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(SW), str(SW / "engine")]
os.chdir(SW)
import app_server as A  # noqa: E402
from desk_matrix import fold_for  # noqa: E402
from render_pipeline import render  # noqa: E402

SR = 48000
KEYS = ("ll", "lr", "cl", "cr", "rl", "rr")


def body(**over):
    b = dict(A.DEFAULTS)
    b.update({"colour_mode": "BYPASS", "decay_lock": False, "ir_length_ms": 80,
              "dry_gain": 0.0, "path_on": False, "two_sources": False,
              "pan_law": "linear"})
    b.update(over)
    return b


def ortf(**over):
    b = body(mic_setup="ortf", space=0.17, toe_half_deg=55.0, car_omni=1.0,
             pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
             family_l="cardioid", family_c="cardioid", family_r="cardioid",
             polar_l=0.5, polar_c=0.5, polar_r=0.5,
             yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0, pair_mode="stereo",
             mic_route_l="pan", mic_route_c="pan", mic_route_r="pan",
             mic_gain_l=1.0, mic_gain_c=0.0, mic_gain_r=1.0,
             mic_pan_l=-1.0, mic_pan_c=0.0, mic_pan_r=1.0,
             mic_phase_l=1.0, mic_phase_c=1.0, mic_phase_r=1.0)
    b.update(over)
    return b


def ms(m_family="cardioid", m_polar=0.5, s_yaw=90.0, m_gain=1.5, **over):
    """MS classic as app.js loadDeskPreset('ms_classic') + MIC_PRESETS.ms_classic post it."""
    b = body(mic_setup="ms_classic", ms_decode=True, space=0.05, toe_half_deg=90.0, car_omni=1.0,
             pattern_l="fig8", pattern_c=("omni" if m_family == "omni" else "cardioid"), pattern_r="fig8",
             family_l="bi", family_c=m_family, family_r="bi",
             polar_l=0.5, polar_c=m_polar, polar_r=0.5,
             yaw_l_deg=s_yaw, yaw_c_deg=0.0, yaw_r_deg=90.0, pair_mode="ms", ms_s="l", ms_m="c",
             mic_route_l="s", mic_route_c="both", mic_route_r="pan",
             mic_gain_l=1.0, mic_gain_c=m_gain, mic_gain_r=0.0,
             mic_pan_l=-1.0, mic_pan_c=0.0, mic_pan_r=1.0,
             mic_phase_l=1.0, mic_phase_c=1.0, mic_phase_r=1.0)
    b.update(over)
    return b


def render_body(b) -> np.ndarray:
    p = A.params_from_body(b)
    dry = np.zeros(32); dry[0] = 1.0
    kw = {n: p[n] for n in inspect.signature(render).parameters if n not in ("dry", "sr") and n in p}
    kw["desk"] = p
    y_l, y_r, _ = render(dry, SR, **kw)
    return np.stack([np.asarray(y_l, float), np.asarray(y_r, float)], axis=1)


def weights(b):
    w, _mk, _sec = fold_for(A.params_from_body(b))
    return {k: w[k] for k in KEYS}


def lr_db(ir, n=None) -> float:
    """Left minus right energy in dB (positive = image to the left)."""
    x = ir[:n] if n else ir
    el, er = float(np.sum(x[:, 0] ** 2)), float(np.sum(x[:, 1] ** 2))
    return 10 * math.log10(max(el, 1e-30) / max(er, 1e-30))


def null_db(a, b) -> float:
    n = min(len(a), len(b))
    return 10 * math.log10(max(float(np.sum((a[:n] - b[:n]) ** 2)), 1e-300) / max(float(np.sum(a[:n] ** 2)), 1e-300))
