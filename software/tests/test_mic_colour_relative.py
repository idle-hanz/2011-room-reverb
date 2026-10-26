"""Phase 1: aim·ray angle, fitter relative_db, Render hooks. No SciPy package import."""

from __future__ import annotations

import inspect
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

SOFTWARE = Path(__file__).resolve().parents[1]
ENGINE = SOFTWARE / "engine"
for _p in (str(SOFTWARE), str(ENGINE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# SM57 relative_db, degrees, Hz. Printed from the fitter model (no SciPy).
_SM57_DB = {
    (0.0, 1000.0): 0.0,
    (0.0, 8000.0): 0.0,
    (90.0, 1000.0): -9.2827946111,
    (90.0, 8000.0): -10.7408382084,
    (180.0, 1000.0): -16.2618319376,
    (180.0, 8000.0): -18.2254855762,
}


def _db_at(model, theta_deg, freq):
    from mic_colour.model import relative_db
    return float(np.asarray(relative_db(model, [freq], theta_deg)).reshape(-1)[0])


def _fresh_mic_colour_imports():
    """mic_colour must not import scipy. An earlier test in this process may have."""
    code = (
        "import sys\n"
        "sys.path[:0] = [%r, %r]\n"
        "import mic_colour.model\n"
        "bad = [k for k in ('scipy', 'mic_fitter', 'mic_fitter.fit') if k in sys.modules]\n"
        "raise SystemExit(0 if not bad else 1)\n"
    ) % (str(SOFTWARE), str(ENGINE))
    r = subprocess.run([sys.executable, "-c", code], cwd=str(SOFTWARE), capture_output=True, text=True)
    assert r.returncode == 0, (r.returncode, r.stderr[-500:])


def test_no_scipy_package_import():
    import mic_colour.model  # noqa: F401
    _fresh_mic_colour_imports()
    root = SOFTWARE / "mic_colour"
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            s = line.strip()
            assert not s.startswith("import early_field")
            assert not s.startswith("from early_field")
            assert not s.startswith("import mic_fitter")
            assert not s.startswith("from mic_fitter")
    pipe = (SOFTWARE / "render_pipeline.py").read_text(encoding="utf-8")
    assert "mic_one_pole_coeff" not in pipe
    assert "apply_mic=True" not in pipe
    assert "wall_tone" not in pipe


def test_repo_root_not_parents1():
    from mic_colour import model as mm
    here = Path(mm.__file__).resolve()
    root = mm.repo_root()
    assert (root / "software").is_dir() and (root / "mic_fitter").is_dir()
    assert root != here.parents[1]
    assert not ((here.parents[1] / "software").is_dir() and (here.parents[1] / "mic_fitter").is_dir())


def test_sm57_relative_db_goldens():
    from mic_colour.model import (
        angle_weight,
        high_shelf_db,
        low_shelf_db,
        soft_one_pole_db,
    )
    from mic_colour.preset_store import get_store
    model = get_store().model_for("ShureSM57")
    for (theta, freq), expect in _SM57_DB.items():
        got = _db_at(model, theta, freq)
        assert abs(got - expect) < 1e-6, (theta, freq, got, expect)
    assert abs(_db_at(model, 0.0, 1000.0)) < 1e-12
    w = float(np.asarray(angle_weight(90.0, model.p)).reshape(-1)[0])
    hs = float(np.asarray(high_shelf_db([8000.0], model.f0, model.depth_max_db * w, model.shelf_slope)).reshape(-1)[0])
    ls = float(np.asarray(low_shelf_db([8000.0], model.f_lo, model.depth_lo_db * w)).reshape(-1)[0])
    fc = model.res_hz + (model.fc_floor - model.res_hz) * w
    lp = float(np.asarray(
        (soft_one_pole_db([8000.0], fc) - soft_one_pole_db([8000.0], model.res_hz)) * model.lp_mix * w
    ).reshape(-1)[0])
    full = _db_at(model, 90.0, 8000.0)
    assert abs(full - (hs + ls + lp)) < 1e-6
    assert abs(lp) > 0.05
    assert abs(hs) > abs(lp) * 2.0
    assert full < -3.0


def test_minimum_phase_matches_relative_db():
    from mic_colour.design import design_ir, design_n_fft, response_db
    from mic_colour.preset_store import get_store
    model = get_store().model_for("ShureSM57")
    assert design_ir(model, 0.0, 44100) is None
    ir = design_ir(model, 90.0, 44100)
    assert ir is not None and ir.ndim == 1
    n = design_n_fft(44100)
    freqs, db = response_db(model, 90.0, 44100, n, None, False)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(np.fft.rfft(ir, n=n)), 1e-12))
    mask = (freqs >= 20.0) & (freqs <= 16000.0)
    assert float(np.max(np.abs(mag_db[mask] - db[mask]))) < 0.05
    # A second rate is a new design, not the 44.1 kHz impulse.
    ir48 = design_ir(model, 90.0, 48000)
    assert len(ir48) == design_n_fft(48000)
    assert len(ir48) != len(ir) or not np.allclose(ir48, ir)


def test_hpf_orthogonal_and_sm57_null():
    from mic_colour.hpf import stack_hpf
    from mic_colour.preset_store import get_store
    store = get_store()
    sm = store.hpf_of("ShureSM57")
    u87 = store.hpf_of("NeumannU87AiCardioid")
    c414 = store.hpf_of("AKGC414Cardioid")
    assert sm["hpf_hz"] is None
    assert u87["hpf_hz"] is not None and c414["hpf_hz"] is not None
    freqs = np.array([50.0, 1000.0, 8000.0])
    db = np.zeros(3)
    assert np.allclose(stack_hpf(db, freqs, sm["hpf_hz"], 12, True), db)
    assert np.allclose(stack_hpf(db, freqs, u87["hpf_hz"], 12, False), db)
    cut = np.asarray(stack_hpf(db, freqs, u87["hpf_hz"], int(u87["hpf_slope"]), True), dtype=float)
    assert cut[0] < -3.0
    assert abs(cut[2]) < 1.0


def test_preset_loader_and_pattern_map():
    from mic_colour.pattern_map import capsule_law
    from mic_colour.preset_store import get_store, resolve_preset_id
    store = get_store()
    ids = set(store.ids())
    assert "ShureSM57" in ids
    assert "RoyerR121" in ids
    assert "NeumannU87AiOmni" in ids
    assert "NeumannU87AiCardioid" in ids
    assert "proxy_fig8_ribbon" in ids
    assert not any("2200" in i or "se2200" in i.lower() for i in ids)
    assert resolve_preset_id(None) == "NeumannU87AiCardioid"
    assert resolve_preset_id("SM57") == "ShureSM57"
    assert resolve_preset_id("Royer") == "RoyerR121"
    royer = capsule_law(store.family_of("RoyerR121"))
    assert royer == {"pattern": "fig8", "family": "bi", "polar": 0.5}
    assert set(royer) == {"pattern", "family", "polar"}
    omni = capsule_law(store.family_of("NeumannU87AiOmni"))
    card = capsule_law(store.family_of("NeumannU87AiCardioid"))
    assert omni["pattern"] == "omni" and omni["polar"] == 0.0
    assert card["pattern"] == "cardioid" and card["polar"] == 0.5
    assert omni["pattern"] != card["pattern"]
    hyper = capsule_law("hypercardioid")
    assert hyper["pattern"] == "supercardioid" and hyper["polar"] == 1.0


