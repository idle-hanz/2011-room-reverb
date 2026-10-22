"""Bloom gates that do not render a room: colour unity, glue key, alias, clicks.

Writes roadmap/overnight/bloom_gates.json. Does not change product code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\IdleHanz\Desktop\2011 Room Reverb")
SW = ROOT / "software"
R3 = ROOT / "handoff_build_support_2" / "roadmap" / "bloom" / "uad" / "round3"
sys.path[:0] = [str(SW), str(SW / "engine"), str(R3 / "scripts")]

import app_server as A  # noqa: E402
import bloom_dsp  # noqa: E402
from alias import tone_alias  # noqa: E402
from render_pipeline import live_fdn_params  # noqa: E402

SR = 48000
NODE = (
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages"
    r"\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\node-v26.7.0-win-x64\node.exe"
)
WASM = (
    ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests"
    / "harness" / "lib" / "wasm_run.js"
)
OUT = ROOT / "handoff_build_support_2" / "roadmap" / "overnight" / "bloom_gates.json"
UNIT = {
    "la2as_pr50": "natural",
    "ssl_4_auto": "glue",
    "fet_all": "room_crush",
    "fc_t5": "swell",
    "dis_nuke_room": "nuke",
}


def colour_gain(preset: str) -> dict:
    """1 kHz at -80 dBFS through the shipped shaper and EQ. Linear path should stay near 0 dB."""
    body = {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True}
    if preset == "glue":
        body["glue_colour"] = True
    spec = bloom_dsp.design(body, SR)
    pack = bloom_dsp.pack_coeffs(spec)
    n = SR
    t = np.arange(n) / SR
    x = (10.0 ** (-80.0 / 20.0)) * np.sin(2.0 * np.pi * 1000.0 * t)
    st = bloom_dsp._Colour(pack)
    y = np.empty_like(x)
    for i, v in enumerate(x):
        z = st.shape(float(v), 0.0, 1.0)
        y[i] = st.eq(z)
    a = y[SR // 2:]
    b = x[SR // 2:]
    den = float(np.dot(b, b))
    g = float(np.dot(a, b) / den) if den else 0.0
    db = float(20.0 * np.log10(max(abs(g), 1e-12)))
    return {"preset": preset, "gain_db": round(db, 4), "inside_0p05": abs(db) <= 0.05}


def glue_key() -> dict:
    x = np.random.default_rng(1).standard_normal(SR // 2) * 0.05
    def run(body):
        spec = bloom_dsp.design(body, SR)
        g, gr = bloom_dsp._gain_env(x, spec)
        pack = bloom_dsp.pack_coeffs(spec)
        return pack[26], g, pack
    p_off, g_off, pack_off = run({"bloom_preset": "glue", "bloom_amount": 100})
    p_false, g_false, _ = run({
        "bloom_preset": "glue", "bloom_amount": 100, "glue_colour": False, "bloom_colour": True,
    })
    p_on, _g_on, pack_on = run({
        "bloom_preset": "glue", "bloom_amount": 100, "glue_colour": True, "bloom_colour": True,
    })
    return {
        "colour_flag_absent": p_off,
        "colour_flag_explicit_false": p_false,
        "colour_flag_on": p_on,
        "gain_max_abs_false_vs_absent": float(np.max(np.abs(g_off - g_false))),
        "pack_colour_slots_differ_when_on": float(np.max(np.abs(
            np.asarray(pack_on[26:40]) - np.asarray(pack_off[26:40])
        ))),
    }


def parse_uad(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "M1 alias" not in line:
            continue
        head, rest = line.split("|", 1)
        bits = head.split()
        unit, freq, level = bits[0], int(bits[1]), float(bits[2])
        m1 = float(rest.split("M1 alias")[1].split("dBFS")[0])
        rows.append((unit, freq, level, m1))
    return rows


def run_colour_tone(preset: str, freq: float, level_db: float) -> np.ndarray:
    body = {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True}
    if preset == "glue":
        body["glue_colour"] = True
    spec = bloom_dsp.design(body, SR)
    n = SR
    t = np.arange(n) / SR
    x = (10.0 ** (level_db / 20.0)) * np.sin(2.0 * np.pi * freq * t)
    g, gr = bloom_dsp._gain_env(x, spec)
    pack = bloom_dsp.pack_coeffs(spec)
    st = bloom_dsp._Colour(pack)
    swell = pack[38] > 0.5 and pack[26] > 0.5
    y = np.empty(n)
    for i in range(n):
        v = float(x[i])
        if swell:
            v = st.shape(v, float(gr[i]), 1.0)
            v *= float(g[i])
            v = st.eq(v)
        else:
            v = v * float(g[i])
            v = st.shape(v, float(gr[i]), 1.0)
            v = st.eq(v)
        y[i] = v
    return y


def alias_comps() -> list:
    out = []
    for unit, freq, level, uad in parse_uad(R3 / "data" / "alias_uad.txt"):
        preset = UNIT[unit]
        y = run_colour_tone(preset, freq, level)
        m = tone_alias(y, freq)
        m1 = m["m1_worst_alias_dbfs"]
        m2 = m["m2_peak_below16k_dbfs"]
        ok = (m1 <= uad - 10.0 or m1 <= -90.0) and (m2 <= -90.0 or m2 <= uad - 10.0)
        row = {
            "preset": preset, "hz": freq, "dbfs": level,
            "uad_m1": uad, "ours_m1": round(m1, 2), "ours_m2_16k": round(m2, 2),
            "pass": bool(ok),
        }
        out.append(row)
        print("ALIAS", preset, freq, level, "m1", round(m1, 1), "uad", uad, "pass", ok, flush=True)
    return out


def alias_pres() -> list:
    """UAD numbers from alias_pre_os.txt. Shipped pres are both 8x."""
    text = (R3 / "data" / "alias_pre_os.txt").read_text(encoding="utf-8")
    want = {}
    for line in text.splitlines():
        if not line.startswith("neve ") and not line.startswith("u610a "):
            continue
        # keep one UAD figure per kind/freq/level. 8x rows are the shipped rate.
        bits = line.split()
        if len(bits) < 8 or bits[1] != "8x":
            continue
        kind, freq, level = bits[0], int(bits[2][1:]), float(bits[3][1:])
        uad = float(line.split("UAD")[1].split("|")[0])
        want[(kind, freq, level)] = uad
    out = []
    for (kind, freq, level), uad in sorted(want.items()):
        name = "neve1073" if kind == "neve" else "u610a"
        spec = bloom_dsp.design({
            "bloom_amount": 0, "pre_colour": name, "pre_drive_db": 0.0,
        }, SR)
        n = SR
        t = np.arange(n) / SR
        x = (10.0 ** (level / 20.0)) * np.sin(2.0 * np.pi * freq * t)
        y = bloom_dsp._pre_bus(x, bloom_dsp.pack_pre(spec))
        m = tone_alias(y, freq)
        m1 = m["m1_worst_alias_dbfs"]
        m2 = m["m2_peak_below16k_dbfs"]
        ok = (m1 <= uad - 10.0 or m1 <= -90.0) and (m2 <= -90.0 or m2 <= uad - 10.0)
        row = {
            "pre": kind, "hz": freq, "dbfs": level, "uad_m1": uad,
            "ours_m1": round(m1, 2), "ours_m2_16k": round(m2, 2), "pass": bool(ok),
        }
        out.append(row)
        print("ALIAS_PRE", kind, freq, level, "m1", round(m1, 1), "uad", uad, "pass", ok, flush=True)
    return out


def clicks() -> dict:
    work = OUT.parent / "_click"
    work.mkdir(parents=True, exist_ok=True)
    base = A.params_from_body({})
    live = live_fdn_params(base)

    def pack(body):
        p = A.params_from_body(body)
        return live_fdn_params(p)

    variants = {
        "off": {},
        "nuke": {"bloom_preset": "nuke", "bloom_amount": 100, "bloom_colour": True},
        "natural": {"bloom_preset": "natural", "bloom_amount": 100, "bloom_colour": True},
        "pre": {"bloom_amount": 0, "pre_colour": "u610a", "pre_drive_db": 6},
        "drive": {"bloom_amount": 0, "pre_colour": "neve1073", "pre_drive_db": 12},
    }
    blobs = {}
    for name, body in variants.items():
        got = pack(body)
        over = {}
        if got.get("bloom"):
            over["bloom"] = got["bloom"]
        else:
            over["bloom"] = []
        if got.get("pre_colour"):
            over["pre_colour"] = got["pre_colour"]
        else:
            over["pre_colour"] = []
        over["predelay_n"] = got.get("predelay_n") or 0
        blobs[name] = over
    times = (0.40, 0.80, 1.20, 1.60, 2.00)
    on_sched = [
        [0.40, blobs["nuke"]],
        [0.80, blobs["natural"]],
        [1.20, blobs["pre"]],
        [1.60, blobs["drive"]],
        [2.00, blobs["off"]],
    ]
    off_sched = [[t, blobs["off"]] for t in times]
    params = work / "p.json"
    params.write_text(json.dumps(live), encoding="utf-8")

    def run(sched, dest):
        proc = subprocess.run(
            [NODE, str(WASM), str(SW), str(params), "{}", "switch",
             "2.2", "2.6", str(dest), json.dumps(sched)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout)[-600:])
        y = np.fromfile(dest, np.float32).reshape(-1, 2)
        return y

    on = run(on_sched, work / "on.f32")
    off = run(off_sched, work / "off.f32")

    def window(y, t, n=128):
        i = int(t * SR)
        seg = y[max(0, i - 2):i + n]
        return float(np.max(np.abs(np.diff(seg, axis=0))))

    rows = []
    worst = 0.0
    for t in times:
        a, b = window(on, t), window(off, t)
        extra = a - b
        worst = max(worst, extra)
        rows.append({"t": t, "on_step": round(a, 6), "off_step": round(b, 6), "extra": round(extra, 6)})
        print("CLICK", t, "on", round(a, 5), "off", round(b, 5), flush=True)
    return {"windows": rows, "worst_extra": round(worst, 6)}


def main() -> None:
    report = {
        "colour_small_signal": [colour_gain(p) for p in ("natural", "glue", "room_crush", "nuke", "swell")],
        "glue_key": glue_key(),
    }
    print("COLOUR", report["colour_small_signal"], flush=True)
    print("GLUE", report["glue_key"], flush=True)
    report["alias_comp"] = alias_comps()
    report["alias_pre"] = alias_pres()
    report["clicks"] = clicks()
    report["alias_comp_fail"] = [r for r in report["alias_comp"] if not r["pass"]]
    report["alias_pre_fail"] = [r for r in report["alias_pre"] if not r["pass"]]
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("GATES_DONE", "comp_fail", len(report["alias_comp_fail"]),
          "pre_fail", len(report["alias_pre_fail"]), flush=True)


if __name__ == "__main__":
    main()
