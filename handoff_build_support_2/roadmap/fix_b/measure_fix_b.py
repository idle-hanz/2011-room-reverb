"""FIX-B numbers. Before is the pre-change render_pipeline from the zip."""
from __future__ import annotations

import importlib.util
import inspect
import json
import math
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
ZIP = ROOT / "software_backup_2026-10-10_preFIXB.zip"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "fix_b"
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


def load_old():
    zf = zipfile.ZipFile(ZIP)
    name = next(n for n in zf.namelist() if n.replace("\\", "/").endswith("software/render_pipeline.py"))
    tmp = Path(tempfile.gettempdir()) / "render_pipeline_preFIXB.py"
    tmp.write_bytes(zf.read(name))
    spec = importlib.util.spec_from_file_location("render_pipeline_preFIXB", tmp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def play(mod, body):
    p = A.params_from_body(body)
    live = mod.live_fdn_params(p, 48000)
    return {
        "makeup": float(live["makeup"]),
        "makeup_db": round(db(live["makeup"]), 4),
        "g_decay": float(live["g_decay"]),
        "direct_index": int(live["direct_index"]),
    }


def _kw(mod, p, sr, dry):
    sig = inspect.signature(mod.render)
    kw = {}
    for name in sig.parameters:
        if name in ("dry", "sr"):
            continue
        if name == "desk":
            kw["desk"] = p
        elif name in p:
            kw[name] = p[name]
    return kw


def render_noise(mod, body, seed=1):
    p = A.params_from_body(body)
    sr = 48000
    rng = np.random.default_rng(seed)
    n = int(0.20 * sr)
    dry = rng.standard_normal(n).astype(np.float64)
    dry *= 0.5 / max(float(np.max(np.abs(dry))), 1e-12)
    L, R, info = mod.render(dry, sr, **_kw(mod, p, sr, dry))
    mix = 0.5 * (L * L + R * R)
    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R))))
    return {
        "peak_db": round(db(peak), 4),
        "rms_db": round(db(math.sqrt(max(float(np.mean(mix)), 0.0))), 4),
        "limiter_db": round(float(info.get("limiter_db") or 0.0), 4),
        "limiter_samples": int(info.get("limiter_samples") or 0),
        "peak_before_db": round(db(float(info.get("peak_before_norm") or 0.0)), 4),
    }


def render_impulse_maxabs(old, new, body):
    p = A.params_from_body(body)
    sr = 48000
    dry = np.zeros(64, dtype=np.float64)
    dry[0] = 1.0
    Lo, Ro, _ = old.render(dry, sr, **_kw(old, p, sr, dry))
    Ln, Rn, _ = new.render(dry, sr, **_kw(new, p, sr, dry))
    n = min(len(Lo), len(Ln), len(Ro), len(Rn))
    d = max(float(np.max(np.abs(Lo[:n] - Ln[:n]))), float(np.max(np.abs(Ro[:n] - Rn[:n]))))
    return d


def solo(dist):
    return ortf(
        W=24.0, H=6.0, L=24.0,
        sx=12.0, sy=1.5, sz=16.0,
        mcx=12.0, mcz=8.0, my=1.5,
        third_mic="room",
        mic_gain_l=0.0, mic_gain_c=1.0, mic_gain_r=0.0,
        mic_x_c=12.0, mic_y_c=1.5, mic_z_c=16.0 - dist,
        yaw_c_deg=0.0,
    )


def source_move(dist):
    return ortf(
        W=24.0, H=6.0, L=32.0,
        sx=12.0, sy=1.5, sz=8.0 + dist,
        mcx=12.0, mcz=8.0, my=1.5,
        third_mic="off", mic_gain_c=0.0,
    )


