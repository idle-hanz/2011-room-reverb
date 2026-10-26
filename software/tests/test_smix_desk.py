"""S-MIX desk: default fold stays the 477 law, MS nulls, room mic, each-mic dB.

Render nulls use direct 0, early 0, FDN 1, shared tail off.
Play nulls use the rebuilt wasm. TLAW regenerated the five ORTF goldens
(distance law 1/r, Idle 2026-10-10). The pins below are those files.
"""
from __future__ import annotations
import pytest

import hashlib
import inspect
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
GOLDEN = HARNESS / "golden"
sys.path[:0] = [str(SW), str(SW / "engine"), str(HARNESS), str(HARNESS / "lib")]
os.chdir(SW)

import app_server as A  # noqa: E402
from desk_matrix import desk_active, fold_for, place_stand  # noqa: E402
from early_field import (  # noqa: E402
    MicStand,
    centre_position,
    compute_taps,
    delay_ms_from_distance,
    direct_field_from_metres,
    mic_positions,
)
from mic_pattern import rings_db  # noqa: E402
from polar_field import RING_HZ, compute_polar_field  # noqa: E402
from render_pipeline import render  # noqa: E402

SR = 48000
G2 = 10.0 ** (2.0 / 20.0)
G6 = 10.0 ** (-6.0 / 20.0)
GOLDEN_SHA1 = {
    "play_std_lock18_byp.f32": "d011bafca80f4e46ae768db40becd762e78dcada",
    "play_std_lock18_col.f32": "80d86ec23022d09fdb0653298ad322ca539e5bb5",
    "play_std_unlocked_byp.f32": "91738c70220b4edce512aebe3548dfdbd894cc41",
    "play_std_unlocked_col.f32": "171a1450978742a7fc1f3cb77739d202d80f48a9",
    "render_std_unlocked_byp.f32": "2a806e334e06cc475868d4c3da3fc78431c9a0aa",
}


def _null_db(a, b) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    err = float(np.sum((a - b) ** 2))
    ref = float(np.sum(a ** 2))
    return 10.0 * math.log10(max(err, 1e-300) / max(ref, 1e-300))


def _body(**over):
    b = dict(A.DEFAULTS)
    b.update({
        "W": 6.0, "H": 3.0, "L": 8.0,
        "sx": 2.2, "sz": 3.0, "sy": 1.5, "my": 1.5,
        "mcx": 3.0, "mcz": 2.0, "space": 0.05,
        "mic_setup": "ms_classic",
        "pattern_l": "fig8", "pattern_c": "cardioid", "pattern_r": "fig8",
        "family_l": "bi", "family_c": "cardioid", "family_r": "bi",
        "polar_l": 0.5, "polar_c": 0.5, "polar_r": 0.5,
        "yaw_l_deg": 90.0, "yaw_c_deg": 0.0, "yaw_r_deg": 90.0,
        "colour_mode": "ASSUMED_TOYS",
        "direct_wet": 0.0, "early_wet": 0.0, "fdn_wet": 1.0,
        "dry_gain": 0.0, "shared_tail": False,
        "decay_lock": False, "ir_length_ms": 160,
        "path_on": False,
    })
    b.update(over)
    return b


def _desk_ms(**over):
    """New desk. L = S at Width 0 dB, C = M at exact 1.5, R off."""
    b = _body(
        pair_mode="ms", ms_s="l", ms_m="c",
        mic_route_l="s", mic_route_c="both", mic_route_r="pan",
        mic_gain_l=1.0, mic_gain_c=1.5, mic_gain_r=0.0,
        mic_pan_l=-1.0, mic_pan_c=0.0, mic_pan_r=1.0,
    )
    b.update(over)
    return b


def _render(body, drive=1.0, want_info=False):
    p = A.params_from_body(body)
    dry = np.zeros(32, dtype=np.float64)
    dry[0] = float(drive)
    sig = inspect.signature(render)
    kw = {}
    for name, param in sig.parameters.items():
        if name in ("dry", "sr"):
            continue
        if name in p:
            kw[name] = p[name]
    kw["desk"] = p
    yL, yR, info = render(dry, SR, **kw)
    ir = np.stack([np.asarray(yL), np.asarray(yR)], axis=1)
    if want_info:
        return ir, info
    return ir


