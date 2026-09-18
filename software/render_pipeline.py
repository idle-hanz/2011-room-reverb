#!/usr/bin/env python3
"""
Render pipeline for the 2011 Room Reverb tweak app.

Wraps the copied early-field / FDN engine. Unscaled ±1 FDN + Prepare VERIFIED
algebra. Optional ASSUMED Surfaces A–F absorb×EQ + seeded path-length jitter
(see surface_colour.py) — does NOT claim Structure-locked A–F EQ dictionary.
"""

from __future__ import annotations

import math
import sys
import wave
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

# Engine lives beside this file under software/engine/
_ENGINE = Path(__file__).resolve().parent / "engine"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from early_field import (  # noqa: E402
    DEFAULT_HADAMARD_N,
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    MicStand,
    allpass_ir_for_stages,
    cascade_biquads,
    biquad_process,
    compute_taps,
    grid_bias_for_hadamard_n,
    humidity_shelf_coeffs,
    normalize_hadamard_n,
    peaking_stages_for_tap,
    precompute_wall_peaking_coeffs,
    prepare_direct_field,
)
from fdn import (  # noqa: E402
    FDN,
    FDN32,
    build_inject_from_taps,
    propose_fdn_delays_samples,
)

from surface_colour import (  # noqa: E402
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    apply_surface_to_buffer,
    jittered_distance,
    parse_lambda_ref,
    parse_surfaces,
    surfaces_hit_by_n,
    surfaces_payload,
)


Vec3 = Tuple[float, float, float]

# Processing defaults tagged ASSUMED (musical / demo; not from ensemble)
DEFAULT_HOP_MS = 100.0
DEFAULT_FRAME_MS = 200.0
DEFAULT_EARLY_MS = 90.0
DEFAULT_DEPTH = 1.5
DEFAULT_HUMIDITY = 0.0
TARGET_PEAK_DBTP = -1.0


