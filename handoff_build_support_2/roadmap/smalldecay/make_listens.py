"""SMALLDECAY / AMBIENCE listen harness.

The original generator was not kept. This copies the method in
roadmap/smalldecay/listen/listen_report.json:

  * render() of a one-sample impulse (page defaults, Flat, lock 1.8 s,
    early 0, direct 0, dry gain 0)
  * the render already fades the last 50 ms
  * first 8 s of test_guitar_dualmono.wav, channel 0, convolved with that IR
  * then the same soft knee as Play

Room rows and PLACE poses come from that report. room_WHL is engine (W, H, L).
Boot keeps the unscaled stand. Run with --null before any DSP change.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[3]
SW = ROOT / "software"
if str(SW) not in sys.path:
    sys.path.insert(0, str(SW))

import app_server as APP  # noqa: E402
from render_pipeline import (  # noqa: E402
    apply_soft_limit,
    fft_convolve,
    render,
)

LISTEN = Path(__file__).resolve().parent / "listen"
REPORT = LISTEN / "listen_report.json"
GUITAR = ROOT / "roadmap" / "robotic_1240" / "test_guitar_dualmono.wav"
# The guitar lives under handoff_build_support_2, not a root roadmap folder.
if not GUITAR.is_file():
    GUITAR = (
        ROOT
        / "handoff_build_support_2"
        / "roadmap"
        / "robotic_1240"
        / "test_guitar_dualmono.wav"
    )
SR = 48000
GUITAR_S = 8.0
FADE_S = 0.050
BANDS = (63, 125, 250, 500, 1000, 2000, 4000)
PCM_SCALE = 2147483647.0  # int32 full scale used by the saved listens


def page_body(row, **over):
    """Page defaults, then this row's room and stand, then the listen locks."""
    placed = row["placed"]
    W, H, L = row["room_WHL"]
    body = {
        "W": W,
        "H": H,
        "L": L,
        "sx": placed["sx"],
        "sy": placed["sy"],
        "sz": placed["sz"],
        "mcx": placed["mcx"],
        "my": placed["my"],
        "mcz": placed["mcz"],
        "space": placed["space"],
        "early_wet": 0.0,
        "direct_wet": 0.0,
        "fdn_wet": 1.0,
        "dry_gain": 0.0,
        "decay_lock": True,
        "decay_s": 1.8,
        "decay_mode": "flat",
        "phys_ceiling": False,
        "smooth": True,
        "humidity": 0.35,
        "air_lp": 0.0,
        "air_shelf": 1.0,
        "air_iso": True,
        "two_sources": False,
        "movement": 0.0,
    }
    body.update(over)
    return body