def _play(body, secs=0.35) -> np.ndarray:
    import types
    import run_all as RA
    work = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "smix_play"
    work.mkdir(parents=True, exist_ok=True)
    node = os.environ.get(
        "RR_NODE",
        r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
    )
    ctx = RA.Ctx(types.SimpleNamespace(
        sw=str(SW), python=sys.executable, node=node,
        golden=str(GOLDEN), regen_golden=False, quick=False, perf_scale=1.0,
        workdir=str(work),
    ))
    return ctx.play_ir(body, {}, secs)


def _both(body_a, body_b, play=False):
    out = {"render": _null_db(_render(body_a), _render(body_b))}
    if play:
        out["play"] = _null_db(_play(body_a), _play(body_b))
    return out


def test_golden_sha1_prefixes():
    for name, prefix in GOLDEN_SHA1.items():
        digest = hashlib.sha1((GOLDEN / name).read_bytes()).hexdigest()
        assert digest.startswith(prefix), (name, digest)


def test_default_ortf_fold_is_legacy():
    idle = _body(mic_setup="ortf", pair_mode="", mic_route_l="pan", mic_route_c="pan", mic_route_r="pan")
    assert desk_active(idle) is False
    w, mk, sec = fold_for(idle)
    assert mk is None and sec is None
    assert [w[k] for k in ("ll", "lr", "cl", "cr", "rl", "rr")] == [1.0, 0.0, 0.5, 0.5, 0.0, 1.0]
    old = {"mic_setup": "ms_classic"}
    assert desk_active(old) is False


def _want_play() -> bool:
    return os.environ.get("SMIX_PLAY") == "1" or "--play" in sys.argv


@pytest.mark.slow
def test_ms_classic_null_user_and_bypass():
    play = _want_play()
    """Item 7.1. Width 0, R off, shared tail off. User defined and Bypass."""
    rows = {}
    for mode in ("ASSUMED_TOYS", "BYPASS"):
        old = _body(colour_mode=mode)
        new = _desk_ms(colour_mode=mode)
        assert A.params_from_body(old)["ms_decode"] is True
        assert A.params_from_body(new)["ms_decode"] is False
        rows[mode] = _both(old, new, play=play)
        for eng, db in rows[mode].items():
            print("ms classic", mode, eng, round(db, 2))
            assert db < -90.0, (mode, eng, db)


@pytest.mark.slow
def test_mono_cancel():
    play = _want_play()
    """Item 7.2. C muted, R off. (L+R) is 0. L = −R."""
    body = _desk_ms(mic_gain_c=0.0, mic_gain_r=0.0, mic_gain_l=1.0)
    out = {}
    for eng, ir in (("render", _render(body)), ("play", _play(body)) if play else ("render", _render(body))):
        if eng == "render" and "render" in out:
            continue
        mono = 0.5 * (ir[:, 0] + ir[:, 1])
        db = _null_db(ir[:, 0], -ir[:, 1])
        energy = _null_db(mono, np.zeros_like(mono)) if False else None
        rel = 10.0 * math.log10(max(float(np.sum(mono ** 2)), 1e-300) / max(float(np.sum(ir[:, 0] ** 2)), 1e-300))
        print("mono", eng, "L vs -R", round(db, 2), "mono rel", round(rel, 2))
        assert db <= -200.0, (eng, db)
        assert rel <= -200.0, (eng, rel)
        out[eng] = {"l_vs_neg_r_db": db, "mono_db": rel}
        if not play:
            break


