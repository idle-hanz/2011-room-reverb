"""Nuke makeup is min(amount, GR). The hard knee and CM0 GR stay."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
ROOT = SW.parent
WASM_RUN = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib" / "wasm_run.js"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import bloom_dsp as B  # noqa: E402

SR = 48000
CYCLE = 48
SETTLE = 3 * SR
PLAY_N = 2 * SR
TAIL = 2048
CM0_GR = {-30.0: 0.000, -18.0: 1.666, -6.0: 13.564}
CM0_T = -19.784137


def _spec():
    spec = B.design({
        "bloom_amount": 100,
        "bloom_preset": "nuke",
        "bloom_colour": False,
    }, SR)
    assert spec is not None and spec["preset"] == "nuke"
    return spec


def _tone(n: int, db: float, i0: int = 0) -> np.ndarray:
    amp = 10.0 ** (db / 20.0)
    i = np.arange(n, dtype=np.float64) + i0
    return amp * np.sin(2.0 * math.pi * 1000.0 * i / SR)


def _run(st: B.DetState, spec: dict, db: float, n: int, i0: int) -> np.ndarray:
    x = _tone(n, db, i0)
    gr = np.empty(n, dtype=np.float64)
    for i in range(n):
        gr[i] = B.step_gr(st, float(x[i]), spec)
    return gr


def _settled(gr: np.ndarray) -> float:
    n = (gr.shape[0] // CYCLE) * CYCLE
    series = gr[:n].reshape(-1, CYCLE).max(axis=1)
    last = np.sort(series[-100:])
    return float(last[len(last) // 2])


def _net_db(level_db: float, n: int = SR) -> float:
    spec = _spec()
    g, _gr = B._gain_env(_tone(n, level_db), spec)
    return 20.0 * math.log10(float(np.mean(g[-TAIL:])))


def test_nuke_knee_gr_and_net():
    spec = _spec()
    assert spec["W"] == 0.0
    assert spec["R"] == 1.0e6
    assert abs(spec["T"] - CM0_T) < 0.001
    for db, want in CM0_GR.items():
        got = _settled(_run(B.DetState(), spec, db, SETTLE, 0))
        assert abs(got - want) <= 0.2, (db, got)
        assert _net_db(db) <= 0.5, (db, _net_db(db))


def _play_db(level_db: float, tmp: Path) -> tuple[float, float]:
    tone = _tone(PLAY_N, level_db).astype(np.float32)
    pcm = tmp / f"in_{level_db:.0f}.f32"
    pcm.write_bytes(tone.tobytes())
    over = json.dumps({
        "direct_wet": 0,
        "early_wet": 0,
        "dry_gain": 0,
        "fdn_wet": 0.01,
        "colour_on": False,
    })

    def run(tag: str, body: dict) -> np.ndarray:
        body = dict(body)
        body["sample_rate"] = SR
        p = A.params_from_body(body)
        blob = A.live_fdn_params(p)
        pj = tmp / f"{tag}.json"
        pj.write_text(json.dumps(blob), encoding="utf-8")
        out = tmp / f"{tag}.f32"
        proc = subprocess.run(
            ["node", str(WASM_RUN), str(SW), str(pj), over, "pcm", str(pcm), str(out)],
            check=True,
            capture_output=True,
            text=True,
        )
        info = json.loads(proc.stdout.strip() or "{}")
        lim = info.get("limiter") or []
        assert not lim, lim
        raw = np.frombuffer(out.read_bytes(), dtype=np.float32)
        return np.array(raw[0::2], dtype=np.float64)

    off = run("off", {})
    on = run("on", {
        "bloom_amount": 100,
        "bloom_preset": "nuke",
        "bloom_colour": False,
    })
    off_t = off[-TAIL:]
    on_t = on[-TAIL:]
    off_rms = float(np.sqrt(np.mean(off_t * off_t)))
    on_rms = float(np.sqrt(np.mean(on_t * on_t)))
    assert off_rms > 1.0e-8, off_rms
    play = 20.0 * math.log10(on_rms / off_rms)
    render = _net_db(level_db, n=PLAY_N)
    return render, play


def test_play_matches_render_on_the_same_tone():
    assert WASM_RUN.is_file()
    with tempfile.TemporaryDirectory(prefix="cm5b_") as folder:
        tmp = Path(folder)
        for level in (-18.0, -6.0):
            render, play = _play_db(level, tmp)
            assert abs(render - play) <= 0.1, (level, render, play)
