"""Re-render the five harness goldens and require max-abs 0.

Slow. Does not rewrite the files. From software\\:

software\\.venv\\Scripts\\python.exe -m pytest tests\\test_golden_rerender.py -q -m slow
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
sys.path.insert(0, str(HARNESS))

import run_all as RA  # noqa: E402


def _max_abs(name: str, arr: np.ndarray) -> float:
    ref = np.fromfile(HARNESS / "golden" / f"{name}.f32", np.float32).reshape(-1, 2).astype(np.float64)
    if len(ref) != len(arr):
        raise AssertionError(f"{name}: length {len(arr)} != golden {len(ref)}")
    return float(np.max(np.abs(ref - arr)))


@pytest.mark.slow
def test_five_goldens_max_abs_zero():
    """Harness t03 Play and t04 Render against the five on-disk goldens."""
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW),
        python=sys.executable,
        node="node",
        golden=str(HARNESS / "golden"),
        regen_golden=False,
        quick=False,
        perf_scale=1.0,
        workdir=os.environ.get("TEMP") or str(ROOT),
    ))
    for sc in ("std_unlocked", "std_lock18"):
        for tag, over in (("byp", {"colour_on": False}), ("col", {})):
            name = f"play_{sc}_{tag}"
            mx = _max_abs(name, ctx.play_ir(sc, over, 1.5))
            assert mx == 0.0, (name, mx)
    body = dict(RA.SCENES["std_unlocked"])
    body.update({"colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1})
    mx = _max_abs("render_std_unlocked_byp", ctx.render_ir(body, 500))
    assert mx == 0.0, ("render_std_unlocked_byp", mx)