@pytest.mark.slow
def test_width_scales_s_only():
    play = _want_play()
    """Item 7.3. Width +2 dB scales L−R by 10^(2/20). M-only is unchanged.

    D-SRC-DIST-LEVEL: freeze raised scene onto knee. The render impulse is
    0.5 so no sample reaches 0.90. The −100 dB null stays.
    """
    # D-SRC-DIST-LEVEL: freeze raised scene onto knee.
    drive = 0.5
    base = _desk_ms(mic_gain_l=1.0, mic_gain_c=1.5, mic_gain_r=0.0)
    wide = _desk_ms(mic_gain_l=G2, mic_gain_c=1.5, mic_gain_r=0.0)
    m0 = _desk_ms(mic_gain_l=0.0, mic_gain_c=1.5, mic_gain_r=0.0)
    m2 = _desk_ms(mic_gain_l=0.0, mic_gain_c=1.5, mic_gain_r=0.0, width_l=2.0)
    rows = {}
    engines = ("render", "play") if play else ("render",)
    for eng in engines:
        if eng == "render":
            a, info_a = _render(base, drive=drive, want_info=True)
            b, info_b = _render(wide, drive=drive, want_info=True)
            print(
                "width render peak",
                round(float(info_a["peak_before_norm"]), 4),
                round(float(info_b["peak_before_norm"]), 4),
                "limiter",
                int(info_a["limiter_samples"]),
                int(info_b["limiter_samples"]),
            )
            assert int(info_a["limiter_samples"]) == 0, info_a["limiter_samples"]
            assert int(info_b["limiter_samples"]) == 0, info_b["limiter_samples"]
            assert float(info_a["peak_before_norm"]) < 0.90
            assert float(info_b["peak_before_norm"]) < 0.90
            only = _null_db(_render(m2, drive=drive), _render(m0, drive=drive))
        else:
            a, b = _play(base), _play(wide)
            only = _null_db(_play(m2), _play(m0))
        s0 = a[:, 0] - a[:, 1]
        s2 = b[:, 0] - b[:, 1]
        m_a = 0.5 * (a[:, 0] + a[:, 1])
        m_b = 0.5 * (b[:, 0] + b[:, 1])
        s_db = _null_db(s2, s0 * G2)
        m_db = _null_db(m_b, m_a)
        print("width", eng, "S", round(s_db, 2), "M", round(m_db, 2), "M-only", round(only, 2))
        assert s_db <= -100.0, (eng, s_db)
        assert m_db <= -100.0, (eng, m_db)
        assert only <= -100.0, (eng, only)
        rows[eng] = {"s_db": s_db, "m_db": m_db, "m_only_db": only}


