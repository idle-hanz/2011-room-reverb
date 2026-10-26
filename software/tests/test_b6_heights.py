"""D-AUD-6 / B6. H-1 per-capsule heights.

Flat or equal heights stay on the old algebra. Image-tap delays follow each
capsule. FDN line length, diffuser and line air stay at the stand height.
Coincident M/S and binaural ignore the heights.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]
os.chdir(SW)

import app_server as A  # noqa: E402
from early_field import (  # noqa: E402
    MicStand,
    SPEED_OF_SOUND_M_S,
    centre_position,
    compute_taps,
    delay_ms_from_distance,
    direct_field_from_params,
    dist,
    fdn_reference_positions,
    mic_positions,
)
from fdn import fdn_delays_from_taps  # noqa: E402
from render_pipeline import render, _place_stand  # noqa: E402

CLIENT = ROOT / "handoff_build_support_2" / "roadmap" / "s4_verify_1140" / "measure" / "client_body_1140.json"
OUT = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b6_gates.json"
GOLDEN = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "golden" / "render_std_unlocked_byp.f32"
SR = 48000
FC = [125, 250, 500, 1000, 2000, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000]
# Empty-body live hash. TLAW 1/r (Idle 2026-10-10) moved it off the T4c hash
# 4bd18877a1a80396108bcafd17d4d762. The blob diff is inject levels, makeup,
# and the unwired direct_makeup field. Delays, g, and the direct fold stay.
_DEFAULT_LIVE_MD5 = "067adbca1930efcd3f7c83bdd1d4c359"


def _live(body):
    p = A.params_from_body(dict(body))
    blob = A.live_fdn_params(p)
    raw = json.dumps(blob, sort_keys=True, default=str)
    return blob, hashlib.md5(raw.encode()).hexdigest()


def _stand(body):
    p = A.params_from_body(dict(body))
    prep = direct_field_from_params(p)
    stand = MicStand.from_prepare(
        prep,
        car_omni=p.get("car_omni") or 1.0,
        pattern_l=p.get("pattern_l"),
        pattern_c=p.get("pattern_c"),
        pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"),
        yaw_c_deg=p.get("yaw_c_deg"),
        yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"),
        family_c=p.get("family_c"),
        family_r=p.get("family_r"),
        polar_l=p.get("polar_l"),
        polar_c=p.get("polar_c"),
        polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0,
        ms_decode=bool(p.get("ms_decode")),
        capsule_mm=p.get("capsule_mm") or 17.0,
    )
    if str(p.get("mic_setup") or "") == "binaural":
        stand = MicStand.binaural(
            cx=float(prep.mic_centre[0]),
            cy=float(prep.mic_centre[1]),
            cz=float(prep.mic_centre[2]),
            head_yaw_deg=float(p.get("head_yaw_deg") or 0.0),
            preset=str(p.get("binaural_preset") or "SADIE2_KU100"),
        )
    else:
        stand = _place_stand(stand, p)
    taps = compute_taps(
        (p["W"], p["H"], p["L"]),
        prep.source,
        stand,
        c=SPEED_OF_SOUND_M_S,
        grid="32",
        hadamard_n=int(p.get("hadamard_n") or 32),
        include_offaxis_shelf=True,
    )
    return p, prep, stand, taps


def _render(body, ms, desk=True):
    src = dict(A.DEFAULTS)
    src.update(body)
    src["ir_length_ms"] = float(ms)
    p = A.params_from_body(src)
    dry = np.zeros(1, dtype=np.float64)
    dry[0] = 1.0
    kw = dict(
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
        ms_decode=bool(p.get("ms_decode")),
        capsule_mm=p.get("capsule_mm") or 17.0,
        surfaces=p.get("surfaces"),
        diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"],
        humidity=p.get("humidity") or 0.0,
        air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.25,
        air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
        reaktor_parity=bool(p.get("reaktor_parity")),
        air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
        air_iso=bool(p.get("air_iso")) if p.get("air_iso") is not None else True,
        diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.25,
        decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
        mic_gain_l=p.get("mic_gain_l", 1.0), mic_gain_c=p.get("mic_gain_c", 1.0),
        mic_gain_r=p.get("mic_gain_r", 1.0),
        mic_pan_l=p.get("mic_pan_l", -1.0), mic_pan_c=p.get("mic_pan_c", 0.0),
        mic_pan_r=p.get("mic_pan_r", 1.0),
        mic_phase_l=p.get("mic_phase_l", 1.0), mic_phase_c=p.get("mic_phase_c", 1.0),
        mic_phase_r=p.get("mic_phase_r", 1.0),
        colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
        colour_impl=p.get("colour_impl") or "sos",
        sub_hp=bool(p.get("sub_hp")),
        mic_preset_l=p.get("mic_preset_l") or "NeumannU87AiCardioid",
        mic_preset_c=p.get("mic_preset_c") or "NeumannU87AiCardioid",
        mic_preset_r=p.get("mic_preset_r") or "NeumannU87AiCardioid",
        source_radiation=str(p.get("source_radiation") or "omni"),
        source_yaw=float(p.get("source_yaw") or 0.0),
        source_pitch=float(p.get("source_pitch") or 0.0),
        desk=p if desk else None,
    )
    L, R, info = render(dry, SR, **kw)
    sc = float(info.get("norm_scale") or 1.0)
    ir = np.stack([np.asarray(L, dtype=np.float64) / sc, np.asarray(R, dtype=np.float64) / sc], 1)
    return ir


def _maxabs(a, b):
    n = min(len(a), len(b))
    return float(np.max(np.abs(a[:n] - b[:n])))


def _bands(x):
    x = np.asarray(x, dtype=np.float64)
    spec = np.abs(np.fft.rfft(x, 1 << 18)) ** 2
    f = np.fft.rfftfreq(1 << 18, 1.0 / SR)
    out = []
    for c in FC:
        m = (f >= c * 2.0 ** -(1.0 / 6.0)) & (f < c * 2.0 ** (1.0 / 6.0))
        out.append(float(10.0 * np.log10(spec[m].sum() + 1e-30)))
    return np.array(out)


def _energy_db(x):
    return float(10.0 * np.log10(np.sum(np.asarray(x, dtype=np.float64) ** 2) + 1e-30))


def test_b6_gate1_flat_is_bit_identical():
    """Absent heights and heights equal to the stand match. Play hash stays put."""
    blob, digest = _live({})
    assert digest == _DEFAULT_LIVE_MD5
    assert "my_l" not in blob and "hy_l" not in blob

    _, dig_eq = _live({"my_l": 1.5, "my_r": 1.5, "my_c": 1.5, "align_horizontal": True})
    assert dig_eq == digest

    _, dig_null = _live({"my_l": None, "my_r": None, "my_c": None})
    assert dig_null == digest

    # D20. This pin is the stored ORTF centre, where posting the desk stays the 477 fold.
    scene = {
        "decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0,
        "colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1,
        "third_mic": "centre", "mic_gain_c": 1.0,
    }
    bare = _render(scene, 500, desk=False)
    posted = _render(scene, 500, desk=True)
    equal = _render(dict(scene, my_l=1.5, my_r=1.5, my_c=1.5), 500, desk=True)
    d_desk = _maxabs(bare, posted)
    d_eq = _maxabs(bare, equal)
    print("gate1 desk-on vs desk-off maxabs", d_desk)
    print("gate1 equal heights vs bare maxabs", d_eq)
    assert d_desk == 0.0
    assert d_eq == 0.0
    if GOLDEN.exists():
        gold = np.fromfile(GOLDEN, np.float32).reshape(-1, 2).astype(np.float64)
        print("gate1 bare vs on-disk golden maxabs", _maxabs(bare, gold), "n", len(bare), len(gold))


def test_b6_gate2_delays_match_capsule_geometry():
    """Four heights. Image delay is the 3D capsule. FDN delay is the stand."""
    heights = (0.40, 1.20, 1.80, 2.60)
    worst_image = 0
    worst_fdn = 0
    moved = 0
    for i, h in enumerate(heights):
        # Spread the four heights across the capsules, one scene per height on L
        # and a shared scene that places L/C/R on three of them.
        body = {
            "align_horizontal": False,
            "my_l": heights[i],
            "my_c": heights[(i + 1) % 4],
            "my_r": heights[(i + 2) % 4],
            "early_wet": 1.0,
        }
        _p, _prep, stand, taps = _stand(body)
        left, right = mic_positions(stand)
        centre = centre_position(stand)
        left_f, right_f, centre_f = fdn_reference_positions(stand)
        assert abs(left[1] - body["my_l"]) < 1e-9
        assert abs(right[1] - body["my_r"]) < 1e-9
        assert abs(centre[1] - body["my_c"]) < 1e-9
        assert abs(left_f[1] - stand.cy) < 1e-9
        assert abs(right_f[1] - stand.cy) < 1e-9
        assert abs(centre_f[1] - stand.cy) < 1e-9
        assert stand.cy == 1.5
        for t in taps:
            for cap, pos, fdn_pos, delay_ms, fdn_d in (
                ("l", left, left_f, t.delay_ms_l, t.fdn_distance_l),
                ("r", right, right_f, t.delay_ms_r, t.fdn_distance_r),
                ("c", centre, centre_f, t.delay_ms_c, t.fdn_distance_c),
            ):
                geom = dist(pos, t.position)
                expect = delay_ms_from_distance(geom, SPEED_OF_SOUND_M_S)
                got = int(round(delay_ms * 0.001 * SR))
                want = int(round(expect * 0.001 * SR))
                worst_image = max(worst_image, abs(got - want))
                fdn_geom = dist(fdn_pos, t.position)
                fdn_got = int(round(float(fdn_d) / SPEED_OF_SOUND_M_S * SR))
                fdn_want = int(round(fdn_geom / SPEED_OF_SOUND_M_S * SR))
                worst_fdn = max(worst_fdn, abs(fdn_got - fdn_want))
                if abs(fdn_got - got) > 1:
                    moved += 1
        delays = fdn_delays_from_taps(taps, sr=SR, c=SPEED_OF_SOUND_M_S, n=32, channel="l")
        flat_delays = []
        for k in range(32):
            t = taps[k % len(taps)]
            flat_delays.append(int(round(float(t.fdn_distance_l) / SPEED_OF_SOUND_M_S * SR)))
        assert delays == [max(2, min(int(round(1.0 * SR)), d)) for d in flat_delays]
    print("gate2 worst image samples", worst_image, "worst fdn samples", worst_fdn, "lines moved", moved)
    assert worst_image <= 1
    assert worst_fdn <= 1
    assert moved > 0


def test_b6_gate5_ms_and_binaural_ignore_heights():
    heights = {"my_l": 2.2, "my_r": 0.45, "my_c": 2.4, "align_horizontal": False}
    cases = {
        "ms_decode": {"ms_decode": True, "mic_setup": "ms_classic"},
        "ms_pair": {"pair_mode": "ms", "ms_m": "c", "ms_s": "l"},
        "binaural": {"mic_setup": "binaural"},
    }
    report = {}
    for name, base in cases.items():
        a, da = _live(base)
        b, db = _live(dict(base, **heights))
        same = da == db and json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
        short = {
            "decay_lock": False, "fdn_g": 0.8, "ir_length_ms": 200,
            "colour_mode": "BYPASS", "direct_wet": 1, "early_wet": 1, "fdn_wet": 1,
            "humidity": 0.0,
        }
        ir_a = _render(dict(short, **base), 200)
        ir_b = _render(dict(short, **base, **heights), 200)
        d = _maxabs(ir_a, ir_b)
        print("gate5", name, "live", same, "render maxabs", d)
        report[name] = {"live_identical": same, "render_maxabs": d}
        assert same
        assert d == 0.0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prev = {}
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    prev["gate5"] = report
    OUT.write_text(json.dumps(prev, indent=2), encoding="utf-8")


def _client():
    return json.loads(CLIENT.read_text(encoding="utf-8"))


def test_b6_gate3_tilt_tail_and_early():
    """Tilt 1.2 / 1.5 / 1.8 on the client standard body. Stop numbers are printed."""
    base = _client()
    base["align_horizontal"] = False
    # D20. The capture has mic_setup ortf and no centre key. The H-1 numbers are C on.
    base["third_mic"] = "centre"
    base["mic_gain_c"] = 1.0
    tilt = dict(base, my_l=1.2, my_r=1.8, my_c=1.5, align_horizontal=False)
    print("gate3 rendering flat", flush=True)
    flat = _render(base, 3000)
    print("gate3 rendering tilt", len(flat), flush=True)
    tipped = _render(tilt, 3000)
    n = min(len(flat), len(tipped))
    flat, tipped = flat[:n], tipped[:n]
    d0 = int(np.argmax(np.abs(flat).sum(1)[: int(0.05 * SR)]))
    early = slice(0, d0 + int(0.08 * SR))
    tail = slice(d0 + int(0.08 * SR), None)
    early_db = []
    tail_worst = 0.0
    tail_bands = {}
    for ch, name in ((0, "L"), (1, "R")):
        early_db.append(round(_energy_db(tipped[early, ch]) - _energy_db(flat[early, ch]), 4))
        delta = _bands(tipped[tail, ch]) - _bands(flat[tail, ch])
        tail_bands[name] = [round(float(v), 4) for v in delta]
        tail_worst = max(tail_worst, float(np.max(np.abs(delta))))
    direct = []
    for ch in (0, 1):
        direct.append([
            int(np.argmax(np.abs(flat[: int(0.05 * SR), ch]))),
            int(np.argmax(np.abs(tipped[: int(0.05 * SR), ch]))),
        ])
    print("gate3 early broadband L/R", early_db, "expect -0.69 / -0.46 ±0.3")
    print("gate3 tail worst", round(tail_worst, 4), "direct samples", direct)
    print("gate3 tail bands", json.dumps(tail_bands))
    row = {
        "early_broadband_L": early_db[0],
        "early_broadband_R": early_db[1],
        "tail_worst_abs_db": round(tail_worst, 4),
        "tail_bands": tail_bands,
        "direct_samples": {"L": direct[0], "R": direct[1]},
        "direct_index_flat": d0,
        "n": int(n),
    }
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev["gate3"] = row
    OUT.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    assert abs(early_db[0] - (-0.69)) <= 0.3
    assert abs(early_db[1] - (-0.46)) <= 0.3
    assert tail_worst <= 0.5


def test_b6_gate4_play_matches_render_tail():
    """Same tilt, colour bypass. Tail third-octaves within 0.1 dB."""
    sys.path[:0] = [
        str(ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"),
        str(ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"),
    ]
    import run_all as RA
    import types
    import tempfile

    node = os.environ.get(
        "RR_NODE",
        r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
    )
    work = Path(tempfile.mkdtemp(prefix="b6_play_"))
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=sys.executable, node=node,
        golden=str(ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "golden"),
        regen_golden=False, quick=False, perf_scale=1.0, workdir=str(work),
    ))
    body = _client()
    body.update({
        "align_horizontal": False,
        "my_l": 1.2, "my_c": 1.5, "my_r": 1.8,
        "colour_mode": "BYPASS",
        "direct_wet": 1.0, "early_wet": 1.0, "fdn_wet": 1.0,
        "phys_ceiling": False,
    })
    print("gate4 render", flush=True)
    rendered = _render(body, 2000)
    print("gate4 play", flush=True)
    played = ctx.play_ir(body, {"colour_on": False}, 2.0)
    n = min(len(rendered), len(played))
    rendered, played = rendered[:n], played[:n]
    d0 = int(np.argmax(np.abs(rendered).sum(1)[: int(0.05 * SR)]))
    tail = slice(d0 + int(0.08 * SR), None)
    worst = 0.0
    bands = {}
    for ch, name in ((0, "L"), (1, "R")):
        delta = _bands(played[tail, ch]) - _bands(rendered[tail, ch])
        bands[name] = [round(float(v), 4) for v in delta]
        worst = max(worst, float(np.max(np.abs(delta))))
    print("gate4 play-render tail worst", round(worst, 4), bands)
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    prev["gate4"] = {"tail_worst_abs_db": round(worst, 4), "bands": bands, "n": int(n)}
    OUT.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    assert worst <= 0.1
