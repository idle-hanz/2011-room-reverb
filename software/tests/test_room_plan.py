"""Plan and tilt stay on the existing room_shape string. A box keeps the live MD5."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
try:
    import _sl_harness as H  # noqa: E402
except ImportError:
    from tests import _sl_harness as H  # noqa: E402
import surf_panels as P  # noqa: E402
import surf_target as ST  # noqa: E402
from early_field import MicStand  # noqa: E402
from poly_room import (  # noqa: E402
    box_faces,
    compute_poly_taps,
    faces_for,
    normalize_shape,
    shape_metrics,
)
from render_pipeline import live_fdn_params, play_listen_scene  # noqa: E402

EMPTY = "067adbca1930efcd3f7c83bdd1d4c359"
PLAN = "plan:1.00,1.00,5.00,1.00,5.00,6.00,3.00,7.00,1.00,5.00"


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _delays(shape):
    stand = MicStand(cx=3.0, cy=1.5, cz=1.5, space=0.25, car_omni=1.0)
    taps = compute_poly_taps((6.0, 3.0, 8.0), (2.2, 1.3, 3.4), stand, shape, n=8)
    return [round(t.delay_ms_l, 4) for t in taps]


def test_box_ignores_a_plan_argument_and_keeps_the_products():
    assert normalize_shape("nope") == "box"
    plan = [(1.0, 1.0), (5.0, 1.0), (5.0, 6.0), (3.0, 7.0), (1.0, 5.0)]
    plain = box_faces(6.0, 3.0, 8.0)
    ignored = faces_for("box", 6.0, 3.0, 8.0, plan=plan)
    assert len(ignored) == len(plain)
    assert np.allclose(ignored[0].v, plain[0].v)
    V, areas = shape_metrics("box", 6.0, 3.0, 8.0)
    assert V == 144.0
    assert areas == {"A": 24.0, "C": 24.0, "B": 18.0, "D": 18.0, "E": 48.0, "F": 48.0}
    W, Hh, L, surfaces, hum = H.room("real_default")
    base = ST.room_target(W, Hh, L, surfaces, hum, ST.BANDS)
    same = ST.room_target(
        W, Hh, L, surfaces, hum, ST.BANDS,
        volume=W * Hh * L, areas=ST.face_areas(W, Hh, L),
    )
    assert np.allclose(base, same)
    boxed = ST.room_result(W, Hh, L, surfaces, hum, decay_s=1.8, decay_lock=True, shape="box")
    plain_result = ST.room_result(W, Hh, L, surfaces, hum, decay_s=1.8, decay_lock=True)
    assert boxed["T_faces_air"] == plain_result["T_faces_air"]


def test_plan_and_tilt_change_only_the_existing_room_shape_word():
    assert normalize_shape(PLAN) == "plan"
    assert normalize_shape("tilt:4:0") == "tilt"
    assert normalize_shape("tilt:0:0.2") == "tilt"
    empty = live_fdn_params(A.params_from_body({}))
    assert "room_shape" not in empty
    assert _md5(empty) == EMPTY
    flat = live_fdn_params(A.params_from_body({"room_shape": "tilt:0:0"}))
    assert "room_shape" not in flat
    assert _md5(flat) == EMPTY
    played = live_fdn_params(A.params_from_body({"room_shape": PLAN}))
    assert played.get("room_shape") == "plan"
    for key in ("plan_xy", "wall_tilt", "ceiling_slope"):
        assert key not in played
    assert played["buses"]["l"]["delay_ms"] != empty["buses"]["l"]["delay_ms"]
    tilted = live_fdn_params(A.params_from_body({"room_shape": "tilt:4:0.1"}))
    assert tilted.get("room_shape") == "tilt"
    assert "wall_tilt" not in tilted
    assert _delays("hex") == _delays("hex")
    stand = MicStand(cx=3.0, cy=1.5, cz=1.5, space=0.25, car_omni=1.0)
    bare = compute_poly_taps((6.0, 3.0, 8.0), (2.2, 1.3, 3.4), stand, "hex", n=8)
    with_plan = compute_poly_taps(
        (6.0, 3.0, 8.0), (2.2, 1.3, 3.4), stand, "hex", n=8, plan=[(0, 0), (1, 0), (1, 1), (0, 1)]
    )
    assert [t.delay_ms_l for t in bare] == [t.delay_ms_l for t in with_plan]
    Vs, areas = shape_metrics("splay", 6.0, 3.0, 8.0)
    assert Vs < 144.0
    assert areas["E"] < 48.0
    shaped = ST.room_result(6.0, 3.0, 8.0, H.room("real_default")[3], 0.35, shape="splay")
    stock = ST.room_result(6.0, 3.0, 8.0, H.room("real_default")[3], 0.35)
    assert shaped["T_faces_air"] != stock["T_faces_air"]


def _face(shape, name):
    return next(face for face in faces_for(shape, 6.0, 3.0, 8.0) if face.name == name)


def test_play_render_and_the_drawing_share_one_polygon():
    """Tilt floor and ceiling match the mesh. Play taps are Render's compute_poly_taps."""
    import math

    inset = min(0.4 * 6.0, abs(8.0 * math.tan(math.radians(4.0))))
    tilt = "tilt:4:0.2"
    floor = sorted((round(float(v[0]), 6), round(float(v[2]), 6)) for v in _face(tilt, "floor").v)
    expect = sorted([(inset, 0.0), (6.0 - inset, 0.0), (6.0, 8.0), (0.0, 8.0)])
    assert len(floor) == 4
    for got, want in zip(floor, expect):
        assert abs(got[0] - want[0]) < 1e-6
        assert abs(got[1] - want[1]) < 1e-6
    heights = {}
    for v in _face(tilt, "ceiling").v:
        heights.setdefault(round(float(v[2]), 6), set()).add(round(float(v[1]), 6))
    assert heights[0.0] == {2.4}
    assert heights[8.0] == {3.0}
    plan_pts = {(round(float(v[0]), 2), round(float(v[2]), 2)) for v in _face(PLAN, "floor").v}
    assert plan_pts == {(1.0, 1.0), (5.0, 1.0), (5.0, 6.0), (3.0, 7.0), (1.0, 5.0)}
    scene = play_listen_scene(A.params_from_body({"room_shape": tilt}))
    direct = compute_poly_taps(
        scene["room"], scene["prep"].source, scene["stand"], scene["shape"],
        c=scene["c"], n=scene["n_had"],
        include_offaxis_shelf=scene["colour"].include_offaxis_shelf,
        include_pattern=not scene["colour"].measured,
    )
    assert [round(t.delay_ms_l, 6) for t in scene["taps"]] == [round(t.delay_ms_l, 6) for t in direct]
    assert normalize_shape(scene["shape"]) == "tilt"
    assert _md5(live_fdn_params(A.params_from_body({}))) == EMPTY


