"""Polygon image sources. Absent or box stays the shoebox live MD5.

The polygon-on-box set is the corner lattice through order 4.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from early_field import MicStand, dist, image_position_corner  # noqa: E402
from fdn import fdn_delays_from_taps  # noqa: E402
from poly_room import (  # noqa: E402
    QUOTA,
    box_faces,
    build_tree,
    collect_audible,
    compute_poly_taps,
    faces_for,
    normalize_shape,
    poly_on,
)
from render_pipeline import live_fdn_params  # noqa: E402

EMPTY = "b20cf5dc675f613992aa6a31c2cd74f4"
CENTRE = "ba1bbc6d386ed75bf484156f08043f37"
ROOM = (6.0, 3.0, 8.0)
SRC = (2.2, 1.3, 3.4)
MIC = (3.2, 1.4, 4.2)


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _stand():
    return MicStand(cx=3.0, cy=1.5, cz=1.5, space=0.25, car_omni=1.0)


def test_absent_or_box_leaves_play_bytes():
    empty = live_fdn_params(A.params_from_body({}))
    assert "room_shape" not in empty
    assert _md5(empty) == EMPTY
    boxed = live_fdn_params(A.params_from_body({"room_shape": "box"}))
    assert "room_shape" not in boxed
    assert _md5(boxed) == EMPTY
    named = live_fdn_params(A.params_from_body({"room_shape": "splay"}))
    assert "room_shape" not in named
    assert _md5(named) == EMPTY
    centre = live_fdn_params(A.params_from_body({"third_mic": "centre", "mic_gain_c": 1.0}))
    assert _md5(centre) == CENTRE
    played = live_fdn_params(
        A.params_from_body({"third_mic": "centre", "mic_gain_c": 1.0, "room_shape": "lede"})
    )
    assert _md5(played) == CENTRE
    src = inspect.getsource(live_fdn_params)
    assert "poly_on" not in src
    assert "room_shape" not in src


def test_unknown_word_is_the_box():
    assert normalize_shape(None) == "box"
    assert normalize_shape("") == "box"
    assert normalize_shape("box") == "box"
    assert normalize_shape("nope") == "box"
    assert not poly_on("box")
    assert poly_on("splayed control room")
    assert poly_on("LEDE")
    assert poly_on("non-parallel")
    assert normalize_shape("non-parallel") == "live"


def _mirror_axis(s: float, size: float, k: int) -> float:
    """Shoebox mirror. Even rooms keep s. Odd rooms use size - s."""
    if k % 2 == 0:
        return k * size + s
    return k * size + (size - s)


def test_polygon_on_box_matches_the_lattice():
    faces = box_faces(*ROOM)
    heard = collect_audible(SRC, faces, MIC, order=4)
    lattice = []
    verified = []
    W, H, L = ROOM
    for nx in range(-4, 5):
        for ny in range(-4, 5):
            for nz in range(-4, 5):
                if abs(nx) + abs(ny) + abs(nz) > 4:
                    continue
                pos = (
                    _mirror_axis(SRC[0], W, nx),
                    _mirror_axis(SRC[1], H, ny),
                    _mirror_axis(SRC[2], L, nz),
                )
                lattice.append(pos)
                if max(abs(nx), abs(ny), abs(nz)) <= 2:
                    verified.append(image_position_corner(SRC, ROOM, (nx, ny, nz)))
    assert len(lattice) == 129
    assert len(heard) == 129
    for pos in lattice:
        assert any(dist(pos, h[0]) < 1e-6 for h in heard)
    for pos in verified:
        assert any(dist(pos, h[0]) < 1e-6 for h in heard)


def test_parent_prune_keeps_every_box_image():
    faces = box_faces(*ROOM)
    kept = collect_audible(SRC, faces, MIC, order=3, prune=True)
    full = collect_audible(SRC, faces, MIC, order=3, prune=False)
    assert len(build_tree(SRC, faces, order=3, prune=True)) < len(
        build_tree(SRC, faces, order=3, prune=False)
    )
    assert len(kept) == len(full) == 63


def test_distance_cut_drops_far_images():
    faces = box_faces(*ROOM)
    wide_n = len(build_tree(SRC, faces, order=4, max_dist=None))
    near_n = len(build_tree(SRC, faces, order=4, max_dist=5.0))
    assert near_n < wide_n
    wide = collect_audible(SRC, faces, MIC, order=4, max_dist=None)
    near = collect_audible(SRC, faces, MIC, order=4, max_dist=5.0)
    assert near
    near_pos = {tuple(round(v, 5) for v in pos) for pos, _o, _s in near}
    wide_pos = {tuple(round(v, 5) for v in pos) for pos, _o, _s in wide}
    assert near_pos < wide_pos


def test_presets_fill_the_quota_and_freeze_the_stand():
    stand = _stand()
    src = (2.6, 1.2, 4.75)
    stand_pt = (stand.cx, stand.cy, stand.cz)
    for name in ("splay", "lede", "live"):
        taps = compute_poly_taps(ROOM, src, stand, name, n=32)
        assert len(taps) == 32
        counts = [sum(1 for t in taps if t.order == k) for k in range(5)]
        assert tuple(counts) == QUOTA, (name, counts)
        assert taps[0].order == 0
        assert dist(taps[0].position, src) < 1e-6
        for t in taps:
            assert t.n == (0, 0, 0)
            assert t.wall_combo == frozenset()
            assert t.fdn_distance_l == t.fdn_distance_r == t.fdn_distance_c
            assert abs(t.fdn_distance_l - dist(stand_pt, t.position)) < 1e-9
            assert math_finite(t)
        delays_l = fdn_delays_from_taps(taps, sr=48000, n=32, channel="l")
        delays_r = fdn_delays_from_taps(taps, sr=48000, n=32, channel="r")
        delays_c = fdn_delays_from_taps(taps, sr=48000, n=32, channel="c")
        assert delays_l == delays_r == delays_c
        assert abs(taps[0].distance_l - taps[0].fdn_distance_l) > 1e-4


def math_finite(tap) -> bool:
    nums = (
        tap.distance_l, tap.distance_r, tap.distance_c,
        tap.level_l, tap.level_r, tap.level_c,
        tap.delay_ms_l, tap.delay_ms_r, tap.delay_ms_c,
    )
    return all(v == v and abs(v) < 1e6 for v in nums)


def test_presets_scale_with_the_box():
    small = faces_for("splay", 6.0, 3.0, 8.0)
    big = faces_for("splay", 12.0, 3.0, 8.0)
    sx = max(float(v[0]) for face in small for v in face.v)
    bx = max(float(v[0]) for face in big for v in face.v)
    assert abs(bx - 2.0 * sx) < 1e-9
    live = faces_for("live", 6.0, 3.0, 8.0)
    floor = next(face for face in live if face.name == "floor")
    front = [v for v in floor.v if abs(float(v[2])) < 1e-9]
    assert front
    assert all(0.0 < float(v[0]) < 6.0 for v in front)
    ceil = next(face for face in live if face.name == "ceiling")
    front_y = [float(v[1]) for v in ceil.v if abs(float(v[2])) < 1e-9]
    rear_y = [float(v[1]) for v in ceil.v if abs(float(v[2]) - 8.0) < 1e-6]
    assert front_y and rear_y
    assert max(front_y) < min(rear_y)