def test_server_defaults_do_not_move_the_desk():
    from app_server import params_from_body
    missing = params_from_body({})
    assert missing["colour_mode"] == "MEASURED_SHELF"
    assert missing["colour_impl"] == "sos"
    assert missing["mic_preset_l"] == missing["mic_preset_c"] == missing["mic_preset_r"] == "NeumannU87AiCardioid"
    assert missing["pattern_l"] == "cardioid"
    assert missing["yaw_l_deg"] is None
    assert abs(missing["space"] - 0.25) < 1e-9
    assert missing["mic_hpf_engaged"] is False
    kept = params_from_body({"pattern_l": "omni", "polar_l": 0.0, "yaw_l_deg": -55.0, "space": 0.17})
    assert kept["pattern_l"] == "omni"
    assert kept["mic_preset_l"] == "NeumannU87AiCardioid"
    assert kept["yaw_l_deg"] == -55.0
    assert abs(kept["space"] - 0.17) < 1e-9
    loaded = params_from_body({
        "mic_preset_l": "RoyerR121",
        "yaw_l_deg": -55.0,
        "yaw_r_deg": 55.0,
        "space": 0.17,
        "mic_setup": "ortf",
        "pattern_l": "cardioid",
    })
    assert loaded["pattern_l"] == "fig8"
    assert loaded["family_l"] == "bi"
    assert loaded["pattern_c"] == "cardioid"
    assert loaded["yaw_l_deg"] == -55.0
    assert loaded["yaw_r_deg"] == 55.0
    assert abs(loaded["space"] - 0.17) < 1e-9
    assert loaded["mic_setup"] == "ortf"
    omni = params_from_body({"mic_preset_c": "NeumannU87AiOmni", "yaw_c_deg": 12.0})
    card = params_from_body({"mic_preset_c": "NeumannU87AiCardioid", "yaw_c_deg": 12.0})
    assert omni["pattern_c"] == "omni" and card["pattern_c"] == "cardioid"
    assert omni["yaw_c_deg"] == 12.0 and card["yaw_c_deg"] == 12.0
    unknown_mode = params_from_body({"colour_mode": "STRUCTURE_ONE_POLE"})
    assert unknown_mode["colour_mode"] == "MEASURED_SHELF"
    toys = params_from_body({"colour_mode": "ASSUMED_TOYS"})
    assert toys["colour_mode"] == "ASSUMED_TOYS"


def test_ray_angle_replaces_floor_plan():
    import early_field as ef
    from early_field import (
        MicStand,
        arrival_cos_ray,
        arrival_cos_xz,
        arrival_theta_ray,
        compute_taps,
        direction_angles,
        direct_field_from_metres,
        look_vector,
        pattern_gain,
    )
    src = inspect.getsource(compute_taps)
    assert "arrival_theta_ray" in src
    assert "arrival_cos_xz" not in src
    assert "direction_angles" not in src
    mic = (3.0, 1.5, 1.5)
    assert arrival_cos_ray(mic, mic, 0.4) == 1.0
    lx, ly, lz = look_vector(0.0)
    assert abs(lx) < 1e-12 and abs(ly) < 1e-12 and abs(lz - 1.0) < 1e-12
    level = (4.2, 1.5, 6.0)
    for yaw in (0.0, -0.7, 0.4, 1.1):
        assert abs(arrival_cos_ray(mic, level, yaw) - arrival_cos_xz(mic, level, yaw)) < 1e-12
    front_up = (3.0, 2.8, 6.0)
    behind_up = (3.0, 2.8, -1.0)
    c_front_ray = arrival_cos_ray(mic, front_up, 0.0)
    c_front_xz = arrival_cos_xz(mic, front_up, 0.0)
    assert c_front_ray < c_front_xz - 1e-4
    assert pattern_gain(math.acos(c_front_ray), "cardioid") < pattern_gain(math.acos(c_front_xz), "cardioid") - 1e-4
    c_back_ray = arrival_cos_ray(mic, behind_up, 0.0)
    c_back_xz = arrival_cos_xz(mic, behind_up, 0.0)
    assert c_back_ray > c_back_xz + 1e-4
    assert pattern_gain(arrival_theta_ray(mic, behind_up, 0.0), "cardioid") > pattern_gain(
        math.acos(c_back_xz), "cardioid"
    )
    room = (6.0, 3.0, 8.0)
    prep = direct_field_from_metres(
        6, 3, 8, sx=3, sy=1.5, sz=4.75, mcx=3, my=1.5, mcz=1.5,
        space=0.17, diverg=1.0, yaw_l_deg=-55.0, yaw_r_deg=55.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0,
        pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    )
    taps = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=False)
    direct = [t for t in taps if t.n == (0, 0, 0)][0]
    deg_l = math.degrees(direct.theta_l)
    deg_c = math.degrees(direct.theta_c)
    assert 45.0 < deg_l < 65.0
    assert deg_c < 2.0
    left, _right = ef.mic_positions(stand)
    th_h = abs(direction_angles(left, direct.position, stand.mlalr)[0])
    assert abs(direct.theta_l - th_h) < 1e-6
    found = False
    for t in taps:
        if t.n[1] == 0:
            continue
        horiz = abs(direction_angles(left, t.position, stand.mlalr)[0])
        if t.position[1] > left[1] and t.position[2] > left[2] and t.theta_l > horiz + 1e-3:
            assert pattern_gain(t.theta_l, "cardioid") < pattern_gain(horiz, "cardioid") - 1e-4
            found = True
            break
    assert found
    shelved = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=True)
    bare = {t.n: t for t in taps}
    for t in shelved:
        b = bare[t.n]
        assert abs(b.shelf_l - 1.0) < 1e-12
        if t.shelf_l > 1e-8:
            assert abs(b.level_l - t.level_l / t.shelf_l) < 1e-8 * (1.0 + abs(b.level_l))
    assert direct.level_l > 0.0
    d_on = [t for t in shelved if t.n == (0, 0, 0)][0]
    assert d_on.shelf_l < 0.98
    assert bare[(0, 0, 0)].level_l > d_on.level_l * 1.01