def main():
    old = load_old()
    rows = {"solo": [], "places": [], "shots": [], "source": [], "agree": []}

    print("--- solo C, new render, old and new makeup ---", flush=True)
    prev = None
    for dist in (0.5, 1.0, 2.0, 4.0, 8.0):
        body = solo(dist)
        before = play(old, body)
        after = play(rp, body)
        ren = render_noise(rp, body)
        step = None if prev is None else round(ren["peak_db"] - prev, 4)
        prev = ren["peak_db"]
        row = {"dist_m": dist, "before": before, "after": after, "render": ren, "peak_step_db": step}
        rows["solo"].append(row)
        print(dist, "mk", before["makeup_db"], "->", after["makeup_db"], "g", round(after["g_decay"], 6),
              "peak", ren["peak_db"], "step", step, "rms", ren["rms_db"], "lim", ren["limiter_db"], flush=True)

    print("--- stand places, makeup and impulse max-abs ---", flush=True)
    places = {
        "studio": ortf(W=5.6, H=2.8, L=7.2, sx=2.8, sz=4.6, sy=1.2, my=1.2, mcx=2.8, mcz=1.55),
        "club": ortf(W=14, H=5.2, L=22, sx=7, sz=14.5, sy=1.6, my=1.6, mcx=7, mcz=3.4, space=0.25, humidity=0.4),
        "hall": ortf(
            W=57, H=34.241, L=97, sx=24.925, sz=72.083, sy=1.88, my=1.9, mcz=24.25,
            mcx=28.5, space=0.25, reaktor_parity=True, decay_lock=False, decay_s=1.8,
            humidity=0.5, air_lp=0.25, diffusion_master=-0.5,
            direct_wet=1.0, fdn_wet=1.0, early_wet=0.0,
            third_mic="off", mic_gain_c=0.0,
        ),
        "boot": ortf(),
    }
    for name, body in places.items():
        b, a = play(old, body), play(rp, body)
        mx = render_impulse_maxabs(old, rp, body)
        rows["places"].append({"name": name, "before": b, "after": a, "impulse_max_abs": mx})
        print(name, "mk", b["makeup_db"], a["makeup_db"], "maxabs", mx, flush=True)

    print("--- screenshot far / on source ---", flush=True)
    shots = {
        "far": ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=5.7, mic_y_c=1.5, mic_z_c=0.3, yaw_c_deg=180.0),
        "on_source": ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=2.6, mic_y_c=1.2, mic_z_c=4.75, yaw_c_deg=0.0),
        "above_0.30": ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=2.6, mic_y_c=1.5, mic_z_c=4.75, yaw_c_deg=0.0),
    }
    for name, body in shots.items():
        bmk, amk = play(old, body), play(rp, body)
        br, ar = render_noise(old, body), render_noise(rp, body)
        row = {"name": name, "before_mk": bmk, "after_mk": amk, "before_render": br, "after_render": ar}
        rows["shots"].append(row)
        print(name, "mk", bmk["makeup_db"], "->", amk["makeup_db"],
              "peak", br["peak_db"], "->", ar["peak_db"],
              "rms", br["rms_db"], "->", ar["rms_db"],
              "lim", br["limiter_db"], ar["limiter_db"], flush=True)

    print("--- source move, stand mics only ---", flush=True)
    for dist in (0.5, 1.0, 2.0, 4.0, 8.0):
        body = source_move(dist)
        amk = play(rp, body)
        ren = render_noise(rp, body)
        row = {"dist_m": dist, "after": amk, "render": ren}
        rows["source"].append(row)
        print("src", dist, "mk", amk["makeup_db"], "peak", ren["peak_db"], "rms", ren["rms_db"], "lim", ren["limiter_db"], flush=True)

    print("--- play vs render makeup ---", flush=True)
    seen = []
    real = rp.makeup_at_stand

    def wrap(*a, **k):
        m = real(*a, **k)
        seen.append(float(m))
        return m

    rp.makeup_at_stand = wrap
    agree_bodies = {
        "boot": ortf(),
        "solo_0.5": solo(0.5),
        "solo_8": solo(8.0),
        "far": shots["far"],
        "on_source": shots["on_source"],
        "two": ortf(two_sources=True, sx_b=3.4, sz_b=4.75),
    }
    for name, body in agree_bodies.items():
        seen.clear()
        p = A.params_from_body(body)
        live_mk = float(rp.live_fdn_params(p, 48000)["makeup"])
        play_calls = list(seen)
        seen.clear()
        sr = 48000
        dry = np.zeros(32, dtype=np.float64)
        dry[0] = 1.0
        kw = _kw(rp, p, sr, dry)
        if body.get("two_sources"):
            kw["dry_l"] = dry
            kw["dry_r"] = dry * 0.5
        rp.render(dry, sr, **kw)
        render_calls = list(seen)
        row = {"name": name, "live": live_mk, "play_calls": play_calls, "render_calls": render_calls,
               "match": play_calls == render_calls and play_calls and play_calls[0] == live_mk}
        rows["agree"].append(row)
        print(name, row["match"], live_mk, render_calls, flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "measure_fix_b.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print("wrote", OUT / "measure_fix_b.json", flush=True)


if __name__ == "__main__":
    main()
