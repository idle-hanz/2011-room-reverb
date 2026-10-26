"""F13. Two-source hall Render vs Play, key absent.

Render goes through render() with two_sources and both dry channels.
render_ir.py forces two_sources off, so this test does not use it.
"""
from __future__ import annotations
import pytest

import os
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
TESTS = HARNESS.parent / "tests"
PY = SW / ".venv" / "Scripts" / "python.exe"
NODE = Path(os.environ.get(
    "RR_NODE",
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
))
SR = 48000
BANDS = [125, 250, 500, 1000, 2000, 4000]


def _ctx():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(TESTS), str(SW), str(SW / "engine")]
    os.chdir(SW)
    import run_all as RA
    import app_server as A
    from render_pipeline import render
    work = Path(os.environ["TEMP"]) / "f13_hall_render_play"
    work.mkdir(parents=True, exist_ok=True)
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(HARNESS / "golden"), regen_golden=False, quick=False,
        perf_scale=1.0, workdir=str(work),
    ))
    return ctx, A, render


def _one_render(A, render, body, ms_len=3000):
    p = A.params_from_body(dict(body, ir_length_ms=ms_len))
    assert p.get("phys_ceiling") is True
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    kw = dict(
        W=p["W"], H=p["H"], L=p["L"], sox=p["sox"], soz=p["soz"], mz=p["mz"], my=p["my"], sy=p.get("sy"),
        sx=p["sx"], sz=p["sz"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
        early_wet=0.0, fdn_wet=1.0, dry_gain=0.0, direct_wet=0.0,
        fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"], path_on=p["path_on"], path_preset=p["path_preset"],
        ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"), hadamard_n=p["hadamard_n"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
        polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0, mic_hp_on=False, mic_hp_hz=40.0,
        mic_response_hz=p.get("mic_response_hz") or 10000.0, mic_proximity=0.0,
        ms_decode=False, capsule_mm=p.get("capsule_mm") or 17.0, surfaces=p.get("surfaces"),
        diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"], humidity=p.get("humidity") or 0.0,
        air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.25,
        air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
        reaktor_parity=False, air_climate="studio_20C_50RH", air_iso=True,
        diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.5,
        decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
        smooth=True, movement=0.0, sub_hp=True,
        mic_gain_l=p.get("mic_gain_l", 1.0), mic_gain_c=p.get("mic_gain_c", 1.0), mic_gain_r=p.get("mic_gain_r", 1.0),
        mic_pan_l=p.get("mic_pan_l", -1.0), mic_pan_c=0.0, mic_pan_r=1.0,
        mic_phase_l=1.0, mic_phase_c=1.0, mic_phase_r=1.0,
        two_sources=True, source_balance=p.get("source_balance") or 0.0, mirror_b=bool(p.get("mirror_b")),
        sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"), dry_l=dry, dry_r=dry,
        colour_mode="BYPASS",
        phys_ceiling=bool(p.get("phys_ceiling")),
    )
    L, R, info = render(dry, SR, **kw)
    L = np.asarray(L, dtype=np.float64).reshape(-1)
    R = np.asarray(R, dtype=np.float64).reshape(-1)
    n = min(len(L), len(R))
    return np.stack([L[:n], R[:n]], 1), info


def _t30(x):
    from analyze import t60_bands
    row = t60_bands(np.asarray(x, dtype=np.float64), SR, bands=BANDS)
    return [float(row[b]) for b in BANDS]


def _within_tol(m, tol):
    return [k for k in tol if m[k] > tol[k]]


@pytest.mark.slow
def test_hall_render_and_play_mirror_and_t30():
    ctx, A, render = _ctx()
    from test_mirror_symmetry import TOL, _body, mirror_metrics
    ov = dict(colour_mode="BYPASS")
    ba = _body("twoA", **ov)
    bb = _body("twoB", **ov)
    RA, info_a = _one_render(A, render, ba)
    RB, info_b = _one_render(A, render, bb)
    assert isinstance(info_a.get("phys_ceiling"), dict)
    assert isinstance(info_b.get("phys_ceiling"), dict)
    rm = mirror_metrics(RA, RB)
    print("F3 render", {k: round(float(rm[k]), 4) for k in TOL}, "n", len(RA))
    bad = _within_tol(rm, TOL)
    assert not bad, f"render mirror {bad} {rm}"

    PA = ctx.play_ir(ba, {"colour_on": False}, 3.0)
    PB = ctx.play_ir(bb, {"colour_on": False}, 3.0)
    pm = mirror_metrics(PA, PB)
    print("F3 play", {k: round(float(pm[k]), 4) for k in TOL}, "n", len(PA))
    bad = _within_tol(pm, TOL)
    assert not bad, f"play mirror {bad} {pm}"

    fails = []
    report = {}
    for name, play, rend in (("twoA", PA, RA), ("twoB", PB, RB)):
        n = min(len(play), len(rend))
        for ch, label in ((0, "L"), (1, "R")):
            tp = _t30(play[:n, ch])
            tr = _t30(rend[:n, ch])
            report[f"{name}_{label}"] = {"play": [round(v, 4) for v in tp], "render": [round(v, 4) for v in tr]}
            for hz, a, b in zip(BANDS, tp, tr):
                if not (np.isfinite(a) and np.isfinite(b) and b != 0.0):
                    fails.append(f"{name} {label} {hz} play {a} render {b}")
                    continue
                rel = abs(a / b - 1.0)
                if rel > 0.10:
                    fails.append(f"{name} {label} {hz} {a:.4f} vs {b:.4f} ({rel:.3%})")
    print("F3 t30", report)
    assert not fails, fails