def test_direct_colour_before_fold_and_centre_flat():
    from early_field import MicStand, compute_taps, direct_field_from_metres
    from fdn import apply_capsule_weights, capsule_speaker_weights
    from mic_colour.colour import MicColour
    from render_pipeline import LIVE_DIRECT_FOLD, render_listen_direct_ir
    room = (6.0, 3.0, 8.0)
    prep = direct_field_from_metres(
        6, 3, 8, sx=3, sy=1.5, sz=4.75, mcx=3, my=1.5, mcz=1.5,
        space=0.17, diverg=1.0, yaw_l_deg=-55.0, yaw_r_deg=55.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0,
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    )
    taps = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=False)
    direct = [t for t in taps if t.n == (0, 0, 0)][0]
    sr = 44100
    ms = 80.0
    colour = MicColour("MEASURED_SHELF", "SM57", "SM57", "SM57", sr)
    toys = MicColour("ASSUMED_TOYS", "SM57", "SM57", "SM57", sr)
    n = max(1, int(sr * ms / 1000.0) + 1)

    def at(delay_ms):
        i = int(round(float(delay_ms) * 0.001 * sr))
        return max(0, min(n - 1, i))

    Ld = np.zeros(n)
    Cd = np.zeros(n)
    Rd = np.zeros(n)
    Ld[at(direct.delay_ms_l)] = 1.0
    Cd[at(direct.delay_ms_c)] = 1.0
    Rd[at(direct.delay_ms_r)] = 1.0
    Ld = colour.apply(Ld, direct.theta_l, "l")
    Cd = colour.apply(Cd, direct.theta_c, "c")
    Rd = colour.apply(Rd, direct.theta_r, "r")
    left, right = apply_capsule_weights(Ld, Cd, Rd, capsule_speaker_weights())
    got_l, got_r = render_listen_direct_ir(taps, sr, ms, colour=colour)
    assert np.allclose(got_l, LIVE_DIRECT_FOLD * left)
    assert np.allclose(got_r, LIVE_DIRECT_FOLD * right)
    iso_l = capsule_speaker_weights(gain_c=0.0, gain_r=0.0)
    iso_c = capsule_speaker_weights(gain_l=0.0, gain_r=0.0)
    meas_l, _r = render_listen_direct_ir(taps, sr, ms, weights=iso_l, colour=colour)
    toy_l, _r = render_listen_direct_ir(taps, sr, ms, weights=iso_l, colour=toys)
    meas_c, _r = render_listen_direct_ir(taps, sr, ms, weights=iso_c, colour=colour)
    toy_c, _r = render_listen_direct_ir(taps, sr, ms, weights=iso_c, colour=toys)
    assert np.allclose(meas_c, toy_c)
    assert abs(float(np.max(np.abs(toy_c))) - 0.5 * LIVE_DIRECT_FOLD) < 1e-9
    assert float(np.max(np.abs(meas_l))) < float(np.max(np.abs(toy_l))) * 0.98
    assert not np.allclose(meas_l, toy_l)


def test_fdn_null_and_per_bus_theta():
    from fdn import FDN, build_inject_from_taps, capsule_speaker_weights, fdn_delays_from_taps, loop_level_trim_lin
    from mic_colour.colour import MicColour
    from render_pipeline import render_fdn_ir

    class Tap:
        def __init__(self, i, dist, level_l, level_c, theta_l, theta_c):
            self.n = (0, 0, 0) if i == 0 else (1, 0, 0)
            self.index = i
            self.distance_l = dist
            self.distance_r = dist
            self.distance_c = dist
            self.level_l = level_l
            self.level_r = 0.0
            self.level_c = level_c
            self.theta_l = theta_l
            self.theta_r = 0.0
            self.theta_c = theta_c

    sr = 48000
    c = 340.0
    n_lines = 8
    taps = []
    for i in range(n_lines):
        samples = 12 + 6 * i
        dist = samples * c / float(sr)
        taps.append(Tap(i, dist, 0.25 if i == 0 else 0.0, 0.0, 0.0, 0.0))
    room = (6.0, 3.0, 8.0)
    length_ms = 20.0
    n_samp = int(sr * length_ms / 1000.0) + 1
    iso_l = capsule_speaker_weights(gain_c=0.0, gain_r=0.0)
    bypass = MicColour("BYPASS", "SM57", "SM57", "SM57", sr)
    measured = MicColour("MEASURED_SHELF", "SM57", "SM57", "SM57", sr)
    kw = dict(
        taps=taps, room=room, sr=sr, c=c, length_ms=length_ms, g=0.0,
        depth_per_axis=0.0, delays=None, n_lines=n_lines, surfaces=None,
        humidity=0.0, air_lp=0.0, air_shelf=0.0, weights=iso_l,
    )
    left_b, _right = render_fdn_ir(colour=bypass, **kw)
    left_m, _right = render_fdn_ir(colour=measured, **kw)
    dly = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_lines, channel="l")
    inj = build_inject_from_taps(taps, n_samp, sr, c, n_lines, channel="l", humidity=0.0, air_lp=0.0, air_shelf=0.0)
    fdn = FDN(dly, g=0.0, room=room, sr=sr, n=n_lines, depth_per_axis=0.0, peaking=True)
    summed = fdn.process_block_sum(inj)
    # D3b: render_fdn_ir applies the Render F3 trim. The loop output does not.
    trim = loop_level_trim_lin("render", False)
    assert np.allclose(left_b, summed * trim)
    assert np.allclose(left_m, summed * trim)
    assert abs(float(inj[0, 0]) - 0.25) < 1e-12
    assert float(np.max(np.abs(inj[1:, 0]))) == 0.0
    # Off-axis L is coloured on the way out. The inject sample stays 0.25.
    for i, t in enumerate(taps):
        t.theta_l = math.pi / 2.0
    left_off, _right = render_fdn_ir(colour=measured, **kw)
    inj_off = build_inject_from_taps(taps, n_samp, sr, c, n_lines, channel="l", humidity=0.0, air_lp=0.0, air_shelf=0.0)
    assert abs(float(inj_off[0, 0]) - 0.25) < 1e-12
    assert not np.allclose(left_off, left_b)
    # Centre bus uses theta_c. theta_l is 90° and must not colour a silent-L, on-axis C.
    for i, t in enumerate(taps):
        t.level_l = 0.0
        t.level_c = 0.3 if i == 0 else 0.0
        t.theta_l = math.pi / 2.0
        t.theta_c = 0.0
    iso_c = capsule_speaker_weights(gain_l=0.0, gain_r=0.0)
    kw["weights"] = iso_c
    centre, _right = render_fdn_ir(colour=measured, **kw)
    centre_b, _right = render_fdn_ir(colour=bypass, **kw)
    assert np.allclose(centre, centre_b)
    for t in taps:
        t.theta_c = math.pi / 2.0
    centre_off, _right = render_fdn_ir(colour=measured, **kw)
    assert not np.allclose(centre_off, centre_b)


