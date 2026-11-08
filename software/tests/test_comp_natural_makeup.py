"""Natural makeup is min(amount, GR). Glue still boosts. Room Crush still ducks at -18."""
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
PLAY_N = 24576  # 0.512 s, a whole number of 128-sample blocks
TAIL = 2048


def _tone(n: int, db: float) -> np.ndarray:
    amp = 10.0 ** (db / 20.0)
    i = np.arange(n, dtype=np.float64)
    return amp * np.sin(2.0 * math.pi * 1000.0 * i / SR)


def _settled_db(level_db: float, preset: str, n: int = SR) -> float:
    spec = B.design({
        "bloom_amount": 100,
        "bloom_preset": preset,
        "bloom_colour": False,
    }, SR)
    assert spec is not None and spec["preset"] == preset
    g, _gr = B._gain_env(_tone(n, level_db), spec)
    tail = g[-TAIL:]
    return 20.0 * math.log10(float(np.mean(tail)))


def test_natural_net_gain_at_three_levels():
    nets = {level: _settled_db(level, "natural") for level in (-30.0, -18.0, -6.0)}
    for level, db in nets.items():
        assert db <= 0.5, (level, db)
    assert abs(nets[-18.0]) <= 0.5, nets[-18.0]


def test_other_models_are_not_capped():
    glue = _settled_db(-18.0, "glue")
    crush = _settled_db(-18.0, "room_crush", n=SR // 2)
    assert glue > 4.0, glue
    assert crush < -4.0, crush


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
        "bloom_preset": "natural",
        "bloom_colour": False,
    })
    off_t = off[-TAIL:]
    on_t = on[-TAIL:]
    off_rms = float(np.sqrt(np.mean(off_t * off_t)))
    on_rms = float(np.sqrt(np.mean(on_t * on_t)))
    assert off_rms > 1.0e-8, off_rms
    play = 20.0 * math.log10(on_rms / off_rms)
    render = _settled_db(level_db, "natural", n=PLAY_N)
    return render, play


def test_play_matches_render_on_the_same_tone():
    assert WASM_RUN.is_file()
    with tempfile.TemporaryDirectory(prefix="cm1b_") as folder:
        tmp = Path(folder)
        for level in (-18.0, -6.0):
            render, play = _play_db(level, tmp)
            assert abs(render - play) <= 0.1, (level, render, play)