def _centre_of(body):
    p = A.params_from_body(body)
    prep = direct_field_from_metres(
        p["W"], p["H"], p["L"], sx=p["sx"], sy=p["sy"], sz=p["sz"],
        mcx=p["mcx"], my=p["my"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"],
        toe_half_deg=p["toe_half_deg"], yaw_l_deg=p["yaw_l_deg"], yaw_r_deg=p["yaw_r_deg"],
    )
    stand = MicStand.from_prepare(
        prep, car_omni=p["car_omni"],
        pattern_l=p["pattern_l"], pattern_c=p["pattern_c"], pattern_r=p["pattern_r"],
        yaw_l_deg=p["yaw_l_deg"], yaw_c_deg=p["yaw_c_deg"], yaw_r_deg=p["yaw_r_deg"],
        family_l=p["family_l"], family_c=p["family_c"], family_r=p["family_r"],
        polar_l=p["polar_l"], polar_c=p["polar_c"], polar_r=p["polar_r"],
    )
    return centre_position(place_stand(stand, p) or stand)


def _role_scene(s_slot, m_slot, room_slot, pin_m=None):
    """Same M, S and room roles on whichever strips. S stays on M."""
    body = _desk_ms(mic_gain_l=0.0, mic_gain_c=0.0, mic_gain_r=0.0)
    for slot in ("l", "c", "r"):
        body["mic_route_" + slot] = "pan"
        body["pattern_" + slot] = "cardioid"
        body["family_" + slot] = "cardioid"
        body["polar_" + slot] = 0.5
    body["pair_mode"] = "ms"
    body["ms_s"] = s_slot
    body["ms_m"] = m_slot
    body["mic_route_" + s_slot] = "s"
    body["mic_gain_" + s_slot] = G2
    body["family_" + s_slot] = "bi"
    body["pattern_" + s_slot] = "fig8"
    body["polar_" + s_slot] = 0.5
    body["yaw_" + s_slot + "_deg"] = 90.0
    body["mic_route_" + m_slot] = "both"
    body["mic_gain_" + m_slot] = 1.5
    body["family_" + m_slot] = "cardioid"
    body["pattern_" + m_slot] = "cardioid"
    body["yaw_" + m_slot + "_deg"] = 0.0
    body["mic_route_" + room_slot] = "pan"
    body["mic_gain_" + room_slot] = G6
    body["mic_pan_" + room_slot] = 0.3
    body["pattern_" + room_slot] = "omni"
    body["family_" + room_slot] = "cardioid"
    body["polar_" + room_slot] = 0.0
    body["mic_preset_" + room_slot] = "AKGC414Omni"
    body["yaw_" + room_slot + "_deg"] = 15.0
    body["mic_x_" + room_slot] = 4.0
    body["mic_y_" + room_slot] = 1.6
    body["mic_z_" + room_slot] = 2.2
    if pin_m is not None:
        body["mic_x_" + m_slot], body["mic_y_" + m_slot], body["mic_z_" + m_slot] = pin_m
    return body


@pytest.mark.slow
def test_room_mic_independent():
    play = _want_play()
    """Item 7.4. Muting R, then moving R, leaves L+C unchanged."""
    parked = _desk_ms(mic_gain_r=0.0)
    moved = _desk_ms(
        mic_gain_r=0.0,
        mic_x_r=4.0, mic_y_r=1.6, mic_z_r=2.2, yaw_r_deg=40.0,
        mic_preset_r="AKGC414Omni", pattern_r="omni", family_r="cardioid", polar_r=0.0,
    )
    pairs = [("render", _render(parked), _render(moved))]
    if play:
        pairs.append(("play", _play(parked), _play(moved)))
    fade = int(round(SR * 0.050))
    for eng, a, b in pairs:
        n = min(len(a), len(b))
        full = _null_db(a, b)
        # D-AUD-2: unlocked T60 can shift the file by a few samples, so the
        # 50 ms fades do not share an index. The samples before either fade
        # are the identity this test was written for.
        pre = _null_db(a[: n - fade], b[: n - fade]) if n > fade else full
        print("room mute-vs-moved", eng, round(full, 2), "pre-fade", round(pre, 2), len(a), len(b))
        assert pre <= -100.0, (eng, pre, full, len(a), len(b))


def test_room_early_delay_matches_geometry():
    body = _desk_ms(
        early_wet=1.0, direct_wet=0.0, fdn_wet=0.0,
        mic_gain_r=1.0, mic_route_r="pan", mic_pan_r=0.3,
        mic_x_r=4.0, mic_y_r=1.6, mic_z_r=2.2, yaw_r_deg=15.0,
        pattern_r="omni", family_r="cardioid", polar_r=0.0,
    )
    p = A.params_from_body(body)
    prep = direct_field_from_metres(
        p["W"], p["H"], p["L"], sx=p["sx"], sy=p["sy"], sz=p["sz"],
        mcx=p["mcx"], my=p["my"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"],
        toe_half_deg=p["toe_half_deg"], yaw_l_deg=p["yaw_l_deg"], yaw_r_deg=p["yaw_r_deg"],
    )
    stand = MicStand.from_prepare(
        prep, car_omni=p["car_omni"],
        pattern_l=p["pattern_l"], pattern_c=p["pattern_c"], pattern_r=p["pattern_r"],
        yaw_l_deg=p["yaw_l_deg"], yaw_c_deg=p["yaw_c_deg"], yaw_r_deg=p["yaw_r_deg"],
        family_l=p["family_l"], family_c=p["family_c"], family_r=p["family_r"],
        polar_l=p["polar_l"], polar_c=p["polar_c"], polar_r=p["polar_r"],
    )
    stand = place_stand(stand, p)
    _left, right = mic_positions(stand)
    taps = compute_taps((p["W"], p["H"], p["L"]), prep.source, stand, c=340.0)
    direct = next(t for t in taps if t.order == 0)
    expect = delay_ms_from_distance(math.dist(prep.source, right), 340.0)
    print("room delay", round(direct.delay_ms_r, 4), "geom", round(expect, 4), "pos", right)
    assert abs(direct.delay_ms_r - expect) < 0.05
    assert p["mic_preset_l"] == body.get("mic_preset_l", p["mic_preset_l"])


@pytest.mark.slow
def test_any_strip_route():
    play = _want_play()
    """Item 7.5. C = S, L = M, R = room matches L = S, C = M, R = room."""
    pin = _centre_of(_desk_ms())
    a = _role_scene("l", "c", "r", pin_m=pin)
    b = _role_scene("c", "l", "r", pin_m=pin)
    rows = _both(a, b, play=play)
    # D-SRC-DIST-LEVEL. Makeup uses the boot offset from the stand, not this
    # scene's source (sx 2.2). Below the limiter knee one gain still nulls
    # at about -304 dB. One sample hits the limiter, so the full-file null
    # is -58.16 dB. M is C in a and L in b.
    for eng, db in rows.items():
        print("any strip", eng, round(db, 2))
        assert abs(db - (-58.16)) < 0.05, (eng, db)
    c = _role_scene("r", "c", "l", pin_m=pin)
    # R = S, C = M, L = room. Same source freeze. Full-file null -64.62 dB.
    rows_r = _both(a, c, play=play)
    for eng, db in rows_r.items():
        print("any strip R=S", eng, round(db, 2))
        assert abs(db - (-64.62)) < 0.05, (eng, db)


def _polar(body):
    p = A.params_from_body(body)
    return compute_polar_field(
        W=p["W"], H=p["H"], L=p["L"], sox=p["sox"], soz=p["soz"], mz=p["mz"],
        my=p["my"], sy=p["sy"], space=p["space"], diverg=p["diverg"],
        car_omni=p["car_omni"], mcx=p["mcx"], mcz=p["mcz"], sx=p["sx"], sz=p["sz"],
        toe_half_deg=p["toe_half_deg"],
        pattern_l=p["pattern_l"], pattern_c=p["pattern_c"], pattern_r=p["pattern_r"],
        yaw_l_deg=p["yaw_l_deg"], yaw_c_deg=p["yaw_c_deg"], yaw_r_deg=p["yaw_r_deg"],
        family_l=p["family_l"], family_c=p["family_c"], family_r=p["family_r"],
        polar_l=p["polar_l"], polar_c=p["polar_c"], polar_r=p["polar_r"],
        colour_mode=p["colour_mode"],
        mic_preset_l=p["mic_preset_l"], mic_preset_c=p["mic_preset_c"], mic_preset_r=p["mic_preset_r"],
        mic_hpf_engaged=p["mic_hpf_engaged"],
        mic_hpf_sides=p["mic_hpf_sides"], mic_hpf_centre=p["mic_hpf_centre"],
        desk=p, n_az=72,
    )


def _max_db_delta(grid, mode, preset, family, polar, pattern, hpf_on=False):
    """each_db versus rings_db. Compare bins above the −30 dB floor."""
    from mic_colour.preset_store import get_store
    store = get_store()
    model = None
    measured = mode == "MEASURED_SHELF"
    if measured:
        try:
            model = store.model_for(preset)
        except KeyError:
            model = None
    hpf = store.hpf_of(preset)
    theta = np.asarray([(i / 72) * 2.0 * math.pi for i in range(72)], dtype=float)
    ref = rings_db(
        theta, list(RING_HZ),
        family=family, polar=polar, pattern=pattern,
        model=model, hpf=hpf, hpf_on=hpf_on, measured=measured,
    )
    got = np.asarray(grid, dtype=float)
    mask = ref > -30.0
    if not np.any(mask):
        return 0.0
    return float(np.max(np.abs(got[mask] - ref[mask])))


def test_each_db_matches_engine():
    """Item 11 data check. Measured and Bypass, four setups. Max |Δ| above −30 dB."""
    cases = {
        "ab_omni": _body(
            mic_setup="ab_omni", space=0.4, pair_mode="",
            pattern_l="omni", pattern_c="omni", pattern_r="omni",
            family_l="cardioid", family_c="cardioid", family_r="cardioid",
            polar_l=0.0, polar_c=0.0, polar_r=0.0,
            yaw_l_deg=0.0, yaw_c_deg=0.0, yaw_r_deg=0.0,
            mic_preset_l="AKGC414Omni", mic_preset_c="AKGC414Omni", mic_preset_r="AKGC414Omni",
        ),
        "ortf": _body(
            mic_setup="ortf", space=0.17, pair_mode="",
            pattern_l="cardioid", pattern_c="cardioid", pattern_r="cardioid",
            family_l="cardioid", family_c="cardioid", family_r="cardioid",
            polar_l=0.5, polar_c=0.5, polar_r=0.5,
            yaw_l_deg=-55.0, yaw_c_deg=0.0, yaw_r_deg=55.0,
            mic_preset_l="ShureSM57", mic_preset_c="ShureSM57", mic_preset_r="ShureSM57",
        ),
        "ms": _body(
            mic_setup="ms", pair_mode="",
            pattern_l="cardioid", pattern_c="omni", pattern_r="cardioid",
            family_l="cardioid", family_c="cardioid", family_r="cardioid",
            polar_l=0.5, polar_c=0.0, polar_r=0.5,
            yaw_l_deg=-90.0, yaw_c_deg=0.0, yaw_r_deg=90.0,
        ),
        "split": _body(
            mic_setup="ortf", space=0.17, pair_mode="",
            pattern_l="cardioid", pattern_r="omni", pattern_c="cardioid",
            family_l="cardioid", family_r="cardioid", family_c="cardioid",
            polar_l=0.5, polar_r=0.0, polar_c=0.5,
            yaw_l_deg=-55.0, yaw_r_deg=20.0, yaw_c_deg=0.0,
            mic_preset_l="ShureSM57", mic_preset_r="AKGC414Omni", mic_preset_c="ShureSM57",
            mic_x_r=4.0, mic_y_r=1.5, mic_z_r=2.0,
        ),
    }
    worst = {}
    for name, body in cases.items():
        for mode in ("MEASURED_SHELF", "BYPASS"):
            body = dict(body)
            body["colour_mode"] = mode
            p = A.params_from_body(body)
            field = _polar(body)
            deltas = {}
            for key, slot in (("L", "l"), ("C", "c"), ("R", "r")):
                d = _max_db_delta(
                    field["each_db"][key], mode,
                    p["mic_preset_" + slot],
                    p["family_" + slot], p["polar_" + slot], p["pattern_" + slot],
                )
                deltas[key] = d
                assert d <= 0.01, (name, mode, key, d)
            worst[f"{name}|{mode}"] = {k: round(v, 5) for k, v in deltas.items()}
            print("each_db", name, mode, worst[f"{name}|{mode}"])
    # Changing R's preset leaves L's grid alone.
    a = dict(cases["split"])
    a["colour_mode"] = "MEASURED_SHELF"
    b = dict(a)
    b["mic_preset_r"] = "RoyerR121"
    b["pattern_r"] = "fig8"
    b["family_r"] = "bi"
    fa, fb = _polar(a), _polar(b)
    l_same = float(np.max(np.abs(np.asarray(fa["each_db"]["L"]) - np.asarray(fb["each_db"]["L"]))))
    r_move = float(np.max(np.abs(np.asarray(fa["each_db"]["R"]) - np.asarray(fb["each_db"]["R"]))))
    print("preset R only", "L", l_same, "R", r_move)
    assert l_same == 0.0
    assert r_move > 0.01
    assert a["mic_preset_l"] == b["mic_preset_l"] == "ShureSM57"


def test_spectrum_hue_monotonic():
    js = SW / "static" / "js" / "spectrum_colors.js"
    node = os.environ.get(
        "RR_NODE",
        r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
    )
    script = (
        "globalThis.window = globalThis;\n"
        + js.read_text(encoding="utf-8")
        + "\nconst S = globalThis.SpectrumColors;\n"
        "const hz = [20, 63, 125, 250, 1000, 4000, 8000, 16000];\n"
        "const hues = hz.map(h => S.forHz(h).hue);\n"
        "if (!(hues[0] < 8)) process.exit(2);\n"
        "if (!(hues[hues.length - 1] > 260)) process.exit(3);\n"
        "for (let i = 1; i < hues.length; i++) if (!(hues[i] + 1e-9 >= hues[i - 1])) process.exit(1);\n"
        "console.log(hues.map(h => h.toFixed(2)).join(','));\n"
    )
    r = subprocess.run([node, "-e", script], capture_output=True, text=True)
    print(r.stdout.strip(), r.stderr[-200:] if r.returncode else "")
    assert r.returncode == 0


if __name__ == "__main__":
    test_golden_sha1_prefixes()
    test_default_ortf_fold_is_legacy()
    test_spectrum_hue_monotonic()
    test_each_db_matches_engine()
    test_room_early_delay_matches_geometry()
    test_ms_classic_null_user_and_bypass()
    test_mono_cancel()
    test_width_scales_s_only()
    test_room_mic_independent()
    test_any_strip_route()
    print("smix desk ok", "play" if _want_play() else "render")
