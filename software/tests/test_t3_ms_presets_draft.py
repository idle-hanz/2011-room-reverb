"""T3 draft: MS preset b/c weights, and the direct-sound image check found on 4 Oct.

FINDING (VERIFIED on the box, build 51): with one source the direct spike ignores the
mic pattern (render_pipeline.py direct_capsule_spikes 1050-1063: "One source stays
(1, 1, 1)"). In MS the Side strip (route s) therefore adds +1 to L and -1 to R for every
source angle: direct-only MS classic sits 11.2 dB left of centre wherever the source is
(roadmap/research/proto/ms_direct_image.json). ORTF is unaffected (both capsules get 1).
T3b (D19) centres that direct image. The marker is removed."""
from __future__ import annotations
import json
from pathlib import Path
try:
    import _harness as H  # loose folder (prebuild)
except ModuleNotFoundError:
    from tests import _harness as H  # software/tests is a package

FIX = Path(__file__).resolve().parent / "fixtures" / "ui_body_ms_classic.json"


def test_ms_b_weights():
    w = H.weights(H.ms())
    assert w == {"ll": 1.0, "lr": -1.0, "cl": 1.5, "cr": 1.5, "rl": 0.0, "rr": 0.0}


def test_ms_c_back_to_back_weights():
    b = H.ms(pattern_l="cardioid", family_l="cardioid", pattern_r="cardioid", family_r="cardioid",
             yaw_l_deg=90.0, yaw_r_deg=-90.0, mic_route_r="s", mic_phase_r=-1.0, mic_gain_r=1.0)
    w = H.weights(b)
    assert (w["ll"], w["lr"], w["rl"], w["rr"]) == (1.0, -1.0, -1.0, 1.0)


def test_ui_body_fixture_still_flips_to_custom():
    """B3 inverted: selecting the MS preset posts ms_b (or ms_classic) with ms_decode, not Custom."""
    b = json.loads(FIX.read_text())
    assert b["mic_setup"] in ("ms_b", "ms_classic") and b.get("ms_decode") is True


def test_ms_direct_sound_is_centred_for_a_front_source():
    ir = H.render_body(H.ms(sx=3.0, sz=4.75, fdn_wet=0.0, early_wet=0.0, direct_wet=1.0))
    assert abs(H.lr_db(ir)) < 1.0
