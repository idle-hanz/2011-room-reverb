"""Set 1 B2 listens. New files only. A, B and C are not rewritten.

The round-2 captures of the dry program are not on this PC. This script
rebuilds the synthetic programs from prog.py (seeds in that file), applies
the hot-job gain of -9.36 dB, and runs the shipped Bloom law. A null against
the stored UAD file is kept only when the rebuilt dry matches the stored C
file. Otherwise the null is UNKNOWN.
"""
from __future__ import annotations

import hashlib
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[6]
SW = ROOT / "software"
HERE = Path(__file__).resolve().parent
LISTEN = HERE.parent / "listen"
ROUND3 = ROOT / "handoff_build_support_2" / "roadmap" / "bloom" / "uad" / "round3" / "listen"
sys.path[:0] = [str(HERE), str(SW), str(SW / "engine")]

import bloom_dsp  # noqa: E402
import prog  # noqa: E402

SR = 48000
A0 = SR
A1 = 5 * SR
HOT_DB = -9.36
PEAK = 10.0 ** (-1.0 / 20.0)
BP = butter(6, [20.0, 19000.0], btype="band", fs=SR, output="sos")

COMP = (
    ("natural", "mix"),
    ("natural", "vocal"),
    ("glue", "mix"),
    ("room_crush", "mix"),
    ("room_crush", "drums"),
    ("room_crush", "bass"),
    ("nuke", "mix"),
    ("nuke", "drums"),
    ("nuke", "bass"),
    ("swell", "mix"),
)
PRE = (
    ("u610a", "vocal"),
    ("u610a", "drums"),
    ("neve", "vocal"),
    ("neve", "drums"),
)


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        ch, sw, n = w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        x = (
            b[:, 0].astype(np.int32)
            | (b[:, 1].astype(np.int32) << 8)
            | (b[:, 2].astype(np.int32) << 16)
        )
        x = np.where(x >= 0x800000, x - 0x1000000, x).astype(np.float64) / 8388608.0
    elif sw == 2:
        x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768.0
    else:
        raise RuntimeError(f"sampwidth {sw} in {path}")
    x = x.reshape(-1, ch)
    return x[:, 0]


def write24(path: Path, x: np.ndarray) -> None:
    q = np.clip(np.rint(np.asarray(x, np.float64) * 8388607.0), -8388607, 8388607).astype(np.int32)
    raw = bytearray(q.size * 3)
    for i, v in enumerate(q):
        raw[i * 3:i * 3 + 3] = int(v).to_bytes(3, "little", signed=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(bytes(raw))


def fade(y: np.ndarray) -> np.ndarray:
    n = int(0.01 * SR)
    w = np.ones(len(y))
    w[:n] = np.linspace(0.0, 1.0, n)
    w[-n:] = w[:n][::-1]
    return y * w


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))


def corr(a, b) -> float:
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    n = min(a.size, b.size)
    a = a[:n] - np.mean(a[:n])
    b = b[:n] - np.mean(b[:n])
    den = float(np.linalg.norm(a) * np.linalg.norm(b))
    if den <= 0.0:
        return 0.0
    return float(np.dot(a, b) / den)


def null_db(y, yh):
    """Round-2 bandpass least-squares null. Returns dB and the scale."""
    y = sosfiltfilt(BP, np.asarray(y, np.float64))
    yh = sosfiltfilt(BP, np.asarray(yh, np.float64))
    n = min(y.size, yh.size)
    y, yh = y[:n], yh[:n]
    den = float(np.dot(yh, yh))
    if den <= 0.0:
        return None, 0.0
    c = float(np.dot(y, yh) / den)
    num = float(np.sum((y - c * yh) ** 2))
    ref = float(np.sum(y ** 2))
    return float(10.0 * np.log10(max(num, 1e-300) / max(ref, 1e-300))), c


