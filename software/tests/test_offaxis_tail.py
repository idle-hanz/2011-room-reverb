"""Off-axis tail switch. Absent or false stays today's live MD5. No listen render."""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
from mic_colour import tail_diffuse as T  # noqa: E402
from mic_colour.sos_fit import sos_db, unpack_record  # noqa: E402
from render_pipeline import live_fdn_params, pack_blob_v2, render_fdn_ir  # noqa: E402

EMPTY_MD5 = "b20cf5dc675f613992aa6a31c2cd74f4"


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


# 8–16 kHz, Hann rFFT power, left channel, 0.25 s at 48 kHz. Measured 2026-10-24.
# Tolerance is 0.05 dB. A missing filter misses by several dB.
_HI_LO = 8000.0
_HI_HI = 16000.0
_SR = 48000
_SECS = 0.25
_TOL_DB = 0.05
_ANGLE_HI_DB = -9.2777
_TAIL_HI_DB = -7.1268


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])


def _band_db(x):
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    n = int(x.size)
    spec = np.fft.rfft(x * np.hanning(n))
    freqs = np.fft.rfftfreq(n, 1.0 / _SR)
    m = (freqs >= _HI_LO) & (freqs < _HI_HI)
    power = float(np.sum(np.abs(spec[m]) ** 2))
    return 10.0 * math.log10(max(power, 1e-30))


def _left(path):
    raw = np.fromfile(path, dtype=np.float32)
    return raw[0::2].astype(np.float64)


def _dump(body, dest):
    _run([
        sys.executable, str(LIB / "dump_params.py"), str(SW),
        json.dumps(body), str(dest), str(_SR),
    ])
    return json.loads(dest.read_text(encoding="utf-8"))


def _wasm(params, override, dest):
    node = shutil.which("node")
    assert node, "node is required"
    _run([
        node, str(LIB / "wasm_run.js"), str(SW), str(params),
        json.dumps(override), "ir", str(_SECS), str(dest),
    ])
    return _left(dest)


def _scene(sx, sz, **kw):
    body = {
        "third_mic": "centre",
        "mic_gain_c": 1.0,
        "mic_gain_l": 0.0,
        "mic_gain_r": 0.0,
        "mcx": 3.0,
        "mcz": 1.5,
        "my": 1.5,
        "sy": 1.5,
        "sx": sx,
        "sz": sz,
        "dry_gain": 0.0,
        "early_wet": 0.0,
    }
    body.update(kw)
    return body


def test_offaxis_high_band_matches_the_reference(tmp_path):
    """Shipped wasm. One source, centre mic, 2 m, on-axis versus 90 degrees.

    The direct high band drops by the packed 90 degree colour SOS. The FDN
    high band, section 14 against the key absent, drops by that bus SOS.
    pushParams does not copy offaxis_tail, so the tail run puts the dumped
    45 floats on the worklet message. Default scene stays the empty live MD5.
    """
    empty = live_fdn_params(A.params_from_body({}))
    assert _md5(empty) == EMPTY_MD5
    assert "offaxis_tail" not in empty

    on_json = tmp_path / "on.json"
    off_json = tmp_path / "off.json"
    on_f = tmp_path / "on.f32"
    off_f = tmp_path / "off.f32"
    on_live = _dump(_scene(3.0, 3.5, direct_wet=1.0, fdn_wet=0.0), on_json)
    off_live = _dump(_scene(5.0, 1.5, direct_wet=1.0, fdn_wet=0.0), off_json)
    assert on_live["colour"]["on"] is True and on_live["colour"]["direct"]["c"] == -1
    idx = int(off_live["colour"]["direct"]["c"])
    assert idx >= 0
    rec = np.frombuffer(base64.b64decode(off_live["colour"]["irs"][idx]), dtype=np.float32)
    sos90 = unpack_record(rec.astype(np.float64))
    assert sos90 is not None
    on = _wasm(on_json, {}, on_f)
    off = _wasm(off_json, {}, off_f)
    ref = T.apply_sos_df1(on, sos90)
    wasm_drop = _band_db(off) - _band_db(on)
    ref_drop = _band_db(ref) - _band_db(on)
    assert abs(wasm_drop - ref_drop) < _TOL_DB
    assert abs(wasm_drop - _ANGLE_HI_DB) < _TOL_DB, (wasm_drop, ref_drop)
    assert abs(ref_drop - _ANGLE_HI_DB) < _TOL_DB, (wasm_drop, ref_drop)
    assert float(np.max(np.abs(off - ref))) < 1e-6

    bare_json = tmp_path / "bare.json"
    tail_json = tmp_path / "tail.json"
    bare_f = tmp_path / "bare.f32"
    tail_f = tmp_path / "tail.f32"
    _dump(_scene(3.0, 3.5, direct_wet=0.0, fdn_wet=1.0), bare_json)
    tail_live = _dump(_scene(3.0, 3.5, direct_wet=0.0, fdn_wet=1.0, offaxis_tail=True), tail_json)
    coeffs = tail_live["offaxis_tail"]
    assert len(coeffs) == 45
    assert 14 in _section_ids(pack_blob_v2(tail_live))
    bare = _wasm(bare_json, {"colour_on": False}, bare_f)
    heard = _wasm(tail_json, {"colour_on": False, "offaxis_tail": coeffs}, tail_f)
    bus = np.asarray(coeffs[15:30], dtype=np.float64).reshape(3, 5)
    tail_ref = T.apply_sos_df1(bare, bus)
    tail_wasm = _band_db(heard) - _band_db(bare)
    tail_py = _band_db(tail_ref) - _band_db(bare)
    assert abs(tail_wasm - tail_py) < _TOL_DB
    assert abs(tail_wasm - _TAIL_HI_DB) < _TOL_DB, (tail_wasm, tail_py)
    assert abs(tail_py - _TAIL_HI_DB) < _TOL_DB, (tail_wasm, tail_py)
    assert float(np.max(np.abs(heard - tail_ref))) < 1e-6