def test_early_toys_gated_and_colour_per_tap():
    import render_pipeline as rp
    from early_field import MicStand, allpass_ir_for_stages, compute_taps, direct_field_from_metres, precompute_wall_peaking_coeffs
    from mic_colour.colour import MicColour
    room = (6.0, 3.0, 8.0)
    prep = direct_field_from_metres(
        6, 3, 8, sx=1.2, sy=1.2, sz=2.0, mcx=3.0, my=1.5, mcz=4.0,
        space=0.2, diverg=1.0, yaw_l_deg=-40.0, yaw_r_deg=50.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0, yaw_l_deg=-40.0, yaw_c_deg=0.0, yaw_r_deg=50.0,
    )
    taps = compute_taps(room, prep.source, stand, hadamard_n=8, include_offaxis_shelf=False)
    sr = 48000
    c = 340.0
    wall = precompute_wall_peaking_coeffs(room, sr, c, 1.5)
    ap = {0: None, 1: allpass_ir_for_stages(1, sr), 2: allpass_ir_for_stages(2, sr)}
    calls = {"g": 0, "b": 0}
    real_g, real_b = rp.gradient_hp_hz, rp.beaming_lp_hz

    def g(mm):
        calls["g"] += 1
        return real_g(mm)

    def b(theta, mm):
        calls["b"] += 1
        return real_b(theta, mm)

    rp.gradient_hp_hz = g
    rp.beaming_lp_hz = b
    try:
        rp.render_early_ir(
            taps, room, sr, c, 12.0, 0.0, 0.0, wall, ap, early_toys=False,
        )
        assert calls["g"] == 0 and calls["b"] == 0
        rp.render_early_ir(
            taps, room, sr, c, 12.0, 0.0, 0.0, wall, ap, early_toys=True,
        )
        assert calls["g"] > 0 and calls["b"] > 0
    finally:
        rp.gradient_hp_hz = real_g
        rp.beaming_lp_hz = real_b
    dry = rp.render_early_ir(taps, room, sr, c, 15.0, 0.0, 0.0, wall, ap, air_lp=1.0, air_shelf=0.0, early_toys=False)
    wet = rp.render_early_ir(taps, room, sr, c, 15.0, 0.0, 1.0, wall, ap, air_lp=1.0, air_shelf=0.0, early_toys=False)
    assert float(np.max(np.abs(dry[0] - wet[0]))) > 1e-8
    colour = MicColour("MEASURED_SHELF", "SM57", "SM57", "SM57", sr)
    ordered = sorted(taps, key=lambda t: t.theta_l)
    pair = [ordered[0], ordered[-1]]
    assert abs(pair[0].theta_l - pair[1].theta_l) > 0.05
    # K1 (28 Sep 2026): with the yaw flip the extreme-theta taps arrive at 24-30 ms, so 40 ms window (was 15).
    both = rp.render_early_ir(pair, room, sr, c, 40.0, 0.0, 0.0, wall, ap, early_toys=False, colour=colour)
    a = rp.render_early_ir([pair[0]], room, sr, c, 40.0, 0.0, 0.0, wall, ap, early_toys=False, colour=colour)
    b = rp.render_early_ir([pair[1]], room, sr, c, 40.0, 0.0, 0.0, wall, ap, early_toys=False, colour=colour)
    assert np.allclose(both[0], a[0] + b[0])
    raw = rp.render_early_ir(pair, room, sr, c, 40.0, 0.0, 0.0, wall, ap, early_toys=False)
    wrong = colour.apply(raw[0], pair[0].theta_l, "l")
    assert not np.allclose(both[0], wrong, atol=1e-8)
    src = inspect.getsource(rp.render_early_ir)
    assert src.rindex("apply_air_absorption") < src.index("_colour_apply")
    assert src.rindex("apply_surface_to_buffer") < src.index("_colour_apply")
    fdn_src = inspect.getsource(rp.render_fdn_ir)
    assert "process_block_poly" in fdn_src
    assert "process_block_sum" not in fdn_src
    assert fdn_src.index("process_block_poly") < fdn_src.index("colour.apply")
    assert "colour.apply(inj" not in fdn_src
    direct_src = inspect.getsource(rp.render_listen_direct_ir)
    assert direct_src.index("_colour_apply") < direct_src.index("apply_capsule_weights")


