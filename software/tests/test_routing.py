"""Routing R1. Buses stay separate until the fold. Master Room Crush is one Bloom call."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

SW = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import bloom_dsp as B  # noqa: E402
from fdn import apply_capsule_weights  # noqa: E402
from render_pipeline import _apply_chain, _route_buses  # noqa: E402

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"
PAGE = {
    "bloom_preset": "room_crush",
    "bloom_amount": 100,
    "bloom_colour": False,
    "glue_colour": False,
    "pre_colour": "off",
    "pre_drive_db": 0.0,
    "predelay_ms": 0.0,
    "bloom_attack_scale": 1.0,
    "bloom_release_scale": 1.0,
}


def _md5(body: dict) -> str:
    blob = A.live_fdn_params(A.params_from_body(body))
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _buses(rng, n=128):
    return {k: rng.normal(size=n) for k in ("l", "c", "r")}


def test_fold_is_linear_so_the_buses_stay_separable():
    rng = np.random.default_rng(0)
    L, C, R = (rng.normal(size=64) for _ in range(3))
    w = {"ll": 0.7, "lr": 0.2, "cl": 0.5, "cr": 0.5, "rl": 0.1, "rr": 0.8}
    full_l, full_r = apply_capsule_weights(L, C, R, w)
    array_l, array_r = apply_capsule_weights(L, np.zeros_like(C), R, w)
    room_l, room_r = apply_capsule_weights(np.zeros_like(L), C, np.zeros_like(R), w)
    assert np.max(np.abs(full_l - (array_l + room_l))) < 1e-12
    assert np.max(np.abs(full_r - (array_r + room_r))) < 1e-12


def test_master_room_crush_is_one_bloom_call():
    spec = B.design(PAGE, 48000)
    rng = np.random.default_rng(0)
    det = rng.normal(size=128)
    via = _buses(rng)
    direct = {k: v.copy() for k, v in via.items()}
    _apply_chain(via, det, spec)
    B.apply_fdn_buses(direct, det, spec)
    for k in ("l", "c", "r"):
        assert np.max(np.abs(via[k] - direct[k])) == 0.0


def test_master_neve_is_one_bloom_call():
    spec = B.design({"bloom_preset": "natural", "bloom_amount": 0, "pre_colour": "neve1073", "pre_drive_db": 6}, 48000)
    rng = np.random.default_rng(1)
    det = rng.normal(size=64)
    via = _buses(rng, 64)
    direct = {k: v.copy() for k, v in via.items()}
    _apply_chain(via, det, spec)
    B.apply_fdn_buses(direct, det, spec)
    for k in ("l", "c", "r"):
        assert np.max(np.abs(via[k] - direct[k])) == 0.0


def test_array_insert_leaves_the_room_channel():
    spec = B.design({"bloom_preset": "glue", "bloom_amount": 100, "pre_colour": "off"}, 48000)
    rng = np.random.default_rng(2)
    buses = _buses(rng, 96)
    det = rng.normal(size=96)
    left = buses["l"].copy()
    room = buses["c"].copy()
    place = {"l": "array", "c": "room", "r": "array"}
    _route_buses(buses, det, spec, None, place)
    assert np.max(np.abs(buses["c"] - room)) == 0.0
    assert np.max(np.abs(buses["l"] - left)) > 0.0


def test_room_insert_leaves_the_array_channels():
    spec = B.design({"bloom_preset": "room_crush", "bloom_amount": 80, "pre_colour": "u610a", "pre_drive_db": 3}, 48000)
    rng = np.random.default_rng(3)
    buses = _buses(rng, 96)
    det = rng.normal(size=96)
    left, right = buses["l"].copy(), buses["r"].copy()
    place = {"l": "array", "c": "room", "r": "array"}
    _route_buses(buses, det, None, spec, place)
    assert np.max(np.abs(buses["l"] - left)) == 0.0
    assert np.max(np.abs(buses["r"] - right)) == 0.0


def test_off_body_keeps_the_empty_md5_and_routes_nothing():
    assert _md5({}) == EMPTY
    assert A._bloom_render_kw(A.params_from_body({})) == {}
    assert A._routing_render_kw(A.params_from_body({})) == {}


def test_array_keys_stay_out_of_the_live_dict():
    off = {
        "array_preset": "glue",
        "array_amount": 0,
        "array_pre": "off",
        "place_c": "room",
    }
    off_blob = A.live_fdn_params(A.params_from_body(off))
    assert "side" not in off_blob
    assert "array_preset" not in off_blob
    assert "place_c" not in off_blob
    assert _md5(off) == EMPTY
    body = {
        "array_preset": "glue",
        "array_amount": 100,
        "array_pre": "neve1073",
        "array_drive_db": 6,
        "place_l": "array",
        "place_c": "array",
        "place_r": "array",
    }
    p = A.params_from_body(body)
    blob = A.live_fdn_params(p)
    assert "array_preset" not in blob
    assert "room_preset" not in blob
    assert "place_c" not in blob
    side = blob["side"]
    assert len(side) == 217
    assert side[85] == 2.0
    assert side[86] == 1.0
    assert _md5(body) != EMPTY
    kw = A._routing_render_kw(p)
    assert kw["array_preset"] == "glue"
    assert kw["array_pre"] == "neve1073"
    assert kw["room_amount"] == 0.0


def test_page_room_crush_still_forwards_as_master_bloom():
    p = A.params_from_body(PAGE)
    kw = A._bloom_render_kw(p)
    assert kw["bloom_preset"] == "room_crush"
    assert kw["bloom_amount"] == 100.0
    assert kw["pre_colour"] == "off"
    assert A._routing_render_kw(p) == {}


def test_master_room_crush_live_params_are_preset_two():
    """The Play body for Master Room Crush is the 40-float section the worklet arms."""
    on = A.live_fdn_params(A.params_from_body(PAGE))
    bloom = on["bloom"]
    assert len(bloom) >= 40
    assert bloom[0] == 2.0
    assert bloom[1] > 0.0
    off = A.live_fdn_params(A.params_from_body({}))
    assert "bloom" not in off
    assert "pre_colour" not in off


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])


def test_array_glue_moves_a_play_sample(tmp_path):
    """Shipped wasm. Array Glue at 100, preamp off, changes the left channel."""
    root = SW.parent
    lib = root / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
    node = shutil.which("node")
    assert node, "node is required"
    off_json = tmp_path / "side_off.json"
    on_json = tmp_path / "side_on.json"
    off_f = tmp_path / "side_off.f32"
    on_f = tmp_path / "side_on.f32"
    on_body = json.dumps({"array_preset": "glue", "array_amount": 100, "array_pre": "off"})
    colour = json.dumps({"colour_on": False})
    _run([sys.executable, str(lib / "dump_params.py"), str(SW), "{}", str(off_json), "48000"])
    _run([sys.executable, str(lib / "dump_params.py"), str(SW), on_body, str(on_json), "48000"])
    side = json.loads(on_json.read_text(encoding="utf-8"))["side"]
    assert len(side) == 217
    assert side[3] == 1.0
    _run([node, str(lib / "wasm_run.js"), str(SW), str(off_json), colour, "ir", "0.25", str(off_f)])
    _run([node, str(lib / "wasm_run.js"), str(SW), str(on_json), colour, "ir", "0.25", str(on_f)])
    off = np.fromfile(off_f, dtype=np.float32)
    on = np.fromfile(on_f, dtype=np.float32)
    n = min(off.size, on.size)
    left = float(np.max(np.abs(on[:n:2].astype(np.float64) - off[:n:2].astype(np.float64))))
    assert left > 0.0, left
