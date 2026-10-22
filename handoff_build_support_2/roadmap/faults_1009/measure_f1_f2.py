"""Read-only F1/F2 measurements. Does not write under software\\."""
from __future__ import annotations

import inspect
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "faults_1009"
sys.path.insert(0, str(SW))
sys.path.insert(0, str(SW / "engine"))

from app_server import params_from_body  # noqa: E402
from early_field import centre_position, geometric_level, mic_positions  # noqa: E402
from image_geometry import build_images_payload  # noqa: E402
from render_pipeline import live_fdn_params, render  # noqa: E402


def db(x: float) -> float:
    a = abs(float(x))
    if a < 1e-12:
        return -300.0
    return 20.0 * math.log10(a)


def rms(a: np.ndarray) -> float:
    if a.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(a))))


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
        "mic_setup": "ortf",
        "third_mic": "off",
        "mic_gain_l": 1.0, "mic_gain_c": 0.0, "mic_gain_r": 1.0,
        "mic_pan_l": -1.0, "mic_pan_c": 0.0, "mic_pan_r": 1.0,
        "fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0, "dry_gain": 0.0,
        "fdn_g": 1.0, "decay_lock": True, "decay_s": 1.8,
        "ir_length_ms": 1500.0, "humidity": 0.35, "air_lp": 0.0, "air_shelf": 1.0,
        "air_iso": True, "smooth": True, "colour_mode": "BYPASS",
        "source_radiation": "omni", "hadamard_n": 32,
        "sample_rate": 48000,
    }
    body.update(over)
    return body


def coeffs(label: str, body: dict) -> dict:
    p = params_from_body(body)
    live = live_fdn_params(p, 48000)
    di = int(live["direct_index"])
    inj = {ch: live["buses"][ch]["inject"] for ch in ("l", "c", "r")}
    peak_ch = {ch: max(abs(float(v)) for v in inj[ch]) for ch in ("l", "c", "r")}
    # Mixer fold of the loudest sample is what makeup uses. Report the direct-line fold too.
    gl = float(p["mic_gain_l"])
    gc = float(p["mic_gain_c"])
    gr = float(p["mic_gain_r"])
    # Pan law at the boot desk: L hard left, C centre, R hard right.
    # heard fold of one line: L*1 + C*0.5, R*1 + C*0.5 when gains are 1 and C is centre.
    def fold(i):
        L = gl * float(inj["l"][i]) + 0.5 * gc * float(inj["c"][i])
        R = gr * float(inj["r"][i]) + 0.5 * gc * float(inj["c"][i])
        return max(abs(L), abs(R))

    peak_fold = max(fold(i) for i in range(len(inj["l"])))
    direct_fold = fold(di)
    src = live["source"]
    # Placed C, else the stand centre is not in the live dict. Use the posted spot.
    if body.get("mic_x_c") not in (None, ""):
        mic = (float(body["mic_x_c"]), float(body["mic_y_c"]), float(body["mic_z_c"]))
    else:
        mic = (float(p["mcx"]), float(p["my"]), float(p["mcz"]))
    dist = math.dist((float(src["x"]), float(src["y"]), float(src["z"])), mic)
    row = {
        "label": label,
        "dist_c_m": round(dist, 4),
        "mic_gain_c": gc,
        "mic_gain_l": gl,
        "play_makeup": live["makeup"],
        "play_makeup_db": round(db(live["makeup"]), 2),
        "direct_makeup_computed_not_applied": live["direct_makeup"],
        "g_decay": live["g_decay"],
        "g_loop": live["g"],
        "fdn_wet_after_trim": live["fdn_wet"],
        "loop_trim_db": live["loop_trim_db"],
        "direct_wet": live["direct_wet"],
        "early_wet": live["early_wet"],
        "inject_peak": {k: peak_ch[k] for k in peak_ch},
        "inject_peak_db": {k: round(db(peak_ch[k]), 2) for k in peak_ch},
        "fold_peak": peak_fold,
        "fold_peak_db": round(db(peak_fold), 2),
        "direct_line_fold": direct_fold,
        "direct_line_fold_db": round(db(direct_fold), 2),
        "direct_out_db": round(db(0.55 * direct_fold), 2),
        "fdn_first_db": round(db(live["makeup"] * live["fdn_wet"] * direct_fold), 2),
        "geo_1_r2": geometric_level(dist),
        "geo_db": round(db(geometric_level(dist)), 2),
        "source": src,
        "mic_used": {"x": mic[0], "y": mic[1], "z": mic[2]},
    }
    print(
        f"{label:28} dist {dist:7.3f}  makeup {row['play_makeup_db']:7.2f} dB"
        f"  fold {row['fold_peak_db']:7.2f} dB  geo {row['geo_db']:7.2f} dB"
        f"  fdn1 {row['fdn_first_db']:7.2f} dB  direct {row['direct_out_db']:7.2f} dB"
        f"  gc {gc:.2f}",
        flush=True,
    )
    return row


