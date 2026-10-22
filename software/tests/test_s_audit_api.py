"""S-AUDIT API gates: validation (A7) and a render that does not block the server (A3)."""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import threading
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path[:0] = [str(ROOT / "software")]
import app_server as A  # noqa: E402

# Empty-body live hash. TLAW 1/r (Idle 2026-10-10) moved it off the T4c hash
# 4bd18877a1a80396108bcafd17d4d762. A stored centre moved with the same law
# (was 16bc17806a12f9c0ad3db32d104eaaaf). The blob diff is inject levels,
# makeup, and the unwired direct_makeup field. Delays, g, and the direct fold stay.
_DEFAULT_LIVE_MD5 = "b6c55d429fa63d6d0d3cd1fcc7d23e88"
_ORTF_PLUS_C_LIVE_MD5 = "b3e6bcd9dfa13ad737d2b15d561f7d30"


def _wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\x00\x00" * 480)
    return buf.getvalue()


def test_a7_default_live_hash_unchanged():
    body = {}
    p = A.params_from_body(body)
    blob = A.live_fdn_params(p)
    digest = hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()
    assert digest == _DEFAULT_LIVE_MD5
    assert "warnings" not in blob
    assert body.get("_clamp_warnings") == []
    kept = A.params_from_body({"third_mic": "centre", "mic_gain_c": 1.0})
    kept_blob = A.live_fdn_params(kept)
    kept_digest = hashlib.md5(json.dumps(kept_blob, sort_keys=True, default=str).encode()).hexdigest()
    assert kept_digest == _ORTF_PLUS_C_LIVE_MD5


def test_a7_ir_length_3000_is_not_clamped():
    body = {"ir_length_ms": 3000}
    p = A.params_from_body(body)
    assert p["ir_length_ms"] == 3000
    assert body["_clamp_warnings"] == []


def test_a7_out_of_range_is_clamped_and_named():
    w = {"W": 0}
    A.params_from_body(w)
    assert w["W"] == 1.0 and w["_clamp_warnings"] == ["W"]
    neg = {"W": -5}
    A.params_from_body(neg)
    assert neg["W"] == 1.0 and "W" in neg["_clamp_warnings"]
    decay = {"decay_s": 1e6}
    p = A.params_from_body(decay)
    assert p["decay_s"] == 8.0 and decay["_clamp_warnings"] == ["decay_s"]
    mic = {"mcx": 50, "mcz": -3, "my": -1}
    p = A.params_from_body(mic)
    assert p["mcx"] == pytest.approx(6.0)
    assert p["mcz"] == pytest.approx(0.0)
    assert p["my"] == pytest.approx(0.0)
    assert mic["_clamp_warnings"] == ["mcx", "mcz", "my"]


def test_a7_non_finite_and_non_numeric_are_400():
    client = TestClient(A.app)
    nan = client.post("/api/live_params", content=b'{"W": NaN}', headers={"Content-Type": "application/json"})
    assert nan.status_code == 400 and "W" in nan.text
    abc = client.post("/api/live_params", json={"W": "abc"})
    assert abc.status_code == 400 and "W" in abc.text
    ok = client.post("/api/live_params", json={"W": 0})
    assert ok.status_code == 200
    body = ok.json()
    assert "W" in body.get("warnings", [])


def test_a3_endpoints_are_sync_and_second_render_is_busy(monkeypatch):
    for name in (
        "api_geometry", "api_live_params", "api_images", "api_source_preview",
        "api_render", "api_colour", "api_polar",
    ):
        assert not inspect.iscoroutinefunction(getattr(A, name)), name
    started = threading.Event()
    release = threading.Event()

    def slow(_file, _params):
        started.set()
        assert release.wait(5)
        return {"ok": True, "status": "slow"}

    monkeypatch.setattr(A, "_render_impl", slow)
    client = TestClient(A.app)
    wav = _wav_bytes()

    def post():
        client.post("/api/render", files={"file": ("t.wav", wav, "audio/wav")}, data={"params_json": "{}"})

    t = threading.Thread(target=post)
    t.start()
    assert started.wait(5)
    t0 = time.perf_counter()
    defaults = client.get("/api/defaults")
    d_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    live = client.post("/api/live_params", json={})
    l_s = time.perf_counter() - t1
    busy = client.post(
        "/api/render",
        files={"file": ("t.wav", wav, "audio/wav")},
        data={"params_json": "{}"},
    )
    release.set()
    t.join(timeout=5)
    assert defaults.status_code == 200
    assert live.status_code == 200
    assert d_s < 0.5, d_s
    assert l_s < 1.0, l_s
    assert busy.status_code == 200
    assert busy.json().get("error") == "render busy"


def _fn_body(src: str, name: str) -> str:
    i = src.find(name + "(")
    assert i >= 0, name
    b = src.find("{", i)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[b:j + 1]
    raise AssertionError("unclosed " + name)


def test_a6_process_and_apply_do_not_allocate():
    src = (ROOT / "software" / "static" / "js" / "fdn_worklet.js").read_text(encoding="utf-8")
    for name in ("_apply", "process"):
        body = _fn_body(src, name)
        assert "concat" not in body, name
        assert "new Float32Array" not in body, name
    assert "function packRoom" not in src
    assert (ROOT / "software" / "static" / "js" / "pack_room.js").is_file()
    assert not (ROOT / "software" / "static" / "js" / "fdn_worklet.js.orig").exists()