def test_polar_uses_fitter_radius_not_lf_morph():
    """MEASURED radius is the fitter alone. BYPASS stays the ideal pattern."""
    import polar_field as pf
    from early_field import pattern_gain
    from mic_colour.model import relative_db
    from mic_colour.preset_store import get_store
    from app_server import params_from_body

    _fresh_mic_colour_imports()
    rings = [20.0, 63.0, 125.0, 250.0, 1000.0, 4000.0, 8000.0, 16000.0]
    assert list(pf.RING_HZ) == rings

    def _at(grid, freq, deg, centres):
        bi = centres.index(freq)
        ai = int(round(deg / 360.0 * len(grid[0]))) % len(grid[0])
        return float(grid[bi][ai])

    room = dict(
        W=6, H=3, L=8, sox=0.5, soz=0.55, mz=6.5, my=1.5,
        space=0.17, diverg=1.0, car_omni=1.0, mcx=3.0, n_az=72,
        pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
        family_l="cardioid", family_c="cardioid", family_r="cardioid",
        polar_l=0.5, polar_c=0.5, polar_r=0.5,
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    )
    measured = pf.compute_polar_field(
        **room, colour_mode="MEASURED_SHELF",
        mic_preset_l="ShureSM57", mic_preset_c="ShureSM57", mic_preset_r="ShureSM57",
        mic_hpf_engaged=False,
    )
    assert measured["measured"] is True
    assert measured["centres_hz"] == rings
    assert measured["ring_labels"] == ["20", "63", "125", "250", "1k", "4k", "8k", "16k"]
    assert measured["presets"]["C"]["id"] == "ShureSM57"
    assert measured["presets"]["C"]["honesty"] == "MEASURED"
    centres = measured["centres_hz"]
    fit = get_store().model_for("ShureSM57")
    # On axis the fitter is 0 dB, so every ring is 1. The ideal pattern is not applied.
    for freq in rings:
        assert abs(_at(measured["C"], freq, 0.0, centres) - 1.0) < 1e-6
    h180 = float(np.asarray(relative_db(fit, [20.0], 180.0)).reshape(-1)[0])
    assert abs(_at(measured["C"], 20.0, 180.0, centres) - (10.0 ** (h180 / 20.0))) < 1e-6
    toys = pf.compute_polar_field(**room, colour_mode="ASSUMED_TOYS")
    assert toys["measured"] is False
    assert _at(toys["C"], 20.0, 180.0, centres) > 0.9
    gain90 = abs(pattern_gain(math.pi / 2.0, "cardioid"))
    for freq in (1000.0, 8000.0):
        h = float(np.asarray(relative_db(fit, [freq], 90.0)).reshape(-1)[0])
        expect = 10.0 ** (h / 20.0)
        assert abs(_at(measured["C"], freq, 90.0, centres) - expect) < 1e-6
    assert _at(measured["C"], 8000.0, 90.0, centres) < _at(measured["C"], 1000.0, 90.0, centres)

    bypass = pf.compute_polar_field(**room, colour_mode="BYPASS", mic_hpf_engaged=False)
    assert abs(_at(bypass["C"], 20.0, 90.0, centres) - gain90) < 1e-6
    assert abs(_at(bypass["C"], 16000.0, 90.0, centres) - gain90) < 1e-6

    u87 = pf.compute_polar_field(
        **room, colour_mode="MEASURED_SHELF",
        mic_preset_l="NeumannU87AiCardioid",
        mic_preset_c="NeumannU87AiCardioid",
        mic_preset_r="NeumannU87AiCardioid",
        mic_hpf_engaged=True,
    )
    assert u87["presets"]["C"]["hpf_hz"] is not None
    assert _at(u87["C"], 20.0, 0.0, centres) < 0.5
    assert abs(_at(u87["C"], 1000.0, 0.0, centres) - 1.0) < 0.05
    sm_hpf = pf.compute_polar_field(
        **room, colour_mode="MEASURED_SHELF", mic_hpf_engaged=True,
        mic_preset_l="ShureSM57", mic_preset_c="ShureSM57", mic_preset_r="ShureSM57",
    )
    assert sm_hpf["presets"]["L"]["hpf_hz"] is None
    assert abs(_at(sm_hpf["C"], 20.0, 0.0, centres) - 1.0) < 1e-6

    royer_body = params_from_body({
        "mic_preset_l": "RoyerR121",
        "mic_preset_c": "RoyerR121",
        "mic_preset_r": "RoyerR121",
        "yaw_l_deg": -55.0,
        "yaw_r_deg": 55.0,
        "yaw_c_deg": 0.0,
        "space": 0.17,
        "pattern_l": "cardioid",
    })
    assert royer_body["pattern_l"] == "fig8"
    assert royer_body["family_l"] == "bi"
    assert royer_body["yaw_l_deg"] == -55.0
    assert abs(royer_body["space"] - 0.17) < 1e-9
    royer_room = dict(room)
    royer_room.update(
        pattern_l="fig8", pattern_c="fig8", pattern_r="fig8",
        family_l="bi", family_c="bi", family_r="bi",
        polar_l=0.5, polar_c=0.5, polar_r=0.5,
    )
    royer = pf.compute_polar_field(
        **royer_room, colour_mode="MEASURED_SHELF",
        mic_preset_l="RoyerR121", mic_preset_c="RoyerR121", mic_preset_r="RoyerR121",
    )
    assert abs(_at(royer["C"], 1000.0, 0.0, centres) - 1.0) < 1e-5
    roy = get_store().model_for("RoyerR121")
    h90 = float(np.asarray(relative_db(roy, [1000.0], 90.0)).reshape(-1)[0])
    h180r = float(np.asarray(relative_db(roy, [1000.0], 180.0)).reshape(-1)[0])
    assert abs(_at(royer["C"], 1000.0, 90.0, centres) - (10.0 ** (h90 / 20.0))) < 1e-5
    assert abs(_at(royer["C"], 1000.0, 180.0, centres) - (10.0 ** (h180r / 20.0))) < 1e-5

    kept = params_from_body({
        "mic_preset_l": "RoyerR121",
        "pattern_l": "cardioid",
        "family_l": "cardioid",
        "polar_l": 0.5,
        "yaw_l_deg": -55.0,
        "space": 0.17,
        "preset_owns_pattern": False,
        "colour_mode": "ASSUMED_TOYS",
    })
    assert kept["pattern_l"] == "cardioid"
    assert kept["family_l"] == "cardioid"
    assert kept["mic_preset_l"] == "RoyerR121"
    assert kept["yaw_l_deg"] == -55.0
    assert abs(kept["space"] - 0.17) < 1e-9
    for mode in ("MEASURED_SHELF", "BYPASS"):
        forced = params_from_body({
            "mic_preset_l": "RoyerR121",
            "pattern_l": "cardioid",
            "family_l": "cardioid",
            "polar_l": 0.5,
            "yaw_l_deg": -55.0,
            "space": 0.17,
            "preset_owns_pattern": False,
            "colour_mode": mode,
        })
        assert forced["pattern_l"] == "fig8", mode
        assert forced["family_l"] == "bi", mode
        assert abs(forced["polar_l"] - 0.5) < 1e-9, mode
        assert forced["yaw_l_deg"] == -55.0
        assert abs(forced["space"] - 0.17) < 1e-9
        assert forced["mic_preset_l"] == "RoyerR121"
    halo = measured["halo_xz"]
    assert len(halo) == 8 and len(halo[0]) == 72
    assert len(measured["halo_yz"]) == 8
    # 20 Hz, front (+Z) is still louder than the rear. The hard cardioid
    # null is no longer multiplied on top of the fitter.
    assert halo[0][0] > halo[0][36]
    # 17 cm at 1 kHz is half a wavelength along X, so the side ring combs.
    side = 54  # φ = 3π/2 → û = +X
    assert abs(halo[4][side] - halo[0][side]) > 0.2 * max(halo[0][side], 1e-6)
    assert "delay" in measured["halo_note"]
    assert len(measured["vertices"]["base"]) == 8 * 72 * 3
    assert len(measured["vertices"]["one"]) == 8 * 72 * 3
    page = (SOFTWARE / "static" / "index.html").read_text(encoding="utf-8")
    assert "Three mics summed (spacing interference)" in page
    assert 'data-plane="one"' in page
    assert measured["base_plane"]["e2"][2] > 0.5
    tilted = pf.compute_polar_field(**room, colour_mode="MEASURED_SHELF", sy=2.6)
    assert tilted["base_plane"]["tilt_deg"] > measured["base_plane"]["tilt_deg"] + 5.0
    _fresh_mic_colour_imports()