def render_level(label: str, body: dict) -> dict:
    p = params_from_body(body)
    sr = 48000
    rng = np.random.default_rng(1)
    n = int(0.20 * sr)
    dry = rng.standard_normal(n).astype(np.float64)
    dry *= 0.5 / max(float(np.max(np.abs(dry))), 1e-12)
    sig = inspect.signature(render)
    kw = {}
    for name, param in sig.parameters.items():
        if name in ("dry", "sr"):
            continue
        if name == "desk":
            kw["desk"] = p
        elif name in p:
            kw[name] = p[name]
    t0 = time.perf_counter()
    L, R, info = render(dry, sr, **kw)
    dt = time.perf_counter() - t0
    mix = 0.5 * (L * L + R * R)
    tail = int(0.08 * sr)
    row = {
        "label": label,
        "seconds": round(dt, 2),
        "peak": float(max(np.max(np.abs(L)), np.max(np.abs(R)))),
        "peak_before": float(info.get("peak_before_norm") or 0.0),
        "limiter_db": float(info.get("limiter_db") or 0.0),
        "limiter_samples": int(info.get("limiter_samples") or 0),
        "rms_db": round(db(math.sqrt(max(float(np.mean(mix)), 0.0))), 2),
        "tail_rms_db": round(db(rms(np.sqrt(np.maximum(mix[tail:], 0.0)))), 2),
        "onset_rms_db": round(db(rms(np.sqrt(np.maximum(mix[:tail], 0.0)))), 2),
        "fdn_ms": info.get("fdn_ms"),
    }
    print(
        f"RENDER {label:28} {dt:6.1f}s  peak {db(row['peak']):7.2f} dB"
        f"  before {db(row['peak_before']):7.2f} dB  lim {row['limiter_db']:.2f} dB"
        f" ({row['limiter_samples']})  rms {row['rms_db']:.2f}  tail {row['tail_rms_db']:.2f}",
        flush=True,
    )
    return row


def place_c(dist: float, **over) -> dict:
    """Solo C, omni-aim cardioid, source fixed, mic due -Z at `dist` metres."""
    # Room big enough for 8 m. Source at (12, 1.5, 16). Mic at z = 16 - dist.
    z = 16.0 - dist
    body = ortf(
        W=24.0, H=6.0, L=24.0,
        sx=12.0, sy=1.5, sz=16.0,
        mcx=12.0, mcz=8.0, my=1.5,
        third_mic="room",
        mic_gain_l=0.0, mic_gain_c=1.0, mic_gain_r=0.0,
        mic_x_c=12.0, mic_y_c=1.5, mic_z_c=z,
        yaw_c_deg=0.0,
    )
    body.update(over)
    return body


