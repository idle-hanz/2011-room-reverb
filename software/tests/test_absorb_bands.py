"""Per-band absorption. Flat 0.9 and a shaped curve, Play and Render."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from engine.early_field import MicStand, compute_taps, direct_field_from_params  # noqa: E402
from render_pipeline import (  # noqa: E402
    DEFAULT_DEPTH,
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    _place_stand,
    cascade_biquads,
    live_fdn_params,
    render_early_ir,
)
from surface_colour import (  # noqa: E402
    ABSORB_BAND_HZ,
    default_surfaces,
    parse_surfaces,
    third_octave_levels,
)

SR = SAMPLE_RATE_HZ
SHAPE = (0.90, 0.75, 0.50, 0.25, 0.08, 0.02, 0.02)
FLAT_DB = 10.0 * math.log10((1.0 - 0.9) / (1.0 - 0.02))
# Other cards stay flat at 0.02 so the soloed card is the only shape.
_REF = 0.02


def _expect_shape():
    ref = 1.0 - _REF
    return [10.0 * math.log10((1.0 - a) / ref) for a in SHAPE]


def _surfaces(letter, absorb, shelf_db=0.0):
    surfaces = default_surfaces()
    for card in surfaces.values():
        card["absorb"] = [_REF] * 7
    surfaces[letter]["absorb"] = [float(x) for x in absorb]
    if shelf_db:
        surfaces[letter]["eq"]["high_shelf_db"] = float(shelf_db)
    return surfaces


def _body(letter, absorb, shelf_db=0.0):
    return {
        "surfaces_solo": letter,
        "surfaces": _surfaces(letter, absorb, shelf_db),
    }


def _bands(ir):
    raw = third_octave_levels(np.asarray(ir, dtype=np.float64), SR, centres=list(ABSORB_BAND_HZ))
    return [float(x) for x in raw["levels_db_abs"]]


def _delta(hi, lo):
    return [a - b for a, b in zip(hi, lo)]


def _line_coefs(tail, line):
    if not tail:
        return []
    kmax = int(round(float(tail[1])))
    stride = 1 + 5 * kmax
    base = 2 + int(line) * stride
    k = int(round(float(tail[base])))
    coefs = []
    for s in range(k):
        o = base + 1 + 5 * s
        b0, b1, b2, a1, a2 = tail[o:o + 5]
        coefs.append((float(b0), float(b1), float(b2), 1.0, float(a1), float(a2)))
    return coefs


def _play_early(body):
    p = A.params_from_body(body)
    live = live_fdn_params(p, SR)
    n = int(SR * 0.25) + 8
    acc_l = np.zeros(n, dtype=np.float64)
    acc_r = np.zeros(n, dtype=np.float64)
    gate = live.get("early_gate") or [1.0] * 192
    tail = live.get("surf_cascade")
    for ch, buf, gate0 in (("l", acc_l, 0), ("r", acc_r, 128)):
        bus = live["buses"][ch]
        for i in range(32):
            if float(gate[gate0 + i]) == 0.0:
                continue
            spike = np.zeros(n, dtype=np.float64)
            spike[0] = float(bus["inject"][i])
            coefs = _line_coefs(tail, i)
            if coefs:
                spike = cascade_biquads(spike, coefs)
            k = int(round(float(bus["delay_ms"][i]) * SR / 1000.0))
            if k < 0 or k >= n:
                continue
            buf[k:] += spike[: n - k]
    return acc_l + acc_r


def _render_early(body):
    p = A.params_from_body(body)
    room = (float(p["W"]), float(p["H"]), float(p["L"]))
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
    stand = _place_stand(stand, p)
    taps = compute_taps(
        room, prep.source, stand, c=SPEED_OF_SOUND_M_S, grid="32", origin="corner",
        hadamard_n=32,
        include_offaxis_shelf=True,
        include_pattern=True,
    )
    surfaces = parse_surfaces(p.get("surfaces"))
    left, right = render_early_ir(
        taps, room, SR, SPEED_OF_SOUND_M_S, 250.0, DEFAULT_DEPTH, 0.0, None, {},
        surfaces=surfaces,
        mic_left=prep.mic_left,
        mic_right=prep.mic_right,
        colour=None,
        early_toys=False,
        surfaces_solo=p.get("surfaces_solo"),
    )
    n = int(SR * 0.25) + 8
    return np.asarray(left[:n], dtype=np.float64) + np.asarray(right[:n], dtype=np.float64)


def _pair(letter, absorb, shelf_db=0.0):
    body_hi = _body(letter, absorb, shelf_db)
    body_lo = _body(letter, [_REF] * 7, 0.0)
    play = _delta(_bands(_play_early(body_hi)), _bands(_play_early(body_lo)))
    render = _delta(_bands(_render_early(body_hi)), _bands(_render_early(body_lo)))
    return play, render


def test_flat_solo_is_minus_9_9_on_every_band():
    play, render = _pair("D", [0.9] * 7)
    for path in (play, render):
        for got in path:
            assert got == pytest.approx(FLAT_DB, abs=0.3)
    for a, b in zip(play, render):
        assert a == pytest.approx(b, abs=0.5)


def test_shaped_curve_follows_sqrt_per_band():
    play, render = _pair("D", SHAPE)
    expect = _expect_shape()
    for path in (play, render):
        for got, want in zip(path, expect):
            assert got == pytest.approx(want, abs=0.5)
    for a, b in zip(play, render):
        assert a == pytest.approx(b, abs=0.5)


def test_eq_shelf_follows_the_absorb():
    """A +6 dB high shelf still sits after the absorb scalar."""
    bare_p, bare_r = _pair("D", [0.5] * 7, 0.0)
    shelf_p, shelf_r = _pair("D", [0.5] * 7, 6.0)
    # 8 kHz is the last absorb band. The 5 kHz shelf must lift it.
    assert shelf_p[-1] - bare_p[-1] > 2.0
    assert shelf_r[-1] - bare_r[-1] > 2.0
    for a, b in zip(shelf_p, shelf_r):
        assert a == pytest.approx(b, abs=0.5)
