"""D-SRC-DIST-LEVEL source-move table. Stand mics, 24 x 6 x 32 m.

Makeup is the stand-offset source. The live source still drives the injects.
Writes measure_srcdist.json next to this file.
"""
from __future__ import annotations

import inspect
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import render_pipeline as rp  # noqa: E402


def db(x: float) -> float:
    a = abs(float(x))
    if a < 1e-12:
        return -300.0
    return 20.0 * math.log10(a)


def ortf(**over) -> dict:
    toe = 55.0 * math.pi / 180.0
    diverg = 2.0 * (-abs(toe) + 0.25)
    body = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "sx": 2.6, "sy": 1.2, "sz": 4.75,
        "mcx": 3.0, "mcz": 1.5, "my": 1.5,
        "space": 0.17, "toe_half_deg": 55.0, "diverg": diverg,
        "car_omni": 1.0,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "family_l": "cardioid", "family_c": "cardioid", "family_r": "cardioid",
        "polar_l": 0.5, "polar_c": 0.5, "polar_r": 0.5,
        "yaw_l_deg": -55.0, "yaw_c_deg": 0.0, "yaw_r_deg": 55.0,
        "mic_setup": "ortf", "third_mic": "off",
        "mic_gain_l": 1.0, "mic_gain_c": 0.0, "mic_gain_r": 1.0,
        "mic_pan_l": -1.0, "mic_pan_c": 0.0, "mic_pan_r": 1.0,
        "fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0, "dry_gain": 0.0,
        "fdn_g": 1.0, "decay_lock": True, "decay_s": 1.8,
        "ir_length_ms": 1500.0, "humidity": 0.35, "air_lp": 0.0, "air_shelf": 1.0,
        "air_iso": True, "smooth": True, "colour_mode": "BYPASS",
        "source_radiation": "omni", "hadamard_n": 32, "sample_rate": 48000,
    }
    body.update(over)
    return body


def source_move(dist: float) -> dict:
    return ortf(
        W=24.0, H=6.0, L=32.0,
        sx=12.0, sy=1.5, sz=8.0 + dist,
        mcx=12.0, mcz=8.0, my=1.5,
        third_mic="off", mic_gain_c=0.0,
    )


def play(body):
    p = A.params_from_body(body)
    live = rp.live_fdn_params(p, 48000)
    return {
        "makeup": float(live["makeup"]),
        "makeup_db": round(db(live["makeup"]), 4),
        "g_decay": float(live["g_decay"]) if "g_decay" in live else None,
        "g": float(live["g"]),
    }


def _kw(p):
    sig = inspect.signature(rp.render)
    kw = {}
    for name in sig.parameters:
        if name in ("dry", "sr"):
            continue
        if name == "desk":
            kw["desk"] = p
        elif name in p:
            kw[name] = p[name]
    return kw


def render_noise(body, seed=1):
    p = A.params_from_body(body)
    sr = 48000
    rng = np.random.default_rng(seed)
    n = int(0.20 * sr)
    dry = rng.standard_normal(n).astype(np.float64)
    dry *= 0.5 / max(float(np.max(np.abs(dry))), 1e-12)
    L, R, info = rp.render(dry, sr, **_kw(p))
    mix = 0.5 * (L * L + R * R)
    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R))))
    return {
        "peak_db": round(db(peak), 4),
        "rms_db": round(db(math.sqrt(max(float(np.mean(mix)), 0.0))), 4),
        "limiter_db": round(float(info.get("limiter_db") or 0.0), 4),
        "limiter_samples": int(info.get("limiter_samples") or 0),
        "peak_before_db": round(db(float(info.get("peak_before_norm") or 0.0)), 4),
    }


def main():
    rows = []
    prev_peak = None
    prev_before = None
    for dist in (0.3, 0.5, 1.0, 2.0, 4.0, 8.0):
        body = source_move(dist)
        amk = play(body)
        ren = render_noise(body)
        step = None if prev_peak is None else round(ren["peak_db"] - prev_peak, 4)
        step_before = None if prev_before is None else round(ren["peak_before_db"] - prev_before, 4)
        prev_peak = ren["peak_db"]
        prev_before = ren["peak_before_db"]
        row = {
            "dist_m": dist,
            "makeup": amk,
            "render": ren,
            "peak_step_db": step,
            "peak_before_step_db": step_before,
        }
        rows.append(row)
        print(
            "src", dist,
            "mk", amk["makeup_db"],
            "peak", ren["peak_db"],
            "before", ren["peak_before_db"],
            "step", step,
            "step_before", step_before,
            "lim", ren["limiter_db"], ren["limiter_samples"],
            flush=True,
        )
    # Boot must match the pre-change empty-body scalar.
    boot = play({})
    print("empty makeup", boot["makeup"], boot["makeup_db"], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "reason": "D-SRC-DIST-LEVEL",
        "room_m": [24.0, 6.0, 32.0],
        "stand_m": [12.0, 1.5, 8.0],
        "rows": rows,
        "empty_makeup": boot,
    }
    (OUT / "measure_srcdist.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("wrote", OUT / "measure_srcdist.json", flush=True)


if __name__ == "__main__":
    main()
