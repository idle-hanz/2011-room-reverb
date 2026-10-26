"""Movement knob. Default 0 stays off. Knob 100 is 0.15 ms on Play and Render.

Play packs section 8 from movement_ms. Render passes the same percent into
movement_peak_ms. Parity, flat cards, mirror/null, and a direct-only body stay 0.

The wasm sample goes through pushParams. Knob 0 stays the empty and centre
live scenes. Knob 100 changes the impulse. Play against the Python render,
FDN only and colour bypass, is an accepted parity gap (ring allpass against
history allpass). The floor is -58 dB left and -48 dB right.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import render_pipeline as rp  # noqa: E402

EMPTY_MD5 = "067adbca1930efcd3f7c83bdd1d4c359"
CENTRE_MD5 = "35db578a18557d5729c0450e26f24a9d"
EMPTY_MOVE_MAX = 0.173830654
CENTRE_MOVE_MAX = 0.116135473
MOVE_TOL = 1e-6
NULL_L_DB = -58.0
NULL_R_DB = -48.0
SR = 48000
SECS = 0.25
NCMP = 12000


def _section_ids(blob):
    n = int(blob[3])
    directory = blob[5:5 + 4 * n]
    return [directory[i] for i in range(0, len(directory), 4)]


def _section_payload(blob, sid):
    n = int(blob[3])
    directory = blob[5:5 + 4 * n]
    for i in range(0, len(directory), 4):
        if directory[i] == sid:
            off = int(directory[i + 1])
            ln = int(directory[i + 2])
            return blob[off:off + ln]
    return None


def test_flag_is_off_and_curve_holds():
    assert rp.MOVEMENT_FORCED_OFF is False
    assert rp.movement_peak_ms({}) == 0.0
    assert rp.movement_peak_ms({"movement": 0}) == 0.0
    assert rp.movement_peak_ms({"movement": 50}) == pytest.approx(0.10)
    assert rp.movement_peak_ms({"movement": 100}) == pytest.approx(0.15)
    assert rp.movement_peak_ms({"movement": 100, "mirror_null": True}) == 0.0
    assert rp.movement_peak_ms({"movement": 100, "fdn_wet": 0.0, "early_wet": 0.0}) == 0.0


def test_play_packs_knob_and_default_omits_section_8():
    off = A.live_fdn_params(A.params_from_body({}))
    assert float(off.get("movement_ms") or 0.0) == 0.0
    assert 8.0 not in _section_ids(rp.pack_blob_v2(off))
    on = A.live_fdn_params(A.params_from_body({"movement": 100}))
    assert on["movement_ms"] == pytest.approx(0.15)
    assert _section_payload(rp.pack_blob_v2(on), 8.0) == pytest.approx([0.15])


def test_render_takes_the_same_knob():
    assert "movement" in inspect.signature(rp._render_core).parameters
    text = (SW / "render_pipeline.py").read_text(encoding="utf-8")
    assert '"movement": movement,' in text
    server = (SW / "app_server.py").read_text(encoding="utf-8")
    assert 'movement=float(p.get("movement") or 0.0)' in server
    assert rp.movement_peak_ms(
        {"reaktor_parity": False, "movement": 100, "fdn_wet": 1.0, "early_wet": 1.0},
        None,
    ) == pytest.approx(0.15)
    assert rp.movement_peak_ms(
        {"reaktor_parity": False, "movement": 0, "fdn_wet": 1.0, "early_wet": 1.0},
        None,
    ) == 0.0


def test_knob_is_visible_and_defaults_to_zero():
    page = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="movementRow" hidden' not in page
    assert 'id="movement" min="0" max="100" step="1" value="0"' in page
    app = (SW / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "movement: 0" in app


def _md5(blob) -> str:
    return hashlib.md5(json.dumps(blob, sort_keys=True, default=str).encode()).hexdigest()


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])


# Posts the dumped live dict through live_fdn.js pushParams, then runs that
# message on the shipped worklet. movement_ms is forwarded only when it is > 0.
_PUSH_JS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const [SW, PJ, OUT, SECS] = process.argv.slice(2);
const SR = 48000, BLK = 128;
const reg = {};
const errors = [];
class AWP { constructor() { this.port = { postMessage: (m) => { if (m) errors.push(m); }, onmessage: null }; } }
const packJs = fs.readFileSync(path.join(SW, 'static/js/pack_room.js'), 'utf8');
const workJs = fs.readFileSync(path.join(SW, 'static/js/fdn_worklet.js'), 'utf8');
new Function('AudioWorkletProcessor', 'registerProcessor', 'sampleRate', packJs + '\n' + workJs)(AWP, (n, c) => { reg[n] = c; }, SR);
let live = fs.readFileSync(path.join(SW, 'static/js/live_fdn.js'), 'utf8');
const needle = 'var node = null;';
if (!live.includes(needle)) throw new Error('pushParams node binding moved');
live = live.replace(needle, 'var node = { port: { postMessage: function (m) { global.__posted = m; } } };');
const sandbox = {
  console, setTimeout, clearTimeout, Float32Array, Float64Array, Int32Array,
  Uint8Array, ArrayBuffer, WebAssembly, Date, Math, Number, String, Object, Array,
  isFinite, isNaN, performance: { now: () => Date.now() },
  document: { getElementById: () => null }
};
sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(packJs + '\n' + live, sandbox);
const params = JSON.parse(fs.readFileSync(PJ, 'utf8'));
sandbox.LiveFDN.update(params);
const msg = sandbox.__posted;
if (!msg || !msg.blob) throw new Error('pushParams posted no room blob');
const want = Number(params.movement_ms) || 0;
const got = Number(msg.movement_ms) || 0;
if (want > 0) {
  if (!(got > 0)) throw new Error('pushParams dropped movement_ms ' + got);
} else if (got > 0) {
  throw new Error('pushParams added movement_ms ' + got);
}
const wasmBytes = fs.readFileSync(path.join(SW, 'static/wasm/live_stereo.wasm'));
const pr = new reg['room-fdn']({ processorOptions: { wasm: wasmBytes } });
(async () => {
  for (let i = 0; i < 100 && !pr.ready; i++) await new Promise(r => setTimeout(r, 20));
  if (!pr.ready) throw new Error('wasm not ready ' + JSON.stringify(errors));
  pr.port.onmessage({ data: msg });
  if (errors.length) throw new Error('worklet ' + JSON.stringify(errors));
  const total = Math.round(+SECS * SR);
  const inp = [[new Float32Array(BLK), new Float32Array(BLK)]];
  const out = [[new Float32Array(BLK), new Float32Array(BLK)]];
  const buf = new Float32Array(Math.ceil(total / BLK) * BLK * 2);
  let o = 0;
  for (let t0 = 0; t0 < total; t0 += BLK) {
    for (let i = 0; i < BLK; i++) {
      const v = (t0 + i) === 0 ? 1 : 0;
      inp[0][0][i] = v; inp[0][1][i] = v;
    }
    pr.process(inp, out);
    for (let i = 0; i < BLK; i++) { buf[o++] = out[0][0][i]; buf[o++] = out[0][1][i]; }
  }
  fs.writeFileSync(OUT, Buffer.from(buf.buffer, buf.byteOffset, buf.byteLength));
})().catch(e => { console.error(e); process.exit(1); });
"""


