"""T4b draft (D20, locked 4 Oct 2026 16:43): ORTF without the centre mic by default, plus an
"ORTF + C" preset that keeps today's sound (C at 0 dB, the 477 fold). GOLDEN CHANGE (main golden).
Copy next to _harness.py in software/tests/. The strict xfail flips when T4b lands."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
import _harness as H

FIX = Path(__file__).resolve().parent / "fixtures" / "ui_body_ortf.json"
FOLD_477 = {"ll": 1.0, "lr": 0.0, "cl": 0.5, "cr": 0.5, "rl": 0.0, "rr": 1.0}


def test_ortf_plus_c_keeps_todays_477_fold():
    assert H.weights(H.ortf(mic_gain_c=1.0)) == FOLD_477


def test_ortf_without_c_drops_the_centre():
    w = H.weights(H.ortf(mic_gain_c=0.0))
    assert (w["cl"], w["cr"]) == (0.0, 0.0) and (w["ll"], w["rr"]) == (1.0, 1.0)


def test_today_ui_posts_c_on_for_ortf():
    """Captured UI body (4 Oct, build 51). T4b: ORTF posts third_mic 'off' / mic_gain_c 0;
    'ORTF + C' posts this body. Then invert this test for the plain ORTF preset."""
    b = json.loads(FIX.read_text())
    assert b["mic_gain_c"] == 1 and b["third_mic"] == "centre"


@pytest.mark.xfail(strict=True, reason="passes once T4b (D20) lands; then remove this marker")
def test_empty_body_default_fold_has_no_centre():
    w = H.weights(H.body())
    assert (w["cl"], w["cr"]) == (0.0, 0.0)
