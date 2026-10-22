"""Two-source physics pack. Each tank has its own sections.

A two-source body with the key absent arms the pack: surf_on 1, both
surf_sos and surf_sos_b length 1440, and both banks under 0 dB. The live
dict still has no phys_ceiling field. Explicit false stays the PHYSDEFAULT
live MD5, with no second pack. One source does not grow surf_sos_b.
The T30 numbers live in test_physdefault_t30.py and are not re-pinned here.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
PY = SW / ".venv" / "Scripts" / "python.exe"
NODE = Path(os.environ.get(
    "RR_NODE",
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
))
TWO_ABSENT_MD5 = "a5dcacc67a269c234c4b5745899b038e"
TWO_FALSE_MD5 = "0e94bd03d899b76b43adf31ae87f0cd2"


def _ctx():
    sys.path[:0] = [str(HARNESS), str(HARNESS / "lib"), str(SW), str(SW / "engine")]
    os.chdir(SW)
    import run_all as RA
    import app_server as A
    work = Path(os.environ["TEMP"]) / "physdefault_two_source_guard"
    work.mkdir(parents=True, exist_ok=True)
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=str(PY), node=str(NODE),
        golden=str(HARNESS / "golden"), regen_golden=False, quick=False,
        perf_scale=1.0, workdir=str(work),
    ))
    return RA, A, ctx


def _live(A, body):
    p = A.params_from_body(dict(body))
    blob = A.live_fdn_params(p)
    return p, blob


def _md5(blob):
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def test_two_source_pack_and_one_source_stays_without_bank_b():
    RA, A, _ctx_unused = _ctx()
    base = dict(RA.SCENES["std_lock18"])
    assert "phys_ceiling" not in base

    absent_p, absent_blob = _live(A, dict(base, two_sources=True))
    false_p, false_blob = _live(A, dict(base, two_sources=True, phys_ceiling=False))
    true_p, true_blob = _live(A, dict(base, two_sources=True, phys_ceiling=True))
    assert absent_p["phys_ceiling"] is True
    assert true_p["phys_ceiling"] is True
    assert false_p["phys_ceiling"] is False
    assert "phys_ceiling" not in absent_blob
    assert "phys_ceiling" not in false_blob
    assert "phys_ceiling" not in true_blob
    assert int(absent_blob.get("surf_on") or 0) == 1
    assert len(absent_blob.get("surf_sos") or []) == 1440
    assert len(absent_blob.get("surf_sos_b") or []) == 1440
    stab = absent_blob["surf_stab"]
    assert stab["max_loop_db"] < 0.0
    assert stab["max_loop_db_a"] < 0.0
    assert stab["max_loop_db_b"] < 0.0
    assert absent_blob == true_blob
    assert _md5(absent_blob) == TWO_ABSENT_MD5
    assert int(false_blob.get("surf_on") or 0) == 0
    assert "surf_sos_b" not in false_blob
    assert _md5(false_blob) == TWO_FALSE_MD5

    one_p, one_blob = _live(A, base)
    off_p, off_blob = _live(A, dict(base, phys_ceiling=False))
    assert one_p["phys_ceiling"] is True
    assert off_p["phys_ceiling"] is False
    assert "phys_ceiling" not in one_blob
    assert int(one_blob.get("surf_on") or 0) == 1
    assert len(one_blob.get("surf_sos") or []) == 1440
    assert "surf_sos_b" not in one_blob
    assert set(one_blob["surf_stab"]) == {"max_loop_db"}
    assert int(off_blob.get("surf_on") or 0) == 0

    pin_path = Path(__file__).with_name("test_physdefault_t30.py")
    spec = importlib.util.spec_from_file_location("physdefault_t30_pin", pin_path)
    pin_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pin_mod)
    assert pin_mod.PIN == {
        125: 2.271852,
        250: 2.214763,
        500: 2.017107,
        1000: 1.561790,
        2000: 1.160893,
        4000: 0.853239,
    }