def f2_positions() -> dict:
    """Page posts room_* on the raw state. Audio posts mic_* only from heardMix."""
    far = {
        "place_c": "room", "third_mic": "room",
        "room_c_x": 5.5, "room_c_y": 2.5, "room_c_z": 0.4, "room_c_yaw": 0.0,
    }
    page = ortf(**far)  # what fetchImages / refreshPolar send: no mic_x_c
    heard = ortf(
        **far,
        mic_x_c=5.5, mic_y_c=2.5, mic_z_c=0.4, yaw_c_deg=0.0,
        mic_gain_c=1.0,
    )
    pp = params_from_body(page)
    hp = params_from_body(heard)
    images = build_images_payload(
        W=pp["W"], H=pp["H"], L=pp["L"],
        mz=pp["mz"], my=pp["my"], space=pp["space"],
        diverg=pp["diverg"], sox=pp["sox"], soz=pp["soz"],
        mcx=pp["mcx"], toe_half_deg=pp.get("toe_half_deg"),
        mics=["L", "C", "R"], hadamard_n=32,
        sy=pp.get("sy"), sx=pp["sx"], sz=pp["sz"], mcz=pp["mcz"],
    )
    # Audio path: place the stand the way live_fdn_params does.
    from render_pipeline import MicStand, _place_stand, direct_field_from_params
    prep = direct_field_from_params(hp)
    stand = MicStand.from_prepare(
        prep, car_omni=hp["car_omni"],
        pattern_l=hp.get("pattern_l"), pattern_c=hp.get("pattern_c"), pattern_r=hp.get("pattern_r"),
        yaw_l_deg=hp.get("yaw_l_deg"), yaw_c_deg=hp.get("yaw_c_deg"), yaw_r_deg=hp.get("yaw_r_deg"),
        centre_dz=hp.get("centre_dz") or 0.0,
    )
    _place_stand(stand, hp)
    c_audio = centre_position(stand)
    c_images = images["mics"]["C"]
    if isinstance(c_images, dict):
        c_list = [float(c_images["x"]), float(c_images["y"]), float(c_images["z"])]
    else:
        c_list = [float(c_images[0]), float(c_images[1]), float(c_images[2])]
    lr = []
    for pos in mic_positions(stand)[:2]:
        if isinstance(pos, dict):
            lr.append([float(pos["x"]), float(pos["y"]), float(pos["z"])])
        else:
            lr.append([float(pos[0]), float(pos[1]), float(pos[2])])
    return {
        "page_body_has_mic_x_c": "mic_x_c" in page,
        "page_room_c": [5.5, 2.5, 0.4],
        "images_mics_C": c_list,
        "images_uses_stand": abs(c_list[0] - 3.0) < 0.05 and abs(c_list[2] - 1.5) < 0.05,
        "audio_centre": [float(c_audio[0]), float(c_audio[1]), float(c_audio[2])],
        "audio_matches_room_spot": (
            abs(float(c_audio[0]) - 5.5) < 1e-6
            and abs(float(c_audio[2]) - 0.4) < 1e-6
            and abs(float(c_audio[1]) - 2.5) < 1e-6
        ),
        "stand_lr": lr,
    }


