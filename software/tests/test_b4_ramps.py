"""B4 / D-AUD-4. Play desk gains ramp over 10 ms. Init is already at the target.

A static scene stays on the old multiply, so the Play goldens are unchanged.
This file checks a move: the step stays with the sine, and an FDN unmute
keeps the tail that ran while the output was down.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
PY = sys.executable
SR = 48000
BLK = 128


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])
    return r.stdout


def _params(tmp, body):
    dest = tmp / "params.json"
    _run([PY, str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(dest), str(SR)])
    return dest, json.loads(dest.read_text(encoding="utf-8"))


def _play(tmp, params, mode, args, sched=None, tag="out"):
    node = shutil.which("node")
    assert node, "node is required"
    out = tmp / f"{tag}.f32"
    cmd = [node, str(LIB / "wasm_run.js"), str(SW), str(params),
           json.dumps({"colour_on": False}), mode, *[str(a) for a in args], str(out)]
    if sched is not None:
        cmd.append(sched if isinstance(sched, str) else json.dumps(sched))
    _run(cmd)
    return np.fromfile(out, dtype=np.float32).reshape(-1, 2).astype(np.float64)


def _align(t_s):
    return int(round(t_s * SR / BLK)) * BLK


def _max_step(x):
    if len(x) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(x))))


def _hf_db(x):
    """Power above 5 kHz. Hann so a level change at the ends is not a click."""
    w = np.hanning(len(x))
    spec = np.fft.rfft(x * w)
    freq = np.fft.rfftfreq(len(x), 1.0 / SR)
    power = np.abs(spec) ** 2
    total = float(np.sum(power)) + 1e-30
    high = float(np.sum(power[freq >= 5000.0]))
    return 10.0 * np.log10(high / total)


def _event(x, at, n=2400):
    a = max(0, at - n // 2)
    b = a + n
    if b > len(x):
        b = len(x)
        a = b - n
    return x[a:b]


def test_b4_phase_and_fader_steps(tmp_path):
    body = {
        "decay_lock": True, "decay_s": 1.8, "colour_mode": "BYPASS",
        "direct_wet": 1.0, "early_wet": 0.0, "fdn_wet": 0.0, "dry_gain": 0.0,
    }
    params, raw = _params(tmp_path, body)
    w = list(raw.get("desk_w") or [])
    phase_over = {"mic_phase_c": -1}
    if len(w) == 6:
        flipped = w[:]
        flipped[2] = -float(w[2])
        flipped[3] = -float(w[3])
        phase_over["desk_w"] = flipped
    at = _align(0.30)
    steady = _play(tmp_path, params, "sine", [1000, 0.50], tag="steady")
    phase = _play(tmp_path, params, "sine", [1000, 0.50],
                  [[0.30, phase_over]], tag="phase")
    louder = _play(tmp_path, params, "sine", [1000, 0.50],
                   [[0.30, {"direct_wet": 10 ** (6.0 / 20.0)}]], tag="fader")
    pre = steady[:at]
    assert np.array_equal(pre, phase[:at]), float(np.max(np.abs(pre - phase[:at])))
    assert np.array_equal(pre, louder[:at])
    report = {}
    for name, y in (("phase", phase), ("fader", louder)):
        ch = 0 if np.mean(y[:, 0] ** 2) >= np.mean(y[:, 1] ** 2) else 1
        pre_s = y[at - 2400:at, ch]
        post = y[at + 600:at + 600 + 2400, ch]
        ramp = y[at:at + 480, ch]
        window = _event(y[:, ch], at + 240)
        step_sine = max(_max_step(pre_s), _max_step(post))
        step_event = _max_step(ramp)
        hf = _hf_db(window)
        report[name] = {
            "step_event": step_event,
            "step_sine": step_sine,
            "ratio": step_event / step_sine if step_sine else None,
            "hf_db": hf,
        }
        assert step_sine > 0.0
        assert step_event <= 1.5 * step_sine, report
        assert hf <= -60.0, report
    (ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b4_steps.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")


def test_b4_fdn_unmute_keeps_tail(tmp_path):
    body = {
        "decay_lock": True, "decay_s": 1.8, "colour_mode": "BYPASS",
        "direct_wet": 0.0, "early_wet": 0.0, "fdn_wet": 1.0, "dry_gain": 0.0,
    }
    params, _raw = _params(tmp_path, body)
    # The hold run reloads the same wet, so a param reload is not the difference.
    hold = _play(tmp_path, params, "switch", [0.5, 3.0], [
        [0.50, {"fdn_wet": 1.0}],
        [2.00, {"fdn_wet": 1.0}],
    ], tag="hold")
    muted = _play(tmp_path, params, "switch", [0.5, 3.0], [
        [0.50, {"fdn_wet": 0.0}],
        [2.00, {"fdn_wet": 1.0}],
    ], tag="muted")
    a0, a1 = _align(2.03), _align(2.03) + int(0.12 * SR)
    def rms(x):
        return float(np.sqrt(np.mean(x ** 2)))
    rms_hold = rms(hold[a0:a1])
    rms_back = rms(muted[a0:a1])
    rel = 20.0 * np.log10((rms_back + 1e-20) / (rms_hold + 1e-20))
    mute_at = _align(1.20)
    rms_mute = rms(muted[mute_at:mute_at + int(0.10 * SR)])
    rms_live = rms(hold[mute_at:mute_at + int(0.10 * SR)])
    mute_db = 20.0 * np.log10((rms_mute + 1e-20) / (rms_live + 1e-20))
    report = {"unmute_delta_db": rel, "while_muted_db": mute_db,
              "rms_hold": rms_hold, "rms_back": rms_back}
    (ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b4_unmute.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    assert abs(rel) <= 1.0, report
    assert mute_db <= -40.0, report
