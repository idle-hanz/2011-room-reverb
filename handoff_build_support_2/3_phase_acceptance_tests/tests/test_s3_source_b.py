"""S3 fix-up: source B follows A, and one pose rule for the ring, the taps, and the sound.

The audio body is the evaluated app.js state after the ORTF boot preset
(space 0.17, toe ±55). direct_wet and early_wet stay at the stored enables
(1) and fdn_wet is 0, so the scored windows are the direct and the early
field. The locked FDN-first faders would silence those windows.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import shutil
import subprocess

import numpy as np
import pytest

from clientjs import client_state

SR = 48000
BANDS = (500, 1000, 2000, 4000, 8000)
SQRT2 = math.sqrt(2.0)


def _ortf(body: dict) -> None:
    """Same fields applyMicPreset("ortf") writes, including divergFromToe."""
    th = -abs(55.0 * math.pi / 180.0)
    body.update({
        "mic_setup": "ortf",
        "space": 0.17,
        "toe_half_deg": 55,
        "car_omni": 1,
        "diverg": 2.0 * (th + 0.25),
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "family_l": "cardioid", "family_c": "cardioid", "family_r": "cardioid",
        "polar_l": 0.5, "polar_c": 0.5, "polar_r": 0.5,
        "yaw_l_deg": -55, "yaw_c_deg": 0, "yaw_r_deg": 55,
    })


def _client_body(sw, app) -> dict:
    cs = client_state(sw)
    if cs is None:
        pytest.skip("node not found")
    body = dict(cs)
    _ortf(body)
    body.update({
        "two_sources": True,
        "mirror_b": True,
        "source_radiation": "violin_byu",
        "source_radiation_b": None,
        "source_yaw_b": None,
        "source_pitch_b": None,
        "direct_wet": 1.0,
        "early_wet": 1.0,
        "fdn_wet": 0.0,
        "dry_gain": 0.0,
        # FDN is off. 180 ms still covers the 60 ms early window.
        "ir_length_ms": 180,
    })
    import source_radiation as rad
    p0 = app.params_from_body(body)
    geo = app.geometry_payload(p0)
    s, m = geo["source"], geo["mic_centre"]
    yaw, pitch = rad.yaw_pitch_toward(
        (s["x"], s["y"], s["z"]), (m["x"], m["y"], m["z"]),
    )
    body["source_yaw"] = yaw
    body["source_pitch"] = pitch
    return body


def _render_ir(sw, app, body) -> np.ndarray:
    """In-process two-source render. render_ir.py forces two_sources off."""
    from render_pipeline import render

    old = os.getcwd()
    os.chdir(sw)
    try:
        p = app.params_from_body(body)
        dry = np.zeros(1, dtype=np.float64)
        dry[0] = 1.0
        two = bool(p.get("two_sources"))
        L, R, info = render(
            dry, SR,
            W=p["W"], H=p["H"], L=p["L"],
            sox=p["sox"], soz=p["soz"], mz=p["mz"], my=p["my"], sy=p.get("sy"),
            sx=p["sx"], sz=p["sz"], mcz=p["mcz"],
            space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
            early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"],
            direct_wet=p.get("direct_wet", 1.0),
            fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"],
            path_on=p["path_on"], path_preset=p["path_preset"],
            ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
            mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"), hadamard_n=p["hadamard_n"],
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
            diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"],
            humidity=p.get("humidity") or 0.0,
            air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.0,
            air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
            reaktor_parity=bool(p.get("reaktor_parity")),
            air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
            air_iso=bool(p.get("air_iso")) if p.get("air_iso") is not None else True,
            diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.25,
            decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
            mic_gain_l=p.get("mic_gain_l", 1.0),
            mic_gain_c=p.get("mic_gain_c", 1.0),
            mic_gain_r=p.get("mic_gain_r", 1.0),
            mic_pan_l=p.get("mic_pan_l", -1.0),
            mic_pan_c=p.get("mic_pan_c", 0.0),
            mic_pan_r=p.get("mic_pan_r", 1.0),
            mic_phase_l=p.get("mic_phase_l", 1.0),
            mic_phase_c=p.get("mic_phase_c", 1.0),
            mic_phase_r=p.get("mic_phase_r", 1.0),
            two_sources=two,
            source_balance=p.get("source_balance") or 0.0,
            mirror_b=bool(p.get("mirror_b")),
            sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"),
            dry_l=dry if two else None, dry_r=dry if two else None,
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
        )
    finally:
        os.chdir(old)
    sc = float(info.get("norm_scale") or 1.0)
    L = np.asarray(L, dtype=np.float64) / sc
    R = np.asarray(R, dtype=np.float64) / sc
    return np.stack([L, R], 1)


def _null_db(ref, other) -> float:
    n = min(len(ref), len(other))
    a = np.asarray(ref[:n], dtype=np.float64)
    b = np.asarray(other[:n], dtype=np.float64)
    return 10.0 * math.log10(
        max(float(np.sum((a - b) ** 2)), 1e-300) / max(float(np.sum(a ** 2)), 1e-300)
    )


def _bands(x) -> dict:
    x = np.asarray(x, dtype=np.float64)
    nfft = 8192
    w = np.hanning(len(x)) if len(x) > 1 else np.ones(1)
    mag = np.abs(np.fft.rfft(x * w, nfft))
    f = np.fft.rfftfreq(nfft, 1.0 / SR)
    out = {}
    for fc in BANDS:
        m = (f >= fc / SQRT2) & (f < fc * SQRT2)
        out[fc] = 10.0 * math.log10(float(np.sum(mag[m] ** 2)) + 1e-30)
    return out


def _deltas(ref, other) -> dict:
    a, b = _bands(ref), _bands(other)
    return {fc: b[fc] - a[fc] for fc in BANDS}


def _score(name, ir_a, ir_b, ir_omni):
    """ir_* columns are L, R. A is balance −1, B and omni-B are balance +1."""
    ar = ir_a[:, 1]
    n0 = int(np.argmax(np.abs(ar)))
    assert float(np.max(np.abs(ar))) > 1e-5, f"{name}: A.R direct is silent"
    n4 = int(0.004 * SR)
    n60 = int(0.060 * SR)
    bl = ir_b[:, 0]
    om = ir_omni[:, 0]
    d_ref, d_bl = ar[n0:n0 + n4], bl[n0:n0 + n4]
    e_ref, e_bl = ar[n0:n0 + n60], bl[n0:n0 + n60]
    nd = _null_db(d_ref, d_bl)
    dlt = _deltas(d_ref, d_bl)
    elt = _deltas(e_ref, e_bl)
    om8 = _bands(om[n0:n0 + n4])[8000]
    b8 = _bands(d_bl)[8000]
    gap = om8 - b8
    msg = (
        f"{name}: direct null {nd:.1f} dB, direct bands { {k: round(v, 2) for k, v in dlt.items()} }, "
        f"early bands { {k: round(v, 2) for k, v in elt.items()} }, 8 kHz below omni {gap:.2f} dB"
    )
    assert nd <= -35.0, msg
    assert all(abs(v) <= 0.2 for v in dlt.values()), msg
    assert all(abs(v) <= 1.0 for v in elt.values()), msg
    assert gap >= 2.0, msg
    return {"null_db": round(nd, 2), "direct_db": {k: round(v, 2) for k, v in dlt.items()},
            "early_db": {k: round(v, 2) for k, v in elt.items()}, "below_omni_8k_db": round(gap, 2)}


@pytest.mark.phase("S3")
def test_s3_mirror_b_follows_a_directivity(sw, app, ctx):
    """Default room, ORTF, two sources, Mirror, A = violin_byu facing the mic.

    Balance −1 is A, balance +1 is B. B.L matches A.R on the direct and the
    early field, and B's 8 kHz direct sits below an explicit-omni B.
    """
    if not ctx.node:
        pytest.skip("node not found")
    body = _client_body(sw, app)
    p = app.params_from_body(body)
    assert p["source_radiation_b"] is None
    assert p["source_yaw_b"] is None
    assert p["source_pitch_b"] is None
    from render_pipeline import live_fdn_params
    old = os.getcwd()
    os.chdir(sw)
    try:
        packed = live_fdn_params(p)
    finally:
        os.chdir(old)
    src = packed.get("src_rad") or []
    assert len(src) == 716 and src[0] >= 0.5 and src[1] >= 0.5, (
        f"B did not follow A's violin into SRC_RAD (len {len(src)} head {src[:2]})"
    )

    play_a = ctx.play_ir(dict(body, source_balance=-1.0), {}, 0.15)
    play_b = ctx.play_ir(dict(body, source_balance=1.0), {}, 0.15)
    play_o = ctx.play_ir(dict(body, source_balance=1.0, source_radiation_b="omni"), {}, 0.15)
    rend_a = _render_ir(sw, app, dict(body, source_balance=-1.0))
    rend_b = _render_ir(sw, app, dict(body, source_balance=1.0))
    rend_o = _render_ir(sw, app, dict(body, source_balance=1.0, source_radiation_b="omni"))
    play = _score("Play", play_a, play_b, play_o)
    rend = _score("Render", rend_a, rend_b, rend_o)
    assert play["null_db"] <= -35.0 and rend["null_db"] <= -35.0


@pytest.mark.phase("S3")
def test_s3_b_pose_single_rule(sw, app):
    """Mirror on, yaw_A 30: preview and B's taps use −30. The client literal does not send omni for B."""
    cs = client_state(sw)
    if cs is None:
        pytest.skip("node not found")
    assert cs["source_radiation_b"] is None
    assert cs["source_yaw_b"] is None
    assert cs["source_pitch_b"] is None
    assert "source_radiation_b: \"omni\"" not in (sw / "static/js/app.js").read_text(encoding="utf-8")
    empty = app.params_from_body({})
    assert empty["source_radiation_b"] is None
    assert empty["source_yaw_b"] is None
    assert empty["source_pitch_b"] is None

    node = shutil.which("node")
    if not node:
        pytest.skip("node not found")
    js = r"""
const fs = require('fs'); const vm = require('vm');
const window = {};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), { window });
const p = window.RoomMath.effectiveBPose({
  source_radiation: 'violin_byu', source_yaw: 30, source_pitch: 4,
  source_radiation_b: null, source_yaw_b: null, source_pitch_b: null, mirror_b: true
});
const own = window.RoomMath.effectiveBPose({
  source_radiation: 'violin_byu', source_yaw: 30, source_pitch: 4,
  source_radiation_b: 'omni', source_yaw_b: 0, source_pitch_b: 0, mirror_b: true
});
console.log(JSON.stringify({ follow: p, own: own }));
"""
    r = subprocess.run(
        [node, "-e", js, str(sw / "static/js/room_math.js")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[-400:]
    twin = json.loads(r.stdout)
    assert twin["follow"]["preset"] == "violin_byu"
    assert abs(twin["follow"]["yaw"] - (-30)) < 1e-9
    assert abs(twin["follow"]["pitch"] - 4) < 1e-9
    assert twin["own"]["preset"] == "omni"
    assert twin["own"]["yaw"] == 0

    body = {
        "two_sources": True,
        "mirror_b": True,
        "source_radiation": "violin_byu",
        "source_yaw": 30,
        "source_pitch": 4,
        "source_radiation_b": None,
        "source_yaw_b": None,
        "source_pitch_b": None,
        "which": "b",
        "mics": ["L", "C", "R"],
    }
    preview = asyncio.run(app.api_source_preview(dict(body)))
    assert isinstance(preview, dict) and "yaw" in preview, preview
    assert abs(float(preview["yaw"]) - (-30.0)) < 1e-6, preview.get("yaw")
    assert abs(float(preview["pitch"]) - 4.0) < 1e-6
    assert preview.get("id") == "violin_byu"
    images = asyncio.run(app.api_images(dict(body)))
    face = images.get("source_facing_b") or {}
    assert abs(float(face.get("yaw")) - (-30.0)) < 1e-6, face
    assert face.get("preset") == "violin_byu"
    assert images.get("per_mic_b"), "per_mic_b is empty"
    import copy
    import source_radiation as rad
    hit = None
    mics = images.get("mics") or {}
    for mic_id, group in (images.get("per_mic_b") or {}).items():
        cap = mics.get(mic_id) or {"x": 0.0, "y": 0.0, "z": 0.0}
        for tap in group or []:
            raw = {k: v for k, v in tap.items() if k not in ("src_az_deg", "src_el_deg", "src_db_1k", "src_db_4k")}
            neg = copy.deepcopy(raw)
            pos = copy.deepcopy(raw)
            rad.annotate_taps([neg], "violin_byu", -30.0, 4.0, cap, None)
            rad.annotate_taps([pos], "violin_byu", 30.0, 4.0, cap, None)
            if neg["src_az_deg"] != pos["src_az_deg"] or neg["src_db_1k"] != pos["src_db_1k"]:
                hit = (tap, neg, pos)
                break
        if hit is not None:
            break
    assert hit is not None, "no B tap changes between yaw −30 and +30"
    tap, neg, pos = hit
    assert tap["src_az_deg"] == neg["src_az_deg"], (tap["src_az_deg"], neg["src_az_deg"], pos["src_az_deg"])
    assert tap["src_db_1k"] == neg["src_db_1k"]
    assert tap["src_az_deg"] != pos["src_az_deg"] or tap["src_db_1k"] != pos["src_db_1k"]

    old = app.params_from_body({
        "mirror_b": True, "source_yaw": 30, "source_pitch": 4,
        "source_radiation": "violin_byu", "source_radiation_b": "omni",
        "source_yaw_b": 0, "source_pitch_b": 0,
    })
    import source_radiation as rad2
    preset, yaw, pitch = rad2.effective_b_pose(old)
    assert preset == "omni"
    assert yaw == 0.0
    assert pitch == 0.0
