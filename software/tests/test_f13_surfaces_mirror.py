"""F13. Surfaces two-source Play mirror, explicit physics off.

Hall and boot. The before row drops surf_sos_b so the worklet copies A's
sections onto B, which is the pre-fix path. The gate is the after row.
"""
from __future__ import annotations
import pytest

import json
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


def _ctx():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(TESTS), str(SW), str(SW / "engine")]
    os.chdir(SW)
    import run_all as RA
    work = Path(os.environ["TEMP"]) / "f13_surfaces_mirror"
    work.mkdir(parents=True, exist_ok=True)
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(HARNESS / "golden"), regen_golden=False, quick=False,
        perf_scale=1.0, workdir=str(work),
    ))
    return ctx


def _boot(balance):
    return dict(
        toe_half_deg=55.0, space=0.17, decay_lock=True, decay_s=1.8, humidity=0.5,
        mirror_b=True, two_sources=True, source_balance=balance,
        fdn_wet=1.0, direct_wet=0.0, early_wet=0.0, dry_gain=0.0,
        decay_mode="surfaces", phys_ceiling=False, colour_mode="BYPASS",
    )


def _play_stripped(ctx, body, secs, tag):
    src = Path(ctx.params(body))
    data = json.loads(src.read_text(encoding="utf-8"))
    assert len(data.get("surf_sos_b") or []) == 1440, tag
    data.pop("surf_sos_b")
    dst = ctx.work / f"{tag}_before.json"
    dst.write_text(json.dumps(data), encoding="utf-8")
    out = ctx.work / f"{tag}_before.f32"
    if out.exists():
        out.unlink()
    ctx.play(dst, {"colour_on": False}, "ir", secs, out)
    return np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)


def _metrics(A, B, mirror_metrics, tol):
    m = mirror_metrics(A, B)
    row = {k: round(float(m[k]), 4) for k in tol}
    return row, [k for k in tol if m[k] > tol[k]]


@pytest.mark.slow
def test_surfaces_two_source_mirror():
    ctx = _ctx()
    from test_mirror_symmetry import TOL, _body, mirror_metrics
    pairs = {
        "hall": (
            _body("twoA", decay_mode="surfaces", phys_ceiling=False, colour_mode="BYPASS"),
            _body("twoB", decay_mode="surfaces", phys_ceiling=False, colour_mode="BYPASS"),
        ),
        "boot": (_boot(-1.0), _boot(1.0)),
    }
    for name, (ba, bb) in pairs.items():
        before_a = _play_stripped(ctx, ba, 3.0, f"{name}_a")
        before_b = _play_stripped(ctx, bb, 3.0, f"{name}_b")
        after_a = ctx.play_ir(ba, {"colour_on": False}, 3.0)
        after_b = ctx.play_ir(bb, {"colour_on": False}, 3.0)
        before, before_bad = _metrics(before_a, before_b, mirror_metrics, TOL)
        after, after_bad = _metrics(after_a, after_b, mirror_metrics, TOL)
        print(f"F4 {name} before {before} bad {before_bad}")
        print(f"F4 {name} after {after} bad {after_bad}")
        assert not after_bad, f"{name} after {after_bad} {after}"