def _dump(body, dest):
    _run([
        sys.executable, str(LIB / "dump_params.py"), str(SW),
        json.dumps(body), str(dest), str(SR),
    ])


def _push(script, params, dest):
    node = shutil.which("node")
    assert node, "node is required"
    _run([node, str(script), str(SW), str(params), str(dest), str(SECS)])
    raw = np.fromfile(dest, dtype=np.float32)
    return raw.reshape(-1, 2).astype(np.float64)


def _null_db(a, b) -> float:
    d = a - b
    num = float(np.sum(d ** 2))
    den = float(np.sum(a ** 2))
    return 10.0 * float(np.log10(max(num, 1e-300) / max(den, 1e-300)))


def _py_render(body):
    """Same Render call as the 2026-10-24 FDN-only score. First 12000 samples."""
    p = A.params_from_body(dict(body))
    dry = np.zeros(1)
    dry[0] = 1.0
    sig = inspect.signature(rp.render).parameters
    kw = dict(
        W=p["W"], H=p["H"], L=p["L"], sox=p["sox"], soz=p["soz"], mz=p["mz"], my=p["my"], sy=p.get("sy"),
        sx=p["sx"], sz=p["sz"], mcz=p["mcz"], space=p["space"], diverg=p["diverg"], car_omni=p["car_omni"],
        early_wet=p["early_wet"], fdn_wet=p["fdn_wet"], dry_gain=p["dry_gain"], direct_wet=p.get("direct_wet", 1.0),
        fdn_g=p["fdn_g"], ir_length_ms=p["ir_length_ms"], path_on=p["path_on"], path_preset=p["path_preset"],
        ellipse_rate=p["ellipse_rate"], ellipse_rx=p["ellipse_rx"], ellipse_rz=p["ellipse_rz"],
        mcx=p["mcx"], toe_half_deg=p.get("toe_half_deg"), hadamard_n=p["hadamard_n"],
        pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
        yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
        family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
        polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
        centre_dz=p.get("centre_dz") or 0.0, mic_hp_on=p.get("mic_hp_on") or False, mic_hp_hz=p.get("mic_hp_hz") or 40.0,
        mic_response_hz=p.get("mic_response_hz") or 10000.0, mic_proximity=p.get("mic_proximity") or 0.0,
        ms_decode=bool(p.get("ms_decode")), capsule_mm=p.get("capsule_mm") or 17.0, surfaces=p.get("surfaces"),
        diffusion_seed=p["diffusion_seed"], lambda_ref=p["lambda_ref"], humidity=p.get("humidity") or 0.0,
        air_lp=p.get("air_lp") if p.get("air_lp") is not None else 0.25,
        air_shelf=p.get("air_shelf") if p.get("air_shelf") is not None else 1.0,
        reaktor_parity=bool(p.get("reaktor_parity")),
        air_climate=str(p.get("air_climate") or "studio_20C_50RH"),
        air_iso=bool(p.get("air_iso")) if p.get("air_iso") is not None else True,
        diffusion_master=p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.5,
        decay_s=p.get("decay_s") or 0.0, decay_lock=bool(p.get("decay_lock")),
        mic_gain_l=p.get("mic_gain_l", 1.0), mic_gain_c=p.get("mic_gain_c", 1.0), mic_gain_r=p.get("mic_gain_r", 1.0),
        mic_pan_l=p.get("mic_pan_l", -1.0), mic_pan_c=p.get("mic_pan_c", 0.0), mic_pan_r=p.get("mic_pan_r", 1.0),
        mic_phase_l=p.get("mic_phase_l", 1.0), mic_phase_c=p.get("mic_phase_c", 1.0), mic_phase_r=p.get("mic_phase_r", 1.0),
        two_sources=False, source_balance=p.get("source_balance") or 0.0, mirror_b=bool(p.get("mirror_b")),
        sx_b=p.get("sx_b"), sy_b=p.get("sy_b"), sz_b=p.get("sz_b"),
        colour_mode=p.get("colour_mode") or "MEASURED_SHELF",
        mic_preset_l=p.get("mic_preset_l") or "NeumannU87AiCardioid",
        mic_preset_c=p.get("mic_preset_c") or "NeumannU87AiCardioid",
        mic_preset_r=p.get("mic_preset_r") or "NeumannU87AiCardioid",
        mic_hpf_engaged=bool(p.get("mic_hpf_engaged")),
        source_radiation=str(p.get("source_radiation") or "omni"),
        source_yaw=float(p.get("source_yaw") or 0.0),
        source_pitch=float(p.get("source_pitch") or 0.0),
    )
    if "smooth" in sig:
        kw["smooth"] = bool(p["smooth"]) if "smooth" in p else True
    if "movement" in sig:
        kw["movement"] = float(p.get("movement") or 0.0)
    if "mirror_null" in sig:
        kw["mirror_null"] = bool(p.get("mirror_null"))
    if "desk" in sig:
        kw["desk"] = p
    for k in ("prox_l", "prox_c", "prox_r"):
        if k in sig:
            kw[k] = bool(p.get(k, True))
    if p.get("sub_hp"):
        kw["sub_hp"] = True
    if p.get("phys_ceiling"):
        kw["phys_ceiling"] = True
    y_l, y_r, _info = rp.render(dry, SR, **kw)
    return np.stack([np.asarray(y_l, np.float64), np.asarray(y_r, np.float64)], 1)