def main() -> None:
    rows = []
    print("--- F1 coefficients: solo C, cardioid aimed +Z, Direct/Early down ---", flush=True)
    for d in (0.5, 1.0, 2.0, 4.0, 6.0, 8.0):
        rows.append(coeffs(f"soloC {d:.1f}m fdn", place_c(d)))
        rows.append(coeffs(f"soloC {d:.1f}m allup", place_c(d, direct_wet=1.0, early_wet=1.0)))

    print("--- F1 screenshot room (6x3x8, L/R on stand, C room) ---", flush=True)
    # Far corner, same idea as Screenshot 554. Near = on the source, Screenshot 555.
    rows.append(coeffs("shot far C", ortf(
        third_mic="room", mic_gain_c=1.0,
        mic_x_c=5.7, mic_y_c=1.5, mic_z_c=0.3, yaw_c_deg=180.0,
    )))
    rows.append(coeffs("shot near C", ortf(
        third_mic="room", mic_gain_c=1.0,
        mic_x_c=2.6, mic_y_c=1.2, mic_z_c=4.75, yaw_c_deg=0.0,
    )))

    print("--- F1 presets, boot faders (FDN up, Direct/Early down) except Hall ---", flush=True)
    rows.append(coeffs("studio stand", ortf(
        W=5.6, H=2.8, L=7.2, sx=2.8, sz=4.6, sy=1.2, my=1.2, mcx=2.8, mcz=1.55,
    )))
    rows.append(coeffs("club stand", ortf(
        W=14, H=5.2, L=22, sx=7, sz=14.5, sy=1.6, my=1.6, mcx=7, mcz=3.4, space=0.25,
        humidity=0.4,
    )))
    # Hall button: parity, lock off, direct fader up, early fader down, mcx = W/2.
    rows.append(coeffs("hall button", ortf(
        W=57, H=34.241, L=97, sx=24.925, sz=72.083, sy=1.88, my=1.9, mcz=24.25,
        mcx=28.5, space=0.25, reaktor_parity=True, decay_lock=False, decay_s=1.8,
        humidity=0.5, air_lp=0.25, diffusion_master=-0.5,
        direct_wet=1.0, fdn_wet=1.0, early_wet=0.0,
        third_mic="off", mic_gain_c=0.0,
    )))

    print("--- F3 bodies (no render yet) ---", flush=True)
    rows.append(coeffs("boot ORTF C off", ortf()))
    rows.append(coeffs("mix Room C", ortf(
        third_mic="off", mic_gain_c=0.0,
        mic_x_c=3.0, mic_y_c=1.5, mic_z_c=1.5, yaw_c_deg=0.0,
    )))
    rows.append(coeffs("mic Room C", ortf(
        third_mic="room", mic_gain_c=1.0,
        mic_x_c=3.0, mic_y_c=1.5, mic_z_c=1.5, yaw_c_deg=0.0,
    )))
    rows.append(coeffs("mix Room L", ortf(
        mic_x_l=3.0 - 0.085, mic_y_l=1.5, mic_z_l=1.5, yaw_l_deg=-55.0,
    )))

    print("--- F2 display vs audio position ---", flush=True)
    f2 = f2_positions()
    print(json.dumps(f2, indent=2), flush=True)

    OUT.joinpath("f1_coeffs.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    OUT.joinpath("f2_positions.json").write_text(json.dumps(f2, indent=2), encoding="utf-8")

    print("--- renders (0.2 s noise, peak 0.5, BYPASS colour) ---", flush=True)
    renders = []
    jobs = [
        ("soloC 0.5 fdn", place_c(0.5)),
        ("soloC 2.0 fdn", place_c(2.0)),
        ("soloC 8.0 fdn", place_c(8.0)),
        ("soloC 0.5 allup", place_c(0.5, direct_wet=1.0, early_wet=1.0)),
        ("soloC 8.0 allup", place_c(8.0, direct_wet=1.0, early_wet=1.0)),
        ("soloC 0.5 direct", place_c(0.5, fdn_wet=0.0, direct_wet=1.0, early_wet=0.0)),
        ("soloC 8.0 direct", place_c(8.0, fdn_wet=0.0, direct_wet=1.0, early_wet=0.0)),
        ("soloC 0.5 early", place_c(0.5, fdn_wet=0.0, direct_wet=0.0, early_wet=1.0)),
        ("soloC 8.0 early", place_c(8.0, fdn_wet=0.0, direct_wet=0.0, early_wet=1.0)),
        ("shot far C", ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=5.7, mic_y_c=1.5, mic_z_c=0.3, yaw_c_deg=180.0)),
        ("shot near C", ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=2.6, mic_y_c=1.2, mic_z_c=4.75, yaw_c_deg=0.0)),
        ("hall button", ortf(
            W=57, H=34.241, L=97, sx=24.925, sz=72.083, sy=1.88, my=1.9, mcz=24.25,
            mcx=28.5, space=0.25, reaktor_parity=True, decay_lock=False,
            humidity=0.5, air_lp=0.25, diffusion_master=-0.5,
            direct_wet=1.0, fdn_wet=1.0, early_wet=0.0, third_mic="off", mic_gain_c=0.0,
        )),
        ("boot ORTF", ortf()),
        ("mix Room C", ortf(third_mic="off", mic_gain_c=0.0, mic_x_c=3.0, mic_y_c=1.5, mic_z_c=1.5)),
        ("mic Room C", ortf(third_mic="room", mic_gain_c=1.0, mic_x_c=3.0, mic_y_c=1.5, mic_z_c=1.5, yaw_c_deg=0.0)),
    ]
    for label, body in jobs:
        try:
            renders.append(render_level(label, body))
        except Exception as exc:
            renders.append({"label": label, "error": str(exc)})
            print("RENDER FAIL", label, exc, flush=True)
        OUT.joinpath("f1_renders.json").write_text(json.dumps(renders, indent=2), encoding="utf-8")
    print("done", flush=True)


if __name__ == "__main__":
    main()
