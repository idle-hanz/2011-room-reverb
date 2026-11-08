"""PREAMP-AU1. Dry-strip CLI: bypass is the input, 610-A THD matches the shaper test."""
from __future__ import annotations

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