def fft_convolve(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """FFT convolution — much faster than np.convolve for long dry × IR."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = int(a.size + b.size - 1)
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    nfft = 1 << max(0, (n - 1).bit_length())
    fa = np.fft.rfft(a, nfft)
    fb = np.fft.rfft(b, nfft)
    return np.fft.irfft(fa * fb, nfft)[:n].astype(np.float64, copy=False)


def _pcm_bytes_to_float(raw: bytes, sampwidth: int) -> np.ndarray:
    """Decode little-endian PCM to float64 in roughly [-1, 1]."""
    if sampwidth == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if sampwidth == 3:
        # Packed 24-bit little-endian → sign-extended int32 → float
        a = np.frombuffer(raw, dtype=np.uint8)
        if a.size % 3:
            raise ValueError("24-bit WAV byte length is not a multiple of 3")
        b = a.reshape(-1, 3).astype(np.uint32)
        u = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        # sign-extend bit 23
        neg = (u & 0x800000) != 0
        s = u.astype(np.int32)
        s[neg] = s[neg] - 0x1000000
        return s.astype(np.float64) / 8388608.0  # 2^23
    if sampwidth == 4:
        # Assume signed 32-bit PCM (common DAW export). Float32 WAVs need a different reader.
        return np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    if sampwidth == 1:
        # Unsigned 8-bit PCM
        return (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    raise ValueError(
        f"unsupported WAV bit depth (sampwidth={sampwidth}); use 16/24/32-bit PCM"
    )


def load_wav_mono(path: str) -> Tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    pcm = _pcm_bytes_to_float(raw, sw)
    if nch == 1:
        mono = pcm
    elif nch == 2:
        mono = 0.5 * (pcm[0::2] + pcm[1::2])
    else:
        mono = pcm.reshape(-1, nch).mean(axis=1)
    return mono, sr


def write_wav_stereo(path: str, L: np.ndarray, R: np.ndarray, sr: int) -> dict:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
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


def hann_window(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * math.pi * np.arange(n, dtype=np.float64) / (n - 1))


def peak_normalize(L: np.ndarray, R: np.ndarray, target_dbtp: float = TARGET_PEAK_DBTP):
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-12)
    target = 10.0 ** (target_dbtp / 20.0)
    scale = target / peak
    return L * scale, R * scale, peak, scale


def path_sox_soz(
    t_frac: float,
    preset: str,
    *,
    cx: float = 0.50,
    cz: float = 0.55,
    rx: float = 0.42,
    rz: float = 0.35,
    rate: float = 1.0,
    sox_still: float = 0.5,
    soz_still: float = 0.5,
) -> Tuple[float, float]:
    """Source path in Prepare SoX/SoZ. Path shapes are ASSUMED (not from ensemble)."""
    t_frac = min(1.0, max(0.0, t_frac))
    if preset == "still":
        return sox_still, soz_still
    ang = 2.0 * math.pi * t_frac * rate
    if preset == "perimeter":
        # Square-ish perimeter in SoX/SoZ (ASSUMED)
        u = (t_frac * rate) % 1.0
        if u < 0.25:
            sox = 0.08 + (0.92 - 0.08) * (u / 0.25)
            soz = 0.08
        elif u < 0.50:
            sox = 0.92
            soz = 0.08 + (0.92 - 0.08) * ((u - 0.25) / 0.25)
        elif u < 0.75:
            sox = 0.92 - (0.92 - 0.08) * ((u - 0.50) / 0.25)
            soz = 0.92
        else:
            sox = 0.08
            soz = 0.92 - (0.92 - 0.08) * ((u - 0.75) / 0.25)
    else:
        # ellipse (default)
        sox = cx + rx * math.cos(ang)
        soz = cz + rz * math.sin(ang)
    sox = min(0.98, max(0.02, sox))
    soz = min(0.98, max(0.02, soz))
    return sox, soz


def _apply_allpass_cached(buf, delay_samp, amp, stages, ap_cache):
    """Integer-sample placement (legacy). Prefer _apply_ir_at for jittered delays."""
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


def _apply_ir_at(buf, delay_float, amp, stages, ap_cache):
    """Place amp (or amp×allpass IR) at a possibly fractional delay (linear interp).

    Path-length jitter is sub-sample at default λ_ref=0.02 m; integer round()
    would hide Δd. Linear interpolation keeps Δd audible/bit-visible.
    """
    n = len(buf)
    ir = None if stages <= 0 else ap_cache.get(int(stages))
    if delay_float >= n or (ir is None and delay_float <= -1.0):
        return
    i0 = int(math.floor(delay_float))
    f = float(delay_float) - i0
    omf = 1.0 - f
    if ir is None:
        if 0 <= i0 < n:
            buf[i0] += amp * omf
        if 0 <= i0 + 1 < n:
            buf[i0 + 1] += amp * f
        return
    ir_arr = ir
    n_ir = len(ir_arr)
    if i0 >= n or i0 + n_ir + 1 <= 0:
        return
    for k in range(n_ir):
        v = amp * float(ir_arr[k])
        j = i0 + k
        if 0 <= j < n:
            buf[j] += omf * v
        if 0 <= j + 1 < n:
            buf[j + 1] += f * v


def render_early_ir(
    taps, room, sr, c, length_ms, depth_per_axis, humidity, wall_cache, ap_cache,
    surfaces=None,
    diffusion_seed=DEFAULT_DIFFUSION_SEED,
    lambda_ref=DEFAULT_LAMBDA_REF_M,
    mic_left=None,
    mic_right=None,
):
    """Render early IR. Optional ASSUMED surfaces absorb×EQ + path-length jitter.

    Diffusion knob D jitters path length (metres): Δd = D·λ_ref·sin²(θ)·u.
    Geometric Schroeder allpass (tap.allpass_stages) is unchanged — not a
    diffusion proxy. Seeded RNG: same params+seed ⇒ bit-identical IR.
    """
    n_samp = int(sr * length_ms / 1000.0) + 1
    Lch = np.zeros(n_samp, dtype=np.float64)
    Rch = np.zeros(n_samp, dtype=np.float64)
    surfaces = surfaces or None
    seed = int(diffusion_seed)
    lam = float(lambda_ref)
    for t in taps:
        d_l = float(t.distance_l)
        d_r = float(t.distance_r)
        # ASSUMED surface hit from geometric n (not Structure A–F OCR masks)
        hit = surfaces_hit_by_n(t.n) if surfaces else []
        if surfaces and hit:
            img = t.position
            if mic_left is not None:
                d_l = jittered_distance(
                    d_l, t.n, t.index, "L", img, mic_left, surfaces,
                    seed=seed, lambda_ref=lam,
                )
            if mic_right is not None:
                d_r = jittered_distance(
                    d_r, t.n, t.index, "R", img, mic_right, surfaces,
                    seed=seed, lambda_ref=lam,
                )
        dl = d_l / c * sr
        dr = d_r / c * sr
        peaks = peaking_stages_for_tap(
            t, room, sr, c, depth_per_axis, wall_cache=wall_cache
        )
        hum_l = humidity_shelf_coeffs(d_l, sr, humidity)
        hum_r = humidity_shelf_coeffs(d_r, sr, humidity)
        ap_stages = int(t.allpass_stages)  # geometric order; not diffusion
        bl = np.zeros(n_samp, dtype=np.float64)
        br = np.zeros(n_samp, dtype=np.float64)
        _apply_ir_at(bl, dl, t.level_l, ap_stages, ap_cache)
        _apply_ir_at(br, dr, t.level_r, ap_stages, ap_cache)
        if peaks:
            bl = cascade_biquads(bl, peaks)
            br = cascade_biquads(br, peaks)
        if hum_l is not None:
            bl = biquad_process(bl, hum_l)
        if hum_r is not None:
            br = biquad_process(br, hum_r)
        # ASSUMED absorb×EQ cascade for hit surfaces
        if surfaces and hit:
            bl = apply_surface_to_buffer(bl, surfaces, hit, float(sr))
            br = apply_surface_to_buffer(br, surfaces, hit, float(sr))
        Lch += bl
        Rch += br
    return Lch, Rch


def render_fdn_ir(taps, room, sr, c, length_ms, g, depth_per_axis, delays, n_lines=32):
    n_samp = int(sr * length_ms / 1000.0) + 1
    n_lines = int(n_lines)
    inj = build_inject_from_taps(taps, n_samp, sr, c, n_lines)
    fdn = FDN(
        delays,
        g=g,
        room=room,
        sr=sr,
        c=c,
        depth_per_axis=depth_per_axis,
        peaking=True,
        n=n_lines,
    )
    return fdn.process_block(inj)


def combined_ir(
    taps,
    room,
    sr,
    c,
    wall_cache,
    ap_cache,
    delays,
    *,
    early_ms: float,
    fdn_ms: float,
    fdn_g: float,
    early_wet: float,
    fdn_wet: float,
    hadamard_n: int = 32,
    surfaces=None,
    diffusion_seed: int = DEFAULT_DIFFUSION_SEED,
    lambda_ref: float = DEFAULT_LAMBDA_REF_M,
    mic_left=None,
    mic_right=None,
):
    Le, Re = render_early_ir(
        taps, room, sr, c, early_ms, DEFAULT_DEPTH, DEFAULT_HUMIDITY, wall_cache, ap_cache,
        surfaces=surfaces,
        diffusion_seed=diffusion_seed,
        lambda_ref=lambda_ref,
        mic_left=mic_left,
        mic_right=mic_right,
    )
    Lf, Rf = render_fdn_ir(
        taps, room, sr, c, fdn_ms, fdn_g, DEFAULT_DEPTH, delays, n_lines=hadamard_n
    )
    n = max(len(Le), len(Lf))
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)
    L[: len(Le)] += early_wet * Le
    R[: len(Re)] += early_wet * Re
    L[: len(Lf)] += fdn_wet * Lf
    R[: len(Rf)] += fdn_wet * Rf
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-12)
    scale = min(1.0, 0.9 / peak)
    return L * scale, R * scale


def render(
    dry: np.ndarray,
    sr: int,
    *,
    W: float,
    H: float,
    L: float,
    sox: float,
    soz: float,
    mz: float,
    my: float,
    sy: Optional[float] = None,
    space: float,
    diverg: float,
    car_omni: float,
    early_wet: float,
    fdn_wet: float,
    dry_gain: float,
    fdn_g: float,
    ir_length_ms: float,
    path_on: bool,
    path_preset: str = "ellipse",
    ellipse_rate: float = 1.0,
    ellipse_rx: float = 0.42,
    ellipse_rz: float = 0.35,
    mcx: Optional[float] = None,
    toe_half_deg: Optional[float] = None,
    hadamard_n: int = DEFAULT_HADAMARD_N,
    surfaces=None,
    diffusion_seed: int = DEFAULT_DIFFUSION_SEED,
    lambda_ref: float = DEFAULT_LAMBDA_REF_M,
    pattern_l: Optional[str] = None,
    pattern_c: Optional[str] = None,
    pattern_r: Optional[str] = None,
    yaw_l_deg: Optional[float] = None,
    yaw_c_deg: Optional[float] = None,
    yaw_r_deg: Optional[float] = None,
    progress_cb=None,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Render dry mono through early-field (+ optional FDN) with optional motion.

    When path_on is False: single IR convolution (fast).
    When path_on is True: block/OLA moving path (like moving_room_demo.py).
    """
    room: Vec3 = (float(W), float(H), float(L))
    c = SPEED_OF_SOUND_M_S
    surfaces = parse_surfaces(surfaces) if surfaces is not None else default_surfaces()
    seed = int(diffusion_seed)
    lam = parse_lambda_ref(lambda_ref)
    n_dry = len(dry)

    # Split IR length: early gets min(90, ir_len); FDN uses full ir_len (ASSUMED split)
    early_ms = min(DEFAULT_EARLY_MS, float(ir_length_ms))
    fdn_ms = max(early_ms, float(ir_length_ms))
    g = float(np.clip(fdn_g, 1e-6, 0.999))

    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEFAULT_DEPTH)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    n_had = normalize_hadamard_n(hadamard_n)
    grid = grid_bias_for_hadamard_n(n_had)
    delays = propose_fdn_delays_samples(W, H, L, sr=sr, c=c, n=n_had)

    def taps_at(sox_v: float, soz_v: float):
        prep = prepare_direct_field(
            W, H, L, mz=mz, my=my, space=space, diverg=diverg, sox=sox_v, soz=soz_v, mcx=mcx,
            toe_half_deg=toe_half_deg,
            yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
            sy=sy,
        )
        stand = MicStand.from_prepare(
            prep, car_omni=car_omni,
            pattern_l=pattern_l, pattern_c=pattern_c, pattern_r=pattern_r,
            yaw_l_deg=yaw_l_deg, yaw_c_deg=yaw_c_deg, yaw_r_deg=yaw_r_deg,
        )
        taps = compute_taps(
            room, prep.source, stand, c=c, grid=grid, origin="corner",
            z_face_4l=True, hadamard_n=n_had,
        )
        return taps, prep

    if not path_on or path_preset == "still":
        taps, prep = taps_at(sox, soz)
        ir_L, ir_R = combined_ir(
            taps,
            room,
            sr,
            c,
            wall_cache,
            ap_cache,
            delays,
            early_ms=early_ms,
            fdn_ms=fdn_ms,
            fdn_g=g,
            early_wet=early_wet,
            fdn_wet=fdn_wet,
            hadamard_n=n_had,
            surfaces=surfaces,
            diffusion_seed=seed,
            lambda_ref=lam,
            mic_left=prep.mic_left,
            mic_right=prep.mic_right,
        )
        yL = fft_convolve(dry, ir_L)
        yR = fft_convolve(dry, ir_R)
        keep = n_dry + int(sr * fdn_ms * 0.001)
        yL = yL[:keep]
        yR = yR[:keep]
        dry_pad = np.zeros(keep, dtype=np.float64)
        dry_pad[:n_dry] = dry
        mix_L = dry_gain * dry_pad + yL
        mix_R = dry_gain * dry_pad + yR
        mix_L, mix_R, peak, scale = peak_normalize(mix_L, mix_R)
        colour = colour_from_stereo(ir_L, ir_R, sr)
        info = {
            "mode": "still",
            "source": prep.source,
            "mic_centre": prep.mic_centre,
            "mcz": prep.mcz,
            "mcx": prep.mcx,
            "peak_before_norm": peak,
            "norm_scale": scale,
            "c": c,
            "sr": sr,
            "hadamard_n": n_had,
            "n_taps": len(taps),
            "colour": colour,
            "surfaces_assumed": True,
            "diffusion_seed": seed,
            "lambda_ref": lam,
        }
        if progress_cb:
            progress_cb(1.0)
        return mix_L, mix_R, info

    # Moving path — block/OLA (ASSUMED hop/frame like moving_room_demo)
    hop = max(1, int(round(DEFAULT_HOP_MS * 0.001 * sr)))
    frame = max(hop, int(round(DEFAULT_FRAME_MS * 0.001 * sr)))
    win = hann_window(frame)
    ir_max = int(sr * fdn_ms / 1000.0) + 1
    out_n = n_dry + ir_max + frame
    wet_L = np.zeros(out_n, dtype=np.float64)
    wet_R = np.zeros(out_n, dtype=np.float64)
    starts = list(range(0, n_dry, hop))
    last_prep = None
    for i, start in enumerate(starts):
        t_frac = (start + 0.5 * frame) / float(n_dry)
        sox_v, soz_v = path_sox_soz(
            t_frac,
            path_preset,
            cx=sox,
            cz=soz,
            rx=ellipse_rx,
            rz=ellipse_rz,
            rate=ellipse_rate,
            sox_still=sox,
            soz_still=soz,
        )
        taps, last_prep = taps_at(sox_v, soz_v)
        ir_L, ir_R = combined_ir(
            taps,
            room,
            sr,
            c,
            wall_cache,
            ap_cache,
            delays,
            early_ms=early_ms,
            fdn_ms=fdn_ms,
            fdn_g=g,
            early_wet=early_wet,
            fdn_wet=fdn_wet,
            hadamard_n=n_had,
            surfaces=surfaces,
            diffusion_seed=seed,
            lambda_ref=lam,
            mic_left=last_prep.mic_left,
            mic_right=last_prep.mic_right,
        )
        end = min(start + frame, n_dry)
        block = np.zeros(frame, dtype=np.float64)
        block[: end - start] = dry[start:end]
        block *= win
        yL = fft_convolve(block, ir_L)
        yR = fft_convolve(block, ir_R)
        wet_L[start : start + len(yL)] += yL
        wet_R[start : start + len(yR)] += yR
        if progress_cb and (i % 10 == 0 or i == len(starts) - 1):
            progress_cb((i + 1) / len(starts))

    keep = n_dry + int(sr * fdn_ms * 0.001)
    wet_L = wet_L[:keep]
    wet_R = wet_R[:keep]
    dry_pad = np.zeros(keep, dtype=np.float64)
    dry_pad[:n_dry] = dry
    ola_comp = 2.0 / 3.0  # ASSUMED Hann OLA coherent gain compensation
    colour = colour_from_stereo(wet_L, wet_R, sr)
    mix_L = dry_gain * dry_pad + ola_comp * wet_L
    mix_R = dry_gain * dry_pad + ola_comp * wet_R
    mix_L, mix_R, peak, scale = peak_normalize(mix_L, mix_R)
    info = {
        "mode": path_preset,
        "source": last_prep.source if last_prep else None,
        "mic_centre": last_prep.mic_centre if last_prep else None,
        "mcz": last_prep.mcz if last_prep else None,
        "peak_before_norm": peak,
        "norm_scale": scale,
        "c": c,
        "sr": sr,
        "hops": len(starts),
        "hadamard_n": n_had,
        "colour": colour,
        "surfaces_assumed": True,
        "diffusion_seed": seed,
        "lambda_ref": lam,
    }
    return mix_L, mix_R, info


def default_out_path() -> Path:
    return Path(__file__).resolve().parent / "renders" / "out.wav"