def test_stock_ortf_direct_and_makeup():
    """One stock ORTF picture: L/R direct dulls, centre stays, makeup barely moves."""
    from early_field import MicStand, compute_taps, direct_field_from_metres
    from fdn import capsule_speaker_weights, ir_rms_makeup_from_inject
    from mic_colour.colour import MicColour
    from mic_colour.model import relative_db
    from render_pipeline import render_listen_direct_ir, tap_reflect_gain
    from surface_colour import default_surfaces
    room = (6.0, 3.0, 8.0)
    prep = direct_field_from_metres(
        6, 3, 8, sx=3.0, sy=1.5, sz=4.75, mcx=3.0, my=1.5, mcz=1.5,
        space=0.17, diverg=1.0, yaw_l_deg=-55.0, yaw_r_deg=55.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0,
        pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    )
    bare = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=False)
    flat = compute_taps(
        room, prep.source, stand, hadamard_n=32,
        include_offaxis_shelf=False, include_pattern=False,
    )
    shelved = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=True)
    direct = [t for t in bare if t.n == (0, 0, 0)][0]
    direct_f = [t for t in flat if t.n == (0, 0, 0)][0]
    direct_s = [t for t in shelved if t.n == (0, 0, 0)][0]
    assert 50.0 < math.degrees(direct.theta_l) < 60.0
    assert math.degrees(direct.theta_c) < 1.0
    assert direct.level_l > direct_s.level_l
    surfaces = default_surfaces()

    def injects(taps):
        l, c, r = [], [], []
        for t in taps:
            g = tap_reflect_gain(t.n, surfaces)
            l.append(g * float(t.level_l))
            c.append(g * float(t.level_c))
            r.append(g * float(t.level_r))
        return l, c, r

    g = 1.0 / 32.0
    mk_bare = ir_rms_makeup_from_inject(*injects(bare), g, 32, 1500.0, 44100)
    mk_shelf = ir_rms_makeup_from_inject(*injects(shelved), g, 32, 1500.0, 44100)
    ratio_db = 20.0 * math.log10(mk_bare / mk_shelf)
    # Centre scalar is unchanged. The fold peak still includes off-axis L, so
    # makeup moves by about a decibel, not by the old 6 dB shelf.
    assert abs(direct.level_c - direct_s.level_c) < 1e-9
    assert abs(ratio_db) < 1.5
    model = MicColour("MEASURED_SHELF", "SM57", "SM57", "SM57", 44100)
    deg = math.degrees(direct.theta_l)
    from mic_colour.preset_store import get_store
    fit = get_store().model_for("ShureSM57")
    db_lo = float(np.asarray(relative_db(fit, [150.0], deg)).reshape(-1)[0])
    db_hi = float(np.asarray(relative_db(fit, [8000.0], deg)).reshape(-1)[0])
    assert db_hi < db_lo - 2.0
    assert abs(_db_at(fit, math.degrees(direct.theta_c), 8000.0)) < 0.05
    sr = 44100
    iso_l = capsule_speaker_weights(gain_c=0.0, gain_r=0.0)
    iso_c = capsule_speaker_weights(gain_l=0.0, gain_r=0.0)
    toys = MicColour("ASSUMED_TOYS", "SM57", "SM57", "SM57", sr)
    l_m, _r = render_listen_direct_ir(bare, sr, 40.0, weights=iso_l, colour=model)
    l_t, _r = render_listen_direct_ir(bare, sr, 40.0, weights=iso_l, colour=toys)
    c_m, _r = render_listen_direct_ir(bare, sr, 40.0, weights=iso_c, colour=model)
    c_t, _r = render_listen_direct_ir(bare, sr, 40.0, weights=iso_c, colour=toys)
    assert np.allclose(c_m, c_t)
    assert float(np.max(np.abs(l_m))) < float(np.max(np.abs(l_t)))
    from render_pipeline import live_fdn_params
    live = live_fdn_params({
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "yaw_l_deg": -55.0, "yaw_c_deg": 0.0, "yaw_r_deg": 55.0,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "colour_mode": "MEASURED_SHELF",
    })
    # No AudioContext rate yet: the shelf is already gone, the FIR is not.
    di = int(live["direct_index"])
    flat_l = tap_reflect_gain(direct_f.n, surfaces) * direct_f.level_l
    assert abs(live["buses"]["l"]["inject"][di] - flat_l) < 1e-9
    assert live["colour"]["on"] is False
    assert live["colour_mode"] == "MEASURED_SHELF"


def _live_scene(**extra):
    p = {
        "W": 6.0, "H": 3.0, "L": 8.0,
        "mz": 6.5, "my": 1.5, "sy": 1.5, "space": 0.17, "diverg": 1.0,
        "sox": 0.5, "soz": 0.4, "mcx": 3.0,
        "sx": 3.0, "sz": 4.75, "mcz": 1.5, "fdn_g": 1.0,
        "yaw_l_deg": -55.0, "yaw_c_deg": 0.0, "yaw_r_deg": 55.0,
        "pattern_l": "cardioid", "pattern_c": "cardioid", "pattern_r": "cardioid",
        "humidity": 0.35, "air_lp": 0.25, "air_shelf": 1.0,
        "colour_mode": "MEASURED_SHELF",
        "sample_rate": 48000,
    }
    p.update(extra)
    return p


def _decode_ir(b64):
    import base64
    raw = base64.b64decode(b64)
    return np.frombuffer(raw, dtype="<f4").astype(np.float64).copy()


def test_sos_accuracy_against_relative_db():
    """AT-C1: packed SOS vs analytic relative_db on every measured mic."""
    from mic_colour.colour import MicColour
    from mic_colour.model import relative_db
    from mic_colour.preset_store import get_store
    from mic_colour.sos_fit import sos_db, unpack_record
    from mic_colour.sos_table import tables_dir

    store = get_store()
    f = np.geomspace(20, 20000, 600)
    mics = [path.stem for path in sorted(tables_dir().glob("*.json"))]
    assert len(mics) == 20
    worst = []
    for mic_id in mics:
        model = store.model_for(mic_id)
        colour = MicColour("MEASURED_SHELF", mic_id, mic_id, mic_id, 48000)
        errs = []
        for deg in range(1, 181):
            rec = colour.payload_for(math.radians(deg), "l")
            if rec is None:
                ana = np.asarray(relative_db(model, f, float(deg)))
                assert float(np.max(np.abs(ana))) < 0.05
                continue
            sos = unpack_record(rec)
            ana = np.asarray(relative_db(model, f, float(deg)))
            e = float(np.max(np.abs(sos_db(sos, f, 48000) - ana)))
            errs.append(e)
        assert errs, mic_id
        worst.extend(errs)
        assert max(errs) <= 0.5, (mic_id, max(errs))
    assert worst
    p95 = float(np.percentile(worst, 95))
    assert max(worst) <= 0.5
    assert p95 <= 0.5, p95
    f44 = f[f < 0.45 * 44100.0]
    assert f44.size > 0
    worst44 = []
    for mic_id in mics:
        model = store.model_for(mic_id)
        colour = MicColour("MEASURED_SHELF", mic_id, mic_id, mic_id, 44100)
        errs = []
        for deg in range(1, 181):
            rec = colour.payload_for(math.radians(deg), "l")
            if rec is None:
                ana = np.asarray(relative_db(model, f44, float(deg)))
                assert float(np.max(np.abs(ana))) < 0.05
                continue
            sos = unpack_record(rec)
            assert sos is not None, mic_id
            ana = np.asarray(relative_db(model, f44, float(deg)))
            e = float(np.max(np.abs(sos_db(sos, f44, 44100) - ana)))
            errs.append(e)
        assert errs, mic_id
        worst44.extend(errs)
        assert max(errs) <= 0.6, (mic_id, max(errs))
    assert max(worst44) <= 0.6
    from render_pipeline import live_fdn_params
    for sr in (32000, 88200, 96000):
        sos_off = MicColour("MEASURED_SHELF", "ShureSM57", "ShureSM57", "ShureSM57", sr)
        assert sos_off.measured is False
        assert str(sr) in sos_off.notice
        assert "44100" in sos_off.notice and "48000" in sos_off.notice
        assert sos_off.payload_for(math.radians(90.0), "l") is None
        fir = MicColour(
            "MEASURED_SHELF", "ShureSM57", "ShureSM57", "ShureSM57", sr,
            colour_impl="fir",
        )
        assert fir.measured is True
        assert not fir.notice
        fir_rec = fir.payload_for(math.radians(90.0), "l")
        assert fir_rec is not None
        assert unpack_record(fir_rec) is None
        got = live_fdn_params(_live_scene(sample_rate=sr))
        assert got["colour"]["on"] is False
        assert got["colour"]["notice"] == sos_off.notice
        assert got["colour_notice"] == sos_off.notice


