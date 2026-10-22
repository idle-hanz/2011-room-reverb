"""T4b (D20, locked 4 Oct 2026 16:43): ORTF without the centre mic by default, plus an
"ORTF + C" preset that keeps today's sound (C at 0 dB, the 477 fold). GOLDEN CHANGE (main golden).
Copied next to _harness.py. The strict xfail is removed: the empty body now has no centre."""
from __future__ import annotations
import json
from pathlib import Path
try:
    import _harness as H
except ModuleNotFoundError:
    from tests import _harness as H

FIX = Path(__file__).resolve().parent / "fixtures" / "ui_body_ortf.json"
FOLD_477 = {"ll": 1.0, "lr": 0.0, "cl": 0.5, "cr": 0.5, "rl": 0.0, "rr": 1.0}


def test_ortf_plus_c_keeps_todays_477_fold():
    assert H.weights(H.ortf(mic_gain_c=1.0, third_mic="centre")) == FOLD_477


def test_ortf_without_c_drops_the_centre():
    w = H.weights(H.ortf(mic_gain_c=0.0))
    assert (w["cl"], w["cr"]) == (0.0, 0.0) and (w["ll"], w["rr"]) == (1.0, 1.0)


def test_captured_body_is_ortf_plus_c_and_plain_ortf_is_off():
    """The 4 Oct capture posts C on. That body is now ORTF + C.
    Plain ORTF (no stored centre) posts the centre off."""
    b = json.loads(FIX.read_text())
    assert b["mic_gain_c"] == 1 and b["third_mic"] == "centre"
    assert H.weights(b) == FOLD_477
    plain = H.body(mic_setup="ortf")
    plain.pop("third_mic", None)
    plain.pop("mic_gain_c", None)
    w = H.weights(plain)
    assert (w["cl"], w["cr"]) == (0.0, 0.0)


def test_empty_body_default_fold_has_no_centre():
    w = H.weights(H.body())
    assert (w["cl"], w["cr"]) == (0.0, 0.0)


def test_saved_centre_scene_recalls_the_477_fold():
    saved = H.body(mic_setup="ortf", third_mic="centre", mic_gain_c=1.0)
    assert H.weights(saved) == FOLD_477
    only_third = H.body(mic_setup="ortf", third_mic="centre")
    only_third.pop("mic_gain_c", None)
    assert H.weights(only_third) == FOLD_477


def test_xy_nos_ab_still_include_the_centre():
    """D20 changes only ORTF. These setups still fold C at 0 dB when the keys are absent."""
    for setup in ("xy_90", "xy_120", "nos", "ab_omni", "ab_card", "din"):
        w = H.weights(H.body(mic_setup=setup))
        assert (w["cl"], w["cr"]) == (0.5, 0.5), setup