@pytest.mark.slow
def test_section_8_changes_a_play_sample(tmp_path):
    """Shipped wasm, through pushParams. Knob 0 is the pinned live scene.

    Knob 100 packs 0.15 ms and moves the 0.25 s impulse by the pinned max-abs.
    FDN only, colour bypass, first 12000 samples: Play against Render stays
    at or under -58 dB left and -48 dB right. Measured 2026-10-24 was
    -60.51 dB left and -50.69 dB right. Accepted parity gap.
    """
    empty = {"movement": 0}
    centre = {"third_mic": "centre", "mic_gain_c": 1.0, "movement": 0}
    empty_on = {"movement": 100}
    centre_on = {"third_mic": "centre", "mic_gain_c": 1.0, "movement": 100}
    fdn_on = {
        "movement": 100, "early_wet": 0, "direct_wet": 0, "fdn_wet": 1,
        "colour_mode": "BYPASS", "dry_gain": 0,
    }
    assert _md5(A.live_fdn_params(A.params_from_body({}))) == EMPTY_MD5
    assert _md5(A.live_fdn_params(A.params_from_body(empty))) == EMPTY_MD5
    assert _md5(A.live_fdn_params(A.params_from_body(
        {"third_mic": "centre", "mic_gain_c": 1.0}
    ))) == CENTRE_MD5
    assert _md5(A.live_fdn_params(A.params_from_body(centre))) == CENTRE_MD5
    assert 8.0 not in _section_ids(rp.pack_blob_v2(A.live_fdn_params(A.params_from_body(empty))))
    on = A.live_fdn_params(A.params_from_body(empty_on))
    assert on["movement_ms"] == pytest.approx(0.15)
    assert _section_payload(rp.pack_blob_v2(on), 8.0) == pytest.approx([0.15])

    script = tmp_path / "push_ir.js"
    script.write_text(_PUSH_JS, encoding="utf-8")
    played = {}
    for name, body in (
        ("empty", {}),
        ("empty0", empty),
        ("centre", {"third_mic": "centre", "mic_gain_c": 1.0}),
        ("centre0", centre),
        ("empty100", empty_on),
        ("centre100", centre_on),
        ("fdn100", fdn_on),
    ):
        params = tmp_path / f"{name}.json"
        _dump(body, params)
        played[name] = _push(script, params, tmp_path / f"{name}.f32")

    assert float(np.max(np.abs(played["empty"] - played["empty0"]))) == 0.0
    assert float(np.max(np.abs(played["centre"] - played["centre0"]))) == 0.0
    empty_move = float(np.max(np.abs(played["empty"] - played["empty100"])))
    centre_move = float(np.max(np.abs(played["centre"] - played["centre100"])))
    assert empty_move == pytest.approx(EMPTY_MOVE_MAX, abs=MOVE_TOL)
    assert centre_move == pytest.approx(CENTRE_MOVE_MAX, abs=MOVE_TOL)

    py = _py_render(fdn_on)
    play = played["fdn100"]
    left = _null_db(play[:NCMP, 0], py[:NCMP, 0])
    right = _null_db(play[:NCMP, 1], py[:NCMP, 1])
    assert left <= NULL_L_DB, left
    assert right <= NULL_R_DB, right
