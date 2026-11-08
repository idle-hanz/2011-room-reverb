"""Audition the preamp and the compressor on a dry signal. No FDN and no reverb.

The render multiplies the compressor gain onto the FDN. This tool multiplies
that same gain onto the dry signal, after the preamp, so the compressor can
be heard. The detector is the dry input, which is what the render uses.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SW / "engine"))

import bloom_dsp as B  # noqa: E402

SR = 48000
PRE = ("none", "u610a", "neve1073")
COMP = ("off", "natural", "glue", "room_crush", "nuke", "swell")
HELP = """\
Audition the preamp and the compressor on a dry signal. No FDN and no reverb.

The render multiplies the compressor gain onto the FDN. This tool multiplies
that same gain onto the dry signal, after the preamp, so the compressor can
be heard. Amount 0 leaves the compressor off. A processed peak above 0.5 is
scaled to 0.5 and the scale is printed. An unchanged copy of the input wav
is not scaled.
"""


def _spec(pre: str, drive: float, comp: str, amount: float, sr: float) -> dict | None:
    pre_name = "off" if pre in ("none", "off") else pre
    amt = 0.0 if comp == "off" else min(100.0, max(0.0, float(amount)))
    page = {
        "pre_colour": pre_name,
        "pre_drive_db": float(drive),
        "bloom_preset": "natural" if comp == "off" else comp,
        "bloom_amount": amt,
        "bloom_colour": False,
        "glue_colour": False,
        "predelay_ms": 0.0,
    }
    if not B.bloom_is_on(page):
        return None
    return B.design(page, sr)


def _float(raw: np.ndarray) -> np.ndarray:
    x = np.asarray(raw)
    if np.issubdtype(x.dtype, np.integer):
        return x.astype(np.float64) / float(np.iinfo(x.dtype).max)
    return x.astype(np.float64)


def _gen(kind: str, n: int, sr: int, dbfs: float) -> np.ndarray:
    amp = 10.0 ** (float(dbfs) / 20.0)
    t = np.arange(n, dtype=np.float64) / float(sr)
    if kind == "sine":
        return amp * np.sin(2.0 * math.pi * 1000.0 * t)
    if kind == "pad":
        y = (
            np.sin(2.0 * math.pi * 220.0 * t)
            + 0.6 * np.sin(2.0 * math.pi * 277.0 * t)
            + 0.4 * np.sin(2.0 * math.pi * 330.0 * t)
        )
    else:
        rng = np.random.default_rng(1)
        y = np.zeros(n, dtype=np.float64)
        hit = max(1, int(0.04 * sr))
        step = max(hit, int(0.5 * sr))
        for start in range(0, n, step):
            m = min(hit, n - start)
            env = np.linspace(1.0, 0.0, m, dtype=np.float64)
            y[start : start + m] = rng.standard_normal(m) * env
    peak = float(np.max(np.abs(y))) if y.size else 1.0
    if peak < 1.0e-12:
        peak = 1.0
    return y * (amp / peak)


def _mono(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return x
    return np.mean(x, axis=1)


def _is_1k(x: np.ndarray, sr: int) -> bool:
    """True when the settled half is a 1 kHz sine."""
    z = np.asarray(_mono(x), dtype=np.float64)
    z = z[z.size // 2 :]
    per = int(sr // 1000)
    if per < 8 or z.size < per * 8:
        return False
    n = (z.size // per) * per
    z = z[:n]
    mag = np.abs(np.fft.rfft(z))
    k = 1000 * n // int(sr)
    if k <= 0 or k >= mag.size:
        return False
    fund = float(mag[k])
    mag[k] = 0.0
    mag[0] = 0.0
    return fund > 20.0 * float(np.max(mag))


def _thd(y: np.ndarray, sr: int) -> float:
    """Settled half, exact-bin rfft, harmonics 2-15, no window. Percent."""
    z = np.asarray(_mono(y)[len(y) // 2 :], dtype=np.float64)
    per = int(sr // 1000)
    n = (z.size // per) * per
    z = z[:n]
    spec = np.fft.rfft(z)
    scale = 2.0 / n

    def amp(k: int) -> float:
        return abs(spec[k * 1000 * n // int(sr)]) * scale

    fundamental = amp(1)
    if fundamental <= 0.0:
        return 0.0
    harm = sum(amp(k) ** 2 for k in range(2, 16))
    return 100.0 * math.sqrt(harm) / fundamental


def _run(x: np.ndarray, spec: dict | None) -> tuple[np.ndarray, np.ndarray]:
    """Preamp, then the compressor gain, on the dry signal."""
    cols = np.asarray(x, dtype=np.float64)
    mono = cols.ndim == 1
    if mono:
        cols = cols.reshape(-1, 1)
    n = int(cols.shape[0])
    gr = np.zeros(n, dtype=np.float64)
    if spec is None:
        return (cols[:, 0] if mono else cols), gr
    y = cols.copy()
    if (spec.get("pre") or "off") != "off":
        row = B.pack_pre(spec)
        for c in range(y.shape[1]):
            y[:, c] = B._pre_bus(y[:, c], row)
    if float(spec.get("amount_db") or 0.0) > 0.0:
        det = cols.mean(axis=1) if cols.shape[1] > 1 else cols[:, 0]
        g, gr = B._gain_env(det, spec)
        # The render multiplies g onto the FDN. Here it multiplies the dry signal.
        y *= g.reshape(-1, 1)
    if mono:
        return y[:, 0], gr
    return y, gr


def _line(y: np.ndarray, gr: np.ndarray, sr: int, sine: bool, scale: float) -> str:
    a = np.asarray(y, dtype=np.float64)
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    rms = float(np.sqrt(np.mean(a * a))) if a.size else 0.0
    parts = [f"peak={peak:.6f}", f"rms={rms:.6f}"]
    if sine:
        parts.append(f"thd={_thd(y, sr):.6f}")
    parts.append(
        f"gr_min={float(np.min(gr)):.3f} gr_avg={float(np.mean(gr)):.3f} gr_max={float(np.max(gr)):.3f}"
    )
    parts.append(f"scale={scale:.6f}")
    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", nargs="?", help="input wav. Omit it and pass --source.")
    p.add_argument("--source", choices=("sine", "drums", "pad"), help="built-in signal when no wav is given")
    p.add_argument("--dbfs", type=float, default=-18.0, help="peak of a built-in signal, dBFS")
    p.add_argument("--pre", default="none", choices=PRE)
    p.add_argument("--drive", type=float, default=0.0, help="preamp drive, dB")
    p.add_argument("--comp", default="off", choices=COMP)
    p.add_argument("--amount", type=float, default=0.0, help="compressor amount, 0-100. 0 is off")
    p.add_argument("--seconds", type=float, default=8.0)
    p.add_argument("--sr", type=int, default=SR, help="sample rate of a built-in signal")
    p.add_argument("--out", default="audition_strip.wav")
    args = p.parse_args(argv)
    if args.seconds <= 0.0:
        p.error("--seconds must be positive")
    if args.wav:
        sr, raw = wavfile.read(args.wav)
        sr = int(sr)
        audio = _float(raw)
        n = min(int(audio.shape[0]), int(round(args.seconds * sr)))
        if n < 1:
            p.error("input wav is empty")
        audio = audio[:n]
        raw = np.asarray(raw)[:n]
        copied = raw
    else:
        if not args.source:
            p.error("pass a wav or --source sine|drums|pad")
        sr = int(args.sr)
        if sr < 8000:
            p.error("--sr must be at least 8000")
        n = int(round(args.seconds * sr))
        audio = _gen(args.source, n, sr, args.dbfs)
        copied = None
    spec = _spec(args.pre, args.drive, args.comp, args.amount, sr)
    sine = _is_1k(audio, sr)
    if spec is None and copied is not None:
        y = audio
        gr = np.zeros(int(audio.shape[0]), dtype=np.float64)
        scale = 1.0
        out = copied
    else:
        y, gr = _run(audio, spec)
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        scale = 1.0
        if peak > 0.5:
            scale = 0.5 / peak
            y = y * scale
        out = np.asarray(y, dtype=np.float32)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(dest), sr, out)
    print(_line(y, gr, sr, sine, scale))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
