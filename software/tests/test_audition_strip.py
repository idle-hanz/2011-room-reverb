"""PREAMP-AU1 and AU2. Dry-strip CLI, and Play's audition flag against that CLI."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SW = Path(__file__).resolve().parents[1]
TOOL = SW / "tools" / "audition_strip.py"
sys.path[:0] = [str(SW), str(SW / "tests")]

import test_u610a_shaper_level as U  # noqa: E402


def _run(args: list[str]) -> tuple[str, float]:
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(TOOL), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    dt = time.perf_counter() - t0
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, proc.stdout
    return lines[0], dt


def _fields(line: str) -> dict[str, float]:
    out = {}
    for part in line.split():
        key, val = part.split("=")
        out[key] = float(val)
    return out


def test_bypass_is_bit_identical(tmp_path: Path) -> None:
    sr = 48000
    n = 4800
    t = np.arange(n, dtype=np.float64) / sr
    x = (np.sin(2.0 * np.pi * 440.0 * t) * 20000.0).astype(np.int16)
    src = tmp_path / "in.wav"
    dst = tmp_path / "out.wav"
    wavfile.write(str(src), sr, x)
    line, _dt = _run([str(src), "--pre", "none", "--comp", "off", "--seconds", "8", "--out", str(dst)])
    sr2, y = wavfile.read(str(dst))
    assert sr2 == sr
    assert np.array_equal(y, x)
    fields = _fields(line)
    assert fields["scale"] == 1.0
    assert fields["gr_min"] == 0.0 and fields["gr_max"] == 0.0
    assert "thd=" not in line


def test_u610a_thd_matches_shaper_level(tmp_path: Path) -> None:
    dst = tmp_path / "out.wav"
    line, dt = _run([
        "--source", "sine", "--dbfs", "-18",
        "--pre", "u610a", "--drive", "0",
        "--comp", "off", "--seconds", "1",
        "--out", str(dst),
    ])
    fields = _fields(line)
    n = int(U.SR)
    t = np.arange(n, dtype=np.float64) / U.SR
    hot = (10.0 ** (-18.0 / 20.0)) * np.sin(2.0 * np.pi * 1000.0 * t)
    row = U.B.pack_pre({"pre": "u610a", "sr": U.SR, "pre_drive_db": 0.0})
    ref = U._thd_h2_h15(U.B._pre_bus(hot, row))
    assert abs(fields["thd"] / ref - 1.0) < 0.02
    assert abs(fields["thd"] / U.PC2_THD_M57 - 1.0) < 0.02
    assert fields["scale"] == 1.0
    assert dt < 5.0
    _sr, y = wavfile.read(str(dst))
    assert y.shape[0] == n


def test_eight_seconds_finishes_under_five(tmp_path: Path) -> None:
    dst = tmp_path / "out.wav"
    line, dt = _run([
        "--source", "sine", "--dbfs", "-18",
        "--pre", "u610a", "--drive", "0",
        "--comp", "natural", "--amount", "100",
        "--seconds", "8", "--out", str(dst),
    ])
    assert dt < 5.0
    fields = _fields(line)
    assert "thd" in fields
    assert fields["gr_max"] >= fields["gr_min"]
    assert "FDN" in (TOOL.read_text(encoding="utf-8"))
    help_out = subprocess.run(
        [sys.executable, str(TOOL), "--help"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert "FDN" in help_out
    assert "dry signal" in help_out


ROOT = SW.parent
WASM_RUN = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib" / "wasm_run.js"
PC2_THD = 40.106
SR = 48000

# Two engines. B hears one dry block with the flag on, then the flag off, then the same impulse as A.
_CYCLE = r"""
const fs = require('fs'), path = require('path');
const [SW, PJ, OUTA, OUTB, SECS] = process.argv.slice(2);
const SR = 48000, BLK = 128, N = Math.round(+SECS * SR);
const reg = {};
class AWP { constructor() { this.port = { postMessage() {}, onmessage: null }; } }
const packJs = fs.readFileSync(path.join(SW, 'static/js/pack_room.js'), 'utf8');
const workJs = fs.readFileSync(path.join(SW, 'static/js/fdn_worklet.js'), 'utf8');
new Function('AudioWorkletProcessor', 'registerProcessor', 'sampleRate', packJs + '\n' + workJs)(AWP, (n, c) => { reg[n] = c; }, SR);
const wasmBytes = fs.readFileSync(path.join(SW, 'static/wasm/live_stereo.wasm'));
const P = JSON.parse(fs.readFileSync(PJ, 'utf8'));
function msgFrom(over) {
  over = Object.assign({}, over || {});
  const wantColour = over.colour_on !== false; delete over.colour_on;
  const m = { type: 'params', g: P.g, fdn_wet: P.fdn_wet, direct_wet: P.direct_wet, early_wet: P.early_wet, dry_gain: P.dry_gain,
    mic_gain_l: P.mic_gain_l, mic_gain_c: P.mic_gain_c, mic_gain_r: P.mic_gain_r, mic_pan_l: P.mic_pan_l, mic_pan_c: P.mic_pan_c, mic_pan_r: P.mic_pan_r,
    mic_phase_l: P.mic_phase_l, mic_phase_c: P.mic_phase_c, mic_phase_r: P.mic_phase_r, makeup: P.makeup, direct_index: P.direct_index, max_delay_ms: P.max_delay_ms,
    line_t60: P.line_t60 || 0, peaking: P.peaking, two_sources: !!P.two_sources, gain_a: P.gain_a, gain_b: P.gain_b, buses: P.buses, colour_on: false, mono: false,
    hadamard_n: P.hadamard_n != null ? P.hadamard_n : P.n, loop_semantics: P.loop_semantics || 0, shared_tail: !!P.shared_tail };
  if (P.bloom && P.bloom.length >= 26) m.bloom = P.bloom;
  if (P.predelay_n > 0) m.predelay_n = P.predelay_n;
  if (P.pre_colour && P.pre_colour.length >= 16) m.pre_colour = P.pre_colour;
  if (P.prox && P.prox.length === 199) m.prox = Float64Array.from(P.prox);
  if (P.harm && P.harm.length === 243) m.harm = Float64Array.from(P.harm);
  if (P.sub_hp && P.sub_hp.length === 5) m.sub_hp = P.sub_hp;
  if (P.offaxis_tail && P.offaxis_tail.length === 45) m.offaxis_tail = P.offaxis_tail;
  if (wantColour) m.colour_on = true;
  return Object.assign(m, over);
}
async function boot() {
  const pr = new reg['room-fdn']({ processorOptions: { wasm: wasmBytes } });
  for (let i = 0; i < 100 && !pr.ready; i++) await new Promise(r => setTimeout(r, 20));
  if (!pr.ready) throw new Error('wasm not ready');
  return pr;
}
function deliver(pr, over, snap) {
  const msg = msgFrom(over);
  msg.snap = snap;
  msg.blob = global.packRoom(msg);
  pr.port.onmessage({ data: msg });
}
function run(pr, n, fill) {
  const inp = [[new Float32Array(BLK), new Float32Array(BLK)]], out = [[new Float32Array(BLK), new Float32Array(BLK)]];
  const buf = new Float32Array(Math.ceil(n / BLK) * BLK * 2);
  let o = 0;
  for (let t0 = 0; t0 < n; t0 += BLK) {
    for (let i = 0; i < BLK; i++) { const v = fill(t0 + i); inp[0][0][i] = v; inp[0][1][i] = v; }
    pr.process(inp, out);
    for (let i = 0; i < BLK; i++) { buf[o++] = out[0][0][i]; buf[o++] = out[0][1][i]; }
  }
  return buf;
}
(async () => {
  const a = await boot();
  const b = await boot();
  deliver(a, { colour_on: false }, true);
  deliver(a, { colour_on: false }, false);
  deliver(b, { audition: 1, colour_on: false }, true);
  const pre = run(b, BLK, () => 0.25);
  for (let i = 0; i < BLK; i++) {
    if (pre[i * 2] !== 0.25 || pre[i * 2 + 1] !== 0.25) throw new Error('audition block is not the dry input');
  }
  deliver(b, { colour_on: false }, false);
  const irA = run(a, N, t => t === 0 ? 1 : 0);
  const irB = run(b, N, t => t === 0 ? 1 : 0);
  fs.writeFileSync(OUTA, Buffer.from(irA.buffer));
  fs.writeFileSync(OUTB, Buffer.from(irB.buffer));
})().catch(e => { console.error(e); process.exit(1); });
"""


def _rms(y: np.ndarray) -> float:
    z = np.asarray(y[len(y) // 2 :], dtype=np.float64)
    return float(np.sqrt(np.mean(z * z)))


def _thd(y: np.ndarray) -> float:
    z = np.asarray(y[len(y) // 2 :], dtype=np.float64)
    per = int(SR // 1000)
    n = (z.size // per) * per
    z = z[:n]
    spec = np.fft.rfft(z)
    scale = 2.0 / n

    def amp(k: int) -> float:
        return abs(spec[k * 1000 * n // SR]) * scale

    fundamental = amp(1)
    harm = sum(amp(k) ** 2 for k in range(2, 16))
    return 100.0 * math.sqrt(harm) / fundamental


def test_play_audition_matches_cli(tmp_path: Path) -> None:
    """610-A at -18 dBFS, Drive 0, comp off. Play's flag against the CLI."""
    sys.path[:0] = [str(SW), str(SW / "engine")]
    import app_server as A  # noqa: E402

    n = SR
    t = np.arange(n, dtype=np.float64) / SR
    tone = ((10.0 ** (-18.0 / 20.0)) * np.sin(2.0 * math.pi * 1000.0 * t)).astype(np.float32)
    pcm = tmp_path / "tone.f32"
    pcm.write_bytes(tone.tobytes())
    dst = tmp_path / "cli.wav"
    line, _dt = _run([
        "--source", "sine", "--dbfs", "-18",
        "--pre", "u610a", "--drive", "0",
        "--comp", "off", "--seconds", "1",
        "--out", str(dst),
    ])
    _sr, cli = wavfile.read(str(dst))
    cli = np.asarray(cli, dtype=np.float64)
    body = {
        "pre_colour": "u610a",
        "pre_drive_db": 0.0,
        "bloom_amount": 0,
        "bloom_colour": False,
        "sample_rate": SR,
    }
    blob = A.live_fdn_params(A.params_from_body(body))
    assert blob.get("pre_colour") and len(blob["pre_colour"]) >= 16
    pj = tmp_path / "params.json"
    pj.write_text(json.dumps(blob), encoding="utf-8")
    out = tmp_path / "play.f32"
    proc = subprocess.run(
        ["node", str(WASM_RUN), str(SW), str(pj), json.dumps({"audition": 1, "colour_on": False}),
         "pcm", str(pcm), str(out)],
        check=False, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    play = np.frombuffer(out.read_bytes(), dtype=np.float32)[0::2].astype(np.float64)
    assert play.shape[0] == n
    db = 20.0 * math.log10(_rms(play) / _rms(cli))
    thd = _thd(play)
    assert abs(db) < 0.1, (db, _rms(play), _rms(cli), line)
    assert abs(thd / PC2_THD - 1.0) < 0.02, (thd, line)


def test_audition_on_then_off_matches_default(tmp_path: Path) -> None:
    """One dry block with the flag on, then off, leaves the reverb bit-exact."""
    sys.path[:0] = [str(SW), str(SW / "engine")]
    import app_server as A  # noqa: E402

    blob = A.live_fdn_params(A.params_from_body({"sample_rate": SR}))
    pj = tmp_path / "params.json"
    pj.write_text(json.dumps(blob), encoding="utf-8")
    script = tmp_path / "cycle.cjs"
    script.write_text(_CYCLE, encoding="utf-8")
    out_a = tmp_path / "a.f32"
    out_b = tmp_path / "b.f32"
    proc = subprocess.run(
        ["node", str(script), str(SW), str(pj), str(out_a), str(out_b), "0.2"],
        check=False, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    a = np.frombuffer(out_a.read_bytes(), dtype=np.float32)
    b = np.frombuffer(out_b.read_bytes(), dtype=np.float32)
    assert a.shape == b.shape and a.size > 0
    assert np.array_equal(a, b)