def test_diffuser_trap_and_cloud_feed_surfaces():
    rows = [
        {
            "id": "diffuser_0", "face": "A", "type": "porous",
            "material": "absorber_panel_2in_gap2in", "coverage": 0.2, "on": True, "build": "Diffuser",
        },
        {
            "id": "trap_1", "face": "D", "type": "membrane", "f0": 80, "q": 2, "amax": 0.6,
            "coverage": 0.15, "on": True, "build": "Bass trap",
        },
        {
            "id": "cloud_2", "face": "F", "type": "porous",
            "material": "absorber_panel_4in_gap4in", "coverage": 0.25, "on": True, "build": "Cloud",
        },
    ]
    assert P.validate_rows(rows) == []
    W, Hh, L, surfaces, hum = H.room("real_default")
    cards = P.cards_with_treatment(surfaces, rows)
    assert "absorb_fn" in cards["A"]
    assert "absorb_fn" in cards["D"]
    assert "absorb_fn" in cards["F"]
    assert "absorb_fn" not in cards["B"]
    bare = ST.room_target(W, Hh, L, surfaces, hum, np.array([1000.0]))
    treated = ST.room_target(W, Hh, L, cards, hum, np.array([1000.0]))
    assert abs(float(bare[0]) - float(treated[0])) > 1e-6
    empty = live_fdn_params(A.params_from_body({}))
    assert _md5(empty) == EMPTY
    assert "diffuser" not in empty
    assert "surf_treatment" not in empty
