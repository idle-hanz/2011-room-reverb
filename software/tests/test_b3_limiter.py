"""B3 / D-AUD-3. Render uses Play's soft_limit. No whole-file scale.

Gate 2 stops the session when Play and Render RMS differ by more than 0.5 dB.
The harness golden scene peaks above 0.95 on this tree, so that file is allowed
to move. A direct-only render under the knee must stay byte-identical.
"""
from __future__ import annotations
import pytest

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
PRE = Path(r"C:\Users\IdleHanz\AppData\Local\Temp\s_audit_b3_pre")
REPORT = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b3_gates.json"
PY = sys.executable
SR = 48000
WASM = SW / "static" / "wasm" / "live_stereo.wasm"

sys.path[:0] = [str(SW)]
from render_pipeline import limiter_message, soft_limit  # noqa: E402


def test_b3_soft_limit_matches_wasm(tmp_path):
    js = r"""
const fs = require('fs');
WebAssembly.instantiate(fs.readFileSync(process.argv[2])).then((m) => {
  const n = 10000;
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) out[i] = m.instance.exports.live_soft(-4 + 8 * i / 9999);
  fs.writeFileSync(process.argv[3], Buffer.from(out.buffer));
}).catch((e) => { console.error(e); process.exit(1); });
"""
    script = tmp_path / "curve.js"
    script.write_text(js, encoding="utf-8")
    dest = tmp_path / "wasm.f32"
    node = shutil.which("node")
    assert node, "node is required"
    r = subprocess.run([node, str(script), str(WASM), str(dest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
    wasm = np.fromfile(dest, dtype=np.float32)
    py = np.array([soft_limit(-4.0 + 8.0 * i / 9999.0) for i in range(10000)], dtype=np.float64)
    diff = float(np.max(np.abs(py - wasm.astype(np.float64))))
    assert diff <= 1e-7, diff
    assert soft_limit(0.95) == 0.95
    assert soft_limit(-0.4) == -0.4
    assert limiter_message(0, 0) == ""
    assert limiter_message(6.75, 12) == "Limiter: peak reduced by 6.8 dB (12 samples)"


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])
    return r.stdout


@pytest.mark.slow
def test_b3_quiet_identical_and_hot_rms(tmp_path):
    """Quiet direct render stays byte-identical. Hot faders agree with Play within 0.5 dB."""
    quiet_out = tmp_path / "quiet.f32"
    # D20. quiet.f32 is the stored ORTF centre. An empty ORTF body is C off.
    quiet_body = {
        "decay_lock": True, "decay_s": 1.8, "colour_mode": "BYPASS",
        "direct_wet": 1.0, "early_wet": 0.0, "fdn_wet": 0.0, "dry_gain": 0.0,
        "third_mic": "centre", "mic_gain_c": 1.0,
        "phys_ceiling": False,
    }
    quiet_proc = subprocess.Popen(
        [PY, str(LIB / "render_ir.py"), str(SW), json.dumps(quiet_body), str(quiet_out), "200", str(SR)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    rng = np.random.default_rng(1)
    n_burst = int(0.35 * SR)
    n_total = int(4.0 * SR)
    dry = np.zeros(n_total, dtype=np.float64)
    dry[:n_burst] = rng.uniform(-0.6, 0.6, n_burst)
    pcm = tmp_path / "burst.f32"
    dry.astype(np.float32).tofile(pcm)
    # D20. The worker omits desk, so this stays the stored centre. Empty ORTF refits makeup.
    hot = {
        "fdn_wet": 3.98, "direct_wet": 3.98, "early_wet": 3.98,
        "colour_mode": "BYPASS", "decay_lock": True, "decay_s": 1.8, "dry_gain": 0.0,
        "third_mic": "centre", "mic_gain_c": 1.0,
        "phys_ceiling": False,
    }
    worker = tmp_path / "hot_render.py"
    worker.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "import numpy as np\n"
        "sw, dry_p, out_p, info_p, body = sys.argv[1:]\n"
        "sys.path[:0] = [sw, sw + '/engine']\n"
        "import os; os.chdir(sw)\n"
        "import app_server as A\n"
        "from render_pipeline import render, limiter_message\n"
        "p = A.params_from_body(dict(A.DEFAULTS, **json.loads(body)))\n"
        "dry = np.fromfile(dry_p, dtype=np.float32).astype(np.float64)\n"
        "kw = dict(W=p['W'], H=p['H'], L=p['L'], sox=p['sox'], soz=p['soz'], mz=p['mz'], my=p['my'], sy=p.get('sy'),\n"
        "    sx=p['sx'], sz=p['sz'], mcz=p['mcz'], space=p['space'], diverg=p['diverg'], car_omni=p['car_omni'],\n"
        "    early_wet=p['early_wet'], fdn_wet=p['fdn_wet'], dry_gain=p['dry_gain'], direct_wet=p.get('direct_wet', 1.0),\n"
        "    fdn_g=p['fdn_g'], ir_length_ms=p['ir_length_ms'], path_on=p['path_on'], path_preset=p['path_preset'],\n"
        "    ellipse_rate=p['ellipse_rate'], ellipse_rx=p['ellipse_rx'], ellipse_rz=p['ellipse_rz'],\n"
        "    mcx=p['mcx'], toe_half_deg=p.get('toe_half_deg'), hadamard_n=p['hadamard_n'],\n"
        "    pattern_l=p.get('pattern_l'), pattern_c=p.get('pattern_c'), pattern_r=p.get('pattern_r'),\n"
        "    yaw_l_deg=p.get('yaw_l_deg'), yaw_c_deg=p.get('yaw_c_deg'), yaw_r_deg=p.get('yaw_r_deg'),\n"
        "    family_l=p.get('family_l'), family_c=p.get('family_c'), family_r=p.get('family_r'),\n"
        "    polar_l=p.get('polar_l'), polar_c=p.get('polar_c'), polar_r=p.get('polar_r'),\n"
        "    centre_dz=p.get('centre_dz') or 0.0, mic_hp_on=p.get('mic_hp_on') or False, mic_hp_hz=p.get('mic_hp_hz') or 40.0,\n"
        "    mic_response_hz=p.get('mic_response_hz') or 10000.0, mic_proximity=p.get('mic_proximity') or 0.0,\n"
        "    ms_decode=bool(p.get('ms_decode')), capsule_mm=p.get('capsule_mm') or 17.0, surfaces=p.get('surfaces'),\n"
        "    diffusion_seed=p['diffusion_seed'], lambda_ref=p['lambda_ref'], humidity=p.get('humidity') or 0.0,\n"
        "    air_lp=0.0,\n"
        "    air_shelf=p.get('air_shelf') if p.get('air_shelf') is not None else 1.0,\n"
        "    reaktor_parity=False,\n"
        "    air_climate=str(p.get('air_climate') or 'studio_20C_50RH'),\n"
        "    air_iso=bool(p.get('air_iso')) if p.get('air_iso') is not None else True,\n"
        "    diffusion_master=p.get('diffusion_master') if p.get('diffusion_master') is not None else -0.5,\n"
        "    decay_s=p.get('decay_s') or 0.0, decay_lock=bool(p.get('decay_lock')),\n"
        "    mic_gain_l=p.get('mic_gain_l', 1.0), mic_gain_c=p.get('mic_gain_c', 1.0), mic_gain_r=p.get('mic_gain_r', 1.0),\n"
        "    mic_pan_l=p.get('mic_pan_l', -1.0), mic_pan_c=p.get('mic_pan_c', 0.0), mic_pan_r=p.get('mic_pan_r', 1.0),\n"
        "    mic_phase_l=p.get('mic_phase_l', 1.0), mic_phase_c=p.get('mic_phase_c', 1.0), mic_phase_r=p.get('mic_phase_r', 1.0),\n"
        "    two_sources=False, source_balance=p.get('source_balance') or 0.0, mirror_b=bool(p.get('mirror_b')),\n"
        "    colour_mode=p.get('colour_mode') or 'MEASURED_SHELF',\n"
        "    mic_preset_l=p.get('mic_preset_l') or 'NeumannU87AiCardioid', mic_preset_c=p.get('mic_preset_c') or 'NeumannU87AiCardioid',\n"
        "    mic_preset_r=p.get('mic_preset_r') or 'NeumannU87AiCardioid', mic_hpf_engaged=bool(p.get('mic_hpf_engaged')),\n"
        "    source_radiation=str(p.get('source_radiation') or 'omni'), source_yaw=float(p.get('source_yaw') or 0.0),\n"
        "    source_pitch=float(p.get('source_pitch') or 0.0), source_size_m=p.get('source_size_m'))\n"
        "L, R, info = render(dry, 48000, **kw)\n"
        "np.stack([L, R], 1).astype(np.float32).tofile(out_p)\n"
        "msg = limiter_message(info.get('limiter_db') or 0, info.get('limiter_samples') or 0)\n"
        "Path(info_p).write_text(json.dumps({'limiter_db': info.get('limiter_db'), 'limiter_samples': info.get('limiter_samples'), 'message': msg, 'n': len(L), 'peak': float(max(np.max(np.abs(L)), np.max(np.abs(R))))}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    hot_out = tmp_path / "hot.f32"
    hot_info = tmp_path / "hot.json"
    hot_proc = subprocess.Popen(
        [PY, str(worker), str(SW), str(pcm), str(hot_out), str(hot_info), json.dumps(hot)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    params = tmp_path / "play.json"
    play_out = tmp_path / "play.f32"
    _run([PY, str(LIB / "dump_params.py"), str(SW), json.dumps(hot), str(params), str(SR)])
    node = shutil.which("node")
    play = subprocess.Popen(
        [node, str(LIB / "wasm_run.js"), str(SW), str(params),
         json.dumps({"colour_on": False}), "pcm", str(pcm), str(play_out)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    q_out, q_err = quiet_proc.communicate()
    assert quiet_proc.returncode == 0, (q_err or q_out)[-800:]
    pre = np.fromfile(PRE / "quiet.f32", dtype=np.float32)
    got = np.fromfile(quiet_out, dtype=np.float32)
    assert pre.shape == got.shape
    assert np.array_equal(pre, got), float(np.max(np.abs(pre.astype(np.float64) - got.astype(np.float64))))

    h_out, h_err = hot_proc.communicate()
    assert hot_proc.returncode == 0, (h_err or h_out)[-800:]
    p_out, p_err = play.communicate()
    assert play.returncode == 0, (p_err or p_out)[-800:]
    info = json.loads(hot_info.read_text(encoding="utf-8"))
    R = np.fromfile(hot_out, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    P = np.fromfile(play_out, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    n = min(len(R), len(P), n_total)
    def rms(x):
        return float(np.sqrt(np.mean(x ** 2)))
    rms_r, rms_p = rms(R[:n]), rms(P[:n])
    rel = 20.0 * np.log10(max(rms_p, 1e-20) / max(rms_r, 1e-20))
    peak_r = float(np.max(np.abs(R)))
    peak_p = float(np.max(np.abs(P)))
    lim = json.loads([ln for ln in p_out.splitlines() if ln.startswith("{")][-1])
    report = {
        "quiet_max_abs": 0.0,
        "hot_rms_delta_db": round(rel, 3),
        "peak_render": round(peak_r, 4),
        "peak_play": round(peak_p, 4),
        "render_message": info.get("message"),
        "limiter_db": info.get("limiter_db"),
        "limiter_samples": info.get("limiter_samples"),
        "play_limiter_windows": len(lim.get("limiter") or []),
    }
    assert abs(rel) <= 0.5, report
    assert peak_r <= 1.0 and peak_p <= 1.0, report
    assert info["limiter_samples"] > 0, report
    assert str(info["message"]).startswith("Limiter: peak reduced by "), report
    assert report["play_limiter_windows"] > 0, report
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
