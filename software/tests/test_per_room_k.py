"""PERROOMK. The decay dial is the mid T60 of this room when physics is on.

Boot k stays the three F13 floats. Other rooms solve their own k. Off and
unarmed preview replies stay the F13 bytes.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
HARNESS = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness"
sys.path[:0] = [str(SW), str(SW / "engine"), str(HARNESS), str(HARNESS / "lib")]
os.chdir(SW)

import app_server as A  # noqa: E402
import surf_loop as SLP  # noqa: E402
import surf_panels as SP  # noqa: E402
from surface_colour import default_surfaces  # noqa: E402

K_BOOT = {
    1.8: 0.7757907003265825,
    4.0: 0.333072595001391,
    8.0: 0.15200528288314788,
}
ROOMS = (
    ("boot", 6.0, 3.0, 8.0),
    ("small", 4.5, 2.8, 6.0),
    ("hall", 57.0, 34.2, 97.0),
    ("cube", 340.0 / 60.0, 340.0 / 60.0, 340.0 / 60.0),
    ("mid", 12.0, 5.0, 18.0),
)
DIALS = (1.8, 4.0, 8.0)
OFF_BYTES = {
    "off": b'{"ok":true,"on":false,"armed":true,"dial_s":1.8}',
    "unarmed": b'{"ok":true,"on":true,"armed":false,"dial_s":1.8}',
    "off_unlocked": b'{"ok":true,"on":false,"armed":false,"dial_s":0.2}',
}
OFF_BODIES = {
    "off": {"phys_ceiling": False, "decay_lock": True, "decay_s": 1.8},
    "unarmed": {"decay_lock": False, "decay_s": 1.8},
    "off_unlocked": {"phys_ceiling": False, "decay_lock": False, "decay_s": 0.2},
}


def _boot_cards():
    return SP.cards_with_treatment(default_surfaces(), [])


def _rel(got, dial):
    return abs(float(got) - float(dial)) / max(abs(float(dial)), 1e-12)


def test_boot_k_is_the_f13_floats():
    cards = _boot_cards()
    for dial, expect in K_BOOT.items():
        assert SLP.k_for_dial(dial) == expect
        assert SLP.k_for_room(6.0, 3.0, 8.0, cards, dial) == expect


def test_reachable_rooms_hit_the_dial():
    cards = _boot_cards()
    for name, w, h, l in ROOMS:
        for dial in DIALS:
            row = SLP.phys_ceiling_row(w, h, l, cards, dial)
            assert np.isfinite(row["k"]) and np.isfinite(row["mid"])
            if row["reachable"]:
                assert _rel(row["mid"], dial) <= 0.005, (name, dial, row["mid"], row["k"])


def test_a_louder_card_moves_k_and_keeps_the_dial():
    base = _boot_cards()
    loud_surfaces = default_surfaces()
    loud_surfaces["A"]["absorb"] = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    loud = SP.cards_with_treatment(loud_surfaces, [])
    k0 = SLP.k_for_room(6.0, 3.0, 8.0, base, 1.8)
    k1 = SLP.k_for_room(6.0, 3.0, 8.0, loud, 1.8)
    assert k1 != k0
    row = SLP.phys_ceiling_row(6.0, 3.0, 8.0, loud, 1.8)
    assert row["reachable"] is True
    assert _rel(row["mid"], 1.8) <= 0.005


def test_unreachable_dials_stay_finite():
    cards = _boot_cards()
    closet = SLP.phys_ceiling_row(2.0, 2.0, 2.0, cards, 8.0)
    hall = SLP.phys_ceiling_row(57.0, 34.2, 97.0, cards, 0.3)
    for row in (closet, hall):
        assert row["reachable"] is False
        assert np.isfinite(row["k"]) and np.isfinite(row["mid"]) and np.isfinite(row["reached_mid"])


def test_phys_preview_hall_and_off_bytes():
    client = TestClient(A.app)
    for name, body in OFF_BODIES.items():
        got = client.post("/api/phys_preview", json=body).content
        assert got == OFF_BYTES[name], (name, got)
    for dial in (4.0, 8.0):
        data = client.post("/api/phys_preview", json={
            "W": 57, "H": 34.2, "L": 97, "decay_lock": True, "decay_s": dial,
        }).json()
        assert data["on"] is True and data["reachable"] is True
        assert _rel(data["mean_500_1k"], dial) <= 0.005
    short = client.post("/api/phys_preview", json={
        "W": 57, "H": 34.2, "L": 97, "decay_lock": True, "decay_s": 1.8,
    }).json()
    assert short["reachable"] is False
    assert np.isfinite(short["mean_500_1k"]) and np.isfinite(short["k"])


def _ctx():
    import run_all as RA
    node = Path(os.environ.get(
        "RR_NODE",
        r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v26.7.0-win-x64\node.exe",
    ))
    work = Path(os.environ["TEMP"]) / "perroomk_unit"
    work.mkdir(parents=True, exist_ok=True)
    return RA.Ctx(types.SimpleNamespace(
        sw=str(SW),
        python=str(SW / ".venv" / "Scripts" / "python.exe"),
        node=str(node),
        golden=str(HARNESS / "golden"),
        regen_golden=False,
        quick=False,
        perf_scale=1.0,
        workdir=str(work),
    ))


def _mid_t30(x, sr=48000):
    from analyze import t60_bands
    vals = []
    for ch in (0, 1):
        row = t60_bands(np.asarray(x[:, ch], dtype=np.float64), sr, bands=[500, 1000])
        vals.append(float(row[500]))
        vals.append(float(row[1000]))
    return float(np.mean(vals)), vals


def test_hall_dial8_render_matches_play():
    """One source, hall, dial 8, key absent. 500 Hz and 1 kHz T30 within 10 %."""
    body = {
        "W": 57.0, "H": 34.2, "L": 97.0,
        "sx": 24.0, "sz": 60.0, "mcx": 28.5, "mcz": 30.0,
        "decay_lock": True, "decay_s": 8.0,
        "two_sources": False,
        "fdn_wet": 1.0, "direct_wet": 0.0, "early_wet": 0.0,
        "colour_mode": "BYPASS",
    }
    ctx = _ctx()
    play = ctx.play_ir(body, {"colour_on": False}, 12.0)
    rend = ctx.render_ir(body, 12000)
    pm, pvals = _mid_t30(play)
    rm, rvals = _mid_t30(rend)
    assert np.isfinite(pm) and np.isfinite(rm), (pm, rm, pvals, rvals)
    assert _rel(pm, 8.0) <= 0.10, (pm, pvals)
    assert _rel(rm, 8.0) <= 0.10, (rm, rvals)
    assert abs(pm - rm) / max(pm, rm) <= 0.10, (pm, rm, pvals, rvals)
