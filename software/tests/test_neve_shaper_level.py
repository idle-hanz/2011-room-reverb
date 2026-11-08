"""Neve shaper level. H1 sits on kernel G, then the −18 dB capture trim."""
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

# klin_neve at 1 kHz after the sample-64 delay roll. Not vc.
G_1K = 233.316274689952195
TRIM = 10.0 ** (-18.0 / 20.0)
# Model THD at Drive 0, −18 dBFS, harmonics 2–15, settled half, exact-bin rfft.
DRIVE0_THD_M18 = 0.8677
SR = 48000.0
PLAY_N = 2 * int(SR)


def _h1_mag(row) -> float:
    w = 2.0 * math.pi * 1000.0 / SR
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    b0, b1, b2, a1, a2 = row[15:20]
    return abs((b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2))


def _thd_h2_h15(y: np.ndarray) -> float:
    """Settled half, exact-bin rfft, harmonics 2–15, no window."""
    z = np.asarray(y[len(y) // 2 :], dtype=np.float64)
    per = int(SR // 1000.0)
    n = (z.size // per) * per
    z = z[:n]
    spec = np.fft.rfft(z)
    scale = 2.0 / n

    def amp(k: int) -> float:
        return abs(spec[k * 1000 * n // int(SR)]) * scale

    fundamental = amp(1)
    harm = sum(amp(k) ** 2 for k in range(2, 16))
    return 100.0 * math.sqrt(harm) / fundamental


def _fund_db(y: np.ndarray, ref_amp: float) -> float:
    z = np.asarray(y, dtype=np.float64)
    per = int(SR // 1000.0)
    use = per * 100
    z = z[-use:]
    spec = np.fft.rfft(z)
    amp = abs(spec[1000 * use // int(SR)]) * (2.0 / use)
    return 20.0 * math.log10(amp / ref_amp)


def test_neve_drive0_shaper_level_and_unity():
    spec = {"pre": "neve1073", "sr": SR, "pre_drive_db": 0.0}
    row = B.pack_pre(spec)
    play = B.pack_pre(spec, play=True)
    expect = G_1K * TRIM
    assert abs(_h1_mag(row) - expect) < 1e-6
    assert abs(_h1_mag(play) - expect) < 1e-6

    n = int(SR)
    t = np.arange(n, dtype=np.float64) / SR
    quiet = 1.0e-6 * np.sin(2.0 * math.pi * 1000.0 * t)
    y = B._pre_bus(quiet, row)
    tail = slice(n // 2, None)
    gain = float(np.sqrt(np.mean(y[tail] ** 2)) / np.sqrt(np.mean(quiet[tail] ** 2)))
    db = 20.0 * math.log10(gain)
    assert abs(db) < 0.01
    y_play = B._pre_bus(quiet, play)
    gain_p = float(np.sqrt(np.mean(y_play[tail] ** 2)) / np.sqrt(np.mean(quiet[tail] ** 2)))
    assert abs(20.0 * math.log10(gain_p)) < 0.01

    hot = (10.0 ** (-18.0 / 20.0)) * np.sin(2.0 * math.pi * 1000.0 * t)
    thd = _thd_h2_h15(B._pre_bus(hot, row))
    assert abs(thd / DRIVE0_THD_M18 - 1.0) < 0.02

    render_db = _fund_db(B._pre_bus(hot, row), 10.0 ** (-18.0 / 20.0))
    play_db = _fund_db(B._pre_bus(hot, play), 10.0 ** (-18.0 / 20.0))
    assert abs(render_db - play_db) <= 0.1, (render_db, play_db)


def test_play_matches_render_on_the_same_tone():
    """Play pack versus render pack on one tone, then the wasm at a linear level.

    The FDN bus is hotter than the sine, and Play's oversample is 1 against
    render's 8, so a −18 dBFS sine through the room is not the shaper's −18
    point. The same-tone check is _pre_bus. The wasm check is the 0 dB
    small-signal gain, which does not depend on that bus level.
    """
    assert WASM_RUN.is_file()
    body = {
        "pre_colour": "neve1073",
        "pre_drive_db": 0.0,
        "bloom_amount": 0,
        "bloom_colour": False,
        "sample_rate": int(SR),
    }
    blob = A.live_fdn_params(A.params_from_body(body))
    packed = blob["pre_colour"]
    assert abs(_h1_mag(packed) - G_1K * TRIM) < 1e-6

    ref = 10.0 ** (-30.0 / 20.0)
    n = PLAY_N
    tone = (ref * np.sin(2.0 * math.pi * 1000.0 * np.arange(n) / SR)).astype(np.float32)
    row = B.pack_pre({"pre": "neve1073", "sr": SR, "pre_drive_db": 0.0})
    render_db = _fund_db(B._pre_bus(tone.astype(np.float64), row), ref)
    over = json.dumps({
        "direct_wet": 0,
        "early_wet": 0,
        "dry_gain": 0,
        "fdn_wet": 0.01,
        "colour_on": False,
    })

    def run(tag: str, on: bool, tmp: Path) -> np.ndarray:
        use = body if on else {"sample_rate": int(SR)}
        p = A.params_from_body(use)
        pj = tmp / f"{tag}.json"
        pj.write_text(json.dumps(A.live_fdn_params(p)), encoding="utf-8")
        pcm = tmp / f"{tag}.f32"
        pcm.write_bytes(tone.tobytes())
        out = tmp / f"{tag}_out.f32"
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

    with tempfile.TemporaryDirectory(prefix="cm5d_") as folder:
        tmp = Path(folder)
        off = run("off", False, tmp)
        on = run("on", True, tmp)
    play_db = _fund_db(on, ref) - _fund_db(off, ref)
    assert abs(render_db - play_db) <= 0.1, (render_db, play_db)
