"""Off-axis tail switch. Absent or false stays today's live MD5. No listen render."""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from mic_colour import tail_diffuse as T  # noqa: E402
from mic_colour.sos_fit import sos_db  # noqa: E402
from render_pipeline import live_fdn_params, pack_blob_v2, render_fdn_ir  # noqa: E402

EMPTY_MD5 = "b6c55d429fa63d6d0d3cd1fcc7d23e88"


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _section_ids(blob):
    nsec = int(blob[3])
    return [int(blob[5 + 4 * i]) for i in range(nsec)]


def test_absent_and_false_omit_the_key():
    empty = live_fdn_params(A.params_from_body({}))
    assert "offaxis_tail" not in empty
    assert 14 not in _section_ids(pack_blob_v2(empty))
    assert _md5(empty) == EMPTY_MD5
    off = live_fdn_params(A.params_from_body({"offaxis_tail": False}))
    assert "offaxis_tail" not in off
    assert _md5(off) == EMPTY_MD5
    assert 14 not in _section_ids(pack_blob_v2(off))


def test_true_packs_45_k3():
    on = live_fdn_params(A.params_from_body({"offaxis_tail": True}))
    coeffs = on["offaxis_tail"]
    assert len(coeffs) == 45
    assert all(np.isfinite(v) for v in coeffs)
    ids = _section_ids(pack_blob_v2(on))
    assert 14 in ids
    blob = pack_blob_v2(on)
    nsec = int(blob[3])
    for i in range(nsec):
        if int(blob[5 + 4 * i]) == 14:
            assert int(blob[5 + 4 * i + 2]) == 45
    assert T.LAYOUT == ("LS", "HS", "HS")


def test_u87_cardioid_shape():
    """Absolute -DI from the engine model. A cardioid sits near -5 dB at 1 kHz.

    The raw §2.5 −13.9 dB is the diffuse field re 1 kHz, including on-axis
    tone. G_tail is only -DI. This model’s 16 kHz DI rise is milder than the
    raw IR, and the tail is still darker there than at 1 kHz.
    """
    f = np.array([1000.0, 16000.0])
    g = T.gain_db("NeumannU87AiCardioid", 48000.0, None, f)
    assert -8.0 < float(g[0]) < -4.0
    assert float(g[1]) < float(g[0]) - 1.0
    sos = T.design_bus("NeumannU87AiCardioid", 48000.0, None)
    fit = sos_db(sos, f, 48000.0)
    assert abs(float(fit[0] - g[0])) < 3.0
    assert abs(float(fit[1] - g[1])) < 4.0


def test_tail_sits_after_bloom_and_does_not_call_the_dead_function():
    src = inspect.getsource(render_fdn_ir)
    assert src.index("colour.apply") < src.index("_apply_chain")
    assert src.index("_apply_chain") < src.index("_apply_tail_buses")
    assert "tail_sos is None" in src
    text = (SW / "mic_colour" / "tail_diffuse.py").read_text(encoding="utf-8")
    assert "apply_capsule_colour" not in text
    assert "scipy" not in text
    assert "early_field" not in text


def test_design_is_deterministic():
    a = T.design_pack(("NeumannU87AiCardioid", "SchoepsCMC5UCardioid", "RoyerR121"), 48000.0)
    b = T.design_pack(("u87", "SchoepsCMC5UCardioid", "royer"), 48000.0)
    assert a == b
    assert len(a) == 45
