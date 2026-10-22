"""PHYSDEFAULT pin. Boot harness std_lock18, phys_ceiling key absent.

Play T30 (Schroeder -5..-35) on the left channel, 125 Hz to 4 kHz.
Colour off, early 0, direct 0, 8 s. The gate is 0.02 relative to the
values measured on 2026-10-19. This row is T30. It is not the F9 T20 row.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
PY = SW / ".venv" / "Scripts" / "python.exe"
NODE = Path(os.environ.get(
    "RR_NODE",
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
))
SR = 48000
BANDS = (125, 250, 500, 1000, 2000, 4000)
# Measured this run: harness play_ir std_lock18, key absent, left channel, 8 s.
PIN = {
    125: 2.271852,
    250: 2.214763,
    500: 2.017107,
    1000: 1.561790,
    2000: 1.160893,
    4000: 0.853239,
}


def test_physdefault_std_lock18_t30_pin():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(SW), str(SW / "engine")]
    os.chdir(SW)
    import run_all as RA
    from analyze import t60_bands

    work = Path(os.environ["TEMP"]) / "physdefault_t30_pin"
    work.mkdir(parents=True, exist_ok=True)
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(HARNESS / "golden"), regen_golden=False, quick=False,
        perf_scale=1.0, workdir=str(work),
    ))
    body = dict(RA.SCENES["std_lock18"])
    assert "phys_ceiling" not in body
    x = ctx.play_ir(
        "std_lock18",
        {"colour_on": False, "early_wet": 0, "direct_wet": 0},
        8.0,
    )
    t = t60_bands(np.asarray(x[:, 0], np.float64), SR, bands=list(BANDS))
    for fc, exp in PIN.items():
        got = float(t[fc])
        rel = abs(got / exp - 1.0)
        assert rel <= 0.02, f"{fc} Hz T30 {got:.4f} vs pin {exp:.4f} (rel {rel:.4f})"
