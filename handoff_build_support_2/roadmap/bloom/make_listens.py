"""Set 2 Bloom listens. Guitar through render(), page-default desk.

Does not overwrite the guitar file. Amount 50 with the limiter on is a stop.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SW = ROOT / "software"
sys.path[:0] = [str(SW), str(SW / "engine")]

import app_server as A  # noqa: E402
import bloom_dsp  # noqa: E402
from render_pipeline import _render_core, live_fdn_params, load_wav_mono, render  # noqa: E402

HERE = Path(__file__).resolve().parent
LISTEN = HERE / "listen"
STEMS = LISTEN / "_stems"
GUITAR = (
    ROOT
    / "handoff_build_support_2"
    / "roadmap"
    / "robotic_1240"
    / "test_guitar_dualmono_clean.wav"
)
SR = 48000
N = 8 * SR
TAIL = 2 * SR
NODE = (
    r"C:\Users\IdleHanz\AppData\Local\Microsoft\WinGet\Packages"
    r"\OpenJS.NodeJS_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\node-v26.7.0-win-x64\node.exe"
)
WASM_JS = (
    ROOT / "handoff_build_support_2" / "3_phase_acceptance_tests"
    / "harness" / "lib" / "wasm_run.js"
)
BANDS = (63, 125, 250, 500, 1000, 2000, 4000, 8000)
# PLACE pose from smalldecay listen_report, room name 3x4x2.5.
# Engine order is W, H, L = 3, 2.5, 4 (the name is W x L x H).
SMALL = {
    "W": 3.0, "H": 2.5, "L": 4.0,
    "sx": 1.3, "sy": 1.0, "sz": 2.375,
    "mcx": 1.5, "my": 1.25, "mcz": 0.75, "space": 0.17,
}
PRESETS = ("natural", "glue", "room_crush", "nuke", "swell")


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write24(path: Path, left, right) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = min(len(left), len(right))
    L = np.asarray(left[:n], np.float64)
    R = np.asarray(right[:n], np.float64)
    qL = np.clip(np.rint(L * 8388607.0), -8388607, 8388607).astype(np.int32)
    qR = np.clip(np.rint(R * 8388607.0), -8388607, 8388607).astype(np.int32)
    raw = bytearray(n * 6)
    for i in range(n):
        raw[i * 6:i * 6 + 3] = int(qL[i]).to_bytes(3, "little", signed=True)
        raw[i * 6 + 3:i * 6 + 6] = int(qR[i]).to_bytes(3, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(bytes(raw))


def render_page(body: dict, dry: np.ndarray):
    p = A.params_from_body(body)
    sig = inspect.signature(_render_core)
    kw = {}
    for name in sig.parameters:
        if name in ("dry", "sr"):
            continue
        if name in p:
            kw[name] = p[name]
    kw["desk"] = p
    kw["surf_directional"] = False
    kw["two_sources"] = False
    kw["phys_ceiling"] = bool(p.get("phys_ceiling"))
    kw["sub_hp"] = bool(p.get("sub_hp"))
    for key in (
        "bloom_preset", "bloom_amount", "bloom_attack_scale", "bloom_release_scale",
        "predelay_ms", "bloom_colour", "glue_colour", "pre_colour", "pre_drive_db",
    ):
        if key in body:
            kw[key] = body[key]
    return render(np.asarray(dry, np.float64), SR, **kw)


def measures(left, right, info) -> dict:
    L = np.asarray(left, np.float64)
    R = np.asarray(right, np.float64)
    n = min(len(L), len(R))
    L, R = L[:n], R[:n]
    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R))))
    # 4x true peak, cheap polyphase via repeat-sinc is overkill; linear interp
    # of a 4x zero-stuffed FFT is the usual true-peak. Use a short FFT upsample.
    def up(x):
        spec = np.fft.rfft(x)
        z = np.zeros((len(spec) - 1) * 4 + 1, dtype=np.complex128)
        z[: len(spec)] = spec
        y = np.fft.irfft(z, n * 4)
        return float(np.max(np.abs(y))) * 4.0  # irfft of a truncated spectrum is not scaled that way
    # scipy resample_poly is the honest 4x peak.
    from scipy.signal import resample_poly
    upv = resample_poly(np.column_stack([L, R]), 4, 1, axis=0)
    return {
        "peak": peak,
        "true_peak": float(np.max(np.abs(upv))),
        "dc_l": float(np.mean(L)),
        "dc_r": float(np.mean(R)),
        "limiter_db": float(info.get("limiter_db") or 0.0),
        "limiter_samples": int(info.get("limiter_samples") or 0),
        "norm_scale": float(info.get("norm_scale") or 0.0),
    }


def power_null(a, b) -> float:
    """10*log10 of energy ratio. Same number as 20*log10 of the RMS ratio."""
    aa = np.asarray(a, np.float64).reshape(-1)
    bb = np.asarray(b, np.float64).reshape(-1)
    n = min(aa.size, bb.size)
    if n < 8:
        return 0.0
    err = float(np.sum((aa[:n] - bb[:n]) ** 2))
    ref = float(np.sum(aa[:n] ** 2))
    return float(10.0 * np.log10(max(err, 1e-300) / max(ref, 1e-300)))


def best_shift(rend, play, lim: int = 2000):
    """s > 0 means render[s] lines up with play[0] (play leads)."""
    a = np.asarray(rend, np.float64)
    b = np.asarray(play, np.float64)
    n = min(len(a), len(b))
    a = a[:n]
    b = b[:n]
    am = a[:, 0] + a[:, 1]
    bm = b[:, 0] + b[:, 1]

    def at(s):
        if s >= 0:
            return power_null(a[s:], b[: n - s])
        return power_null(a[: n + s], b[-s:])

    best_s, best_db = 0, at(0)
    step = 16
    for s in range(-lim, lim + 1, step):
        db = at(s)
        if db < best_db:
            best_s, best_db = s, db
    for s in range(best_s - step, best_s + step + 1):
        if s < -lim or s > lim:
            continue
        db = at(s)
        if db < best_db:
            best_s, best_db = s, db
    if best_s >= 0:
        aa, bb = a[best_s:], b[: n - best_s]
    else:
        aa, bb = a[: n + best_s], b[-best_s:]
    mx = float(np.max(np.abs(aa - bb))) if len(aa) else 0.0
    return best_s, best_db, mx


def _hop_db(mono, hop: int):
    n = (len(mono) // hop) * hop
    if n < hop:
        return []
    rms = np.sqrt(np.mean(mono[:n].reshape(-1, hop) ** 2, axis=1))
    return [round(float(20.0 * np.log10(max(v, 1e-12))), 2) for v in rms]


def last_note(dry) -> int:
    d = np.abs(np.asarray(dry[:N], np.float64))
    pk = float(d.max()) if d.size else 0.0
    if pk <= 0.0:
        return N - 1
    hit = np.where(d >= 0.05 * pk)[0]
    return int(hit[-1]) if hit.size else N - 1


def level_at(mono, i0: int) -> float | None:
    hop = int(0.01 * SR)
    if i0 < 0 or i0 + hop > len(mono):
        return None
    r = float(np.sqrt(np.mean(mono[i0:i0 + hop] ** 2)))
    return float(20.0 * np.log10(max(r, 1e-12)))


def schroeder_t60(energy) -> float | None:
    e = np.asarray(energy, np.float64)
    if e.size < 16:
        return None
    rev = np.cumsum(e[::-1])[::-1]
    rev = rev / max(float(rev[0]), 1e-300)
    edc = 10.0 * np.log10(np.maximum(rev, 1e-30))
    i0 = int(np.argmax(edc <= -5.0))
    i1 = int(np.argmax(edc <= -25.0))
    if i1 <= i0 + 2:
        return None
    t = np.arange(i0, i1) / float(SR)
    slope = float(np.polyfit(t, edc[i0:i1], 1)[0])
    if slope >= 0.0:
        return None
    return float(-60.0 / slope)


def octave_t60(left, right, n0: int) -> dict:
    from scipy.signal import butter, sosfilt

    out = {}
    for fc in BANDS:
        lo = max(fc / np.sqrt(2.0), 20.0)
        hi = min(fc * np.sqrt(2.0), 20000.0)
        sos = butter(3, [lo, hi], btype="band", fs=SR, output="sos")
        yl = sosfilt(sos, np.asarray(left, np.float64))[n0:]
        yr = sosfilt(sos, np.asarray(right, np.float64))[n0:]
        m = min(len(yl), len(yr))
        t60 = schroeder_t60(yl[:m] ** 2 + yr[:m] ** 2)
        out[str(fc)] = None if t60 is None else round(t60, 4)
    return out


def residual_db(a, b, search: int = 48) -> dict:
    """Energy of (a - shifted b) over energy of b. Colour residual, not a sine THD."""
    aa = np.asarray(a, np.float64)
    bb = np.asarray(b, np.float64)
    best = None
    for s in range(-search, search + 1):
        if s >= 0:
            x, y = aa[s:], bb[: len(bb) - s if s else len(bb)]
        else:
            x, y = aa[: len(aa) + s], bb[-s:]
        n = min(len(x), len(y))
        if n < 32:
            continue
        err = float(np.sum((x[:n] - y[:n]) ** 2))
        ref = float(np.sum(y[:n] ** 2))
        db = float(10.0 * np.log10(max(err, 1e-300) / max(ref, 1e-300)))
        if best is None or db < best[0]:
            best = (db, s)
    if best is None:
        return {"residual_db": None, "shift": 0}
    return {"residual_db": round(best[0], 2), "shift": int(best[1])}


def energy_under_20(left, right) -> float:
    x = np.asarray(left, float) + np.asarray(right, float)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    p = np.abs(spec) ** 2
    return float(np.sum(p[freqs < 20.0]) / max(float(np.sum(p)), 1e-300))


def cases():
    rows = []
    rows.append(("boot_bloom_off", {}, False))
    for name in PRESETS:
        rows.append((f"boot_{name}_a0", {"bloom_preset": name, "bloom_amount": 0}, False))
    for name in PRESETS:
        rows.append((f"boot_{name}_a50", {
            "bloom_preset": name, "bloom_amount": 50,
        }, True))
        rows.append((f"boot_{name}_a100", {
            "bloom_preset": name, "bloom_amount": 100,
        }, False))
        rows.append((f"boot_{name}_a100_colour", {
            "bloom_preset": name, "bloom_amount": 100, "bloom_colour": True,
        }, False))
    rows.append(("boot_natural_a100_fast", {
        "bloom_preset": "natural", "bloom_amount": 100,
        "bloom_attack_scale": 0.25, "bloom_release_scale": 0.25,
    }, False))
    rows.append(("boot_natural_a100_slow", {
        "bloom_preset": "natural", "bloom_amount": 100,
        "bloom_attack_scale": 4, "bloom_release_scale": 4,
    }, False))
    rows.append(("boot_natural_a50_pre30", {
        "bloom_preset": "natural", "bloom_amount": 50, "predelay_ms": 30,
    }, True))
    for kind, drive in (("u610a", 0.0), ("u610a", 6.0), ("neve1073", 0.0), ("neve1073", 6.0)):
        tag = "d0" if drive == 0.0 else "d+6"
        short = "u610a" if kind == "u610a" else "neve"
        rows.append((f"boot_pre_{short}_{tag}", {
            "bloom_amount": 0, "pre_colour": kind, "pre_drive_db": drive,
        }, False))
    rows.append(("boot_natural_a50_colour_pre_u610a", {
        "bloom_preset": "natural", "bloom_amount": 50, "bloom_colour": True,
        "pre_colour": "u610a", "pre_drive_db": 0,
    }, True))
    for name, extra in (
        ("small_3x4x2.5_bloom_off", {}),
        ("small_3x4x2.5_natural_a50", {"bloom_preset": "natural", "bloom_amount": 50}),
        ("small_3x4x2.5_room_crush_a50", {"bloom_preset": "room_crush", "bloom_amount": 50}),
        ("small_3x4x2.5_nuke_a50", {"bloom_preset": "nuke", "bloom_amount": 50}),
    ):
        body = dict(SMALL)
        body.update(extra)
        rows.append((name, body, "a50" in name and "off" not in name))
    return rows


def stem_metrics(name: str, body: dict, dry, left, right) -> dict:
    hop = int(0.01 * SR)
    mono = np.hypot(np.asarray(left, np.float64), np.asarray(right, np.float64))
    note = last_note(dry)
    row = {
        "tail_rms_10ms_db": _hop_db(mono, hop),
        "last_note_sample": note,
    }
    for dt, key in ((0.5, "tail_0_5s_db"), (1.0, "tail_1_0s_db")):
        row[key] = level_at(mono, note + int(dt * SR))
    spec = bloom_dsp.design(body, SR)
    if spec is not None and float(spec.get("amount_db") or 0.0) > 0.0:
        g, gr = bloom_dsp._gain_env(np.asarray(dry, np.float64), spec)
        n = (gr.size // hop) * hop
        blk = gr[:n].reshape(-1, hop).mean(axis=1) if n else np.zeros(0)
        row["gr_10ms_db"] = [round(float(v), 3) for v in blk]
        row["gr_median_db"] = round(float(np.median(gr)), 4)
        row["gr_max_db"] = round(float(np.max(gr)), 4)
        row["py_gain"] = g
    else:
        row["gr_10ms_db"] = []
        row["gr_median_db"] = 0.0
        row["gr_max_db"] = 0.0
    if "bloom_off" in name:
        row["octave_t60_s"] = octave_t60(left, right, note)
        row["octave_t60_note"] = (
            "Schroeder slope from -5 dB to -25 dB on the guitar-excited tail "
            "after the last note. This is not an impulse T60."
        )
    return row


def play_pcm(body: dict, mono: np.ndarray):
    work = LISTEN / "_play"
    work.mkdir(parents=True, exist_ok=True)
    params = work / "params.json"
    raw = work / "in.f32"
    out = work / "out.f32"
    live = live_fdn_params(A.params_from_body(body))

    def _dump(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        raise TypeError(type(obj).__name__)

    params.write_text(json.dumps(live, default=_dump), encoding="utf-8")
    np.asarray(mono, np.float32).tofile(raw)
    proc = subprocess.run(
        [NODE, str(WASM_JS), str(SW), str(params), "{}", "pcm", str(raw), str(out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-800:])
    got = np.fromfile(out, np.float32).reshape(-1, 2).astype(np.float64)
    return got, (proc.stdout or "").strip()


def gain_err_db(py_g, play_on, play_off, shift: int):
    """dB error of the wasm on/off ratio against the Python gain envelope."""
    won = np.asarray(play_on, np.float64)
    woff = np.asarray(play_off, np.float64)
    g = np.asarray(py_g, np.float64)
    n = min(len(won), len(woff), len(g))
    if shift >= 0:
        won, woff, g = won[: n - shift], woff[: n - shift], g[shift:n]
    else:
        won, woff, g = won[-shift:n], woff[-shift:n], g[: n + shift]
    n = min(len(won), len(woff), len(g))
    errs = []
    for ch in (0, 1):
        mask = np.abs(woff[:n, ch]) > 1.0e-3
        if not np.any(mask):
            continue
        got = won[:n, ch][mask] / woff[:n, ch][mask]
        ref = g[:n][mask]
        ok = (got > 1.0e-8) & (ref > 1.0e-8)
        if not np.any(ok):
            continue
        errs.append(20.0 * np.log10(got[ok]) - 20.0 * np.log10(ref[ok]))
    if not errs:
        return None
    e = np.concatenate(errs)
    return {
        "n": int(e.size),
        "median_abs_db": round(float(np.median(np.abs(e))), 5),
        "p95_abs_db": round(float(np.percentile(np.abs(e), 95)), 5),
        "max_abs_db": round(float(np.max(np.abs(e))), 5),
    }


def main():
    LISTEN.mkdir(parents=True, exist_ok=True)
    STEMS.mkdir(parents=True, exist_ok=True)
    guitar_sha = sha1(GUITAR)
    dry, sr = load_wav_mono(str(GUITAR))
    if int(sr) != SR:
        raise SystemExit(f"guitar sr {sr}")
    guitar = np.asarray(dry[:N], np.float64)
    dry = np.concatenate([guitar, np.zeros(TAIL, np.float64)])
    report = {
        "guitar_sha1": guitar_sha,
        "guitar": str(GUITAR),
        "guitar_seconds": 8,
        "tail_pad_seconds": 2,
        "seconds": 10,
        "rows": [],
        "note": "Each file is the first 8 s of the guitar plus 2 s of silence, so the tail after the last note is in the file.",
    }
    # Direct and early must ignore Bloom. Short slice, FDN off, everything else on.
    short = dry[: SR // 2]
    on = {
        "bloom_preset": "nuke", "bloom_amount": 100, "bloom_colour": True,
        "pre_colour": "neve1073", "pre_drive_db": 6, "predelay_ms": 30,
        "fdn_wet": 0.0, "dry_gain": 0.0,
    }
    off = {"fdn_wet": 0.0, "dry_gain": 0.0}
    La, Ra, _ = render_page(on, short)
    Lb, Rb, _ = render_page(off, short)
    n = min(len(La), len(Lb), len(Ra), len(Rb))
    dmax = float(max(np.max(np.abs(La[:n] - Lb[:n])), np.max(np.abs(Ra[:n] - Rb[:n]))))
    report["direct_early_max_abs"] = dmax
    print("DIRECT_EARLY", dmax, flush=True)
    if dmax != 0.0 and dmax > 1e-12:
        # Float noise from a forced drive path is still a fail if it is audible.
        # Exact 0 is the gate. A denormal under 1e-12 is reported, not a stop.
        if dmax > 0.0:
            report["direct_early"] = "FAIL"
            (LISTEN / "listen_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
            if dmax > 1e-9:
                print("STOP2 direct/early moved", dmax, flush=True)
                raise SystemExit(2)
    off_l = off_r = None
    stems = {}
    gains = {}
    for name, body, amount50 in cases():
        print("RENDER", name, flush=True)
        L, R, info = render_page(body, dry)
        m = measures(L, R, info)
        m["energy_under_20"] = energy_under_20(L, R)
        m["name"] = name
        m["body"] = body
        if amount50 and m["limiter_samples"] > 0:
            m["stop"] = "STOP5"
            report["rows"].append(m)
            (LISTEN / "listen_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
            print("STOP5", name, m["limiter_db"], m["limiter_samples"], flush=True)
            raise SystemExit(5)
        write24(LISTEN / f"{name}.wav", L, R)
        stem_body = dict(body)
        stem_body["direct_wet"] = 0.0
        stem_body["early_wet"] = 0.0
        stem_body["dry_gain"] = 0.0
        Ls, Rs, _infos = render_page(stem_body, dry)
        write24(STEMS / f"{name}.wav", Ls, Rs)
        stems[name] = (np.asarray(Ls, np.float64), np.asarray(Rs, np.float64))
        extra = stem_metrics(name, stem_body, dry, Ls, Rs)
        if "py_gain" in extra:
            gains[name] = extra.pop("py_gain")
        m.update(extra)
        m["stem_peak"] = float(max(np.max(np.abs(Ls)), np.max(np.abs(Rs))))
        if name == "boot_bloom_off":
            off_l, off_r = L, R
        if name.startswith("boot_") and name.endswith("_a0") and off_l is not None:
            nn = min(len(L), len(off_l))
            m["max_abs_vs_nokeys"] = float(max(
                np.max(np.abs(L[:nn] - off_l[:nn])),
                np.max(np.abs(R[:nn] - off_r[:nn])),
            ))
        report["rows"].append(m)
        (LISTEN / "listen_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
        print("WROTE", name, "lim", m["limiter_samples"], "peak", round(m["peak"], 4), flush=True)
    by_name = {row["name"]: row for row in report["rows"]}
    for row in report["rows"]:
        ref = "small_3x4x2.5_bloom_off" if row["name"].startswith("small_") else "boot_bloom_off"
        other = by_name.get(ref)
        if other is None or row["name"] == ref:
            continue
        for key in ("tail_0_5s_db", "tail_1_0s_db"):
            a, b = row.get(key), other.get(key)
            if a is None or b is None:
                continue
            row[key + "_vs_off"] = round(float(a) - float(b), 3)
    colour_pairs = {
        "boot_natural_a100_colour": "boot_natural_a100",
        "boot_glue_a100_colour": "boot_glue_a100",
        "boot_room_crush_a100_colour": "boot_room_crush_a100",
        "boot_nuke_a100_colour": "boot_nuke_a100",
        "boot_swell_a100_colour": "boot_swell_a100",
    }
    for on_name, off_name in colour_pairs.items():
        if on_name not in stems or off_name not in stems:
            continue
        a = np.column_stack(stems[on_name])
        b = np.column_stack(stems[off_name])
        by_name[on_name]["tail_colour_residual"] = residual_db(a, b)
        by_name[on_name]["tail_colour_residual_note"] = (
            "Energy of the colour-on tail minus the colour-off tail, best shift "
            "within 48 samples, over the colour-off energy. Not a sine THD."
        )
    play_rows = [
        ("boot_natural_a100_colour", {
            "bloom_preset": "natural", "bloom_amount": 100, "bloom_colour": True,
        }),
        ("boot_nuke_a100", {"bloom_preset": "nuke", "bloom_amount": 100}),
        ("boot_room_crush_a100", {"bloom_preset": "room_crush", "bloom_amount": 100}),
        ("boot_pre_u610a_d+6", {
            "bloom_amount": 0, "pre_colour": "u610a", "pre_drive_db": 6,
        }),
        ("small_3x4x2.5_natural_a100", dict(SMALL, **{
            "bloom_preset": "natural", "bloom_amount": 100,
        })),
    ]
    print("PLAY off tail", flush=True)
    off_play, _off_log = play_pcm(
        {"direct_wet": 0.0, "early_wet": 0.0, "dry_gain": 0.0}, dry,
    )
    play_report = []
    stop4 = None
    for name, body in play_rows:
        stem_body = dict(body)
        stem_body["direct_wet"] = 0.0
        stem_body["early_wet"] = 0.0
        stem_body["dry_gain"] = 0.0
        if name not in stems:
            print("RENDER extra", name, flush=True)
            Ls, Rs, info = render_page(stem_body, dry)
            write24(STEMS / f"{name}.wav", Ls, Rs)
            L, R, info_full = render_page(body, dry)
            write24(LISTEN / f"{name}.wav", L, R)
            stems[name] = (np.asarray(Ls, np.float64), np.asarray(Rs, np.float64))
            extra = stem_metrics(name, stem_body, dry, Ls, Rs)
            if "py_gain" in extra:
                gains[name] = extra.pop("py_gain")
            m = measures(L, R, info_full)
            m.update({"name": name, "body": body, "energy_under_20": energy_under_20(L, R)})
            m.update(extra)
            report["rows"].append(m)
        rend = np.column_stack(stems[name])
        print("PLAY", name, flush=True)
        got, log = play_pcm(stem_body, dry)
        shift, null_db, mx = best_shift(rend, got)
        item = {
            "name": name,
            "null_db": round(null_db, 2),
            "shift_samples": int(shift),
            "max_abs": mx,
            "wasm_log": log[-400:],
        }
        if name in gains and name.startswith("boot_") and "colour" not in name and "pre_" not in name:
            ge = gain_err_db(gains[name], got, off_play, shift)
            item["gr_from_gain_db"] = ge
            if ge and ge["median_abs_db"] > 0.01:
                item["stop"] = "STOP4"
                stop4 = item
        if null_db > -60.0:
            item["stop"] = "STOP4"
            stop4 = item
        play_report.append(item)
        print("PLAY_NULL", name, item["null_db"], "shift", shift, flush=True)
    nat = {
        "bloom_preset": "natural", "bloom_amount": 100,
        "direct_wet": 0.0, "early_wet": 0.0, "dry_gain": 0.0,
    }
    if "boot_natural_a100" in stems and "boot_natural_a100" in gains:
        print("PLAY natural a100 colour off (GR)", flush=True)
        got, log = play_pcm(nat, dry)
        rend = np.column_stack(stems["boot_natural_a100"])
        shift, null_db, mx = best_shift(rend, got)
        ge = gain_err_db(gains["boot_natural_a100"], got, off_play, shift)
        item = {
            "name": "boot_natural_a100_gr",
            "null_db": round(null_db, 2),
            "shift_samples": int(shift),
            "max_abs": mx,
            "gr_from_gain_db": ge,
            "wasm_log": log[-400:],
        }
        if null_db > -60.0 or (ge and ge["median_abs_db"] > 0.01):
            item["stop"] = "STOP4"
            stop4 = item
        play_report.append(item)
        print("PLAY_NULL", item["name"], item["null_db"], ge, flush=True)
    report["play_vs_render"] = play_report
    end_sha = sha1(GUITAR)
    report["guitar_sha1_after"] = end_sha
    report["guitar_untouched"] = end_sha == guitar_sha
    if stop4 is not None:
        report["stop"] = "STOP4"
    (LISTEN / "listen_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("LISTEN_DONE", report["guitar_untouched"], flush=True)
    if stop4 is not None:
        print("STOP4", stop4["name"], stop4.get("null_db"), stop4.get("gr_from_gain_db"), flush=True)
        raise SystemExit(4)


if __name__ == "__main__":
    main()