def test_live_colour_parity():
    """Play packs SOS at the given rate. ASSUMED_TOYS keeps the shelf."""
    from early_field import MicStand, compute_taps, direct_field_from_metres
    from fdn import ir_rms_makeup_from_inject
    from mic_colour.colour import MicColour
    from mic_colour.model import relative_db
    from mic_colour.sos_fit import sos_db, unpack_record
    from render_pipeline import live_fdn_params, tap_reflect_gain
    from surface_colour import default_surfaces

    room = (6.0, 3.0, 8.0)
    prep = direct_field_from_metres(
        6, 3, 8, sx=3.0, sy=1.5, sz=4.75, mcx=3.0, my=1.5, mcz=1.5,
        space=0.17, diverg=1.0, yaw_l_deg=-55.0, yaw_r_deg=55.0,
    )
    stand = MicStand.from_prepare(
        prep, car_omni=1.0,
        pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
        yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
    )
    bare = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=False)
    flat = compute_taps(
        room, prep.source, stand, hadamard_n=32,
        include_offaxis_shelf=False, include_pattern=False,
    )
    shelved = compute_taps(room, prep.source, stand, hadamard_n=32, include_offaxis_shelf=True)
    direct = [t for t in bare if t.n == (0, 0, 0)][0]
    direct_f = [t for t in flat if t.n == (0, 0, 0)][0]
    direct_s = [t for t in shelved if t.n == (0, 0, 0)][0]
    surfaces = default_surfaces()

    measured = live_fdn_params(_live_scene())
    toys = live_fdn_params(_live_scene(colour_mode="ASSUMED_TOYS"))
    bypass = live_fdn_params(_live_scene(colour_mode="BYPASS"))
    di = int(measured["direct_index"])
    bare_l = tap_reflect_gain(direct.n, surfaces) * float(direct.level_l)
    flat_l = tap_reflect_gain(direct_f.n, surfaces) * float(direct_f.level_l)
    shelf_l = tap_reflect_gain(direct_s.n, surfaces) * float(direct_s.level_l)
    assert abs(measured["buses"]["l"]["inject"][di] - flat_l) < 1e-9
    assert abs(bypass["buses"]["l"]["inject"][di] - bare_l) < 1e-9
    assert abs(toys["buses"]["l"]["inject"][di] - shelf_l) < 1e-9
    assert shelf_l < bare_l
    assert measured["colour"]["on"] is True and measured["colour"]["sr"] == 48000
    assert toys["colour"]["on"] is False and bypass["colour"]["on"] is False
    assert measured["colour_mode"] == "MEASURED_SHELF"
    assert measured["mic_preset_l"] == "NeumannU87AiCardioid"
    assert measured["mic_preset_c"] == "NeumannU87AiCardioid"
    assert measured["mic_preset_r"] == "NeumannU87AiCardioid"
    assert measured["mic_hpf_sides"] is False and measured["mic_hpf_centre"] is False
    g = 1.0 / 32.0
    # D-SRC-DIST-LEVEL. Play makeup is ir_rms of the reference-source injects.
    # Boot source (2.6, 1.2, 4.75) minus boot stand (3.0, 1.5, 1.5), added to
    # the placed stand centre. The live-inject asserts above stay on this scene.
    import copy
    from render_pipeline import _desk_at_stand, _place_stand
    placed = _place_stand(copy.copy(stand), _desk_at_stand(_live_scene()))
    boot_src = (2.6, 1.2, 4.75)
    boot_stand = (3.0, 1.5, 1.5)
    mk_source = (
        float(placed.cx) + (boot_src[0] - boot_stand[0]),
        float(placed.cy) + (boot_src[1] - boot_stand[1]),
        float(placed.cz) + (boot_src[2] - boot_stand[2]),
    )
    ref = live_fdn_params(_live_scene(
        sx=mk_source[0], sy=mk_source[1], sz=mk_source[2],
    ))
    mk = ir_rms_makeup_from_inject(
        ref["buses"]["l"]["inject"],
        ref["buses"]["c"]["inject"],
        ref["buses"]["r"]["inject"],
        g, 32, 1500.0, 48000,
    )
    assert abs(measured["makeup"] - mk) < 1e-9
    assert abs(toys["makeup"] - measured["makeup"]) > 1e-6
    # Air one-pole and the assumed shelf are not part of this phase.
    assert measured["buses"]["l"]["air_lp"] == toys["buses"]["l"]["air_lp"] > 0.0
    assert measured["buses"]["l"]["air_g"] == toys["buses"]["l"]["air_g"]
    assert measured["buses"]["l"]["shelf"] == toys["buses"]["l"]["shelf"]
    assert measured["buses"]["l"]["shelf"][di]["on"] is True

    bank = measured["colour"]
    assert measured.get("colour_impl") == "sos"
    assert "c" not in bank["early"]
    assert bank["direct"]["c"] == -1
    assert bank["direct"]["l"] >= 0 and bank["direct"]["r"] >= 0
    ir_l = _decode_ir(bank["irs"][bank["direct"]["l"]])
    colour = MicColour("MEASURED_SHELF", "NeumannU87AiCardioid", "NeumannU87AiCardioid", "NeumannU87AiCardioid", 48000)
    expect = colour.payload_for(direct.theta_l, "l")
    assert expect is not None
    assert ir_l.shape == expect.shape
    assert np.allclose(ir_l, expect, atol=1e-5)
    assert abs(float(ir_l[0]) + 2011.0) < 1e-3
    sos = unpack_record(ir_l)
    assert sos is not None
    f = np.geomspace(20, 16000, 400)
    ana = np.asarray(relative_db(colour._models["l"], f, math.degrees(direct.theta_l)))
    err = float(np.max(np.abs(sos_db(sos, f, 48000) - ana)))
    assert err < 0.5, err
    sos44 = unpack_record(MicColour(
        "MEASURED_SHELF", "NeumannU87AiCardioid", "NeumannU87AiCardioid", "NeumannU87AiCardioid", 44100,
    ).payload_for(direct.theta_l, "l"))
    assert sos44 is not None
    assert not np.allclose(sos, sos44, atol=1e-5)
    off = None
    for i, idx in enumerate(bank["fdn"]["l"]):
        if idx >= 0 and abs(math.degrees(bare[i].theta_l) - math.degrees(direct.theta_l)) > 5.0:
            off = i
            break
    assert off is not None
    ir_line = _decode_ir(bank["irs"][bank["fdn"]["l"][off]])
    expect_line = colour.payload_for(bare[off].theta_l, "l")
    assert np.allclose(ir_line, expect_line, atol=1e-5)
    assert not np.allclose(ir_line, ir_l)

    again = live_fdn_params(_live_scene(colour_rev=bank["rev"]))
    assert again["colour"]["same"] is True and "irs" not in again["colour"]
    assert abs(again["buses"]["l"]["inject"][di] - flat_l) < 1e-9

    other = {}
    for name in ("ShureSM57", "RoyerR121"):
        got = live_fdn_params(_live_scene(
            mic_preset_l=name, mic_preset_c=name, mic_preset_r=name,
        ))
        assert got["colour"]["on"] is True
        assert got["mic_preset_l"] == name
        idx = got["colour"]["direct"]["l"]
        assert idx >= 0
        other[name] = _decode_ir(got["colour"]["irs"][idx])
        assert not np.allclose(other[name], ir_l)
    assert not np.allclose(other["ShureSM57"], other["RoyerR121"])

    u87 = live_fdn_params(_live_scene(
        mic_preset_l="NeumannU87AiCardioid",
        mic_preset_c="NeumannU87AiCardioid",
        mic_preset_r="NeumannU87AiCardioid",
        mic_hpf_sides=True,
        mic_hpf_centre=False,
    ))
    u87_c = live_fdn_params(_live_scene(
        mic_preset_l="NeumannU87AiCardioid",
        mic_preset_c="NeumannU87AiCardioid",
        mic_preset_r="NeumannU87AiCardioid",
        mic_hpf_sides=False,
        mic_hpf_centre=True,
    ))
    assert u87["mic_hpf_sides"] is True and u87["mic_hpf_centre"] is False
    side_ir = _decode_ir(u87["colour"]["irs"][u87["colour"]["direct"]["l"]])
    assert int(side_ir[1]) > int(ir_l[1])
    assert u87["colour"]["direct"]["c"] == -1
    assert u87_c["colour"]["direct"]["c"] >= 0
    side_plain = _decode_ir(u87_c["colour"]["irs"][u87_c["colour"]["direct"]["l"]])
    centre_hpf = _decode_ir(u87_c["colour"]["irs"][u87_c["colour"]["direct"]["c"]])
    assert np.allclose(side_plain, ir_l, atol=1e-5)
    sos_c = unpack_record(centre_hpf)
    assert sos_c is not None
    mag_50 = float(sos_db(sos_c, [50.0], 48000)[0])
    assert mag_50 < -3.0, mag_50

    sm_plain = live_fdn_params(_live_scene(
        mic_preset_l="ShureSM57", mic_preset_c="ShureSM57", mic_preset_r="ShureSM57",
    ))
    sm_hpf = live_fdn_params(_live_scene(
        mic_preset_l="ShureSM57", mic_preset_c="ShureSM57", mic_preset_r="ShureSM57",
        mic_hpf_sides=True, mic_hpf_centre=True,
    ))
    sm_ir = _decode_ir(sm_hpf["colour"]["irs"][sm_hpf["colour"]["direct"]["l"]])
    sm_ref = _decode_ir(sm_plain["colour"]["irs"][sm_plain["colour"]["direct"]["l"]])
    assert np.allclose(sm_ir, sm_ref, atol=1e-5)
    assert sm_hpf["colour"]["direct"]["c"] == -1

    two = live_fdn_params(_live_scene(
        two_sources=True, mirror_b=False, sx_b=1.0, sy_b=1.5, sz_b=2.0,
    ))
    assert two["colour"]["fdn"] == bank["fdn"]
    assert two["colour"]["fdn_b"]["l"] != bank["fdn"]["l"]
    assert two["colour"]["direct_b"]["l"] >= 0
    ir_b = _decode_ir(two["colour"]["irs"][two["colour"]["direct_b"]["l"]])
    assert not np.allclose(ir_b, ir_l)
    assert "c" not in two["colour"]["early_b"]

    one_wet = live_fdn_params(_live_scene(early_wet=1.0))
    assert one_wet["colour"]["on"] is True
    assert len(one_wet["colour"]["irs"]) <= 192
    apart = live_fdn_params(_live_scene(
        two_sources=True, mirror_b=False, sx_b=1.5, sz_b=5.5, early_wet=1.0,
    ))
    assert apart["colour"]["on"] is True
    n_apart = len(apart["colour"]["irs"])
    assert 64 < n_apart <= 192, n_apart

    work = (SOFTWARE / "static/js/fdn_worklet.js").read_text(encoding="utf-8")
    live_js = (SOFTWARE / "static/js/live_fdn.js").read_text(encoding="utf-8")
    page = (SOFTWARE / "static/index.html").read_text(encoding="utf-8")
    pipe = (SOFTWARE / "render_pipeline.py").read_text(encoding="utf-8")
    assert "apply_mic=True" not in pipe
    assert "mic_one_pole_coeff" not in pipe
    stereo = (SOFTWARE / "engine" / "live_stereo.c").read_text(encoding="utf-8")
    assert "WORKLET_VER = 63" in live_js
    assert "live_fdn.js?v=64" in page
    assert "MAX_IRS = 192" in stereo
    assert "var MAX_IRS = 192" in work
    assert "Mic colour is OFF:" in live_js
    assert "entries, cap" in live_js
    assert "design_sos" in stereo
    assert "MAX_SOS" in stereo

    fir = live_fdn_params(_live_scene(colour_impl="fir"))
    assert fir["colour_impl"] == "fir"
    fir_l = _decode_ir(fir["colour"]["irs"][fir["colour"]["direct"]["l"]])
    assert abs(float(fir_l[0]) + 2011.0) > 1.0
    expect_fir = MicColour(
        "MEASURED_SHELF", "NeumannU87AiCardioid", "NeumannU87AiCardioid", "NeumannU87AiCardioid", 48000,
        colour_impl="fir",
    ).ir_for(direct.theta_l, "l")
    assert np.allclose(fir_l, expect_fir, atol=1e-5)
    assert "createConvolver" not in live_js
    assert "colour.sr === ctx.sampleRate" in live_js
    assert "live_stereo" in work
    assert "DIRECT_FOLD = 0.55" in stereo
    # Shared tail names the inject injUse. The old line->inj expression is gone.
    assert "0.5 * xA * injUse" in stereo
    assert "0.5 * xB * injUse" in stereo
    assert "double injUse = line->inj;" in stereo
    assert "N = 32" in stereo
    assert "0.68" not in stereo
    assert "mic_one_pole" not in live_js
    assert "mic_one_pole" not in stereo


TESTS = [
    test_no_scipy_package_import,
    test_repo_root_not_parents1,
    test_sm57_relative_db_goldens,
    test_minimum_phase_matches_relative_db,
    test_hpf_orthogonal_and_sm57_null,
    test_preset_loader_and_pattern_map,
    test_server_defaults_do_not_move_the_desk,
    test_ray_angle_replaces_floor_plan,
    test_direct_colour_before_fold_and_centre_flat,
    test_fdn_null_and_per_bus_theta,
    test_early_toys_gated_and_colour_per_tap,
    test_polar_uses_fitter_radius_not_lf_morph,
    test_stock_ortf_direct_and_makeup,
    test_sos_accuracy_against_relative_db,
    test_live_colour_parity,
]


def run_all() -> None:
    for fn in TESTS:
        fn()


if __name__ == "__main__":
    run_all()
    print("PASS", len(TESTS))