def test_a11d_worklet_reports_distinct_errors(tmp_path):
    script = tmp_path / "fail.js"
    script.write_text(
        r"""
const fs = require('fs');
const SW = process.argv[2];
const reg = {};
class AWP { constructor() { this.port = { postMessage: (m) => { (global.__errs = global.__errs || []).push(m); }, onmessage: null }; } }
const src = fs.readFileSync(SW + '/static/js/fdn_worklet.js', 'utf8');
new Function('AudioWorkletProcessor', 'registerProcessor', 'sampleRate', src)(AWP, (n, c) => { reg[n] = c; }, 48000);
global.__errs = [];
const pr = new reg['room-fdn']({ processorOptions: {} });
pr._fail('alpha');
pr._fail('alpha');
pr._fail('beta');
const msgs = global.__errs.map(m => m.message);
const nAlpha = msgs.filter(m => m === 'alpha').length;
const nBeta = msgs.filter(m => m === 'beta').length;
if (nAlpha !== 1 || nBeta !== 1) {
  console.error(JSON.stringify(msgs));
  process.exit(1);
}
console.log('ok');
""",
        encoding="utf-8",
    )
    import subprocess
    proc = subprocess.run(
        ["node", str(script), str(ROOT / "software")],
        capture_output=True, text=True, timeout=20,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_a11e_missing_fitter_refuses_start(monkeypatch):
    monkeypatch.setattr(A, "fitter_model_path", lambda: Path("Z:/no-such/mic_fitter/mic_fitter/model.py"))
    with pytest.raises(SystemExit, match="mic_fitter"):
        A.require_fitter()


def test_a11e_present_fitter_starts():
    assert A.fitter_model_path().is_file()
    A.require_fitter()


def test_a8_preview_parent_path_is_forbidden():
    client = TestClient(A.app)
    denied = client.get("/api/preview", params={"path": "../secret.wav"})
    assert denied.status_code == 403


def test_a8_twelve_renders_keep_ten_and_bytes_match(tmp_path, monkeypatch):
    import numpy as np
    from render_pipeline import preview_path, write_wav_stereo

    renders = tmp_path / "renders"
    renders.mkdir()
    monkeypatch.setattr(A, "default_out_path", lambda: renders / "out.wav")

    def fake_render(dry, sr, **_kw):
        z = np.zeros(len(dry), dtype=np.float64)
        return z, z.copy(), {
            "mode": "bypass",
            "mcz": 1.0,
            "mcx": 3.0,
            "source": [1.0, 1.0, 1.0],
            "mic_centre": [3.0, 1.5, 4.0],
            "n_taps": 8,
            "colour_mode": "BYPASS",
            "mic_preset_l": "ShureSM57",
            "peak_before_norm": 0.0,
            "norm_scale": 1.0,
            "colour": {"centres_hz": [1000.0]},
        }

    monkeypatch.setattr(A, "render", fake_render)
    client = TestClient(A.app)
    wav = _wav_bytes()
    paths = []
    for _ in range(12):
        res = client.post(
            "/api/render",
            files={"file": ("t.wav", wav, "audio/wav")},
            data={"params_json": "{}"},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body.get("ok") is True, body
        paths.append(body["preview_url"].split("path=", 1)[1])
    stamps = list(renders.glob("out_*.wav"))
    assert (renders / "out.wav").is_file()
    assert len(stamps) <= 10
    assert len(list(renders.glob("*.wav"))) <= 11
    for old in paths[:-1]:
        assert not Path(old).is_file(), old
    assert Path(paths[-1]).is_file()
    assert preview_path() is not None and preview_path().is_file()
    ref = tmp_path / "ref.wav"
    write_wav_stereo(str(ref), np.zeros(480), np.zeros(480), 48000)
    assert (renders / "out.wav").read_bytes() == ref.read_bytes()
    newest = max(stamps, key=lambda p: p.stat().st_mtime_ns)
    assert newest.read_bytes() == ref.read_bytes()


def _write_wav16(path: Path, left, right, sr: int) -> None:
    """The pre-B1 16-bit writer, kept only so the size gate has an old file."""
    import numpy as np
    n = len(left)
    interleaved = np.empty(n * 2, dtype=np.float64)
    interleaved[0::2] = left
    interleaved[1::2] = right
    pcm = (np.clip(interleaved, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def test_b1_wav_is_24bit_and_nulls(tmp_path):
    import numpy as np
    import struct
    from render_pipeline import load_wav_stereo, write_wav_stereo

    sr = 48000
    t = np.arange(sr, dtype=np.float64) / sr
    left = 0.9 * np.sin(2.0 * np.pi * 440.0 * t)
    right = 0.4 * np.sin(2.0 * np.pi * 660.0 * t)
    left[-1] = 1e-6
    right[-1] = -1e-6
    path = tmp_path / "b1.wav"
    old = tmp_path / "b1_16.wav"
    write_wav_stereo(str(path), left, right, sr)
    _write_wav16(old, left, right, sr)
    raw = path.read_bytes()
    assert raw[0:4] == b"RIFF" and raw[8:12] == b"WAVE"
    fmt = raw.find(b"fmt ")
    assert fmt > 0
    audio_format, channels, rate, _byte_rate, block_align, bits = struct.unpack_from("<HHIIHH", raw, fmt + 8)
    assert (audio_format, channels, rate, block_align, bits) == (1, 2, sr, 6, 24)
    ratio = path.stat().st_size / old.stat().st_size
    assert 1.45 < ratio < 1.55, ratio
    got_l, got_r, got_sr, nch = load_wav_stereo(str(path))
    assert got_sr == sr and nch == 2
    err = np.maximum(np.abs(got_l - left), np.abs(got_r - right))
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
    null_db = 20.0 * np.log10(float(np.max(err)) / peak)
    assert null_db <= -135.0, null_db
    assert abs(got_l[-1]) > 5e-7 and abs(got_r[-1]) > 5e-7
    old_l, old_r, _, _ = load_wav_stereo(str(old))
    assert old_l[-1] == 0.0 and old_r[-1] == 0.0