def shipped_comp(x: np.ndarray, preset: str) -> tuple[np.ndarray, np.ndarray]:
    body = {"bloom_preset": preset, "bloom_amount": 100, "bloom_colour": True}
    if preset == "glue":
        body["glue_colour"] = True
    spec = bloom_dsp.design(body, SR)
    if spec is None:
        raise RuntimeError(preset)
    g, gr = bloom_dsp._gain_env(np.asarray(x, np.float64), spec)
    pack = bloom_dsp.pack_coeffs(spec)
    y = np.asarray(x, np.float64)
    swell = pack[38] > 0.5 and pack[26] > 0.5
    colour = pack[26] > 0.5
    st = bloom_dsp._Colour(pack)
    out = np.empty_like(y)
    for i in range(y.size):
        v = float(y[i])
        if swell:
            v = st.shape(v, float(gr[i]), 1.0)
            v *= float(g[i])
            v = st.eq(v)
        elif colour:
            v = v * float(g[i])
            v = st.shape(v, float(gr[i]), 1.0)
            v = st.eq(v)
        else:
            v = v * float(g[i])
        out[i] = v
    return out, gr


def shipped_pre(x: np.ndarray, kind: str) -> np.ndarray:
    name = "neve1073" if kind == "neve" else "u610a"
    spec = bloom_dsp.design({"bloom_amount": 0, "pre_colour": name, "pre_drive_db": 0.0}, SR)
    if spec is None:
        raise RuntimeError(kind)
    pack = bloom_dsp.pack_pre(spec)
    return bloom_dsp._pre_bus(np.asarray(x, np.float64), pack)


def match_b2(y: np.ndarray, ref_rms: float) -> tuple[np.ndarray, dict]:
    """RMS-match to the existing set. Cap the peak at -1 dBFS. Do not touch A/B/C."""
    sl = fade(np.asarray(y[A0:A1], np.float64))
    cur = rms(sl)
    scale = ref_rms / cur if cur > 0.0 else 1.0
    out = sl * scale
    pk = float(np.max(np.abs(out))) if out.size else 0.0
    extra = 1.0
    if pk > PEAK:
        extra = PEAK / pk
        out = out * extra
    return out, {"rms_scale": scale, "peak_trim": extra, "peak": float(np.max(np.abs(out)))}


def existing(prefix: str) -> dict[str, Path]:
    found = {}
    for p in LISTEN.glob(prefix + "__*.wav"):
        found[p.name] = p
    return found


