"""D-AUD-1 / B5. S-MIX already mutes L and R in the Mono centre desk preset.

The re-check is that preset against the same body with L/R gains explicitly 0.
Fader travel does not enter the post: mute folds the gain to 0 first.
This file does not change level. The −10.66 dB table is the pre-S-MIX gap
between L/R gains 1 and 0, printed here as a short unlocked render.
"""
from __future__ import annotations

import inspect
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b5_gates.json"
sys.path[:0] = [str(SW), str(SW / "engine")]
os.chdir(SW)

import app_server as A  # noqa: E402
from desk_matrix import desk_active, fold_for  # noqa: E402
from render_pipeline import render  # noqa: E402

SR = 48000
KEYS = ("ll", "lr", "cl", "cr", "rl", "rr")


def _mono(**over):
    """What the Mono centre preset posts. Mute is already folded into the gains."""
    b = dict(A.DEFAULTS)
    b.update({
        "mic_setup": "mono_c",
        "space": 0.0,
        "toe_half_deg": 0.0,
        "car_omni": 1.0,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "family_l": "cardioid", "family_c": "cardioid", "family_r": "cardioid",
        "polar_l": 0.5, "polar_c": 0.5, "polar_r": 0.5,
        "yaw_l_deg": 0.0, "yaw_c_deg": 0.0, "yaw_r_deg": 0.0,
        "pair_mode": "independent",
        "pan_law": "linear",
        "mic_route_l": "pan", "mic_route_c": "centre", "mic_route_r": "pan",
        "mic_gain_l": 0.0, "mic_gain_c": 1.0, "mic_gain_r": 0.0,
        "mic_pan_l": -1.0, "mic_pan_c": 0.0, "mic_pan_r": 1.0,
        "mic_phase_l": 1.0, "mic_phase_c": 1.0, "mic_phase_r": 1.0,
        "colour_mode": "BYPASS",
        "decay_lock": False,
        "ir_length_ms": 80,
        "direct_wet": 1.0, "early_wet": 1.0, "fdn_wet": 1.0,
        "dry_gain": 0.0,
        "path_on": False,
        "two_sources": False,
    })
    b.update(over)
    return b


def _render(body) -> np.ndarray:
    p = A.params_from_body(body)
    dry = np.zeros(32, dtype=np.float64)
    dry[0] = 1.0
    sig = inspect.signature(render)
    kw = {}
    for name in sig.parameters:
        if name in ("dry", "sr"):
            continue
        if name in p:
            kw[name] = p[name]
    kw["desk"] = p
    y_l, y_r, _info = render(dry, SR, **kw)
    return np.stack([np.asarray(y_l, dtype=np.float64), np.asarray(y_r, dtype=np.float64)], axis=1)


def _weights(body):
    p = A.params_from_body(body)
    w, _mk, _sec = fold_for(p)
    return [w[k] for k in KEYS], bool(desk_active(p))


def _null_db(a, b) -> float:
    n = min(len(a), len(b))
    err = float(np.sum((a[:n] - b[:n]) ** 2))
    ref = float(np.sum(a[:n] ** 2))
    return 10.0 * math.log10(max(err, 1e-300) / max(ref, 1e-300))


def _energy_db(x) -> float:
    return 10.0 * math.log10(max(float(np.sum(x ** 2)), 1e-300))


def test_b5_mono_centre_is_c_only_and_faders_inert():
    preset = _mono()
    muted = _mono(mic_gain_l=0.0, mic_gain_r=0.0)
    moved = _mono(fader_l=1.0, fader_r=0.0, trim_l=12.0, trim_r=-12.0)
    w_preset, active = _weights(preset)
    w_moved, _ = _weights(moved)
    assert active is True
    assert w_preset == [0.0, 0.0, 0.5, 0.5, 0.0, 0.0]
    assert w_moved == w_preset

    ir_preset = _render(preset)
    ir_muted = _render(muted)
    ir_moved = _render(moved)
    null_muted = _null_db(ir_preset, ir_muted)
    null_moved = _null_db(ir_preset, ir_moved)
    max_muted = float(np.max(np.abs(ir_preset - ir_muted)))
    max_moved = float(np.max(np.abs(ir_preset - ir_moved)))
    assert null_muted <= -100.0, null_muted
    assert null_moved <= -100.0, null_moved
    assert max_muted == 0.0
    assert max_moved == 0.0
    corr = float(np.corrcoef(ir_preset[:, 0], ir_preset[:, 1])[0, 1])
    assert corr > 0.999, corr

    # Pre-S-MIX geometry: L and R still at unity, routes still pan. Not a B5 change.
    both = _mono(
        mic_gain_l=1.0, mic_gain_r=1.0,
        pair_mode="", mic_route_l="pan", mic_route_c="pan", mic_route_r="pan",
    )
    ir_both = _render(both)
    n = min(len(ir_both), len(ir_preset))
    total_db = _energy_db(ir_preset[:n]) - _energy_db(ir_both[:n])
    peak_db = 20.0 * math.log10(float(np.max(np.abs(ir_preset[:n])) / max(float(np.max(np.abs(ir_both[:n]))), 1e-30)))
    direct_off = _render(_mono(fdn_wet=0.0, early_wet=0.0, direct_wet=1.0))
    direct_on = _render(_mono(
        mic_gain_l=1.0, mic_gain_r=1.0,
        pair_mode="", mic_route_l="pan", mic_route_c="pan", mic_route_r="pan",
        fdn_wet=0.0, early_wet=0.0, direct_wet=1.0,
    ))
    direct_db = _energy_db(direct_off) - _energy_db(direct_on)
    assert abs(direct_db - (-9.54)) < 0.05, direct_db
    report = {
        "fixed_by": "S-MIX",
        "b5_level_change_db": 0.0,
        "preset_vs_explicit_mute_db": null_muted,
        "preset_vs_moved_fader_db": null_moved,
        "max_abs_mute": max_muted,
        "max_abs_fader": max_moved,
        "weights": w_preset,
        "corr_lr": corr,
        "note": "B5 adds no level. Direct L/R-off vs L/R-on is the coherent 3-to-1 law (−9.54 dB), the same number as the table tail. The table total (−10.66 dB) is the box 2000 ms mix.",
        "direct_lr_off_vs_on_db": round(direct_db, 2),
        "short_mix_lr_off_vs_on_total_db": round(total_db, 2),
        "short_mix_lr_off_vs_on_peak_db": round(peak_db, 2),
        "table_total_db": -10.66,
        "table_tail_db": -9.54,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


def test_b5_other_setups_keep_the_legacy_fold():
    # D20. Plain ORTF has no centre. ORTF + C (stored centre, gain 1) keeps the 477 fold.
    ortf = dict(A.DEFAULTS)
    ortf.update({"mic_setup": "ortf", "pair_mode": "", "mic_route_l": "pan", "mic_route_c": "pan", "mic_route_r": "pan"})
    w, _active = _weights(ortf)
    assert w == [1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    plus = dict(ortf)
    plus.update({"third_mic": "centre", "mic_gain_c": 1.0})
    w_plus, active_plus = _weights(plus)
    assert active_plus is False
    assert w_plus == [1.0, 0.0, 0.5, 0.5, 0.0, 1.0]
    ms = dict(A.DEFAULTS)
    ms.update({"mic_setup": "ms", "pair_mode": "", "mic_route_c": "centre"})
    w_ms, active_ms = _weights(ms)
    assert active_ms is True
    assert w_ms[2] == 0.5 and w_ms[3] == 0.5
    assert w_ms[0] == 1.0 and w_ms[1] == 0.0
