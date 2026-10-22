"""AMBIENCE listens. Clean guitar, same render method as smalldecay/make_listens.py.

Writes roadmap/ambience/listen/. Does not touch the original guitar or the
SMALLDECAY wavs.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[3]
SW = ROOT / "software"
SMALL = ROOT / "handoff_build_support_2" / "roadmap" / "smalldecay"
sys.path[:0] = [str(SW), str(SW / "engine"), str(SMALL)]

import make_listens as ML  # noqa: E402
import surf_loop as SL  # noqa: E402

HERE = Path(__file__).resolve().parent
LISTEN = HERE / "listen"
REPORT = LISTEN / "listen_report.json"
CLEAN = (
    ROOT
    / "handoff_build_support_2"
    / "roadmap"
    / "robotic_1240"
    / "test_guitar_dualmono_clean.wav"
)
ORIG = ML.GUITAR
NODE = (
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages"
    r"\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\node-v26.7.0-win-x64\node.exe"
)
LIB = ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests" / "harness" / "lib"
SR = 48000
FADE = int(round(0.050 * SR))
ROOMS = ("boot_6x3x8", "4.5x6x2.8", "3x4x2.5", "2x2.5x2.2")


def load_wav(path, n=None):
    sr, raw = wavfile.read(path)
    if int(sr) != SR:
        raise RuntimeError(f"sr {sr} {path}")
    g = raw[:, 0].astype(np.float64) / 32768.0
    if n is None:
        n = int(round(8.0 * SR))
    return g[:n]


def energy_under(x, f0=20.0):
    x = np.asarray(x, float)
    if x.ndim == 2:
        x = x[:, 0] + x[:, 1]
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    p = np.abs(spec) ** 2
    return float(np.sum(p[freqs < f0]) / max(float(np.sum(p)), 1e-300))


def true_peak(L, R):
    n = min(len(L), len(R))
    stereo = np.column_stack([np.asarray(L[:n], float), np.asarray(R[:n], float)])
    up = resample_poly(stereo, 4, 1, axis=0)
    return float(np.max(np.abs(up)))


# Boot B_phys proper T20, 63 Hz-4 kHz. PHYSDEFAULT pin. Stop if 125 Hz-4 kHz is off.
BOOT_B_PIN = [1.9378, 2.3200, 2.3160, 1.9902, 1.5721, 1.1137, 0.8487]
F9_OUT = ROOT / "handoff_build_support_2" / "roadmap" / "f9_notes" / "f9_remeasure.json"


def _trimmed(x):
    """Drop the last 50 ms (2400 samples at 48 kHz) before a T20, same guard as the old ruler."""
    x = np.asarray(x, float).reshape(-1)
    if len(x) > FADE + 1000:
        x = x[:-FADE]
    return x


def _finite_round(vals):
    out = []
    for v in vals:
        v = float(v)
        out.append(None if v != v else round(v, 4))
    return out


def _schroeder_t20(energy, sr):
    """Same -5 to -25 dB Schroeder slope as surf_loop.t20_per_octave."""
    e = np.asarray(energy, float)
    if e.size < 8:
        return float("nan")
    rev = np.cumsum(e[::-1])[::-1]
    rev = rev / max(float(rev[0]), 1e-300)
    edc = 10.0 * np.log10(np.maximum(rev, 1e-30))
    i0 = int(np.argmax(edc <= -5.0))
    i1 = int(np.argmax(edc <= -25.0))
    if i1 <= i0 + 2:
        return float("nan")
    t = np.arange(i0, i1) / float(sr)
    slope = float(np.polyfit(t, edc[i0:i1], 1)[0])
    if slope == 0.0:
        return float("nan")
    return float(-60.0 / slope)


def _onset_abs_sum(left, right):
    """One onset: first sample where |L|+|R| reaches 0.1 of its peak."""
    n = min(len(left), len(right))
    env = np.abs(left[:n]) + np.abs(right[:n])
    peak = float(env.max()) if n else 0.0
    if peak <= 0.0:
        return 0
    return int(np.argmax(env >= 0.1 * peak))


def octave_t60_hypot(ir_l, ir_r):
    """Old ruler, kept so a re-measure can quote the bent row from the same impulse."""
    left = _trimmed(ir_l)
    right = _trimmed(ir_r)
    n = min(len(left), len(right))
    mono = np.hypot(left[:n], right[:n])
    return _finite_round(SL.t20_per_octave(mono, SR, SL.PHYS_BANDS))


def octave_t60(ir_l, ir_r):
    """Proper T20. Trim 2400 samples. One onset on |L|+|R| at 0.1 of the peak.
    Third-order Butterworth octave on each channel (surf_loop._octave). Sum the
    squared bands. Schroeder slope from -5 dB to -25 dB. Four decimals.
    """
    left = _trimmed(ir_l)
    right = _trimmed(ir_r)
    n = min(len(left), len(right))
    left = left[:n]
    right = right[:n]
    n0 = _onset_abs_sum(left, right)
    vals = []
    for fc in SL.PHYS_BANDS:
        yl = SL._octave(left, float(fc), SR)[n0:]
        yr = SL._octave(right, float(fc), SR)[n0:]
        m = min(len(yl), len(yr))
        vals.append(_schroeder_t20(yl[:m] ** 2 + yr[:m] ** 2, SR))
    return _finite_round(vals)


def file_stats(L, R, lim_db, lim_n, peak):
    n = min(len(L), len(R))
    stereo = np.column_stack([np.asarray(L[:n], float), np.asarray(R[:n], float)])
    return {
        "sample_peak": round(float(peak), 6),
        "sample_peak_db": round(20.0 * np.log10(max(float(peak), 1e-300)), 3),
        "true_peak": round(true_peak(L, R), 6),
        "limiter_db": round(float(lim_db), 4),
        "limiter_samples": int(lim_n),
        "dc": float(np.mean(stereo)),
        "energy_under_20hz": energy_under(stereo),
    }


def one(row, name, over, guitar, guitar_name):
    ir_l, ir_r, info = ML.impulse_ir(row, **over)
    y_l, y_r, peak, _scale, lim_db, lim_n = ML.convolve_guitar(ir_l, ir_r, guitar)
    pcm = ML.to_int32(y_l, y_r)
    dest = LISTEN / f"{name}.wav"
    wavfile.write(dest, SR, pcm)
    phys = info.get("phys_ceiling") or {}
    stats = file_stats(y_l, y_r, lim_db, lim_n, peak)
    stats.update({
        "wav": str(dest),
        "room": row["room"],
        "guitar": guitar_name,
        "over": over,
        "fdn_ms": info.get("fdn_ms"),
        "t60_s": octave_t60(ir_l, ir_r),
        "t60_bands_hz": [int(x) for x in SL.PHYS_BANDS],
        "k": phys.get("k"),
        "ceiling_t": phys.get("ceiling_t"),
        "identity_n": phys.get("identity_n"),
        "placed": row["placed"],
        "room_WHL": row["room_WHL"],
    })
    print(name, "peak", stats["sample_peak"], "lim", stats["limiter_db"], stats["limiter_samples"],
          "dc", f"{stats['dc']:.3e}", "e20", f"{stats['energy_under_20hz']:.4f}",
          "k", stats["k"], "t60", stats["t60_s"], flush=True)
    return stats


def energy_null(a, b):
    n = min(len(a), len(b))
    a = np.asarray(a[:n], float)
    b = np.asarray(b[:n], float)
    err = float(np.sum((a - b) ** 2))
    ref = float(np.sum(a ** 2))
    return 10.0 * np.log10(max(err, 1e-300) / max(ref, 1e-300)), n


def play_vs_render(row):
    """2x2.5x2.2 with phys_ceiling and sub_hp on. Impulse, early 0, direct 0."""
    body = ML.page_body(row, phys_ceiling=True, sub_hp=True, decay_s=1.8)
    ir_l, ir_r, info = ML.impulse_ir(row, phys_ceiling=True, sub_hp=True, decay_s=1.8)
    rend = np.column_stack([np.asarray(ir_l, float), np.asarray(ir_r, float)])
    work = LISTEN / "_play"
    work.mkdir(exist_ok=True)
    params = work / "params.json"
    play = work / "play.f32"
    subprocess.run(
        [sys.executable, str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(params), str(SR)],
        check=True, capture_output=True, text=True,
    )
    node = NODE if Path(NODE).is_file() else shutil.which("node")
    secs = len(rend) / SR
    subprocess.run(
        [node, str(LIB / "wasm_run.js"), str(SW), str(params),
         json.dumps({}), "ir", str(secs), str(play)],
        check=True, capture_output=True, text=True,
    )
    got = np.fromfile(play, np.float32).reshape(-1, 2).astype(np.float64)
    n = min(len(rend), len(got))
    cut = max(0, n - FADE)
    nd, _ = energy_null(rend[:cut], got[:cut])
    mx = float(np.max(np.abs(rend[:cut] - got[:cut])))
    t_r = octave_t60(rend[:, 0], rend[:, 1])
    t_p = octave_t60(got[:, 0], got[:, 1])
    out = {
        "room": row["room"],
        "secs": round(secs, 4),
        "null_db": round(nd, 2),
        "max_abs": mx,
        "t60_render": t_r,
        "t60_play": t_p,
        "identity_n": (info.get("phys_ceiling") or {}).get("identity_n"),
        "k": (info.get("phys_ceiling") or {}).get("k"),
    }
    print("PLAY_RENDER", out["null_db"], "max_abs", f"{mx:.6g}", "t60_r", t_r, "t60_p", t_p, flush=True)
    return out


def main():
    LISTEN.mkdir(parents=True, exist_ok=True)
    rep = json.loads(ML.REPORT.read_text(encoding="utf-8"))
    rows = {}
    for row in rep["rows"]:
        if row["room"] in ROOMS and not row.get("phys_ceiling") and str(row.get("wav", "")).endswith("_off.wav"):
            rows[row["room"]] = row
    clean = load_wav(CLEAN)
    orig = load_wav(ORIG)
    jobs = []
    for room in ROOMS:
        jobs.append((room, f"{room}_A_today", {"phys_ceiling": False, "sub_hp": True, "decay_s": 1.8}, clean, "clean"))
        jobs.append((room, f"{room}_B_phys", {"phys_ceiling": True, "sub_hp": True, "decay_s": 1.8}, clean, "clean"))
        jobs.append((room, f"{room}_C_phys_dial4", {"phys_ceiling": True, "sub_hp": True, "decay_s": 4.0}, clean, "clean"))
    jobs.append(("boot_6x3x8", "boot_6x3x8_D_phys_dial8", {"phys_ceiling": True, "sub_hp": True, "decay_s": 8.0}, clean, "clean"))
    jobs.append(("boot_6x3x8", "boot_6x3x8_A_old", {"phys_ceiling": False, "sub_hp": False, "decay_s": 1.8}, clean, "clean"))
    jobs.append(("3x4x2.5", "3x4x2.5_A_today_original_guitar", {"phys_ceiling": False, "sub_hp": True, "decay_s": 1.8}, orig, "original"))
    done = []
    for room, name, over, guitar, tag in jobs:
        done.append(one(rows[room], name, over, guitar, tag))
        REPORT.write_text(json.dumps({"rows": done}, indent=1), encoding="utf-8")
    cmp = play_vs_render(rows["2x2.5x2.2"])
    report = {
        "guitar_clean": str(CLEAN),
        "guitar_original": str(ORIG),
        "note": "T60 is T20 with each channel filtered, then the octave energies summed, last 50 ms fade left out. The old stereo-magnitude ruler is octave_t60_hypot. Peaks, DC, and energy under 20 Hz are the limited guitar file.",
        "play_vs_render": cmp,
        "rows": done,
    }
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("LISTEN_OK", len(done), flush=True)


def _listen_rows():
    """Same row pick as main(): four rooms, phys off, the _off.wav body."""
    rep = json.loads(ML.REPORT.read_text(encoding="utf-8"))
    rows = {}
    for row in rep["rows"]:
        if row["room"] in ROOMS and not row.get("phys_ceiling") and str(row.get("wav", "")).endswith("_off.wav"):
            rows[row["room"]] = row
    missing = [room for room in ROOMS if room not in rows]
    if missing:
        raise RuntimeError("missing listen rows %s" % missing)
    return rows


def _listen_overs():
    """The overs main() builds at the four-room loop plus the two boot extras. No guitar."""
    jobs = []
    for room in ROOMS:
        jobs.append((room, "%s_A_today" % room, {"phys_ceiling": False, "sub_hp": True, "decay_s": 1.8}))
        jobs.append((room, "%s_B_phys" % room, {"phys_ceiling": True, "sub_hp": True, "decay_s": 1.8}))
        jobs.append((room, "%s_C_phys_dial4" % room, {"phys_ceiling": True, "sub_hp": True, "decay_s": 4.0}))
    jobs.append(("boot_6x3x8", "boot_6x3x8_D_phys_dial8", {"phys_ceiling": True, "sub_hp": True, "decay_s": 8.0}))
    jobs.append(("boot_6x3x8", "boot_6x3x8_A_old", {"phys_ceiling": False, "sub_hp": False, "decay_s": 1.8}))
    return jobs


def _num(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple, np.ndarray)):
        return [_num(x) for x in list(v)]
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _phys_bits(info):
    phys = info.get("phys_ceiling") or {}
    ident = phys.get("identity_n")
    if isinstance(ident, (int, np.integer)):
        ident = int(ident)
    return {
        "k": _num(phys.get("k")),
        "identity_n": ident,
        "ceiling_t": _num(phys.get("ceiling_t")),
        "fdn_ms": _num(info.get("fdn_ms")),
    }


def _play_vs_render_scratch(row):
    """Play vs Render for 2x2.5x2.2. Scratch files stay under %TEMP%. Nothing under listen/."""
    body = ML.page_body(row, phys_ceiling=True, sub_hp=True, decay_s=1.8)
    ir_l, ir_r, info = ML.impulse_ir(row, phys_ceiling=True, sub_hp=True, decay_s=1.8)
    rend = np.column_stack([np.asarray(ir_l, float), np.asarray(ir_r, float)])
    work = Path(tempfile.mkdtemp(prefix="f9_notes_play_", dir=os.environ.get("TEMP") or None))
    params = work / "params.json"
    play = work / "play.f32"
    subprocess.run(
        [sys.executable, str(LIB / "dump_params.py"), str(SW), json.dumps(body), str(params), str(SR)],
        check=True, capture_output=True, text=True,
    )
    node = NODE if Path(NODE).is_file() else shutil.which("node")
    secs = len(rend) / float(SR)
    subprocess.run(
        [node, str(LIB / "wasm_run.js"), str(SW), str(params),
         json.dumps({}), "ir", str(secs), str(play)],
        check=True, capture_output=True, text=True,
    )
    got = np.fromfile(play, np.float32).reshape(-1, 2).astype(np.float64)
    n = min(len(rend), len(got))
    cut = max(0, n - FADE)
    nd, _ = energy_null(rend[:cut], got[:cut])
    mx = float(np.max(np.abs(rend[:cut] - got[:cut])))
    out = {
        "room": row["room"],
        "over": {"phys_ceiling": True, "sub_hp": True, "decay_s": 1.8},
        "secs": round(secs, 4),
        "null_db": round(float(nd), 2),
        "max_abs": mx,
        "t60_render_proper": octave_t60(rend[:, 0], rend[:, 1]),
        "t60_play_proper": octave_t60(got[:, 0], got[:, 1]),
        "t60_render_hypot": octave_t60_hypot(rend[:, 0], rend[:, 1]),
        "t60_play_hypot": octave_t60_hypot(got[:, 0], got[:, 1]),
        "scratch": str(work),
    }
    out.update(_phys_bits(info))
    return out


def _boot_check(row):
    got = row["t60_proper"]
    rels = []
    for i in range(1, 7):
        rels.append(abs(float(got[i]) - BOOT_B_PIN[i]) / BOOT_B_PIN[i])
    k = row.get("k")
    k_ok = k is not None and abs(float(k) - 0.775791) <= 1e-6
    ident_ok = row.get("identity_n") == 0
    return {
        "pin": BOOT_B_PIN,
        "bands_from_125_hz": [125, 250, 500, 1000, 2000, 4000],
        "rel_from_125_hz": [round(r, 8) for r in rels],
        "max_rel": max(rels),
        "k": k,
        "k_ok": k_ok,
        "identity_n": row.get("identity_n"),
        "identity_ok": ident_ok,
        "within_0_0005": max(rels) <= 0.0005 and k_ok and ident_ok,
        "within_0_005": max(rels) <= 0.005 and k_ok and ident_ok,
    }


def measure_only():
    """In-memory IRs only. Does not call main, one, play_vs_render, convolve_guitar, or wavfile.write."""
    if FADE != 2400:
        raise RuntimeError("fade trim is %s samples, expected 2400" % FADE)
    if "listen" in F9_OUT.parts:
        raise RuntimeError("refusing to write a listen path")
    rows = _listen_rows()
    done = []
    for room, name, over in _listen_overs():
        if "phys_ceiling" not in over or "sub_hp" not in over:
            raise RuntimeError("%s missing an explicit phys_ceiling or sub_hp" % name)
        ir_l, ir_r, info = ML.impulse_ir(rows[room], **over)
        item = {
            "name": name,
            "room": rows[room]["room"],
            "room_WHL": rows[room]["room_WHL"],
            "over": over,
            "t60_hypot": octave_t60_hypot(ir_l, ir_r),
            "t60_proper": octave_t60(ir_l, ir_r),
        }
        item.update(_phys_bits(info))
        done.append(item)
        print(name, "proper", item["t60_proper"], "hypot", item["t60_hypot"],
              "k", item["k"], "id", item["identity_n"], flush=True)
    boot = next(r for r in done if r["name"] == "boot_6x3x8_B_phys")
    check = _boot_check(boot)
    print("BOOT_CHECK", "max_rel", "%.3e" % check["max_rel"], "ok", check["within_0_0005"], flush=True)
    cmp = _play_vs_render_scratch(rows["2x2.5x2.2"])
    print("PLAY_RENDER", cmp["null_db"], "max_abs", "%.6g" % cmp["max_abs"],
          "t60_r", cmp["t60_render_proper"], "t60_p", cmp["t60_play_proper"], flush=True)
    report = {
        "method_proper": (
            "trim 2400 samples; one onset on |L|+|R| at 0.1 of peak; "
            "surf_loop._octave per channel; sum squared bands; Schroeder -5 to -25 dB; round 4 decimals"
        ),
        "method_hypot": "np.hypot(L, R) then surf_loop.t20_per_octave, same 2400-sample trim",
        "bands_hz": [int(x) for x in SL.PHYS_BANDS],
        "wrote_listen": False,
        "rows": done,
        "boot_b_phys_check": check,
        "play_vs_render": cmp,
        "f12_quoted_2026-10-19": {
            "remeasured_here": False,
            "room": "4.5x6x2.8",
            "hz_926_s": 1.366,
            "hz_1623_s": 1.172,
            "longest_800_to_4k_s": 1.552,
            "longest_hz": 800,
            "source": "OPEN_FAULTS_2026-10-18.md F12, 4th-order 1/12-octave, per channel",
        },
    }
    F9_OUT.parent.mkdir(parents=True, exist_ok=True)
    F9_OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("MEASURE_OK", F9_OUT, flush=True)
    if not check["within_0_005"]:
        raise SystemExit(2)


if __name__ == "__main__":
    if "--measure-only" in sys.argv:
        measure_only()
    else:
        main()
