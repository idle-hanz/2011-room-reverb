#!/usr/bin/env python3
"""
Minimal working square FDN for the 2011 room reverb rebuild.

Agreed constraints (from them / overnight):
  * Unscaled ±1 Hadamard (Sylvester) — add/invert only; NO 1/sqrt(N)
  * Single loop gain g in (0,1) for decay (AGC label ``0 > In < 1``)
  * FDN delays from room size W,H,L — NOT image-mirror delays; stagger/coprime-ish
  * Images excite the FDN; early field stays separate
  * c=340 VERIFIED-from-file Const (default); sr=44100 ASSUMED
  * Image origin default corner (macro algebra); centre still available

Delay formula and inject pattern are PROPOSAL — not measured from the ensemble.
Do not invent surface→image map or claim a wired formula was restored.
"""

from __future__ import annotations

import argparse
import math
import sys
import wave
from typing import List, Optional, Sequence, Tuple

try:
    import numpy as np
except ImportError as e:  # pragma: no cover
    raise SystemExit("numpy required for fdn.py") from e


# Optional fast C core (fdn_core.so) — same algorithm, much faster IR render
_FDN_CORE = None
try:
    import ctypes
    from pathlib import Path as _Path
    _so = _Path(__file__).resolve().parent / "fdn_core.so"
    if _so.is_file():
        _FDN_CORE = ctypes.CDLL(str(_so))
        _FDN_CORE.fdn32_process.argtypes = [
            ctypes.POINTER(ctypes.c_double),  # bufs_flat
            ctypes.POINTER(ctypes.c_int),     # sizes
            ctypes.POINTER(ctypes.c_int),     # idx
            ctypes.POINTER(ctypes.c_double),  # H
            ctypes.c_double,                  # g
            ctypes.POINTER(ctypes.c_double),  # inject
            ctypes.c_int,                     # n_samp
            ctypes.POINTER(ctypes.c_double),  # Lch
            ctypes.POINTER(ctypes.c_double),  # Rch
            ctypes.c_int,                     # do_peak
            ctypes.POINTER(ctypes.c_int),     # use_peak
            ctypes.POINTER(ctypes.c_double),  # b0
            ctypes.POINTER(ctypes.c_double),  # b1
            ctypes.POINTER(ctypes.c_double),  # b2
            ctypes.POINTER(ctypes.c_double),  # a1
            ctypes.POINTER(ctypes.c_double),  # a2
            ctypes.POINTER(ctypes.c_double),  # z1
            ctypes.POINTER(ctypes.c_double),  # z2
        ]
        _FDN_CORE.fdn32_process.restype = None
except Exception:
    _FDN_CORE = None

from early_field import (
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    MicStand,
    axial_mode_hz,
    compute_taps,
    rbj_peaking,
    render_wav,
    filter_tap_impulse,
    peaking_stages_for_tap,
    humidity_shelf_coeffs,
    precompute_wall_peaking_coeffs,
    PEAKING_Q,
    prepare_angles,
    prepare_direct_field,
)

Vec3 = Tuple[float, float, float]


def unscaled_hadamard_signs(n: int) -> List[List[int]]:
    """
    Recursive Sylvester Hadamard, entries ±1 only. NO 1/√N scaling.
    ASSUMED construction — do not invent OCR/missing Structure sign rows as verified.
    Loop gain g is separate and clamped to (0,1).
    """
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError(f"Hadamard size must be power of 2, got {n}")
    h: List[List[int]] = [[1]]
    while len(h) < n:
        top = [row + row for row in h]
        bot = [row + [-x for x in row] for row in h]
        h = top + bot
    return h


def unscaled_hadamard_matrix(n: int) -> "np.ndarray":
    """±1 Hadamard as float64 ndarray (unscaled)."""
    return np.asarray(unscaled_hadamard_signs(n), dtype=np.float64)


def inject_tap_into_fdn(
    tap_amplitude: float,
    tap_index: int,
    n_lines: int = 32,
    signs: Sequence[Sequence[int]] | None = None,
) -> List[float]:
    """Map one early tap into N-line inject vector via Hadamard column. No 1/sqrt(N)."""
    if signs is None:
        signs = unscaled_hadamard_signs(n_lines)
    col = tap_index % n_lines
    return [float(tap_amplitude) * float(signs[row][col]) for row in range(n_lines)]