def main() -> None:
    before = {p.name: sha1(p) for p in LISTEN.glob("*.wav")}
    programs = prog.all_programs(6.0)
    hot = 10.0 ** (HOT_DB / 20.0)
    rows = []
    for preset, pk in COMP:
        prefix = f"comp_{preset}_{pk}_hot"
        files = existing(prefix)
        c_name = next((n for n in files if "__C_dry_input" in n), None)
        a_name = next((n for n in files if "__A_" in n), None)
        b_name = next((n for n in files if "__B_" in n), None)
        if not (c_name and a_name and b_name):
            rows.append({"set": prefix, "status": "MISSING_ABC"})
            print("MISSING", prefix, flush=True)
            continue
        c = read_mono(files[c_name])
        a = read_mono(files[a_name])
        b = read_mono(files[b_name])
        x = np.asarray(programs[pk], np.float64) * hot
        sl = fade(x[A0:A1])
        den = float(np.dot(sl, sl))
        scale = float(np.dot(c[: sl.size], sl) / den) if den else 0.0
        rho = corr(c, sl * scale)
        print("COMP", preset, pk, "rho", round(rho, 4), flush=True)
        y, gr = shipped_comp(x, preset)
        ref = min(rms(a), rms(b), rms(c))
        b2, scale_info = match_b2(y, ref)
        dest = LISTEN / f"{prefix}__B2_bloom_new.wav"
        write24(dest, b2)
        nb, _ = null_db(b, a)
        row = {
            "set": prefix,
            "preset": preset,
            "program": pk,
            "hot_gain_db": HOT_DB,
            "dry_correlation": round(rho, 5),
            "program_match": rho >= 0.98,
            "null_B_vs_A_db": None if nb is None else round(nb, 2),
            "b2_scale": scale_info,
            "gr_median_db": round(float(np.median(gr)), 3),
            "gr_max_db": round(float(np.max(gr)), 3),
            "colour": "on",
            "glue_colour": preset == "glue",
        }
        if rho >= 0.98:
            n2, _ = null_db(b2, a)
            row["null_B2_vs_A_db"] = None if n2 is None else round(n2, 2)
            row["null_status"] = "VERIFIED shape match of rebuilt dry to stored C"
        else:
            row["null_B2_vs_A_db"] = None
            row["null_status"] = "UNKNOWN rebuilt dry does not match stored C"
        rows.append(row)
        print("WROTE", dest.name, row["null_status"], flush=True)
    for kind, pk in PRE:
        prefix = f"pre_{kind}_{pk}_drive"
        files = existing(prefix)
        a_name = next((n for n in files if "__A_" in n), None)
        b_name = next((n for n in files if "__B_" in n), None)
        x = np.asarray(programs[pk], np.float64) * hot
        y = shipped_pre(x, kind)
        if a_name and b_name:
            a = read_mono(files[a_name])
            b = read_mono(files[b_name])
            ref = min(rms(a), rms(b))
        else:
            ref = rms(fade(y[A0:A1]))
        b2, scale_info = match_b2(y, ref)
        dest = LISTEN / f"{prefix}__B2_bloom_new.wav"
        write24(dest, b2)
        rows.append({
            "set": prefix,
            "pre": kind,
            "program": pk,
            "drive_db": 0.0,
            "drive_note": (
                "Drive 0 is the shipped calibrated point. Round-2 pre dry "
                "captures are not on this PC, so this is the rebuilt program "
                "at the compressor hot gain, not a proven 1% THD capture."
            ),
            "null_B2_vs_A_db": None,
            "null_status": "UNKNOWN no captured dry",
            "b2_scale": scale_info,
        })
        print("WROTE", dest.name, "pre UNKNOWN", flush=True)
    b3 = []
    if ROUND3.is_dir():
        for p in sorted(ROUND3.glob("*__B3_proto.wav")):
            a = next(ROUND3.glob(p.name.split("__")[0] + "__A_*.wav"), None)
            item = {"b3": p.name, "program": "round3 real, not the round-2 synth set"}
            if a is not None:
                nb, _ = null_db(read_mono(p), read_mono(a))
                item["null_B3_vs_own_A_db"] = None if nb is None else round(nb, 2)
                item["a"] = a.name
            b3.append(item)
    after = {p.name: sha1(p) for p in LISTEN.glob("*.wav")}
    protected = []
    for name, digest in before.items():
        if name.endswith("__B2_bloom_new.wav"):
            continue
        if after.get(name) != digest:
            protected.append(name)
    report = {
        "rows": rows,
        "round3_b3_other_program": b3,
        "abc_changed": protected,
        "abc_unchanged": len(protected) == 0,
    }
    (LISTEN / "B2_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    readme = """# Bloom B2 listens

These sit next to the round-2 A, B and C files. A, B and C were not rewritten.

Play this order: Nuke bass, Room Crush drums, Swell mix, Natural vocal, 610-A vocal, Neve vocal, Glue mix.

B2 is the shipped Bloom. Compressors are Amount 100 with colour and EQ on (Glue colour on in this file; the page default for Glue colour is off). The first 15 ms of the full clip rises from unity. The stored 4 s starts at 1 s, so that rise is not in the file.

Pres are the shipped 610-A and the Neve 8x nclip_flux model at Drive 0. The original pre dry captures are not on this PC, so those four nulls are unknown.

A null against the UAD is a number only when the rebuilt dry matches the stored dry file.
"""
    (LISTEN / "B2_README.md").write_text(readme, encoding="utf-8")
    print("B2_DONE", "abc_unchanged", report["abc_unchanged"], "changed", protected, flush=True)
    if protected:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
