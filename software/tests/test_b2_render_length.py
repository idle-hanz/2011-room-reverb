"""B2 / D-AUD-2. Render length follows Decay, then a 50 ms raised-cosine fade.

The four-decay test is slow: Decay 8 s is a few minutes. Gate 5 (the render
golden) is written to b2_gates.json and is not a failure. Section 4 regenerates
goldens once, after every Part B item.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / "software"
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
PRE = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b2_pre_item"
REPORT = ROOT / "handoff_build_support_2" / "research_ui_wishlist" / "s_audit" / "b2_gates.json"
GOLDEN = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "golden" / "render_std_unlocked_byp.f32"
PY = sys.executable
SR = 48000

sys.path[:0] = [str(SW), str(LIB)]
from analyze import t60_from_edc  # noqa: E402
from render_pipeline import fade_render_tail, planned_fdn_ms, render_t60_s  # noqa: E402


def test_b2_formula_fade_and_label():
    assert planned_fdn_ms(90, 1500, 1.0) == 1590
    assert planned_fdn_ms(90, 1500, 1.8) == 2790
    assert planned_fdn_ms(90, 1500, 4.0) == 6090
    assert planned_fdn_ms(90, 1500, 8.0) == 12090
    # Harness posts 3000. Do not clamp to the UI maximum of 2000.
    assert planned_fdn_ms(90, 3000, 1.8) == 3000
    assert planned_fdn_ms(90, 1500, 20.0) == 12500
    assert render_t60_s([1000, 1000], 0.02, 32, SR, 1.8, True) == 1.8

    n = SR
    mix = np.ones(n, dtype=np.float64) * 1e-4
    dry = np.zeros(n, dtype=np.float64)
    out_l, out_r = fade_render_tail(mix, mix.copy(), mix, mix.copy(), dry, 0.0, 1, SR)
    nfade = int(round(SR * 0.050))
    assert abs(out_l[-1]) < 1e-12
    assert out_l[-(nfade + 1)] == mix[-(nfade + 1)]
    step = float(np.max(np.abs(np.diff(out_l[-int(0.1 * SR):]))))
    assert step <= 1e-5

    html = (SW / "static" / "index.html").read_text(encoding="utf-8")
    assert "Minimum IR length" in html
    assert 'id="ir_length_ms" min="50" max="2000" step="10" value="1500"' in html
    app = (SW / "static" / "js" / "app.js").read_text(encoding="utf-8")
    assert "Rendering… FDN " in app
    assert 'app.js?v=65' in html


def _t30(x: np.ndarray) -> float:
    energy = x[:, 0] ** 2 + x[:, 1] ** 2
    e = np.cumsum(energy[::-1])[::-1]
    edc = 10.0 * np.log10(np.maximum(e / max(float(e[0]), 1e-300), 1e-300))
    return float(t60_from_edc(edc, SR, hi=-5.0, lo=-35.0))


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError((r.stderr or r.stdout)[-800:])
    return r.stdout


def _render(body: dict, ms: str, dest: Path) -> dict:
    out = _run([PY, str(LIB / "render_ir.py"), str(SW), json.dumps(body), str(dest), ms, str(SR)])
    line = [ln for ln in out.splitlines() if ln.startswith("{")][-1]
    return json.loads(line)


def _play(body: dict, secs: float, dest: Path, work: Path, tag: str) -> None:
    params = work / f"play_{tag}.json"
    _run([PY, str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(params), str(SR)])
    node = shutil.which("node")
    assert node, "node is required for the Play T30"
    _run([
        node, str(LIB / "wasm_run.js"), str(SW), str(params),
        json.dumps({"colour_on": False}), "ir", str(secs), str(dest),
    ])


def _tail_db(x: np.ndarray) -> float:
    peak = float(np.max(np.abs(x)))
    tail = x[-int(0.05 * SR):]
    return 20.0 * np.log10(float(np.max(np.abs(tail))) / max(peak, 1e-300))


def _step(x: np.ndarray) -> float:
    seg = x[-int(0.10 * SR):]
    return float(np.max(np.abs(np.diff(seg, axis=0))))


def test_b2_t30_tail_and_prefix(tmp_path):
    """Gates 1–4. Decay 8 s dominates the runtime."""
    cases = (1.0, 1.8, 4.0, 8.0)
    play_s = {1.0: 4.0, 1.8: 6.0, 4.0: 8.0, 8.0: 12.0}
    procs = []
    for decay in cases:
        # D20. d18.f32 and d4.f32 are the stored ORTF centre. An empty ORTF body is C off.
        # Those prefixes are the Smooth-off render. T4c's missing key is on.
        # TLAW 1/r (Idle 2026-10-10) regenerated the 72001-frame heads.
        # The full renders stay 133921 frames at 1.8 s and 292321 frames at 4 s.
        body = {
            "decay_lock": True, "decay_s": decay, "colour_mode": "BYPASS",
            "third_mic": "centre", "mic_gain_c": 1.0,
            "smooth": False,
        }
        tag = str(decay).replace(".", "p")
        rend = tmp_path / f"r_{tag}.f32"
        play = tmp_path / f"p_{tag}.f32"
        rp = subprocess.Popen(
            [PY, str(LIB / "render_ir.py"), str(SW), json.dumps(body), str(rend), "1500", str(SR)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        pp = subprocess.Popen(
            [PY, str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(tmp_path / f"play_{tag}.json"), str(SR)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        procs.append((decay, body, tag, rend, play, rp, pp))

    node = shutil.which("node")
    assert node, "node is required for the Play T30"
    play_procs = []
    rows = []
    for decay, body, tag, rend, play, rp, pp in procs:
        pout, perr = pp.communicate()
        assert pp.returncode == 0, (perr or pout)[-800:]
        wp = subprocess.Popen(
            [node, str(LIB / "wasm_run.js"), str(SW), str(tmp_path / f"play_{tag}.json"),
             json.dumps({"colour_on": False}), "ir", str(play_s[decay]), str(play)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        play_procs.append((decay, tag, rend, play, rp, wp))

    report = {"cases": []}
    for decay, tag, rend, play, rp, wp in play_procs:
        rout, rerr = rp.communicate()
        assert rp.returncode == 0, (rerr or rout)[-800:]
        wout, werr = wp.communicate()
        assert wp.returncode == 0, (werr or wout)[-800:]
        meta = json.loads([ln for ln in rout.splitlines() if ln.startswith("{")][-1])
        R = np.fromfile(rend, dtype=np.float32).reshape(-1, 2)
        P = np.fromfile(play, dtype=np.float32).reshape(-1, 2)
        t_r = _t30(R.astype(np.float64))
        t_p = _t30(P.astype(np.float64))
        dur = len(R) / float(SR)
        tail = _tail_db(R.astype(np.float64))
        step = _step(R.astype(np.float64))
        row = {
            "decay_s": decay,
            "n": int(len(R)),
            "duration_s": round(dur, 4),
            "render_s": meta.get("secs"),
            "t30_render": None if t_r != t_r else round(t_r, 4),
            "t30_play": None if t_p != t_p else round(t_p, 4),
            "tail_50ms_db": round(tail, 2),
            "step_100ms": step,
            "fdn_ms_from_n": round((len(R) - 1) / SR * 1000.0, 3),
        }
        if decay in (1.8, 4.0):
            pre_name = "d18.f32" if decay == 1.8 else "d4.f32"
            pre = np.fromfile(PRE / pre_name, dtype=np.float32).reshape(-1, 2)
            npre = len(pre)
            diff = np.max(np.abs(pre.astype(np.float64) - R[:npre].astype(np.float64)))
            row["pre_n"] = int(npre)
            row["prefix_max_abs"] = float(diff)
            y = R.astype(np.float64)
            cut = float(np.sqrt(np.mean(np.sum(y[npre - int(0.05 * SR):npre] ** 2, axis=1))))
            pk = float(np.max(np.abs(y)))
            row["level_at_old_cut_db"] = round(20.0 * np.log10(cut / max(pk, 1e-300)), 2)
            row["added_energy_db"] = round(
                10.0 * np.log10(float(np.sum(y[npre:] ** 2)) / max(float(np.sum(y ** 2)), 1e-300)), 2,
            )
            row["t30_pre"] = round(_t30(pre.astype(np.float64)), 4)
            assert diff == 0.0, f"decay {decay}: prefix max-abs {diff}"
        assert dur <= 12.5, f"decay {decay}: duration {dur}"
        assert t_r == t_r and t_p == t_p, f"decay {decay}: T30 render {t_r} play {t_p}"
        rel = abs(t_r - t_p) / t_p
        row["t30_rel"] = round(rel, 4)
        assert rel <= 0.05, f"decay {decay}: T30 render {t_r:.4f} vs play {t_p:.4f} ({rel:.3%})"
        assert tail <= -90.0, f"decay {decay}: last 50 ms {tail:.1f} dB"
        assert step <= 1e-5, f"decay {decay}: step {step}"
        report["cases"].append(row)

    # Gate 5. Record the render golden. Do not fail the test when the fade moves it.
    gbody = {
        "decay_lock": False, "fdn_g": 0.8, "humidity": 0.5, "early_wet": 1.0,
        "colour_mode": "BYPASS", "direct_wet": 1, "fdn_wet": 1,
    }
    gdest = tmp_path / "golden_render.f32"
    _render(gbody, "500", gdest)
    got = np.fromfile(gdest, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    ref = np.fromfile(GOLDEN, dtype=np.float32).reshape(-1, 2).astype(np.float64)
    n = min(len(got), len(ref))
    null = 10.0 * np.log10(
        max(float(np.sum((got[:n] - ref[:n]) ** 2)), 1e-300) / max(float(np.sum(ref[:n] ** 2)), 1e-300)
    )
    report["golden"] = {
        "name": "render_std_unlocked_byp.f32",
        "null_db": round(float(null), 2),
        "max_abs": float(np.max(np.abs(got[:n] - ref[:n]))),
        "n_new": int(len(got)),
        "n_golden": int(len(ref)),
        "same_length": bool(len(got) == len(ref)),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