def stub_note() -> str:
    return (
        "FDN active in early-field/fdn.py: unscaled ±1 Hadamard, "
        "loop gain 0..1, delays from room size (PROPOSAL)."
    )


def _primes_at_least(count: int) -> List[int]:
    """Small prime table extended by sieve as needed (PROPOSAL stagger keys)."""
    if count < 1:
        return []
    # Seed covers N≤32; sieve further for 64/128.
    primes = [
        2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37,
        41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89,
        97, 101, 103, 107, 109, 113, 127, 131,
    ]
    if len(primes) >= count:
        return primes
    limit = max(200, count * 20)
    while True:
        sieve = bytearray(b"\x01") * (limit + 1)
        sieve[0:2] = b"\x00\x00"
        for p in range(2, int(limit ** 0.5) + 1):
            if sieve[p]:
                step = p
                start = p * p
                sieve[start : limit + 1 : step] = b"\x00" * (((limit - start) // step) + 1)
        primes = [i for i in range(2, limit + 1) if sieve[i]]
        if len(primes) >= count:
            return primes
        limit *= 2


def propose_fdn_delays_samples(
    W: float,
    H: float,
    L: float,
    sr: int = SAMPLE_RATE_HZ,
    c: float = SPEED_OF_SOUND_M_S,
    n: int = 32,
) -> List[int]:
    """
    PROPOSAL — not from file / not restored.

    FDN line delays must sit in the tens of milliseconds (typical late-tail
    territory). An earlier draft used ~0.28–1.43× one-way wall transit, which
    for a ~5×3×7 m room landed at ~5–25 ms and died as a metallic flutter
    under the unscaled-Hadamard stability bound g < 1/sqrt(N).

    Current formula (still PROPOSAL):
      Tmean = ((W+H+L)/3)/c * sr          # mean one-way samples
      # spread ~2.5× .. 9× mean transit → roughly 25–90 ms in a medium room
      scale_i = 2.5 + (prime_i % 97)/97 * 6.5
      d_i = max(int(0.020*sr), round(Tmean * scale_i))
      uniquify by +1 on collision.

    n must be a power of 2 (Sylvester Hadamard size). Mark: c VERIFIED-from-file
    default 340; sr ASSUMED. Mark PROPOSAL: scale range and prime stagger.
    """
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError(f"FDN size n must be power of 2, got {n}")
    Tmean = ((W + H + L) / 3.0) / c * sr
    primes = _primes_at_least(n)
    raw: List[int] = []
    min_d = max(2, int(round(0.020 * sr)))  # ≥20 ms
    for i in range(n):
        scale = 2.5 + (primes[i] % 97) / 97.0 * 6.5
        d = int(round(Tmean * scale))
        raw.append(max(min_d, d))
    used = set()
    out: List[int] = []
    for d in raw:
        while d in used:
            d += 1
        used.add(d)
        out.append(d)
    return out


def axis_for_line(i: int) -> str:
    """PROPOSAL: lines i%3 → X/Y/Z for optional peaking in loop."""
    return ("X", "Y", "Z")[i % 3]


class FDN:
    """
    Square N-line FDN (N = power of 2, Sylvester Hadamard).
    Loop: delay read → optional peaking → unscaled ±1 Hadamard → * g → write.
    Excitation added into delay inputs each sample (images inject).
    No 1/√N scaling — keep g < 1/√N for stability.
    """

    def __init__(
        self,
        delays: Sequence[int],
        g: float,
        room: Vec3,
        sr: int = SAMPLE_RATE_HZ,
        c: float = SPEED_OF_SOUND_M_S,
        depth_per_axis: float = 0.0,
        peaking: bool = True,
        n: Optional[int] = None,
    ) -> None:
        n_lines = int(n) if n is not None else len(delays)
        if n_lines < 1 or (n_lines & (n_lines - 1)) != 0:
            raise ValueError(f"FDN size must be power of 2, got {n_lines}")
        if len(delays) != n_lines:
            raise ValueError(f"need {n_lines} delays, got {len(delays)}")
        self.n = n_lines
        self.g = float(max(0.0, min(1.0, g)))
        self.delays = [int(d) for d in delays]
        self.max_d = max(self.delays) if self.delays else 0
        self.bufs = [np.zeros(d, dtype=np.float64) for d in self.delays]
        self.idx = [0] * self.n
        self.H = unscaled_hadamard_matrix(self.n)  # (N,N) ±1 unscaled
        self.sr = sr
        self.room = room
        self.c = c
        self.depth_per_axis = max(0.0, min(3.0, abs(depth_per_axis)))
        self.peaking = peaking and self.depth_per_axis > 0.0
        self._b0 = np.ones(self.n)
        self._b1 = np.zeros(self.n)
        self._b2 = np.zeros(self.n)
        self._a1 = np.zeros(self.n)
        self._a2 = np.zeros(self.n)
        self._z1 = np.zeros(self.n)
        self._z2 = np.zeros(self.n)
        self._use_peak = np.zeros(self.n, dtype=bool)
        if self.peaking:
            W, Hh, L = room
            dims = {"X": W, "Y": Hh, "Z": L}
            gain_db = -self.depth_per_axis
            for i in range(self.n):
                ax = axis_for_line(i)
                f0 = axial_mode_hz(c, dims[ax])
                if 0.0 < f0 < sr * 0.49:
                    b0, b1, b2, a0, a1, a2 = rbj_peaking(float(sr), f0, PEAKING_Q, gain_db)
                    inv = 1.0 / a0
                    self._b0[i] = b0 * inv
                    self._b1[i] = b1 * inv
                    self._b2[i] = b2 * inv
                    self._a1[i] = a1 * inv
                    self._a2[i] = a2 * inv
                    self._use_peak[i] = True

    def _apply_peaking(self, reads: "np.ndarray") -> "np.ndarray":
        if not self.peaking:
            return reads
        out = reads.copy()
        for i in range(self.n):
            if not self._use_peak[i]:
                continue
            x = reads[i]
            yi = self._b0[i] * x + self._z1[i]
            self._z1[i] = self._b1[i] * x - self._a1[i] * yi + self._z2[i]
            self._z2[i] = self._b2[i] * x - self._a2[i] * yi
            out[i] = yi
        return out

    def process_block(self, inject: "np.ndarray") -> Tuple["np.ndarray", "np.ndarray"]:
        """
        inject: shape (n_samp, N). Returns stereo L,R.
        Prefers fdn_core.so (C) when N==32; otherwise Python+numpy.
        """
        assert inject.shape[1] == self.n
        if _FDN_CORE is not None and self.n == 32:
            return self._process_block_c(inject)
        return self._process_block_py(inject)

    def _process_block_c(self, inject: "np.ndarray") -> Tuple["np.ndarray", "np.ndarray"]:
        import ctypes
        n_samp = inject.shape[0]
        Lch = np.zeros(n_samp, dtype=np.float64)
        Rch = np.zeros(n_samp, dtype=np.float64)
        sizes = np.asarray(self.delays, dtype=np.int32)
        offsets = np.cumsum(np.concatenate([[0], sizes[:-1]])).astype(np.int32)
        total = int(sizes.sum())
        bufs_flat = np.zeros(total, dtype=np.float64)
        idx = np.asarray(self.idx, dtype=np.int32)
        H = np.ascontiguousarray(self.H, dtype=np.float64)
        inj = np.ascontiguousarray(inject, dtype=np.float64)
        use_peak = self._use_peak.astype(np.int32)
        _FDN_CORE.fdn32_process(
            bufs_flat.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            sizes.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            idx.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            H.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_double(self.g),
            inj.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(n_samp),
            Lch.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            Rch.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int(1 if self.peaking else 0),
            use_peak.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
            self._b0.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._b1.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._b2.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._a1.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._a2.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._z1.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            self._z2.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        )
        self.idx = idx.tolist()
        return Lch, Rch

    def _process_block_py(self, inject: "np.ndarray") -> Tuple["np.ndarray", "np.ndarray"]:
        n_samp = inject.shape[0]
        n = self.n
        Lch = np.zeros(n_samp, dtype=np.float64)
        Rch = np.zeros(n_samp, dtype=np.float64)
        g = self.g
        H = self.H
        bufs = self.bufs
        idx = self.idx
        delays = self.delays
        peaking = self.peaking
        reads = np.empty(n, dtype=np.float64)
        b0, b1, b2 = self._b0, self._b1, self._b2
        a1, a2 = self._a1, self._a2
        z1, z2 = self._z1, self._z2
        use_peak = self._use_peak
        for t in range(n_samp):
            for i in range(n):
                reads[i] = bufs[i][idx[i]]
            if peaking:
                for i in range(n):
                    if use_peak[i]:
                        x = reads[i]
                        yi = b0[i] * x + z1[i]
                        z1[i] = b1[i] * x - a1[i] * yi + z2[i]
                        z2[i] = b2[i] * x - a2[i] * yi
                        reads[i] = yi
            mixed = g * (H @ reads)
            inj_t = inject[t]
            for i in range(n):
                wi = idx[i]
                bufs[i][wi] = mixed[i] + inj_t[i]
                ni = wi + 1
                idx[i] = ni - delays[i] if ni >= delays[i] else ni
            sL = 0.0
            sR = 0.0
            # Pair even/odd lines into L/R (N always even for Sylvester ≥2)
            for i in range(0, n, 2):
                sL += reads[i]
                sR += reads[i + 1]
            Lch[t] = sL
            Rch[t] = sR
        return Lch, Rch


class FDN32(FDN):
    """Alias for FDN(n=32) — live / Reaktor-era size."""

    def __init__(
        self,
        delays: Sequence[int],
        g: float,
        room: Vec3,
        sr: int = SAMPLE_RATE_HZ,
        c: float = SPEED_OF_SOUND_M_S,
        depth_per_axis: float = 0.0,
        peaking: bool = True,
    ) -> None:
        super().__init__(
            delays, g, room, sr=sr, c=c,
            depth_per_axis=depth_per_axis, peaking=peaking, n=32,
        )



def build_inject_from_taps(
    taps,
    n_samp: int,
    sr: int,
    c: float,
    n_lines: int = 32,
) -> "np.ndarray":
    """
    PROPOSAL inject: at each image delay (mean of L/R samples), write
    inject_tap_into_fdn(level, tap_index) into the FDN input bus.
    """
    signs = unscaled_hadamard_signs(n_lines)
    inj = np.zeros((n_samp, n_lines), dtype=np.float64)
    for t in taps:
        d_samp = int(round(0.5 * (t.distance_l + t.distance_r) / c * sr))
        amp = 0.5 * (t.level_l + t.level_r)
        if d_samp < 0 or d_samp >= n_samp:
            continue
        vec = inject_tap_into_fdn(amp, t.index, n_lines, signs)
        for i in range(n_lines):
            inj[d_samp, i] += vec[i]
    return inj


def write_wav_stereo(path: str, L: "np.ndarray", R: "np.ndarray", sr: int) -> dict:
    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R)), 1e-12))
    finite = bool(np.isfinite(L).all() and np.isfinite(R).all())
    has_nan = bool(np.isnan(L).any() or np.isnan(R).any())
    scale = 0.8 / peak if finite and peak > 0 else 0.0
    Ls = L * scale
    Rs = R * scale
    n = len(L)
    interleaved = np.empty(n * 2, dtype=np.float64)
    interleaved[0::2] = Ls
    interleaved[1::2] = Rs
    clipped = np.clip(interleaved, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return {
        "path": path,
        "peak_pre_norm": peak,
        "finite": finite,
        "has_nan": has_nan,
        "n_samp": n,
        "sr": sr,
    }


def render_fdn_and_sum(
    room: Vec3,
    source: Vec3,
    stand: MicStand,
    out_fdn: str,
    out_sum: str,
    out_early: Optional[str] = None,
    sr: int = SAMPLE_RATE_HZ,
    c: float = SPEED_OF_SOUND_M_S,
    g: float = 0.08,
    length_ms: float = 1500.0,
    early_ms: float = 200.0,
    depth_per_axis: float = 1.5,
    humidity: float = 0.0,
    peaking_in_loop: bool = True,
    grid: str = "32",
    origin: str = "corner",
    z_face_4l: bool = True,
    hadamard_n: int = 32,
) -> dict:
    """
    Render FDN IR (excited by early taps) and early+FDN sum.
    Default g=0.08 ASSUMED usable with unscaled H32 (g*sqrt(32)≈0.45 < 1).
    Keep g under 1/sqrt(N) for stability with unscaled ±1 Hadamard.
    Early image count and FDN lines both equal hadamard_n (powers of 2).
    """
    from early_field import grid_bias_for_hadamard_n, normalize_hadamard_n
    n = normalize_hadamard_n(hadamard_n)
    if grid == "32" and n != 32:
        grid = grid_bias_for_hadamard_n(n)
    taps = compute_taps(
        room, source, stand, c=c, grid=grid, origin=origin,
        z_face_4l=z_face_4l, hadamard_n=n,
    )
    delays = propose_fdn_delays_samples(room[0], room[1], room[2], sr=sr, c=c, n=n)
    n_samp = int(sr * length_ms / 1000.0) + 1
    inj = build_inject_from_taps(taps, n_samp, sr, c, n)
    fdn = FDN(
        delays,
        g=g,
        room=room,
        sr=sr,
        c=c,
        depth_per_axis=depth_per_axis if peaking_in_loop else 0.0,
        peaking=peaking_in_loop,
        n=n,
    )
    L_fdn, R_fdn = fdn.process_block(inj)
    stats_fdn = write_wav_stereo(out_fdn, L_fdn, R_fdn, sr)

    early_path = out_early or "/tmp/out_early_for_sum.wav"
    render_wav(
        taps,
        early_path,
        room=room,
        sr=sr,
        c=c,
        length_ms=early_ms,
        depth_per_axis=depth_per_axis,
        humidity=humidity,
    )

    n_early = int(sr * early_ms / 1000.0) + 1
    Le = np.zeros(n_samp, dtype=np.float64)
    Re = np.zeros(n_samp, dtype=np.float64)
    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, depth_per_axis)
    for t in taps:
        dl = int(round(t.distance_l / c * sr))
        dr = int(round(t.distance_r / c * sr))
        peaks = peaking_stages_for_tap(t, room, sr, c, depth_per_axis, wall_cache=wall_cache)
        hum_l = humidity_shelf_coeffs(t.distance_l, sr, humidity)
        hum_r = humidity_shelf_coeffs(t.distance_r, sr, humidity)
        bl = filter_tap_impulse(n_early, dl, t.level_l, t.allpass_stages, sr, peaks, hum_l)
        br = filter_tap_impulse(n_early, dr, t.level_r, t.allpass_stages, sr, peaks, hum_r)
        Le[: len(bl)] += bl
        Re[: len(br)] += br

    fdn_wet = 0.15  # ASSUMED mix so early stays audible
    Ls = Le + fdn_wet * L_fdn
    Rs = Re + fdn_wet * R_fdn
    stats_sum = write_wav_stereo(out_sum, Ls, Rs, sr)

    return {
        "delays": delays,
        "g": g,
        "hadamard_n": n,
        "fdn": stats_fdn,
        "sum": stats_sum,
        "early_path": early_path,
        "n_taps": len(taps),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="2011 room reverb — minimal FDN32 render")
    p.add_argument("--W", type=float, default=5.0)
    p.add_argument("--H", type=float, default=3.0)
    p.add_argument("--L", type=float, default=7.0)
    p.add_argument("--sx", type=float, default=0.0)
    p.add_argument("--sy", type=float, default=0.0)
    p.add_argument("--sz", type=float, default=2.0)
    p.add_argument("--mic-x", type=float, default=0.0)
    p.add_argument("--mic-y", type=float, default=0.0)
    p.add_argument("--mic-z", type=float, default=-2.0)
    p.add_argument("--space", type=float, default=0.25)
    p.add_argument("--angle-deg", type=float, default=15.0,
                   help="ASSUMED legacy ±toe degrees (ignored if --diverg / --use-prepare)")
    p.add_argument("--diverg", type=float, default=None,
                   help="Prepare Diverg → MLALR/MRALR = Diverg×0.3×±0.25 VERIFIED")
    p.add_argument("--use-prepare", action="store_true")
    p.add_argument("--sox", type=float, default=0.5)
    p.add_argument("--soz", type=float, default=0.5)
    p.add_argument("--car-omni", type=float, default=1.0)
    p.add_argument("--c", type=float, default=SPEED_OF_SOUND_M_S)
    p.add_argument("--sr", type=int, default=SAMPLE_RATE_HZ)
    p.add_argument("--g", type=float, default=0.08,
                   help="Loop gain 0..1 (default 0.08 ASSUMED for unscaled H32)")
    p.add_argument("--depth-per-axis", type=float, default=1.5)
    p.add_argument("--humidity", type=float, default=0.0)
    p.add_argument("--length-ms", type=float, default=1500.0)
    p.add_argument("--early-ms", type=float, default=200.0)
    p.add_argument("--no-loop-peaking", action="store_true")
    p.add_argument(
        "--grid",
        choices=("8", "16", "32", "64", "64like", "128"),
        default="32",
        help="Early image table (paired with --hadamard-n when set)",
    )
    p.add_argument(
        "--hadamard-n",
        type=int,
        default=32,
        choices=(8, 16, 32, 64, 128),
        help="Hadamard size: images + FDN lines (unscaled ±1; default 32)",
    )
    p.add_argument(
        "--origin",
        choices=("corner", "centre", "center"),
        default="corner",
        help="Image origin (default corner)",
    )
    p.add_argument("--no-z-face-4l", action="store_true")
    p.add_argument("--out-fdn", default="/workspace/early-field/out_fdn.wav")
    p.add_argument("--out-sum", default="/workspace/early-field/out_early_plus_fdn.wav")
    p.add_argument("--out-early", default="/workspace/early-field/out_early.wav")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    room = (args.W, args.H, args.L)
    car = max(0.0, min(1.0, args.car_omni))
    if args.use_prepare:
        diverg = 0.0 if args.diverg is None else float(args.diverg)
        prep = prepare_direct_field(
            args.W, args.H, args.L,
            mz=args.mic_z, my=args.mic_y, space=args.space,
            diverg=diverg, sox=args.sox, soz=args.soz,
        )
        source = prep.source
        stand = MicStand.from_prepare(prep, car_omni=car)
    else:
        source = (args.sx, args.sy, args.sz)
        if args.diverg is not None:
            mlalr, mralr = prepare_angles(float(args.diverg))
        else:
            a = math.radians(args.angle_deg)
            mlalr, mralr = (+a, -a)
        stand = MicStand(
            cx=args.mic_x,
            cy=args.mic_y,
            cz=args.mic_z,
            space=args.space,
            car_omni=car,
            mlalr=mlalr,
            mralr=mralr,
        )
    origin = "centre" if args.origin in ("centre", "center") else "corner"
    print("c =", args.c, "m/s (VERIFIED-from-file default 340); sr =", args.sr, "ASSUMED; origin =", origin)
    print("PROPOSAL: FDN delays from W,H,L transit × prime stagger (not image delays)")
    print("from them: unscaled ±1 Hadamard; loop gain g =", args.g, "(clamped 0..1)")
    print("grid =", args.grid, "hadamard_n =", args.hadamard_n, "(images + FDN lines; unscaled ±1)")
    delays = propose_fdn_delays_samples(
        args.W, args.H, args.L, sr=args.sr, c=args.c, n=args.hadamard_n
    )
    print(f"FDN delay samples ({args.hadamard_n}):", delays)
    print(stub_note())
    stats = render_fdn_and_sum(
        room,
        source,
        stand,
        out_fdn=args.out_fdn,
        out_sum=args.out_sum,
        out_early=args.out_early,
        sr=args.sr,
        c=args.c,
        g=args.g,
        length_ms=args.length_ms,
        early_ms=args.early_ms,
        depth_per_axis=max(0.0, min(3.0, abs(args.depth_per_axis))),
        humidity=max(0.0, min(1.0, args.humidity)),
        peaking_in_loop=not args.no_loop_peaking,
        grid=args.grid,
        origin=origin,
        z_face_4l=not args.no_z_face_4l,
        hadamard_n=args.hadamard_n,
    )
    print()
    print(
        "Wrote", stats["fdn"]["path"],
        "peak_pre_norm=", round(stats["fdn"]["peak_pre_norm"], 6),
        "finite=", stats["fdn"]["finite"],
        "nan=", stats["fdn"]["has_nan"],
    )
    print(
        "Wrote", stats["sum"]["path"],
        "peak_pre_norm=", round(stats["sum"]["peak_pre_norm"], 6),
        "finite=", stats["sum"]["finite"],
        "nan=", stats["sum"]["has_nan"],
    )
    print("Also refreshed early:", stats["early_path"])
    ok = (
        stats["fdn"]["finite"]
        and not stats["fdn"]["has_nan"]
        and stats["sum"]["finite"]
        and not stats["sum"]["has_nan"]
    )
    print("STABLE:" if ok else "UNSTABLE:", "no NaNs, finite peak" if ok else "check output")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
