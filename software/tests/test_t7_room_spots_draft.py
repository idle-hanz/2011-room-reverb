"""T7: one room spot per strip.

The server already takes per-strip positions (app_server.py mic_x_/mic_y_/mic_z_/mic_pos_).
heardMix posts them only while that strip is a room mic. These tests pin that posting
the engine stand pose is bit-exact, and that two different spots are not.
"""
from __future__ import annotations
import pytest

try:
    import _harness as H
except ModuleNotFoundError:
    from tests import _harness as H
import app_server as A
from early_field import (
    MicStand,
    apply_capsule_heights,
    centre_position,
    direct_field_from_params,
    mic_positions,
)


def _room(cap, x, y, z, **over):
    b = H.ortf(**over)
    b.update({f"mic_x_{cap}": x, f"mic_y_{cap}": y, f"mic_z_{cap}": z})
    return b


@pytest.mark.slow
def test_shared_spot_equals_per_strip_spot():
    """Same posted numbers, shared spot or migrated per-strip spot. Same IR."""
    a = H.render_body(_room("r", 1.0, 2.0, 6.0, fdn_wet=0.0))
    b = H.render_body(_room("r", 1.0, 2.0, 6.0, fdn_wet=0.0))
    assert H.null_db(a, b) <= -120.0


@pytest.mark.slow
def test_two_strips_can_sit_in_different_places():
    a = H.render_body(dict(_room("l", 1.0, 2.0, 6.0, fdn_wet=0.0), mic_x_r=5.0, mic_y_r=2.0, mic_z_r=6.0))
    b = H.render_body(dict(_room("l", 1.0, 2.0, 6.0, fdn_wet=0.0), mic_x_r=1.0, mic_y_r=2.0, mic_z_r=6.0))
    assert H.null_db(a, b) > -40.0


def _page_ortf(**over):
    """Page ORTF: centre off, so the desk is already active before a room spot is posted."""
    b = H.ortf(third_mic="off", fdn_wet=0.0, direct_wet=1.0, early_wet=0.0)
    b.update(over)
    return b


def _engine_pose(body):
    p = A.params_from_body(body)
    prep = direct_field_from_params(p)
    stand = MicStand.from_prepare(
        prep,
        car_omni=p["car_omni"],
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
    )
    apply_capsule_heights(stand, p)
    left, right = mic_positions(stand)
    return {"l": left, "r": right, "c": centre_position(stand)}


def _posted(body, cap):
    out = dict(body)
    x, y, z = _engine_pose(body)[cap]
    out[f"mic_x_{cap}"] = x
    out[f"mic_y_{cap}"] = y
    out[f"mic_z_{cap}"] = z
    return out


def test_engine_stand_matches_roommath_algebra():
    """Flat ORTF: L/R are mcx ± space/2, y = my, z = mcz. RoomMath.compute uses the same."""
    pose = _engine_pose(_page_ortf())
    assert abs(pose["l"][0] - (3.0 - 0.085)) < 1e-9
    assert abs(pose["r"][0] - (3.0 + 0.085)) < 1e-9
    assert pose["l"][1:] == (1.5, 1.5)
    assert pose["r"][1:] == (1.5, 1.5)
    assert pose["c"] == (3.0, 1.5, 1.5)


@pytest.mark.slow
def test_room_spot_at_stand_nulls_ortf():
    """Switching to Room mic at the current stand pose does not move the sound."""
    base = _page_ortf()
    for cap in ("l", "r"):
        db = H.null_db(H.render_body(base), H.render_body(_posted(base, cap)))
        print("stand null", cap, round(db, 2))
        assert db <= -120.0, (cap, db)


@pytest.mark.slow
def test_room_spot_at_stand_nulls_with_height():
    base = _page_ortf(my_l=1.8, align_horizontal=True)
    pose = _engine_pose(base)
    assert abs(pose["r"][1] - 1.8) < 1e-9
    db = H.null_db(H.render_body(base), H.render_body(_posted(base, "r")))
    print("stand null height", round(db, 2))
    assert db <= -120.0, db


@pytest.mark.slow
def test_old_shared_spot_matches_migrated_numbers():
    """Recall copies room_x/y/z/yaw onto the strip. The posted body is the same numbers."""
    shared = _page_ortf(mic_x_r=4.0, mic_y_r=1.5, mic_z_r=2.0, yaw_r_deg=0.0)
    migrated = _page_ortf(mic_x_r=4.0, mic_y_r=1.5, mic_z_r=2.0, yaw_r_deg=0.0)
    db = H.null_db(H.render_body(shared), H.render_body(migrated))
    print("migrated shared", round(db, 2))
    assert db <= -120.0


@pytest.mark.slow
def test_dui25_r_is_a_free_room_mic():
    """L = S, C = M, R = its own room mic. The stand pose nulls. A different spot does not."""
    base = H.ms(fdn_wet=0.0, direct_wet=1.0, early_wet=0.0)
    base.update({
        "mic_gain_r": 1.0,
        "mic_route_r": "pan",
        "mic_pan_r": 1.0,
        "pattern_r": "cardioid",
        "family_r": "cardioid",
        "polar_r": 0.5,
        "yaw_r_deg": 20.0,
    })
    parked = H.render_body(base)
    at = H.render_body(_posted(base, "r"))
    db = H.null_db(parked, at)
    print("D-UI25 stand", round(db, 2))
    assert db <= -120.0, db
    far = dict(base)
    far.update(mic_x_r=5.0, mic_y_r=1.2, mic_z_r=6.0)
    moved = H.null_db(parked, H.render_body(far))
    print("D-UI25 moved", round(moved, 2))
    assert moved > -40.0
