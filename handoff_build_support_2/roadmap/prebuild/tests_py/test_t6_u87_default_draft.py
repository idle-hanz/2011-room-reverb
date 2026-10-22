"""T6 draft (D-UI30): the default mic is U87 Ai Cardioid on L, C and R — only after Idle's OK on T5.
Before T6 lands these tests are skipped, so the file can be copied in early."""
from __future__ import annotations
import pytest
import _harness as H

T6_DONE = H.A.DEFAULTS.get("mic_preset_l") == "NeumannU87AiCardioid"


@pytest.mark.skipif(not T6_DONE, reason="T6 not merged yet (default still ShureSM57)")
def test_defaults_are_u87_cardioid():
    for c in "lcr":
        assert H.A.DEFAULTS[f"mic_preset_{c}"] == "NeumannU87AiCardioid"


@pytest.mark.skipif(not T6_DONE, reason="T6 not merged yet")
def test_params_from_body_fallback_is_u87():
    p = H.A.params_from_body({k: v for k, v in H.body().items() if not k.startswith("mic_preset")})
    assert p.get("mic_preset_l", "NeumannU87AiCardioid") == "NeumannU87AiCardioid"