def render_body(body, dry):
    """Same keyword set as POST /api/render."""
    p = APP.params_from_body(body)
    sr = int(dry.shape[0] and SR)
    L, R, info = render(
        dry, sr,
        W=p["W"], H=p["H"], L=p["L"],
        sox=p["sox"], soz=p["soz"],
        mz=p["mz"], my=p["my"], sy=p.get("sy"),
        sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
        space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
        early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"],
        direct_wet=p.get("direct_wet", 1.0),
        fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"],
        path_on=p["path_on"], path_preset=p["path_preset"],
        ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"),
        hadamard_n=p["hadamard_n"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
        polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0,
        mic_hp_on=p.get("mic_hp_on") or False,
        mic_hp_hz=p.get("mic_hp_hz") or 40.0,
        mic_response_hz=p.get("mic_response_hz") or 10000.0,
        mic_proximity=p.get("mic_proximity") or 0.0,
        ms_decode=bool(p.get("ms_decode")),
        capsule_mm=p.get("capsule_mm") or 17.0,
        surfaces=p.get("surfaces"),
        surfaces_solo=p.get("surfaces_solo"),
        surfaces_mute=p.get("surfaces_mute"),
        diffusion_seed=p["diffusion_seed"],
        lambda_ref=p["lambda_ref"],
        humidity=p.get("humidity") or 0.0,
        air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.0,
        air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
        reaktor_parity=bool(p.get("reaktor_parity")),
        air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
        air_iso=bool(p.get("air_iso")) if p.get("air_iso") is not None else True,
        diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.25,
        decay_s=p.get("decay_s") or 0.0,
        decay_lock=bool(p.get("decay_lock")),
        smooth=bool(p.get("smooth", True)),
        movement=float(p.get("movement") or 0.0),
        mirror_null=bool(p.get("mirror_null")),
        mic_gain_l=p.get("mic_gain_l", 1.0),
        mic_gain_c=p.get("mic_gain_c", 1.0),
        mic_gain_r=p.get("mic_gain_r", 1.0),
        mic_pan_l=p.get("mic_pan_l", -1.0),
        mic_pan_c=p.get("mic_pan_c", 0.0),
        mic_pan_r=p.get("mic_pan_r", 1.0),
        mic_phase_l=p.get("mic_phase_l", 1.0),
        mic_phase_c=p.get("mic_phase_c", 1.0),
        mic_phase_r=p.get("mic_phase_r", 1.0),
        two_sources=False,
        source_balance=p.get("source_balance") or 0.0,
        mirror_b=bool(p.get("mirror_b")),
        sx_b=p.get("sx_b"),
        sy_b=p.get("sy_b"),
        sz_b=p.get("sz_b"),
        colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
        colour_impl=p.get("colour_impl") or "sos",
        mic_preset_l=p.get("mic_preset_l") or "ShureSM57",
        mic_preset_c=p.get("mic_preset_c") or "ShureSM57",
        mic_preset_r=p.get("mic_preset_r") or "ShureSM57",
        mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
        mic_hpf_sides=p.get("mic_hpf_sides"),
        mic_hpf_centre=p.get("mic_hpf_centre"),
        source_radiation=str(p.get("source_radiation") or "omni"),
        source_yaw=float(p.get("source_yaw") or 0.0),
        source_pitch=float(p.get("source_pitch") or 0.0),
        source_radiation_b=p.get("source_radiation_b"),
        source_yaw_b=p.get("source_yaw_b"),
        source_pitch_b=p.get("source_pitch_b"),
        source_size_m=p.get("source_size_m"),
        desk=p,
        mic_hpf_l=p.get("mic_hpf_l"),
        mic_hpf_r=p.get("mic_hpf_r"),
        decay_mode=p.get("decay_mode") or "flat",
        phys_ceiling=bool(p.get("phys_ceiling")),
        sub_hp=bool(p.get("sub_hp")),
        surf_treatment=p.get("surf_treatment"),
        surf_cal=p.get("surf_cal"),
        surf_directional=False,
        prox_l=bool(p.get("prox_l", True)),
        prox_c=bool(p.get("prox_c", True)),
        prox_r=bool(p.get("prox_r", True)),
    )
    return L, R, info


def load_guitar(n=None):
    sr, y = wavfile.read(GUITAR)
    if int(sr) != SR:
        raise RuntimeError(f"guitar sr {sr}")
    y = y.astype(np.float64)
    if y.ndim == 2:
        y = y[:, 0]
    if y.dtype == np.float64 and np.max(np.abs(y)) > 2.0:
        y = y / 32768.0
    # int16 read above already converted via astype before the scale check.
    # wavfile gives int16. Scale it.
    raw_sr, raw = wavfile.read(GUITAR)
    g = raw[:, 0].astype(np.float64) / 32768.0
    if n is None:
        n = int(round(GUITAR_S * SR))
    return g[:n]


def impulse_ir(row, **over):
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    L, R, info = render_body(page_body(row, **over), dry)
    return L, R, info


def convolve_guitar(ir_l, ir_r, guitar):
    y_l = fft_convolve(guitar, ir_l)
    y_r = fft_convolve(guitar, ir_r)
    return apply_soft_limit(y_l, y_r)


def to_int32(L, R):
    n = min(len(L), len(R))
    stereo = np.column_stack([L[:n], R[:n]])
    q = np.rint(np.clip(stereo, -1.0, 1.0) * PCM_SCALE)
    return np.clip(q, -2147483647, 2147483647).astype(np.int32)


def read_int32(path):
    sr, x = wavfile.read(path)
    if int(sr) != SR or x.dtype != np.int32 or x.ndim != 2:
        raise RuntimeError(f"unexpected wav {path} {sr} {x.dtype} {getattr(x, 'shape', None)}")
    return x


def null_db(a, b):
    n = min(len(a), len(b))
    if n < 1:
        return None, 0
    d = a[:n].astype(np.float64) - b[:n].astype(np.float64)
    peak = float(np.max(np.abs(d)))
    ref = float(np.max(np.abs(b[:n].astype(np.float64))))
    db = 20.0 * np.log10(peak / ref) if peak > 0 and ref > 0 else -300.0
    return db, n


def off_rows():
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    rows = []
    for row in rep["rows"]:
        if row.get("phys_ceiling"):
            continue
        if row.get("decay_mode") != "flat":
            continue
        # The surfaces file is a separate on-pass. Skip it for the _off null.
        name = Path(row["wav"]).name
        if not name.endswith("_off.wav"):
            continue
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--room", default="")
    args = ap.parse_args()
    if not args.null:
        print("null-only until the DSP change. Pass --null.")
        return
    guitar = load_guitar()
    rows = off_rows()
    if args.room:
        rows = [r for r in rows if args.room in r["room"]]
    for row in rows:
        ir_l, ir_r, info = impulse_ir(row)
        y_l, y_r, peak, scale, lim_db, lim_n = convolve_guitar(ir_l, ir_r, guitar)
        got = to_int32(y_l, y_r)
        ref = read_int32(row["wav"])
        db, n = null_db(got, ref)
        print(
            row["room"],
            "null_db", round(db, 2) if db is not None else None,
            "len", got.shape[0], ref.shape[0],
            "ir", len(ir_l),
            "fdn_ms", info.get("fdn_ms"),
            "makeup", round(float(info.get("norm_scale") or 0), 6),
            "lim", lim_db, lim_n,
            "peak", round(float(peak), 6),
        )


if __name__ == "__main__":
    main()
