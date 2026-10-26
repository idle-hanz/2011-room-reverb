"""F13. Hall Play tails fall once each tank has its own sections.

The mirror hall is acceptance test_mirror_symmetry.HALL. Key absent, 12 s.
1 s RMS windows must fall, and window 12 must be at least 40 dB under window 1.
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


def _ctx():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(TESTS), str(SW), str(SW / "engine")]
    os.chdir(SW)
    import run_all as RA
    work = Path(os.environ["TEMP"]) / "f13_hall_no_runaway"
    work.mkdir(parents=True, exist_ok=True)
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(HARNESS / "golden"), regen_golden=False, quick=False,
        perf_scale=1.0, workdir=str(work),
    ))
    return ctx


def _win_db(y, secs=1.0):
    n = int(secs * SR)
    out = []
    for i in range(0, len(y) - n + 1, n):
        out.append(round(float(10 * np.log10(np.mean(y[i:i + n] ** 2) + 1e-300)), 1))
    return out


def _assert_falls(ws, name):
    assert len(ws) >= 12, f"{name} {ws}"
    for i in range(1, len(ws)):
        if ws[i] < -300.0:
            continue
        assert ws[i] < ws[i - 1], f"{name} rose: {ws}"
    assert ws[11] <= ws[0] - 40.0, f"{name} window 12 not 40 dB down: {ws}"


@pytest.mark.slow
def test_hall_two_source_tails_fall():
    ctx = _ctx()
    from test_mirror_symmetry import _body
    rows = {}
    for kind in ("twoB", "twoA"):
        y = ctx.play_ir(_body(kind), {}, 12.0)
        ws = _win_db(y)
        print(f"F2 {kind} {ws}")
        _assert_falls(ws, kind)
        rows[kind] = ws
    assert rows["twoB"][11] <= rows["twoB"][0] - 40.0
