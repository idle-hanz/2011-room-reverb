#!/usr/bin/env python3
"""
Moving-source room listening demo for Idle Hanz.

Block-based time-varying convolution of a dry WAV through the wired early-field
prototype (corner mirrors, c=340, 1/r, Prepare mic) plus a short FDN32 tail.

ASSUMED (tagged in comments below — not from ensemble):
  * Room W=6, H=3, L=8 m (musical listening-room defaults)
  * Fixed mic via Prepare: MY=1.5, MZ=L−1.5 → MCZ=1.5; Space=0.25; Diverg=1
  * Source path: one elliptical orbit in Prepare SoX/SoZ over the full clip
    sox = 0.50 + 0.42·cos(2π t/T)
    soz = 0.55 + 0.35·sin(2π t/T)
    SY = MY (Prepare) — mid-height
  * Hop 100 ms, 50% overlap Hann frames (frame=200 ms)
  * Early IR 90 ms (grid 32); FDN IR 400 ms, g=0.08, fdn_wet=0.12 into IR
  * Dry bleed 0.10 / wet 1.00 so material stays audible
  * Peak normalize to −1 dBTP

Does NOT invent Hadamard rows or A–F surface maps — uses fdn.py unscaled ±1 + g∈(0,1).
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import wave
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

from early_field import (
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    MicStand,
    allpass_ir_for_stages,
    cascade_biquads,
    biquad_process,
    compute_taps,
    humidity_shelf_coeffs,
    peaking_stages_for_tap,
    precompute_wall_peaking_coeffs,
    prepare_direct_field,
)
from fdn import (
    FDN32,
    build_inject_from_taps,
    propose_fdn_delays_samples,
)

Vec3 = Tuple[float, float, float]

# --- ASSUMED demo geometry / processing --------------------------------------
ROOM_W, ROOM_H, ROOM_L = 6.0, 3.0, 8.0
MIC_Y = 1.5
# MZ so MCZ = L − MZ = 1.5 (mic stand near front wall)
MIC_Z_PANEL = ROOM_L - 1.5
SPACE = 0.25
DIVERG = 1.0
CAR_OMNI = 1.0
DEPTH_PER_AXIS = 1.5
HUMIDITY = 0.0
ORIGIN = "corner"
GRID = "32"

HOP_MS = 100.0          # ASSUMED block hop
FRAME_MS = 200.0        # ASSUMED 50% overlap
EARLY_MS = 90.0         # ASSUMED short early IR
FDN_MS = 400.0          # ASSUMED short tail
FDN_G = 0.08            # ASSUMED usable with unscaled H32
FDN_WET = 0.12          # ASSUMED mix into combined IR (early stays clear)
DRY_GAIN = 0.10         # ASSUMED bleed (low so L/R motion stays clear)
WET_GAIN = 1.00         # ASSUMED
TARGET_PEAK_DBTP = -1.0
SHORT_SECONDS = 25.0    # ASSUMED highlight length
SHORT_START_S = 12.0    # ASSUMED: start where orbit is mid-swing


def load_wav_mono(path: str) -> Tuple[np.ndarray, int]:
    """Load WAV; mix stereo → mono mid (L+R)/2. Resample not supported."""
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise SystemExit(f"expected pcm_s16le (2-byte), got sampwidth={sw}")
    pcm = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if nch == 1:
        mono = pcm
    elif nch == 2:
        mono = 0.5 * (pcm[0::2] + pcm[1::2])
    else:
        mono = pcm.reshape(-1, nch).mean(axis=1)
    return mono, sr


def write_wav_stereo(path: str, L: np.ndarray, R: np.ndarray, sr: int) -> dict:
    n = len(L)
    interleaved = np.empty(n * 2, dtype=np.float64)
    interleaved[0::2] = L
    interleaved[1::2] = R
    peak = float(np.max(np.abs(interleaved))) if n else 0.0
    clipped = np.clip(interleaved, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return {"path": path, "n_samp": n, "sr": sr, "peak": peak, "duration_s": n / float(sr)}


def path_sox_soz(t_frac: float) -> Tuple[float, float]:
    """ASSUMED elliptical orbit in Prepare SoX/SoZ over one full loop."""
    ang = 2.0 * math.pi * t_frac
    sox = 0.50 + 0.42 * math.cos(ang)
    soz = 0.55 + 0.35 * math.sin(ang)
    # clamp gently into (0,1)
    sox = min(0.98, max(0.02, sox))
    soz = min(0.98, max(0.02, soz))
    return sox, soz


def _apply_allpass_cached(
    buf: np.ndarray,
    delay_samp: int,
    amp: float,
    stages: int,
    ap_cache: dict,
) -> None:
    if stages <= 0:
        if 0 <= delay_samp < len(buf):
            buf[delay_samp] += amp
        return
    ir = ap_cache[stages]
    if delay_samp >= len(buf) or delay_samp + len(ir) <= 0:
        return
    start = max(0, delay_samp)
    ir0 = start - delay_samp
    end = min(len(buf), delay_samp + len(ir))
    ir1 = ir0 + (end - start)
    buf[start:end] += amp * ir[ir0:ir1]


def render_early_ir(
    taps,
    room: Vec3,
    sr: int,
    c: float,
    length_ms: float,
    depth_per_axis: float,
    humidity: float,
    wall_cache,
    ap_cache: dict,
) -> Tuple[np.ndarray, np.ndarray]:
    n_samp = int(sr * length_ms / 1000.0) + 1
    Lch = np.zeros(n_samp, dtype=np.float64)
    Rch = np.zeros(n_samp, dtype=np.float64)
    for t in taps:
        dl = int(round(t.distance_l / c * sr))
        dr = int(round(t.distance_r / c * sr))
        peaks = peaking_stages_for_tap(
            t, room, sr, c, depth_per_axis, wall_cache=wall_cache
        )
        hum_l = humidity_shelf_coeffs(t.distance_l, sr, humidity)
        hum_r = humidity_shelf_coeffs(t.distance_r, sr, humidity)
        bl = np.zeros(n_samp, dtype=np.float64)
        br = np.zeros(n_samp, dtype=np.float64)
        _apply_allpass_cached(bl, dl, t.level_l, t.allpass_stages, ap_cache)
        _apply_allpass_cached(br, dr, t.level_r, t.allpass_stages, ap_cache)
        if peaks:
            bl = cascade_biquads(bl, peaks)
            br = cascade_biquads(br, peaks)
        if hum_l is not None:
            bl = biquad_process(bl, hum_l)
        if hum_r is not None:
            br = biquad_process(br, hum_r)
        Lch += bl
        Rch += br
    return Lch, Rch


def render_fdn_ir(
    taps,
    room: Vec3,
    sr: int,
    c: float,
    length_ms: float,
    g: float,
    depth_per_axis: float,
    delays: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray]:
    n_samp = int(sr * length_ms / 1000.0) + 1
    inj = build_inject_from_taps(taps, n_samp, sr, c, 32)
    fdn = FDN32(
        delays,
        g=g,
        room=room,
        sr=sr,
        c=c,
        depth_per_axis=depth_per_axis,
        peaking=True,
    )
    return fdn.process_block(inj)


def combined_ir(
    taps,
    room: Vec3,
    sr: int,
    c: float,
    wall_cache,
    ap_cache: dict,
    delays: Sequence[int],
) -> Tuple[np.ndarray, np.ndarray]:
    Le, Re = render_early_ir(
        taps, room, sr, c, EARLY_MS, DEPTH_PER_AXIS, HUMIDITY, wall_cache, ap_cache
    )
    Lf, Rf = render_fdn_ir(
        taps, room, sr, c, FDN_MS, FDN_G, DEPTH_PER_AXIS, delays
    )
    n = max(len(Le), len(Lf))
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)
    L[: len(Le)] += Le
    R[: len(Re)] += Re
    L[: len(Lf)] += FDN_WET * Lf
    R[: len(Rf)] += FDN_WET * Rf
    # gentle per-IR peak guard so OLA stays stable (ASSUMED; final −1 dBTP later)
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-12)
    scale = min(1.0, 0.9 / peak)
    return L * scale, R * scale


def hann_window(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n, dtype=np.float64) / (n - 1))


def process_moving(
    dry: np.ndarray,
    sr: int,
    *,
    verbose: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    room: Vec3 = (ROOM_W, ROOM_H, ROOM_L)
    c = SPEED_OF_SOUND_M_S
    n_dry = len(dry)
    duration = n_dry / float(sr)

    hop = max(1, int(round(HOP_MS * 0.001 * sr)))
    frame = max(hop, int(round(FRAME_MS * 0.001 * sr)))
    win = hann_window(frame)

    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEPTH_PER_AXIS)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    delays = propose_fdn_delays_samples(ROOM_W, ROOM_H, ROOM_L, sr=sr, c=c, n=32)

    # Fixed mic stand from Prepare (source SoX/SoZ vary per hop)
    prep0 = prepare_direct_field(
        ROOM_W,
        ROOM_H,
        ROOM_L,
        mz=MIC_Z_PANEL,
        my=MIC_Y,
        space=SPACE,
        diverg=DIVERG,
        sox=0.5,
        soz=0.5,
    )
    stand = MicStand.from_prepare(prep0, car_omni=CAR_OMNI)

    # Output length: dry + max IR − 1
    ir_max = int(sr * max(EARLY_MS, FDN_MS) / 1000.0) + 1
    out_n = n_dry + ir_max + frame
    wet_L = np.zeros(out_n, dtype=np.float64)
    wet_R = np.zeros(out_n, dtype=np.float64)

    starts = list(range(0, n_dry, hop))
    t_wall0 = time.time()
    for i, start in enumerate(starts):
        t_frac = (start + 0.5 * frame) / float(n_dry)
        t_frac = min(1.0, max(0.0, t_frac))
        sox, soz = path_sox_soz(t_frac)
        prep = prepare_direct_field(
            ROOM_W,
            ROOM_H,
            ROOM_L,
            mz=MIC_Z_PANEL,
            my=MIC_Y,
            space=SPACE,
            diverg=DIVERG,
            sox=sox,
            soz=soz,
        )
        source = prep.source
        taps = compute_taps(
            room, source, stand, c=c, grid=GRID, origin=ORIGIN, z_face_4l=True
        )
        ir_L, ir_R = combined_ir(
            taps, room, sr, c, wall_cache, ap_cache, delays
        )

        end = min(start + frame, n_dry)
        block = np.zeros(frame, dtype=np.float64)
        block[: end - start] = dry[start:end]
        block *= win

        yL = np.convolve(block, ir_L)
        yR = np.convolve(block, ir_R)
        wet_L[start : start + len(yL)] += yL
        wet_R[start : start + len(yR)] += yR

        if verbose and (i % 50 == 0 or i == len(starts) - 1):
            elapsed = time.time() - t_wall0
            pct = 100.0 * (i + 1) / len(starts)
            print(
                f"  hop {i+1}/{len(starts)} ({pct:.0f}%)  "
                f"t={start/sr:.1f}s  SoX={sox:.3f} SoZ={soz:.3f}  "
                f"src=({source[0]:.2f},{source[1]:.2f},{source[2]:.2f})  "
                f"elapsed={elapsed:.1f}s",
                flush=True,
            )

    # Trim to dry length + small tail (keep ~FDN_MS of reverb after end)
    keep = n_dry + int(sr * FDN_MS * 0.001)
    wet_L = wet_L[:keep]
    wet_R = wet_R[:keep]
    dry_pad = np.zeros(keep, dtype=np.float64)
    dry_pad[:n_dry] = dry

    # Hann OLA coherent gain ~1.5 for 50% hop; compensate (ASSUMED)
    ola_comp = 2.0 / 3.0
    mix_L = DRY_GAIN * dry_pad + WET_GAIN * ola_comp * wet_L
    mix_R = DRY_GAIN * dry_pad + WET_GAIN * ola_comp * wet_R
    return mix_L, mix_R


def peak_normalize(L: np.ndarray, R: np.ndarray, target_dbtp: float = TARGET_PEAK_DBTP):
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-12)
    target = 10.0 ** (target_dbtp / 20.0)
    scale = target / peak
    return L * scale, R * scale, peak, scale


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Moving-source early-field + FDN listening demo")
    p.add_argument(
        "--in",
        dest="infile",
        default=(
            "/home/box/agent-data/agents/d24fb43d-ae40-4297-88a7-a20ba31be48e/"
            "attachments/4d8c414f9dba5cfb1cd8786389f916a0931564bbd7f7e9336338c11c6b3ac48a.wav"
        ),
    )
    p.add_argument(
        "--out",
        default="/workspace/early-field/out_moving_room_demo.wav",
    )
    p.add_argument(
        "--out-short",
        default="/workspace/early-field/out_moving_room_demo_short.wav",
    )
    p.add_argument("--no-short", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    infile = args.infile
    if not Path(infile).is_file():
        print(f"ERROR: input not found: {infile}", file=sys.stderr)
        return 1

    print(f"Loading {infile}")
    dry, sr = load_wav_mono(infile)
    if sr != SAMPLE_RATE_HZ:
        print(
            f"WARNING: input sr={sr} != prototype {SAMPLE_RATE_HZ}; "
            f"delays use input sr (ASSUMED ok for demo)",
            file=sys.stderr,
        )
    print(
        f"Dry mono: {len(dry)} samp, {len(dry)/sr:.2f}s @ {sr} Hz  "
        f"peak={float(np.max(np.abs(dry))):.4f}"
    )
    print(
        f"Room {ROOM_W}×{ROOM_H}×{ROOM_L} m | Prepare MZ={MIC_Z_PANEL} MY={MIC_Y} "
        f"Space={SPACE} Diverg={DIVERG} | hop={HOP_MS}ms frame={FRAME_MS}ms | "
        f"early={EARLY_MS}ms FDN={FDN_MS}ms g={FDN_G}"
    )
    print("Path: elliptical SoX/SoZ orbit (one loop over clip) — ASSUMED")

    t0 = time.time()
    L, R = process_moving(dry, sr, verbose=not args.quiet)
    L, R, peak_pre, scale = peak_normalize(L, R, TARGET_PEAK_DBTP)
    stats = write_wav_stereo(args.out, L, R, sr)
    elapsed = time.time() - t0
    print(
        f"Wrote {args.out}  dur={stats['duration_s']:.2f}s  "
        f"peak_pre={peak_pre:.4f} scale={scale:.4f} → −1 dBTP  "
        f"render={elapsed:.1f}s"
    )

    if not args.no_short:
        s0 = int(SHORT_START_S * sr)
        s1 = min(len(L), s0 + int(SHORT_SECONDS * sr))
        if s0 >= len(L):
            s0 = 0
            s1 = min(len(L), int(SHORT_SECONDS * sr))
        Ls, Rs = L[s0:s1].copy(), R[s0:s1].copy()
        Ls, Rs, _, _ = peak_normalize(Ls, Rs, TARGET_PEAK_DBTP)
        st = write_wav_stereo(args.out_short, Ls, Rs, sr)
        print(
            f"Wrote {args.out_short}  dur={st['duration_s']:.2f}s  "
            f"(slice {s0/sr:.1f}–{s1/sr:.1f}s)"
        )

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
