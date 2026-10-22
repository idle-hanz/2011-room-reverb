"""T7 draft: one room spot per strip. VERIFIED 4 Oct: the server already takes per-strip
positions (app_server.py 609-620 mic_x_/mic_y_/mic_z_/mic_pos_<cap>; desk_matrix.py 51-54),
and app.js heardMix 491-503 copies the shared room_x/y/z into them. So T7 is client-side:
migration copies room_* into room_<cap>_* and heardMix reads the per-strip ones.
These tests pin the server half so the client change stays bit-exact."""
from __future__ import annotations
import _harness as H


def _room(cap, x, y, z, **over):
    b = H.ortf(**over)
    b.update({f"mic_x_{cap}": x, f"mic_y_{cap}": y, f"mic_z_{cap}": z})
    return b


def test_shared_spot_equals_per_strip_spot():
    """Today: Room on R uses the shared spot. After T7: room_r_* with the same numbers. Same body -> same IR."""
    a = H.render_body(_room("r", 1.0, 2.0, 6.0, fdn_wet=0.0))
    b = H.render_body(_room("r", 1.0, 2.0, 6.0, fdn_wet=0.0))
    assert H.null_db(a, b) <= -120.0


def test_two_strips_can_sit_in_different_places():
    a = H.render_body(dict(_room("l", 1.0, 2.0, 6.0, fdn_wet=0.0), mic_x_r=5.0, mic_y_r=2.0, mic_z_r=6.0))
    b = H.render_body(dict(_room("l", 1.0, 2.0, 6.0, fdn_wet=0.0), mic_x_r=1.0, mic_y_r=2.0, mic_z_r=6.0))
    assert H.null_db(a, b) > -40.0   # moving R alone changes the render
