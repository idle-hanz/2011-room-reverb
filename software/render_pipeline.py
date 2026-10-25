#!/usr/bin/env python3
"""
Render pipeline for the 2011 Room Reverb tweak app.

Wraps the copied early-field / FDN engine. Unscaled ±1 FDN + Prepare VERIFIED
algebra. Optional ASSUMED Surfaces A–F absorb×EQ + seeded path-length jitter
(see surface_colour.py) — does NOT claim Structure-locked A–F EQ dictionary.
"""

from __future__ import annotations

import atexit
import contextvars as _cv
import copy
import functools as _ft
import inspect as _insp
import math
import re
import shutil
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np

# Engine lives beside this file under software/engine/
_SOFT = Path(__file__).resolve().parent
_ENGINE = _SOFT / "engine"
if str(_SOFT) not in sys.path:
    sys.path.insert(0, str(_SOFT))
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

# SL2. None is Flat (2011), the old render path.
_SURF_CTX: "_cv.ContextVar[Optional[dict]]" = _cv.ContextVar("rr_surf_ctx", default=None)
_SUB_HP: "_cv.ContextVar[Optional[tuple]]" = _cv.ContextVar("rr_sub_hp", default=None)

from poly_room import compute_poly_taps, normalize_shape, poly_on  # noqa: E402
from early_field import (  # noqa: E402
    DEFAULT_HADAMARD_N,
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    MicStand,
    allpass_ir_for_stages,
    beaming_lp_hz,
    cascade_biquads,
    biquad_process,
    compute_taps,
    direct_line_index,
    gradient_hp_hz,
    grid_bias_for_hadamard_n,
    apply_air_absorption,
    air_abs_cutoff_hz,
    air_abs_wet_from_humidity,
    iso_shelf_pair,
    normalize_biquad,
    one_pole_g_from_fc,
    normalize_hadamard_n,
    peaking_stages_for_tap,
    precompute_wall_peaking_coeffs,
    prepare_direct_field,
    direct_field_from_metres,
    direct_field_from_params,
    rbj_highpass,
    butterworth_highpass,
    rbj_lowpass,
    harmonic_stages,
    harmonic_pack,
)
from fdn import (  # noqa: E402
    FDN,
    FDN32,
    build_inject_from_taps,
    propose_fdn_delays_samples,
    fdn_delays_from_taps,
    _tap_distance,
    dffs_from_taps,
    cap_dffs,
    diffusion_scale_from_room,
    dff_after_master,
    DIFFUSION_MASTER_LIVE,
    loop_level_trim_db,
    loop_level_trim_lin,
    mixer_lcr_fold,
    apply_capsule_weights,
    capsule_speaker_weights,
    automatic_wet_level,
    automatic_wet_gain,
    ir_rms_makeup_from_inject,
    direct_listen_gain,
    live_peaking_banks,
    mic_g_from_taps,
    structure_gain_for_rt60,
    MAX_DELAY_MS,
)

from mic_colour.colour import MicColour  # noqa: E402
from mic_colour.live_bank import build_live_bank  # noqa: E402
from prox import (  # noqa: E402
    apply_prox_shelf,
    capsule_gains,
    early_scale,
    pack_prox,
    prox_is_bypass,
    scales_from_taps,
)


def _mix_pair(desk, gl, gc, gr, pl, pc, pr, hl, hc, hr):
    """(weights, makeup weights or None, section-7 or None).

    An idle desk, including a missing one, stays on capsule_speaker_weights
    and the hardcoded 477 makeup expression.
    """
    from desk_matrix import desk_active, fold_for

    if not desk or not desk_active(desk):
        return capsule_speaker_weights(gl, gc, gr, pl, pc, pr, hl, hc, hr), None, None
    return fold_for(
        desk,
        mic_gain_l=gl, mic_gain_c=gc, mic_gain_r=gr,
        mic_pan_l=pl, mic_pan_c=pc, mic_pan_r=pr,
        mic_phase_l=hl, mic_phase_c=hc, mic_phase_r=hr,
    )


def _place_stand(stand, desk):
    """Heights, then an active desk. An idle body keeps the from_prepare XZ."""
    if stand is None or not desk:
        return stand
    from early_field import apply_capsule_heights
    from desk_matrix import desk_active, place_stand

    apply_capsule_heights(stand, desk)
    if not desk_active(desk):
        return stand
    return place_stand(stand, desk)


_MIC_POS_PREFIXES = ("mic_x_", "mic_y_", "mic_z_", "mic_pos_")


def _desk_at_stand(desk):
    """Copy with room-spot positions removed. Yaw stays. None stays None."""
    if not desk:
        return desk
    out = dict(desk)
    for key in list(out):
        if isinstance(key, str) and key.startswith(_MIC_POS_PREFIXES):
            del out[key]
    return out

from surface_colour import (  # noqa: E402
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    apply_surface_to_buffer,
    jittered_distance,
    mirror_jitter_overrides,
    mirror_x_partner_index,
    card_structure_dif,
    parse_lambda_ref,
    parse_surfaces,
    parse_solo,
    parse_mute,
    image_in_early,
    solo_mute_gates,
    surfaces_hit_by_n,
    surfaces_payload,
    fit_line_cascade,
    _absorb_to_db,
    rbj_peaking,
    surface_filter_stages,
    ABSORB_BAND_HZ,
    SURF_K_MAX,
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


def load_wav_stereo(path: str) -> Tuple[np.ndarray, Optional[np.ndarray], int, int]:
    """Left, right or None, sample rate, channel count.

    Mono stays one channel. More than two channels keeps the first two.
    One source still uses load_wav_mono.
    """
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    pcm = _pcm_bytes_to_float(raw, sw)
    if nch <= 1:
        return pcm, None, sr, int(nch)
    if nch == 2:
        return np.ascontiguousarray(pcm[0::2]), np.ascontiguousarray(pcm[1::2]), sr, 2
    shaped = pcm.reshape(-1, nch)
    return shaped[:, 0].copy(), shaped[:, 1].copy(), sr, int(nch)


def source_balance_gains(bal: float) -> Tuple[float, float]:
    """ASSUMED. Centre 0 is (1, 1). Hard A (−1) is (1, 0). Hard B (+1) is (0, 1)."""
    b = max(-1.0, min(1.0, float(bal)))
    if b <= 0.0:
        return 1.0, 1.0 + b
    return 1.0 - b, 1.0


def mirror_source_b(W: float, sx: float, sy: float, sz: float) -> Tuple[float, float, float]:
    """ASSUMED width centerline. B = (W − sx, sy, sz)."""
    return float(W) - float(sx), float(sy), float(sz)


def two_source_excitation(
    left: np.ndarray,
    right: np.ndarray,
    bal: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Scaled left, scaled right, and 0.5·(those) for Host dry.

    Each source's own FDN is driven by half of that scaled channel.
    The half keeps a hard balance at the old single-tank level.
    """
    ga, gb = source_balance_gains(bal)
    a = np.asarray(left, dtype=np.float64) * ga
    b = np.asarray(right, dtype=np.float64) * gb
    n = max(int(a.size), int(b.size))
    if int(a.size) < n:
        a = np.pad(a, (0, n - int(a.size)))
    if int(b.size) < n:
        b = np.pad(b, (0, n - int(b.size)))
    return a, b, 0.5 * (a + b), ga, gb


def write_wav_stereo(path: str, L: np.ndarray, R: np.ndarray, sr: int) -> dict:
    """24-bit PCM (format 1, 3 bytes/sample, block align 6). Round to nearest, no dither.

    Scale is 2^23 so load_wav_stereo inverts it. ±1 clips to ±(2^23 − 1) here only.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = len(L)
    interleaved = np.empty(n * 2, dtype=np.float64)
    interleaved[0::2] = L
    interleaved[1::2] = R
    peak = float(np.max(np.abs(interleaved))) if n else 0.0
    clipped = np.clip(interleaved, -1.0, 1.0)
    q = np.rint(clipped * 8388608.0)
    q = np.clip(q, -8388607, 8388607).astype("<i4")
    packed = q.view(np.uint8).reshape(-1, 4)[:, :3].reshape(-1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(sr)
        w.writeframes(packed.tobytes())
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


FDN_MS_CAP = 12500.0


def planned_fdn_ms(early_ms: float, ir_length_ms: float, t60_s: float) -> float:
    """Render FDN length. ir_length_ms is the minimum. Cap 12.5 s.

    1.5 × T60 puts the cut about 90 dB down from the tail start.
    """
    t60 = max(0.0, float(t60_s or 0.0))
    raw = max(float(early_ms), float(ir_length_ms), float(early_ms) + 1500.0 * t60)
    return min(FDN_MS_CAP, raw)


def render_t60_s(delays, g_open: float, n_had: int, sr: int, decay_s: float, decay_lock: bool) -> float:
    """decay_s when the lock is on, otherwise the 2011-law readout from the open loop."""
    if decay_lock and float(decay_s) > 0.05:
        return float(decay_s)
    if not delays:
        return 0.0
    mean_t = (float(sum(delays)) / float(len(delays))) / float(sr)
    loop = float(g_open) * math.sqrt(float(n_had))
    if 0.0 < loop < 0.999999 and mean_t > 1e-9:
        return mean_t * (math.log(0.001) / math.log(loop))
    return 0.0


def _raised_cosine_down(x: np.ndarray, nfade: int) -> np.ndarray:
    nfade = int(nfade)
    if nfade < 2 or x.size == 0:
        return x
    nfade = min(nfade, int(x.size))
    t = np.linspace(0.0, 1.0, nfade, dtype=np.float64)
    w = 0.5 * (1.0 + np.cos(math.pi * t))
    y = np.array(x, dtype=np.float64, copy=True)
    y[-nfade:] *= w
    return y


def fade_render_tail(mix_l, mix_r, wet_l, wet_r, dry_pad, dry_gain: float, n_dry: int, sr: int):
    """50 ms raised-cosine on the FDN tail. The whole output, when the dry ends first."""
    nfade = int(round(float(sr) * 0.050))
    if nfade < 2:
        return mix_l, mix_r
    if int(n_dry) <= len(mix_l) - nfade:
        return _raised_cosine_down(mix_l, nfade), _raised_cosine_down(mix_r, nfade)
    wet_l = _raised_cosine_down(wet_l, nfade)
    wet_r = _raised_cosine_down(wet_r, nfade)
    return float(dry_gain) * dry_pad + wet_l, float(dry_gain) * dry_pad + wet_r


def ls_exp(x: float) -> float:
    """Freestanding exp from live_stereo.c, so soft_limit matches the wasm."""
    ln2 = 0.693147180559945309417
    if x > 40.0:
        x = 40.0
    if x < -40.0:
        return 0.0
    nd = x / ln2
    n = int(nd + (-0.5 if nd < 0.0 else 0.5))
    f = x - float(n) * ln2
    f2 = f * f
    p = 1.0 + f + f2 * (0.5 + f * (1.0 / 6.0 + f * (1.0 / 24.0 + f * (1.0 / 120.0
        + f * (1.0 / 720.0 + f * (1.0 / 5040.0 + f * (1.0 / 40320.0
        + f * (1.0 / 362880.0 + f / 3628800.0))))))))
    s = 1.0
    if n >= 0:
        for _ in range(n):
            s *= 2.0
    else:
        for _ in range(-n):
            s *= 0.5
    return s * p


def soft_limit(x: float) -> float:
    """Play's output knee, in float64. Identity through ±0.95, then the wasm curve."""
    a = -x if x < 0.0 else x
    if a <= 0.95:
        return float(x)
    u = (a - 0.95) * 20.0
    if u > 16.0:
        return -0.999 if x < 0.0 else 0.999
    e = ls_exp(-2.0 * u)
    th = (1.0 - e) / (1.0 + e)
    return (-1.0 if x < 0.0 else 1.0) * (0.95 + 0.05 * th)


def limiter_message(db: float, n: int) -> str:
    if int(n) <= 0:
        return ""
    return f"Limiter: peak reduced by {float(db):.1f} dB ({int(n)} samples)"


def apply_soft_limit(L: np.ndarray, R: np.ndarray):
    """Per-sample soft_limit. Whole-file scaling is gone. scale is always 1.

    Under the knee the same arrays come back, so a quiet render is unchanged.
    """
    peak = 0.0
    if len(L):
        peak = float(np.max(np.abs(L)))
    if len(R):
        peak = max(peak, float(np.max(np.abs(R))))
    if peak <= 0.95:
        return L, R, peak, 1.0, 0.0, 0
    out_l = np.array(L, dtype=np.float64, copy=True)
    out_r = np.array(R, dtype=np.float64, copy=True)
    n = 0
    top_in = 0.0
    top_out = 1.0
    for arr in (out_l, out_r):
        hot = np.flatnonzero(np.abs(arr) > 0.95)
        n += int(hot.size)
        for i in hot:
            x = float(arr[i])
            y = soft_limit(x)
            arr[i] = y
            a = -x if x < 0.0 else x
            if a > top_in:
                top_in = a
                top_out = -y if y < 0.0 else y
    db = 20.0 * math.log10(top_in / top_out) if top_out > 0.0 and top_in > top_out else 0.0
    return out_l, out_r, peak, 1.0, db, n


def clip_guard(L: np.ndarray, R: np.ndarray, peak_ceil: float = 0.9):
    """Scale down only if over peak_ceil. Never boost (would cancel mix faders)."""
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-12)
    if peak > float(peak_ceil):
        s = float(peak_ceil) / peak
        return L * s, R * s, peak, s
    return L, R, peak, 1.0


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


def _bus_theta(tap, channel: str) -> float:
    ch = str(channel).strip().lower()
    if ch == "l":
        return float(tap.theta_l)
    if ch == "r":
        return float(tap.theta_r)
    return float(getattr(tap, "theta_c", 0.0))


def _colour_apply(colour, buf, theta: float, bus: str):
    if colour is None:
        return buf
    return colour.apply(buf, theta, bus)


def render_early_ir(
    taps, room, sr, c, length_ms, depth_per_axis, humidity, wall_cache, ap_cache,
    surfaces=None,
    diffusion_seed=DEFAULT_DIFFUSION_SEED,
    lambda_ref=DEFAULT_LAMBDA_REF_M,
    mic_left=None,
    mic_right=None,
    capsule_mm=17.0,
    air_lp=0.25,
    air_shelf=1.0,
    colour=None,
    early_toys=None,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
    src_images=None,
    mirror_x: bool = False,
    surfaces_solo=None,
    surfaces_mute=None,
    g_l: float = 0.0,
    g_r: float = 0.0,
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
    cap_mm = float(capsule_mm or 17.0)
    if early_toys is None:
        toys = True if colour is None else bool(colour.early_toys)
    else:
        toys = bool(early_toys)
    hp_grad = rbj_highpass(sr, gradient_hp_hz(cap_mm)) if toys else None
    beam_cache = {}
    _apply_src = None
    if src_images is not None:
        from source_radiation import apply_coef as _apply_src
    # D-MIX-J. Hash each image by its x-mirror partner so a mirrored scene
    # (source x → W−x, mics L↔R, cards A↔C) draws the mirrored jitter.
    # nx > 0 keeps today's key. nx < 0 uses the partner tap's index, with the
    # side wall and the capsule swapped. nx == 0 is its own partner, so both
    # capsules share the left capsule's draw. Do not also remap on mirror_x:
    # source B at the mirrored point already carries these orders.
    orders = [tuple(int(v) for v in t.n) for t in taps]
    partner = mirror_x_partner_index(orders)
    solo_l = parse_solo(surfaces_solo)
    mute_s = parse_mute(surfaces_mute)
    for ti, t in enumerate(taps):
        # D11 / D16: a silenced image is absent. D15: solo drops n=(0,0,0).
        if not image_in_early(t.n, solo_l, mute_s):
            continue
        d_l = float(t.distance_l)
        d_r = float(t.distance_r)
        # ASSUMED surface hit from geometric n (not Structure A–F OCR masks)
        hit = surfaces_hit_by_n(t.n) if surfaces else []
        if surfaces and hit:
            img = t.position
            # Partner's own tap index, not the slot, so the key matches t.index.
            pref = int(taps[partner[ti]].index)
            h_l = mirror_jitter_overrides(orders[ti], "L", pref)
            h_r = mirror_jitter_overrides(orders[ti], "R", pref)
            if mic_left is not None:
                d_l = jittered_distance(
                    d_l, t.n, t.index, "L", img, mic_left, surfaces,
                    seed=seed, lambda_ref=lam, **h_l,
                )
            if mic_right is not None:
                d_r = jittered_distance(
                    d_r, t.n, t.index, "R", img, mic_right, surfaces,
                    seed=seed, lambda_ref=lam, **h_r,
                )
        dl = d_l / c * sr
        dr = d_r / c * sr
        peaks = peaking_stages_for_tap(
            t, room, sr, c, depth_per_axis, wall_cache=wall_cache
        )
        # 1-pole + high-shelf applied after peaking below
        ap_stages = int(t.allpass_stages)  # geometric order; not diffusion
        bl = np.zeros(n_samp, dtype=np.float64)
        br = np.zeros(n_samp, dtype=np.float64)
        press_l = float(getattr(t, "press_l", 0.0))
        press_r = float(getattr(t, "press_r", 0.0))
        grad_l = float(getattr(t, "grad_l", 0.0))
        grad_r = float(getattr(t, "grad_r", 0.0))
        if press_l == 0.0 and grad_l == 0.0:
            press_l = float(t.level_l)
        if press_r == 0.0 and grad_r == 0.0:
            press_r = float(t.level_r)
        # Early-only floor. Unjittered geometric d. Scale 1 is not multiplied.
        sc_l = early_scale(float(t.distance_l))
        sc_r = early_scale(float(t.distance_r))
        if sc_l != 1.0:
            press_l *= sc_l
            grad_l *= sc_l
        if sc_r != 1.0:
            press_r *= sc_r
            grad_r *= sc_r
        _apply_ir_at(bl, dl, press_l, ap_stages, ap_cache)
        _apply_ir_at(br, dr, press_r, ap_stages, ap_cache)
        if abs(grad_l) > 1e-15:
            if toys:
                gl = np.zeros(n_samp, dtype=np.float64)
                _apply_ir_at(gl, dl, grad_l, ap_stages, ap_cache)
                gl = biquad_process(gl, hp_grad)
                bl += gl
            else:
                _apply_ir_at(bl, dl, grad_l, ap_stages, ap_cache)
        if abs(grad_r) > 1e-15:
            if toys:
                gr = np.zeros(n_samp, dtype=np.float64)
                _apply_ir_at(gr, dr, grad_r, ap_stages, ap_cache)
                gr = biquad_process(gr, hp_grad)
                br += gr
            else:
                _apply_ir_at(br, dr, grad_r, ap_stages, ap_cache)
        if _apply_src is not None and ti < len(src_images):
            bl = _apply_src(bl, src_images[ti])
            br = _apply_src(br, src_images[ti])
        if toys:
            f_l = beaming_lp_hz(float(t.theta_l), cap_mm)
            f_r = beaming_lp_hz(float(t.theta_r), cap_mm)
            if f_l < 19000.0:
                key = int(round(f_l))
                if key not in beam_cache:
                    beam_cache[key] = rbj_lowpass(sr, float(key))
                bl = biquad_process(bl, beam_cache[key])
            if f_r < 19000.0:
                key = int(round(f_r))
                if key not in beam_cache:
                    beam_cache[key] = rbj_lowpass(sr, float(key))
                br = biquad_process(br, beam_cache[key])
        if peaks:
            bl = cascade_biquads(bl, peaks)
            br = cascade_biquads(br, peaks)
        bl = apply_air_absorption(
            bl, d_l, sr, humidity, air_lp=air_lp, air_shelf=air_shelf,
            air_climate=air_climate, air_iso=air_iso,
        )
        br = apply_air_absorption(
            br, d_r, sr, humidity, air_lp=air_lp, air_shelf=air_shelf,
            air_climate=air_climate, air_iso=air_iso,
        )
        # ASSUMED absorb×EQ cascade for hit surfaces
        if surfaces and hit:
            bl = apply_surface_to_buffer(bl, surfaces, hit, float(sr))
            br = apply_surface_to_buffer(br, surfaces, hit, float(sr))
        if g_l != 0.0:
            bl = apply_prox_shelf(bl, g_l, sr)
        if g_r != 0.0:
            br = apply_prox_shelf(br, g_r, sr)
        bl = _colour_apply(colour, bl, float(t.theta_l), "l")
        br = _colour_apply(colour, br, float(t.theta_r), "r")
        Lch += bl
        Rch += br
    return Lch, Rch


def cards_are_flat(surfaces) -> bool:
    """Uniform absorb and zero EQ dB on every card. That is the SURF bypass.

    None means the caller has not parsed cards yet, so this does not force
    Smooth off. An empty dict has no relative colour. structure_dif is not
    part of the test: it still feeds Dffs.
    """
    if surfaces is None:
        return False
    if not isinstance(surfaces, dict) or not surfaces:
        return True
    for card in surfaces.values():
        if not isinstance(card, dict):
            continue
        absorb = card.get("absorb") or []
        if len(absorb) >= 2:
            mean = sum(float(x) for x in absorb) / float(len(absorb))
            for x in absorb:
                if abs(float(x) - mean) > 1e-6:
                    return False
        eq = card.get("eq") or {}
        if isinstance(eq, dict):
            for key in ("low_shelf_db", "high_shelf_db", "peak_db"):
                try:
                    db = float(eq.get(key) or 0.0)
                except (TypeError, ValueError):
                    db = 0.0
                if abs(db) > 1e-6:
                    return False
    return True


def _posted_wet(p, key: str, default: float) -> float:
    if not isinstance(p, dict) or key not in p or p.get(key) is None:
        return float(default)
    try:
        return float(p.get(key))
    except (TypeError, ValueError):
        return float(default)


def smooth_active(p, surfaces=None) -> bool:
    """Smooth defaults ON. A missing key is on. Explicit false is off.

    Parity, flat cards, mirror/null, and a direct-only body force it off
    whatever the switch says. The cap does not scale the decay-lock exponent.
    """
    if not isinstance(p, dict):
        p = {}
    if p.get("reaktor_parity"):
        return False
    sur = surfaces
    if sur is None:
        sur = p.get("surfaces")
    if cards_are_flat(sur):
        return False
    if p.get("mirror_null") or p.get("null_mode"):
        return False
    # MS direct-only checks post both wets at 0. The cap is in the diffusers.
    if "fdn_wet" in p and "early_wet" in p:
        if _posted_wet(p, "fdn_wet", 1.0) <= 1e-12 and _posted_wet(p, "early_wet", 1.0) <= 1e-12:
            return False
    if "smooth" in p and p.get("smooth") is not None:
        return bool(p.get("smooth"))
    return True


# Un-forced 2026-10-23. Shared-off knob 100 median 1.876 ms, under 2.40 ms.
# The 2026-10-10 miss was 2.718 ms on an older wasm. The curve below stays.
# Knob default is 0, so a default body still skips the allpass.
# Do not retune the tank.
MOVEMENT_FORCED_OFF = False


def movement_peak_ms(p, surfaces=None) -> float:
    """UI percent 0..100 to Frenette peak depth in milliseconds.

    0 is off (the path is not entered). 0–50 ramps 0 to 0.10 ms.
    50–100 ramps 0.10 to 0.15 ms. A missing key is off.
    Parity, flat cards, mirror/null, and a direct-only body force 0,
    the same cases as smooth_active. Unlike Smooth, missing is not on.

    MOVEMENT_FORCED_OFF returns 0 before that curve. The flag is false, so
    Play, Render and the blob follow the knob. A missing key and 0 stay off.
    """
    if MOVEMENT_FORCED_OFF:
        return 0.0
    if not isinstance(p, dict):
        return 0.0
    if p.get("reaktor_parity"):
        return 0.0
    sur = surfaces
    if sur is None:
        sur = p.get("surfaces")
    if cards_are_flat(sur):
        return 0.0
    if p.get("mirror_null") or p.get("null_mode"):
        return 0.0
    if "fdn_wet" in p and "early_wet" in p:
        if _posted_wet(p, "fdn_wet", 1.0) <= 1e-12 and _posted_wet(p, "early_wet", 1.0) <= 1e-12:
            return 0.0
    if "movement" not in p or p.get("movement") is None:
        return 0.0
    try:
        pct = float(p.get("movement"))
    except (TypeError, ValueError):
        return 0.0
    if pct != pct or pct <= 0.0:
        return 0.0
    if pct > 100.0:
        pct = 100.0
    if pct >= 100.0:
        return 0.15
    if pct <= 50.0:
        return 0.10 * (pct / 50.0)
    return 0.10 + 0.05 * ((pct - 50.0) / 50.0)


def tap_dff(n, surfaces, master: float = DIFFUSION_MASTER_LIVE) -> float:
    """Dff = Clip(sum(hit Dif) × Diffusion Master). 202 × MDif; 485 Master.

    Geometric hits (both walls when |n|≥2). Not A–F bit tables.
    Master live −0.5 (394/485 Max) makes Dff ≤ 0 like 463.
    """
    if not surfaces:
        return 0.0
    acc = 0.0
    for letter in surfaces_hit_by_n(n):
        card = surfaces.get(letter) if isinstance(surfaces, dict) else None
        if not isinstance(card, dict):
            continue
        acc += card_structure_dif(card)
    return dff_after_master(acc, master)


def tap_reflect_gain(n, surfaces) -> float:
    """ASSUMED: serial |R|=√(1−ᾱ) for geometric hits so walls colour the FDN wet.

    ᾱ is the mean of that card's absorb bands. Direct (no hits) stays 1.
    Not Structure A–F masks.
    """
    if not surfaces:
        return 1.0
    g = 1.0
    for letter in surfaces_hit_by_n(n):
        card = surfaces.get(letter) if isinstance(surfaces, dict) else None
        if not isinstance(card, dict):
            continue
        # Muted / not-soloed faces are full absorb. The 0.95 clamp would still leak.
        if card.get("muted"):
            return 0.0
        absorb = card.get("absorb") or []
        if not absorb:
            continue
        try:
            acc = sum(float(x) for x in absorb) / float(len(absorb))
        except (TypeError, ValueError):
            continue
        acc = max(0.0, min(0.95, acc))
        g *= math.sqrt(1.0 - acc)
    return g


def _surf_rel_stages(surfaces, letters, sr):
    """Absorb peaking relative to the card mean (mean already in tap_reflect_gain) + EQ.

    Copied from the S5 prototype. Muted faces are skipped. Callers that want the
    un-gated tail pass the un-gated cards, the same dict tap_reflect_gain uses.
    """
    out = []
    sr = float(sr)
    for L in letters:
        s = surfaces.get(L) if isinstance(surfaces, dict) else None
        if not isinstance(s, dict) or s.get("muted"):
            continue
        absorb = s.get("absorb") or []
        if absorb:
            m = max(0.0, min(0.95, sum(float(x) for x in absorb) / float(len(absorb))))
            hz_list = s.get("absorb_hz") or list(ABSORB_BAND_HZ)
            for j, hz in enumerate(hz_list):
                if j >= len(absorb):
                    break
                f0 = float(hz)
                if f0 <= 0.0 or f0 >= sr * 0.49:
                    continue
                gdb = _absorb_to_db(float(absorb[j])) - _absorb_to_db(m)
                if abs(gdb) < 0.01:
                    continue
                out.append(rbj_peaking(sr, f0, 0.9, gdb))
        flat = dict(s)
        flat["absorb"] = []
        out.extend(surface_filter_stages({L: flat}, [L], sr))
    return out


def _scale_inject_reflect(inj, taps, surfaces, sr=None, reaktor_parity=False) -> None:
    """FDN inject: broadband |R|, then Play's fitted per-line cascade.

    fit_line_cascade is the same fit, the same K, and the same f32 rounding
    that _play_surf_cascade packs. Early reflections stay on the exact face chain.
    """
    if inj is None or taps is None or not surfaces:
        return
    n_t = len(taps)
    n_lines = int(inj.shape[1]) if hasattr(inj, "shape") else 0
    if n_t <= 0 or n_lines <= 0:
        return
    colour = bool(sr) and not reaktor_parity
    for i in range(n_lines):
        g = tap_reflect_gain(taps[i % n_t].n, surfaces)
        inj[:, i] *= g
        if not colour or g == 0.0:
            continue
        stages = _surf_rel_stages(surfaces, surfaces_hit_by_n(taps[i % n_t].n), float(sr))
        coef = fit_line_cascade(stages, float(sr)).get("coef") or []
        if not coef:
            continue
        rows = tuple((b0, b1, b2, 1.0, a1, a2) for b0, b1, b2, a1, a2 in coef)
        inj[:, i] = cascade_biquads(inj[:, i], rows)


def _play_surf_cascade(surfaces, taps, taps_b, sr, n, parity):
    """SURF v1 tail, or None when every line is a bypass (or parity is on).

    The tail is [version=1, K_max] then per bank A, B and per line: k_i and
    K_max × 5 normalised coefficients. Image and diffuse lanes share k_i.
    """
    report = {
        "worst_db": 0.0,
        "worst_line": None,
        "misses": [],
        "bypass": True,
        "parity": bool(parity),
    }
    if parity or not surfaces:
        return None, report
    # The loader always reads 2 * 32 lines. Hadamard 8/16 still occupies the
    # first hn slots; the rest stay k=0 so a short room is not rejected.
    n_fit = int(n) if n else 0
    if n_fit < 0:
        n_fit = 0
    if n_fit > 32:
        n_fit = 32
    banks = (("A", taps), ("B", taps_b if taps_b is not None else []))
    packed = []
    kmax = 0
    any_k = False
    for name, bank in banks:
        n_t = len(bank) if bank else 0
        rows = []
        for i in range(32):
            if n_t <= 0 or i >= n_fit:
                rows.append((0, []))
                continue
            letters = surfaces_hit_by_n(bank[i % n_t].n)
            stages = _surf_rel_stages(surfaces, letters, sr)
            fit = fit_line_cascade(stages, sr)
            rows.append((int(fit["k"]), list(fit["coef"])))
            db = float(fit["residual_db"])
            line = {
                "bank": name,
                "i": i,
                "hits": list(letters),
                "db": round(db, 4),
                "k": int(fit["k"]),
            }
            if db > report["worst_db"]:
                report["worst_db"] = db
                report["worst_line"] = line
            if fit.get("miss"):
                report["misses"].append(line)
            if fit["k"] > kmax:
                kmax = int(fit["k"])
            if fit["k"] > 0:
                any_k = True
        packed.append(rows)
    if not any_k or kmax < 1:
        report["bypass"] = True
        return None, report
    if kmax > SURF_K_MAX:
        kmax = SURF_K_MAX
    tail = [1.0, float(kmax)]
    for rows in packed:
        for k, coef in rows:
            k = max(0, min(int(k), kmax))
            tail.append(float(k))
            for s in range(kmax):
                if s < k and s < len(coef):
                    tail.extend(float(x) for x in coef[s])
                else:
                    tail.extend((0.0, 0.0, 0.0, 0.0, 0.0))
    report["bypass"] = False
    report["k_max"] = kmax
    expect = 2 + 64 * (1 + 5 * kmax)
    if len(tail) != expect:
        raise RuntimeError(f"SURF tail length {len(tail)} != {expect}")
    return tail, report


def render_direct_ir(
    taps, room, sr, c, length_ms, humidity, wall_cache, ap_cache,
    surfaces=None,
    diffusion_seed=DEFAULT_DIFFUSION_SEED,
    lambda_ref=DEFAULT_LAMBDA_REF_M,
    mic_left=None,
    mic_right=None,
    capsule_mm=17.0,
    air_lp=0.25,
    air_shelf=1.0,
    colour=None,
    early_toys=None,
):
    """Feedforward first arrival only (n=0,0,0). Not through Hadamard."""
    direct = [t for t in (taps or []) if tuple(getattr(t, "n", ())) == (0, 0, 0)]
    if not direct:
        z = np.zeros(1, dtype=np.float64)
        return z, z
    return render_early_ir(
        direct, room, sr, c, length_ms, DEFAULT_DEPTH, humidity, wall_cache, ap_cache,
        surfaces=surfaces,
        diffusion_seed=diffusion_seed,
        lambda_ref=lambda_ref,
        mic_left=mic_left,
        mic_right=mic_right,
        capsule_mm=capsule_mm,
        air_lp=0.0,
        air_shelf=0.0,
        colour=colour,
        early_toys=early_toys,
        air_iso=False,
    )


def _surf_bus(taps, n_lines, line_t60):
    """Per-bus surf dict for the FDN, or None (Flat 2011, or decay lock off).

    Hits are the faces each line's image crosses. Makeup and the 1/r inject
    are computed outside this dict.
    """
    ctx = _SURF_CTX.get()
    if ctx is None or float(line_t60) <= 0.05:
        return None
    from surface_colour import surfaces_hit_by_n
    n_t = len(taps) if taps is not None else 0
    if n_t:
        hits = [surfaces_hit_by_n(taps[i % n_t].n) for i in range(int(n_lines))]
    else:
        hits = [[] for _ in range(int(n_lines))]
    return dict(ctx, hits=hits)


def sub_hp_coeffs(sr: float) -> tuple:
    """Causal 15 Hz Butterworth, five DF1 floats, float32-rounded.

    The room blob is float32. Render uses these same values so Play and
    Render share one set of coefficients.
    """
    return tuple(float(np.float32(v)) for v in butterworth_highpass(float(sr), 15.0))


def _df1_columns(exc: np.ndarray, coeffs) -> np.ndarray:
    """One cold DF1 biquad per column. Same coefficients on every column."""
    b0, b1, b2, a1, a2 = (float(v) for v in coeffs)
    x = np.asarray(exc, dtype=np.float64)
    y = np.empty_like(x)
    z1 = np.zeros(x.shape[1], dtype=np.float64)
    z2 = np.zeros(x.shape[1], dtype=np.float64)
    for t in range(x.shape[0]):
        xt = x[t]
        yi = b0 * xt + z1
        z1 = b1 * xt - a1 * yi + z2
        z2 = b2 * xt - a2 * yi
        y[t] = yi
    return y


def _bus_place(desk) -> dict:
    """Each strip is array or room. A missing key stays on the array."""
    src = desk or {}
    out = {}
    for ch in ("l", "c", "r"):
        raw = str(src.get("place_" + ch) or "array").strip().lower()
        out[ch] = "room" if raw == "room" else "array"
    return out


def _apply_chain(buses, det, spec) -> None:
    """Preamp, then the compressor, using bloom_dsp.

    A spec with only one stage is one apply_fdn_buses call, so a master
    Room Crush or a master Neve matches today's single call.
    """
    import bloom_dsp as _b

    pre_on = (spec.get("pre") or "off") != "off"
    comp_on = float(spec.get("amount_db") or 0.0) > 0.0
    if not pre_on and not comp_on:
        return
    if pre_on and comp_on:
        pre_spec = dict(spec)
        pre_spec["amount_db"] = 0.0
        _b.apply_fdn_buses(buses, det, pre_spec)
        comp_spec = dict(spec)
        comp_spec["pre"] = "off"
        _b.apply_fdn_buses(buses, det, comp_spec)
        return
    _b.apply_fdn_buses(buses, det, spec)


def _route_buses(buses, det, array_spec, room_spec, place) -> None:
    """Array strips, then room strips. The other strips are left alone."""
    where = place or {"l": "array", "c": "array", "r": "array"}
    n = 0
    for ch in ("l", "c", "r"):
        n = max(n, int(np.asarray(buses[ch]).shape[0]))

    def run(spec, kind):
        if spec is None:
            return
        keys = tuple(ch for ch in ("l", "c", "r") if where.get(ch, "array") == kind)
        if not keys:
            return
        work = {}
        for ch in ("l", "c", "r"):
            if ch in keys:
                y = np.asarray(buses[ch], dtype=np.float64)
                if int(y.shape[0]) < n:
                    z = np.zeros(n, dtype=np.float64)
                    z[: int(y.shape[0])] = y
                    y = z
                work[ch] = y
            else:
                work[ch] = np.zeros(n, dtype=np.float64)
        _apply_chain(work, det, spec)
        for ch in keys:
            buses[ch] = work[ch]

    run(array_spec, "array")
    run(room_spec, "room")


def render_fdn_ir(
    taps, room, sr, c, length_ms, g, depth_per_axis, delays, n_lines=32,
    surfaces=None,
    humidity=0.0,
    air_lp=0.25,
    air_shelf=1.0,
    diffusion_master=DIFFUSION_MASTER_LIVE,
    mic_response_hz=10000.0,
    apply_mic=False,
    weights=None,
    colour=None,
    line_t60=0.0,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
    src_diffuse=None,
    reaktor_parity: bool = False,
    smooth: bool = False,
    movement_ms: float = 0.0,
    drive=None,
    bloom_spec=None,
    bloom_det=None,
    array_spec=None,
    room_spec=None,
    bus_place=None,
    tail_sos=None,
):
    """2011 wet: L / C / R Diffuser Delay loops + Hadamard feedback + Mixer fold.

    ``delays`` unused (times from taps; cap 1000 ms). Mixer 477: L+0.5·C, R+0.5·C.
    Dffs allpass from Dis × Dff × (1/Diffusion) (462–465).
    Injects all 32 lines including n=(0,0,0). Mix Direct is a separate
    feedforward first arrival, not a hole in this loop.
    ``apply_mic`` False matches Play live (off-axis 1-pole was mute).
    """
    del delays
    n_samp = int(sr * length_ms / 1000.0) + 1
    n_lines = int(n_lines)
    peak = float(movement_ms or 0.0)
    if peak < 0.0:
        peak = 0.0
    drive_v = None
    det_src = None
    n_out = n_samp
    route_on = array_spec is not None or room_spec is not None or bloom_spec is not None
    if drive is not None and n_lines == 32 and (peak > 0.0 or route_on):
        drive_v = np.asarray(drive, dtype=np.float64).reshape(-1)
        if bloom_det is None:
            det_src = drive_v
        else:
            det_src = np.asarray(bloom_det, dtype=np.float64).reshape(-1)
        npre = 0
        if bloom_spec is not None:
            npre = int(bloom_spec.get("predelay_n") or 0)
            if npre < 0:
                npre = 0
            if npre > 4799:
                npre = 4799
        if npre:
            shifted = np.zeros(drive_v.shape[0] + npre, dtype=np.float64)
            shifted[npre:] = drive_v
            drive_v = shifted
        n_out = int(drive_v.shape[0]) + int(float(sr) * float(length_ms) / 1000.0)
        if n_out < 1:
            n_out = 1
    n_t = len(taps) if taps is not None else 0
    dff_per_tap = [
        tap_dff(t.n, surfaces, master=diffusion_master) for t in taps
    ] if n_t else []
    buses = {
        "l": np.zeros(n_out, dtype=np.float64),
        "c": np.zeros(n_out, dtype=np.float64),
        "r": np.zeros(n_out, dtype=np.float64),
    }
    # Muted centre is multiplied by 0. Skipping the tank leaves that bus at
    # zeros, so a static render stays the same. Shared tail is Live-only.
    skip_c = (
        isinstance(weights, dict)
        and "cl" in weights
        and "cr" in weights
        and float(weights["cl"]) == 0.0
        and float(weights["cr"]) == 0.0
    )
    for ch, out in buses.items():
        if skip_c and ch == "c":
            continue
        dly = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_lines, channel=ch)
        inj = build_inject_from_taps(
            taps, n_samp, sr, c, n_lines, channel=ch, humidity=humidity,
            air_lp=air_lp, air_shelf=air_shelf,
            air_climate=air_climate, air_iso=air_iso,
        )
        _scale_inject_reflect(inj, taps, surfaces, sr=sr, reaktor_parity=bool(reaktor_parity))
        if src_diffuse is not None and not src_diffuse.bypass:
            from source_radiation import apply_coef
            for i in range(n_lines):
                inj[:, i] = apply_coef(inj[:, i], src_diffuse)
        dffs = dffs_from_taps(
            taps, dff_per_tap, diffusion_scale_from_room(room), n=n_lines, channel=ch,
        )
        if smooth:
            dffs = cap_dffs(dffs)
        mic_g = None
        if apply_mic:
            mic_g = mic_g_from_taps(taps, n_lines, ch, sr, res_hz=mic_response_hz)
        harm = harmonic_stages(room, int(sr), float(c), float(line_t60))
        fdn = FDN(
            dly,
            g=g,
            room=room,
            sr=sr,
            c=c,
            depth_per_axis=depth_per_axis,
            peaking=True,
            n=n_lines,
            dffs=dffs,
            mic_g=mic_g,
            line_t60=line_t60,
            parity=bool(reaktor_parity),
            surf=_surf_bus(taps, n_lines, line_t60),
            harm=harm,
        )
        hp = _SUB_HP.get()
        if drive_v is not None:
            driven = np.empty((n_out, n_lines), dtype=np.float64)
            for i in range(n_lines):
                driven[:, i] = fft_convolve(drive_v, inj[:, i])[:n_out]
            # One high-pass on the excitation that enters the tank.
            # Filtering inj as well would filter the movement path twice.
            if hp is not None:
                driven = _df1_columns(driven, hp)
            poly = fdn.process_block_poly(driven, movement_ms=peak)
        else:
            if hp is not None:
                inj = _df1_columns(inj, hp)
            poly = fdn.process_block_poly(inj)
        # Headroom decision 6. F2 applies while line absorption is on.
        # D3b: the F3 row applies on Render too, same total trim as Play.
        poly *= loop_level_trim_lin("render", float(line_t60) > 0.05)
        if tail_sos is None and colour is not None and colour.measured and n_t:
            for i in range(n_lines):
                col = poly[:, i]
                y = colour.apply(col, _bus_theta(taps[i % n_t], ch), ch)
                if y is not col:
                    poly[:, i] = y
        out += np.sum(poly, axis=1)
    if route_on and det_src is not None:
        det = det_src
        if det.shape[0] < n_out:
            z = np.zeros(n_out, dtype=np.float64)
            z[: det.shape[0]] = det
            det = z
        if array_spec is not None or room_spec is not None:
            _route_buses(buses, det, array_spec, room_spec, bus_place)
        if bloom_spec is not None:
            _apply_chain(buses, det, bloom_spec)
    if tail_sos is not None:
        _apply_tail_buses(buses, tail_sos)
    if weights is None:
        return mixer_lcr_fold(buses["l"], buses["r"], buses["c"])
    return apply_capsule_weights(buses["l"], buses["c"], buses["r"], weights)


def _apply_tail_buses(buses, pack) -> None:
    """One K=3 SOS per mic bus, after routing and Bloom, before the fold."""
    from mic_colour.tail_diffuse import apply_sos_df1

    rows = np.asarray(pack, dtype=np.float64).reshape(3, 3, 5)
    for i, ch in enumerate("lcr"):
        buses[ch][:] = apply_sos_df1(buses[ch], rows[i])


def _fft_conv_head(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Causal FFT convolution, truncated to len(x). No SciPy."""
    n = int(x.shape[0])
    nfft = 1 << max(0, (n + int(h.shape[0]) - 2).bit_length())
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[:n]


def render_binaural_fdn_ir(
    taps, room, sr, c, length_ms, g, depth,
    preset: str = "SADIE2_KU100",
    tail_mode: str = "diffuse_ic",
):
    """Uncoloured FDN tail, then the head's diffuse-field IC mixer.

    A = √2 · even lines of the left loop, B = √2 · odd lines of the right loop.
    L = Hc·A + Hs·B, R = Hs·A + Hc·B, via the shipped 513-tap M/S FIRs.
    D3b: the Render F3 trim is applied here. render() never calls this
    function (it trims inside render_fdn_ir), so the scalar is not doubled.
    This loop has no line_t60, so the lock-only F2 row stays off.
    """
    from mic_colour.binaural import tail_fir

    n_samp = int(float(sr) * float(length_ms) / 1000.0) + 1
    n_lines = 32
    dff = [tap_dff(t.n, None, master=DIFFUSION_MASTER_LIVE) for t in taps]
    polys = {}
    for ch in ("l", "r"):
        dly = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_lines, channel=ch)
        inj = build_inject_from_taps(taps, n_samp, sr, c, n_lines, channel=ch)
        dffs = dffs_from_taps(
            taps, dff, diffusion_scale_from_room(room), n=n_lines, channel=ch,
        )
        fdn = FDN(
            dly, g=g, room=room, sr=sr, c=c,
            depth_per_axis=depth, peaking=True, n=n_lines, dffs=dffs,
        )
        hp = _SUB_HP.get()
        if hp is not None:
            inj = _df1_columns(inj, hp)
        polys[ch] = fdn.process_block_poly(inj) * loop_level_trim_lin("render", False)
    if str(tail_mode) != "diffuse_ic":
        return polys["l"].sum(axis=1), polys["r"].sum(axis=1)
    scale = math.sqrt(2.0)
    A = scale * polys["l"][:, 0::2].sum(axis=1)
    B = scale * polys["r"][:, 1::2].sum(axis=1)
    fir = tail_fir(str(preset or "SADIE2_KU100"), int(sr))
    if fir is None:
        return A, B
    hp, hm = fir
    mid = A + B
    side = A - B
    pm = _fft_conv_head(mid, hp)
    sm = _fft_conv_head(side, hm)
    return 0.5 * (pm + sm), 0.5 * (pm - sm)


LIVE_DIRECT_FOLD = 0.55


def has_side_strip(weights) -> bool:
    """D19: a strip folded with opposite signs into L and R (route s) is a Side capsule."""
    if not weights:
        return False
    return any(float(weights[a + "l"]) * float(weights[a + "r"]) < -1e-12 for a in "lcr")


def direct_capsule_spikes(tap) -> Tuple[float, float, float]:
    """ASSUMED direct level. Hottest capsule stays 1.

    Pattern only (cardioid / fig-8 sign). Not the distance law. Callers pass these
    spikes for two sources, and for one source when a strip is route s.
    """
    vals = (
        float(getattr(tap, "cardio_l", 1.0)),
        float(getattr(tap, "cardio_c", 1.0)),
        float(getattr(tap, "cardio_r", 1.0)),
    )
    peak = max(abs(v) for v in vals)
    if peak < 1e-8:
        return (1.0, 1.0, 1.0)
    return (vals[0] / peak, vals[1] / peak, vals[2] / peak)


def render_listen_direct_ir(taps, sr, length_ms, n_lines=32, weights=None, colour=None, spikes=None, src_direct=None, prox_g=None):
    """Delayed spikes, capsule weights, × 0.55.

    Default weights are the 477 fold (L+0.5·C, R+0.5·C).
    Mic colour, when on, filters Ld/Cd/Rd before that fold.
    One source uses spike amplitude 1 unless a strip is route s (D19).
    Two sources pass pattern spikes.
    """
    n_samp = max(1, int(sr * float(length_ms) / 1000.0) + 1)
    Ld = np.zeros(n_samp, dtype=np.float64)
    Cd = np.zeros(n_samp, dtype=np.float64)
    Rd = np.zeros(n_samp, dtype=np.float64)
    if not taps:
        return Ld, Rd
    di = direct_line_index(taps, n_lines)
    if di >= len(taps):
        return Ld, Rd
    t = taps[di]
    if spikes is None and has_side_strip(weights):
        spikes = direct_capsule_spikes(t)
    def _at(ms):
        i = int(round(float(ms) * 0.001 * float(sr)))
        return max(0, min(n_samp - 1, i))
    dc = float(getattr(t, "delay_ms_c", 0.5 * (t.delay_ms_l + t.delay_ms_r)))
    s_l, s_c, s_r = (1.0, 1.0, 1.0) if spikes is None else (
        float(spikes[0]), float(spikes[1]), float(spikes[2]),
    )
    Ld[_at(t.delay_ms_l)] = s_l
    Rd[_at(t.delay_ms_r)] = s_r
    Cd[_at(dc)] = s_c
    if src_direct is not None:
        from source_radiation import apply_coef
        Ld = apply_coef(Ld, src_direct[0])
        Cd = apply_coef(Cd, src_direct[1])
        Rd = apply_coef(Rd, src_direct[2])
    if prox_g is not None:
        g_l, g_c, g_r = float(prox_g[0]), float(prox_g[1]), float(prox_g[2])
        if g_l != 0.0:
            Ld = apply_prox_shelf(Ld, g_l, sr)
        if g_c != 0.0:
            Cd = apply_prox_shelf(Cd, g_c, sr)
        if g_r != 0.0:
            Rd = apply_prox_shelf(Rd, g_r, sr)
    Ld = _colour_apply(colour, Ld, float(t.theta_l), "l")
    Cd = _colour_apply(colour, Cd, float(getattr(t, "theta_c", 0.0)), "c")
    Rd = _colour_apply(colour, Rd, float(t.theta_r), "r")
    w = capsule_speaker_weights() if weights is None else weights
    left, right = apply_capsule_weights(Ld, Cd, Rd, w)
    g = float(LIVE_DIRECT_FOLD)
    return g * left, g * right


def _inject_levels(taps, n, surfaces):
    n = int(n)
    inj_l = [0.0] * n
    inj_c = [0.0] * n
    inj_r = [0.0] * n
    n_t = len(taps) if taps is not None else 0
    if n_t <= 0:
        return inj_l, inj_c, inj_r
    for i in range(n):
        t = taps[i % n_t]
        rg = tap_reflect_gain(t.n, surfaces)
        inj_l[i] = rg * float(t.level_l)
        inj_r[i] = rg * float(t.level_r)
        inj_c[i] = rg * float(getattr(t, "level_c", 0.5 * (t.level_l + t.level_r)))
    return inj_l, inj_c, inj_r


def makeup_at_stand(
    stand,
    desk,
    room,
    source,
    *,
    c,
    grid,
    hadamard_n,
    include_offaxis_shelf,
    reaktor_parity,
    surfaces,
    g,
    ir_length_ms,
    sr,
    weights,
    room_shape=None,
):
    """Mixer makeup from a stand-distance second pass.

    ``stand`` is the unplaced stand, before ``_place_stand``. This copies it
    and places that copy with room-spot positions removed. The caller's stand
    and the audio injects stay on the placed mics. The scalar is the existing
    ``ir_rms_makeup_from_inject``. ``g`` stays the caller's decay gain.

    D-SRC-DIST-LEVEL: the source in this pass is the boot offset from the
    placed stand centre, not the live source. Boot source (DEFAULTS
    2.6, 1.2, 4.75) minus boot stand (3.0, 1.5, 1.5) is (-0.4, -0.3, +3.25).
    On the boot stand that rebuilds the boot source, so the default scene
    stays bit-exact. A moved source then follows 1/r through the injects.
    """
    placed = _place_stand(copy.copy(stand), _desk_at_stand(desk))
    # Same literals as app_server.DEFAULTS. Subtract-then-add keeps the boot
    # source bit-exact when the stand centre is the boot stand.
    boot_src = (2.6, 1.2, 4.75)
    boot_stand = (3.0, 1.5, 1.5)
    if placed is None:
        mk_source = source
    else:
        mk_source = (
            float(placed.cx) + (boot_src[0] - boot_stand[0]),
            float(placed.cy) + (boot_src[1] - boot_stand[1]),
            float(placed.cz) + (boot_src[2] - boot_stand[2]),
        )
    if poly_on(room_shape):
        taps = compute_poly_taps(
            room, mk_source, placed, room_shape,
            c=c, n=hadamard_n,
            include_offaxis_shelf=include_offaxis_shelf,
        )
    else:
        taps = compute_taps(
            room, mk_source, placed, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=hadamard_n,
            include_offaxis_shelf=include_offaxis_shelf,
            reaktor_parity=bool(reaktor_parity),
        )
    inj_l, inj_c, inj_r = _inject_levels(taps, hadamard_n, surfaces)
    return ir_rms_makeup_from_inject(
        inj_l, inj_c, inj_r, g, hadamard_n, ir_length_ms, sr,
        weights=weights,
    )


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
    direct_wet: float = 1.0,
    hadamard_n: int = 32,
    surfaces=None,
    diffusion_seed: int = DEFAULT_DIFFUSION_SEED,
    lambda_ref: float = DEFAULT_LAMBDA_REF_M,
    mic_left=None,
    mic_right=None,
    capsule_mm=17.0,
    humidity=0.0,
    air_lp=0.25,
    air_shelf=1.0,
    diffusion_master=DIFFUSION_MASTER_LIVE,
    mic_response_hz=10000.0,
    mic_gain_l: float = 1.0,
    mic_gain_c: float = 1.0,
    mic_gain_r: float = 1.0,
    mic_pan_l: float = -1.0,
    mic_pan_c: float = 0.0,
    mic_pan_r: float = 1.0,
    mic_phase_l: float = 1.0,
    mic_phase_c: float = 1.0,
    mic_phase_r: float = 1.0,
    colour=None,
    line_t60: float = 0.0,
    loop_g=None,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
    src_plan=None,
    surfaces_solo=None,
    surfaces_mute=None,
    reaktor_parity: bool = False,
    desk=None,
    smooth: bool = False,
    makeup_stand=None,
    makeup_source=None,
    makeup_grid=None,
    makeup_shelf=None,
    include_fdn: bool = True,
    prox_g=None,
    tail_sos=None,
    room_shape=None,
):
    weights, mk_w, _desk_w = _mix_pair(
        desk,
        mic_gain_l, mic_gain_c, mic_gain_r,
        mic_pan_l, mic_pan_c, mic_pan_r,
        mic_phase_l, mic_phase_c, mic_phase_r,
    )
    _g_l = float(prox_g[0]) if prox_g is not None else 0.0
    _g_c = float(prox_g[1]) if prox_g is not None else 0.0
    _g_r = float(prox_g[2]) if prox_g is not None else 0.0
    _prox = (_g_l, _g_c, _g_r) if prox_g is not None else None
    if float(early_wet) > 1e-12:
        Le, Re = render_early_ir(
            taps, room, sr, c, early_ms, DEFAULT_DEPTH, humidity, wall_cache, ap_cache,
            surfaces=surfaces,
            diffusion_seed=diffusion_seed,
            lambda_ref=lambda_ref,
            mic_left=mic_left,
            mic_right=mic_right,
            capsule_mm=capsule_mm,
            air_lp=air_lp,
            air_shelf=air_shelf,
            colour=colour,
            air_climate=air_climate,
            air_iso=air_iso,
            src_images=None if src_plan is None else src_plan.images,
            surfaces_solo=surfaces_solo,
            surfaces_mute=surfaces_mute,
            g_l=_g_l,
            g_r=_g_r,
        )
    else:
        Le = np.zeros(1, dtype=np.float64)
        Re = np.zeros(1, dtype=np.float64)
    Ld, Rd = render_listen_direct_ir(
        taps, sr, fdn_ms, n_lines=hadamard_n, weights=weights, colour=colour,
        src_direct=None if src_plan is None else src_plan.direct,
        prox_g=_prox,
    )
    if not include_fdn:
        Lf = np.zeros(1, dtype=np.float64)
        Rf = np.zeros(1, dtype=np.float64)
    else:
        Lf, Rf = render_fdn_ir(
            taps, room, sr, c, fdn_ms, fdn_g if loop_g is None else loop_g, DEFAULT_DEPTH, delays,
            n_lines=hadamard_n, surfaces=surfaces, humidity=humidity,
            air_lp=air_lp, air_shelf=air_shelf,
            diffusion_master=diffusion_master,
            mic_response_hz=mic_response_hz,
            apply_mic=False,
            weights=weights,
            colour=colour,
            line_t60=line_t60,
            air_climate=air_climate,
            air_iso=air_iso,
            src_diffuse=None if src_plan is None else src_plan.diffuse,
            reaktor_parity=bool(reaktor_parity),
            smooth=bool(smooth),
            tail_sos=tail_sos,
        )
    n = max(len(Le), len(Lf), len(Ld))
    def _pad(a):
        if len(a) >= n:
            return a
        o = np.zeros(n, dtype=np.float64)
        o[: len(a)] = a
        return o
    Ld, Rd, Lf, Rf, Le, Re = _pad(Ld), _pad(Rd), _pad(Lf), _pad(Rf), _pad(Le), _pad(Re)
    if makeup_stand is not None and makeup_source is not None:
        shelf = makeup_shelf
        if shelf is None:
            shelf = bool(getattr(colour, "include_offaxis_shelf", True))
        grid_mk = makeup_grid if makeup_grid is not None else grid_bias_for_hadamard_n(int(hadamard_n))
        mk = makeup_at_stand(
            makeup_stand, desk, room, makeup_source,
            c=c, grid=grid_mk, hadamard_n=hadamard_n,
            include_offaxis_shelf=shelf,
            reaktor_parity=bool(reaktor_parity),
            surfaces=surfaces, g=fdn_g, ir_length_ms=fdn_ms, sr=sr,
            weights=mk_w,
            room_shape=room_shape,
        )
    else:
        inj_l, inj_c, inj_r = _inject_levels(taps, hadamard_n, surfaces)
        mk = ir_rms_makeup_from_inject(
            inj_l, inj_c, inj_r, fdn_g, hadamard_n, fdn_ms, sr,
            weights=mk_w,
        )
    Lf, Rf = Lf * mk, Rf * mk
    # Early FIR is left-capsule / right-capsule, no centre bus.
    # Default weights leave it unchanged. Centre gain does not scale it.
    eL = weights["ll"] * Le + weights["rl"] * Re
    eR = weights["lr"] * Le + weights["rr"] * Re
    Le, Re = eL * mk, eR * mk
    L = float(fdn_wet) * Lf + float(direct_wet) * Ld + float(early_wet) * Le
    R = float(fdn_wet) * Rf + float(direct_wet) * Rd + float(early_wet) * Re
    # No whole-IR scale. A hot fader sum used to hit this 1.2 ceiling and
    # turn the file down before convolution. Play only soft-limits samples.
    return L, R


def _source_plan(preset_id, yaw_deg, pitch_deg, taps_src, prep_src, sr_hz, size_m=None):
    """None for omni. Callers then leave the source stage out."""
    import source_radiation as srcmod

    if prep_src is None or not taps_src:
        return None
    return srcmod.plan_from_scene(
        preset_id, float(yaw_deg or 0.0), float(pitch_deg or 0.0), taps_src,
        prep_src.source, prep_src.mic_centre,
        (prep_src.mic_left, prep_src.mic_centre, prep_src.mic_right),
        sr_hz, size_m=size_m,
    )


def _b_pose(preset_a, yaw_a, pitch_a, preset_b, yaw_b, pitch_b, mirror_b):
    """Source B's preset, yaw and pitch. Null follows A. See effective_b_pose."""
    import source_radiation as srcmod

    return srcmod.effective_b_pose({
        "source_radiation": preset_a,
        "source_yaw": yaw_a,
        "source_pitch": pitch_a,
        "source_radiation_b": preset_b,
        "source_yaw_b": yaw_b,
        "source_pitch_b": pitch_b,
        "mirror_b": bool(mirror_b),
    })


def _render_core(
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
    sx: Optional[float] = None,
    sz: Optional[float] = None,
    mcz: Optional[float] = None,
    space: float,
    diverg: float,
    car_omni: float,
    early_wet: float,
    fdn_wet: float,
    dry_gain: float,
    direct_wet: float = 1.0,
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
    family_l: Optional[str] = None,
    family_c: Optional[str] = None,
    family_r: Optional[str] = None,
    polar_l: Optional[float] = None,
    polar_c: Optional[float] = None,
    polar_r: Optional[float] = None,
    centre_dz: float = 0.0,
    mic_hp_on: bool = False,
    mic_hp_hz: float = 40.0,
    mic_response_hz: float = 10000.0,
    mic_proximity: float = 0.0,
    ms_decode: bool = False,
    capsule_mm: float = 17.0,
    humidity: float = 0.0,
    air_lp: float = 0.25,
    air_shelf: float = 1.0,
    diffusion_master: float = DIFFUSION_MASTER_LIVE,
    decay_s: float = 0.0,
    decay_lock: bool = False,
    mic_gain_l: float = 1.0,
    mic_gain_c: float = 1.0,
    mic_gain_r: float = 1.0,
    mic_pan_l: float = -1.0,
    mic_pan_c: float = 0.0,
    mic_pan_r: float = 1.0,
    mic_phase_l: float = 1.0,
    mic_phase_c: float = 1.0,
    mic_phase_r: float = 1.0,
    two_sources: bool = False,
    source_balance: float = 0.0,
    mirror_b: bool = False,
    sx_b: Optional[float] = None,
    sy_b: Optional[float] = None,
    sz_b: Optional[float] = None,
    dry_l: Optional[np.ndarray] = None,
    dry_r: Optional[np.ndarray] = None,
    colour_mode: str = "MEASURED_SHELF",
    colour_impl: str = "sos",
    mic_preset_l: str = "NeumannU87AiCardioid",
    mic_preset_c: str = "NeumannU87AiCardioid",
    mic_preset_r: str = "NeumannU87AiCardioid",
    mic_hpf_engaged: bool = False,
    mic_hpf_sides: Optional[bool] = None,
    mic_hpf_centre: Optional[bool] = None,
    progress_cb=None,
    reaktor_parity: bool = False,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
    source_radiation: str = "omni",
    source_yaw: float = 0.0,
    source_pitch: float = 0.0,
    source_radiation_b: Optional[str] = None,
    source_yaw_b: Optional[float] = None,
    source_pitch_b: Optional[float] = None,
    source_size_m: Optional[float] = None,
    surfaces_solo=None,
    surfaces_mute=None,
    desk=None,
    mic_hpf_l: Optional[bool] = None,
    mic_hpf_r: Optional[bool] = None,
    smooth: Optional[bool] = None,
    movement: float = 0.0,
    mirror_null: bool = False,
    decay_mode: str = "flat",
    surf_treatment=None,
    surf_cal=None,
    surf_directional: bool = False,
    prox_l: bool = True,
    prox_c: bool = True,
    prox_r: bool = True,
    bloom_preset: str = "natural",
    bloom_amount: float = 0.0,
    bloom_attack_scale: float = 1.0,
    bloom_release_scale: float = 1.0,
    predelay_ms: float = 0.0,
    bloom_colour: bool = False,
    glue_colour: bool = False,
    pre_colour: str = "off",
    pre_drive_db: float = 0.0,
    array_preset: str = "natural",
    array_amount: float = 0.0,
    array_pre: str = "off",
    array_drive_db: float = 0.0,
    room_preset: str = "natural",
    room_amount: float = 0.0,
    room_pre: str = "off",
    room_drive_db: float = 0.0,
    offaxis_tail: bool = False,
    room_shape: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """Render dry mono through early-field (+ optional FDN) with optional motion.

    When path_on is False: single IR convolution (fast).
    When path_on is True: block/OLA moving path (like moving_room_demo.py).
    """
    room: Vec3 = (float(W), float(H), float(L))
    c = SPEED_OF_SOUND_M_S
    mic_colour = MicColour(
        colour_mode, mic_preset_l, mic_preset_c, mic_preset_r, int(sr),
        hpf_engaged=bool(mic_hpf_engaged),
        hpf_sides=mic_hpf_sides,
        hpf_centre=mic_hpf_centre,
        colour_impl=colour_impl,
        hpf_l=mic_hpf_l,
        hpf_r=mic_hpf_r,
    )
    tail_pack = None
    if offaxis_tail:
        from mic_colour.tail_diffuse import design_pack as _tail_design

        tail_pack = _tail_design(
            (mic_preset_l, mic_preset_c, mic_preset_r),
            int(sr),
            (polar_l, polar_c, polar_r),
        )
    surfaces = parse_surfaces(surfaces) if surfaces is not None else default_surfaces()
    smooth_on = smooth_active(
        {
            "reaktor_parity": bool(reaktor_parity),
            "smooth": smooth,
            "fdn_wet": fdn_wet,
            "early_wet": early_wet,
        },
        surfaces,
    )
    # Solo/Mute colours the early field only. FDN inject, Dffs and makeup
    # stay on the un-gated cards.
    seed = int(diffusion_seed)
    lam = parse_lambda_ref(lambda_ref)
    n_dry = len(dry)

    # Split IR length: early gets min(90, ir_len); FDN uses full ir_len (ASSUMED split)
    early_ms = min(DEFAULT_EARLY_MS, float(ir_length_ms))
    # Placeholder until the line delays (and so the unlocked T60) exist.
    fdn_ms = planned_fdn_ms(early_ms, ir_length_ms, float(decay_s) if decay_lock else 0.0)
    t60_used = float(decay_s) if decay_lock else 0.0

    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEFAULT_DEPTH)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    n_had = normalize_hadamard_n(hadamard_n)
    movement_ms = 0.0
    if int(n_had) == 32:
        movement_ms = movement_peak_ms(
            {
                "reaktor_parity": bool(reaktor_parity),
                "movement": movement,
                "fdn_wet": fdn_wet,
                "early_wet": early_wet,
                "mirror_null": bool(mirror_null),
            },
            surfaces,
        )
    import bloom_dsp as _bloom
    _bloom_body = {
        "bloom_preset": bloom_preset,
        "bloom_amount": bloom_amount,
        "bloom_attack_scale": bloom_attack_scale,
        "bloom_release_scale": bloom_release_scale,
        "predelay_ms": predelay_ms,
        "bloom_colour": bloom_colour,
        "glue_colour": glue_colour,
        "pre_colour": pre_colour,
        "pre_drive_db": pre_drive_db,
    }
    bloom_spec = _bloom.design(_bloom_body, sr) if _bloom.bloom_is_on(_bloom_body) else None

    def _side_spec(preset, amount, pre, drive):
        body = {
            "bloom_preset": preset,
            "bloom_amount": amount,
            "pre_colour": pre,
            "pre_drive_db": drive,
        }
        if not _bloom.bloom_is_on(body):
            return None
        return _bloom.design(body, sr)

    array_spec = _side_spec(array_preset, array_amount, array_pre, array_drive_db)
    room_spec = _side_spec(room_preset, room_amount, room_pre, room_drive_db)
    insert_on = bloom_spec is not None or array_spec is not None or room_spec is not None
    bus_place = _bus_place(desk)
    # UI fdn_g is Structure Gain 0–1; loop scale is Gain/N (215).
    g = float(np.clip(fdn_g, 0.0, 1.0)) / float(n_had)
    grid = grid_bias_for_hadamard_n(n_had)
    delays = propose_fdn_delays_samples(W, H, L, sr=sr, c=c, n=n_had)  # fallback; overwritten from taps

    def _unplaced_stand(prep):
        return MicStand.from_prepare(
            prep, car_omni=car_omni,
            pattern_l=pattern_l, pattern_c=pattern_c, pattern_r=pattern_r,
            yaw_l_deg=yaw_l_deg, yaw_c_deg=yaw_c_deg, yaw_r_deg=yaw_r_deg,
            family_l=family_l, family_c=family_c, family_r=family_r,
            polar_l=polar_l, polar_c=polar_c, polar_r=polar_r,
            centre_dz=centre_dz,
            ms_decode=ms_decode,
            capsule_mm=capsule_mm,
        )

    def _placed_taps(prep, place_desk):
        stand = _place_stand(_unplaced_stand(prep), place_desk)
        if poly_on(room_shape):
            return compute_poly_taps(
                room, prep.source, stand, room_shape,
                c=c, n=n_had,
                include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            )
        return compute_taps(
            room, prep.source, stand, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=n_had,
            include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            reaktor_parity=reaktor_parity,
        )

    def taps_at(sox_v: float, soz_v: float):
        prep = prepare_direct_field(
            W, H, L, mz=mz, my=my, space=space, diverg=diverg, sox=sox_v, soz=soz_v, mcx=mcx,
            toe_half_deg=toe_half_deg,
            yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
            sy=sy,
        )
        return _placed_taps(prep, desk), prep

    def taps_for(sx_v: float, sy_v: float, sz_v: float):
        mcx_v = (float(W) * 0.5) if mcx is None else float(mcx)
        prep_i = direct_field_from_metres(
            W, H, L,
            sx=float(sx_v), sy=float(sy_v), sz=float(sz_v),
            mcx=mcx_v, my=float(my), mcz=float(mcz),
            space=space, diverg=diverg,
            toe_half_deg=toe_half_deg,
            yaw_l_deg=yaw_l_deg, yaw_r_deg=yaw_r_deg,
        )
        return _placed_taps(prep_i, desk), prep_i

    def taps_at_metres():
        sy_v = float(my) if sy is None else float(sy)
        return taps_for(float(sx), sy_v, float(sz))

    def _prox_of(prep_src):
        if prep_src is None:
            return (0.0, 0.0, 0.0)
        stand_px = _place_stand(_unplaced_stand(prep_src), desk)
        return capsule_gains(stand_px, prep_src.source, prox_l, prox_c, prox_r)

    if not path_on or path_preset == "still":
        # ASSUMED: stereo file as two sources. Moving path (path_on and not still)
        # never reaches here with a split; it keeps the mono downmix.
        if (
            bool(two_sources)
            and dry_l is not None
            and dry_r is not None
            and sx is not None
            and sz is not None
            and mcz is not None
        ):
            sy_a = float(my) if sy is None else float(sy)
            if mirror_b:
                bx, by, bz = mirror_source_b(float(W), float(sx), sy_a, float(sz))
            else:
                bx = float(W) - float(sx) if sx_b is None else float(sx_b)
                by = sy_a if sy_b is None else float(sy_b)
                bz = float(sz) if sz_b is None else float(sz_b)
            bx = min(max(bx, 0.0), float(W))
            by = min(max(by, 0.0), float(H))
            bz = min(max(bz, 0.0), float(L))
            taps, prep = taps_at_metres()
            taps_b, prep_b = taps_for(bx, by, bz)
            delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
            g_open = g
            g_split = g
            line_t60 = 0.0
            if decay_lock and float(decay_s) > 0.05:
                g_split = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
                lim = 0.99 / math.sqrt(float(n_had))
                g_split = float(max(0.0, min(lim, g_split)))
                line_t60 = float(decay_s)
            t60_used = render_t60_s(delays, g_open, n_had, sr, decay_s, decay_lock)
            fdn_ms = planned_fdn_ms(early_ms, ir_length_ms, t60_used)
            # Loop runs lossless when line absorption carries the decay; makeup keeps g_split.
            g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else g_split
            weights, mk_w, _desk_w = _mix_pair(
                desk,
                mic_gain_l, mic_gain_c, mic_gain_r,
                mic_pan_l, mic_pan_c, mic_pan_r,
                mic_phase_l, mic_phase_c, mic_phase_r,
            )
            mk = makeup_at_stand(
                _unplaced_stand(prep), desk, room, prep.source,
                c=c, grid=grid, hadamard_n=n_had,
                include_offaxis_shelf=mic_colour.include_offaxis_shelf,
                reaktor_parity=reaktor_parity,
                surfaces=surfaces, g=g_split, ir_length_ms=fdn_ms, sr=sr,
                weights=mk_w,
                room_shape=room_shape,
            )
            plan_a = _source_plan(
                source_radiation, source_yaw, source_pitch, taps, prep, sr, source_size_m,
            )
            preset_b, yaw_b, pitch_b = _b_pose(
                source_radiation, source_yaw, source_pitch,
                source_radiation_b, source_yaw_b, source_pitch_b, mirror_b,
            )
            plan_b = _source_plan(
                preset_b, yaw_b, pitch_b,
                taps_b, prep_b, sr, source_size_m,
            )

            def direct_early(taps_src, src_plan, mirror_x=False, prox_g=None):
                di_src = direct_line_index(taps_src, n_had)
                spikes = None
                if taps_src and 0 <= di_src < len(taps_src):
                    spikes = direct_capsule_spikes(taps_src[di_src])
                gL = float(prox_g[0]) if prox_g is not None else 0.0
                gR = float(prox_g[2]) if prox_g is not None else 0.0
                Ld, Rd = render_listen_direct_ir(
                    taps_src, sr, fdn_ms, n_lines=n_had, weights=weights, colour=mic_colour,
                    spikes=spikes,
                    src_direct=None if src_plan is None else src_plan.direct,
                    prox_g=prox_g,
                )
                Ld = float(direct_wet) * Ld
                Rd = float(direct_wet) * Rd
                if float(early_wet) <= 1e-12:
                    return Ld, Rd
                Le, Re = render_early_ir(
                    taps_src, room, sr, c, early_ms, DEFAULT_DEPTH, humidity, wall_cache, ap_cache,
                    surfaces=surfaces,
                    diffusion_seed=seed,
                    lambda_ref=lam,
                    mic_left=prep.mic_left,
                    mic_right=prep.mic_right,
                    capsule_mm=capsule_mm,
                    air_lp=air_lp,
                    air_shelf=air_shelf,
                    colour=mic_colour,
                    air_climate=air_climate,
                    air_iso=air_iso,
                    src_images=None if src_plan is None else src_plan.images,
                    mirror_x=bool(mirror_x),
                    surfaces_solo=surfaces_solo,
                    surfaces_mute=surfaces_mute,
                    g_l=gL,
                    g_r=gR,
                )
                n_ir = max(len(Ld), len(Le))

                def _pad(a):
                    if len(a) >= n_ir:
                        return a
                    o = np.zeros(n_ir, dtype=np.float64)
                    o[: len(a)] = a
                    return o

                Ld, Rd, Le, Re = _pad(Ld), _pad(Rd), _pad(Le), _pad(Re)
                eL = weights["ll"] * Le + weights["rl"] * Re
                eR = weights["lr"] * Le + weights["rr"] * Re
                return Ld + float(early_wet) * mk * eL, Rd + float(early_wet) * mk * eR

            deA_L, deA_R = direct_early(taps, plan_a, False, _prox_of(prep))
            deB_L, deB_R = direct_early(taps_b, plan_b, bool(mirror_b), _prox_of(prep_b))

            if movement_ms <= 0.0 and not insert_on:
                def _fdn_stereo(taps_src, src_plan):
                    left, right = render_fdn_ir(
                        taps_src, room, sr, c, fdn_ms, g_loop, DEFAULT_DEPTH, delays,
                        n_lines=n_had, surfaces=surfaces, humidity=humidity,
                        air_lp=air_lp, air_shelf=air_shelf,
                        diffusion_master=diffusion_master,
                        mic_response_hz=mic_response_hz,
                        apply_mic=False,
                        weights=weights,
                        colour=mic_colour,
                        line_t60=line_t60,
                        air_climate=air_climate,
                        air_iso=air_iso,
                        src_diffuse=None if src_plan is None else src_plan.diffuse,
                        reaktor_parity=bool(reaktor_parity),
                        smooth=bool(smooth_on),
                        tail_sos=tail_pack,
                    )
                    return float(fdn_wet) * mk * left, float(fdn_wet) * mk * right

                fA_L, fA_R = _fdn_stereo(taps, plan_a)
                fB_L, fB_R = _fdn_stereo(taps_b, plan_b)
                exc_a, exc_b, down, ga, gb = two_source_excitation(dry_l, dry_r, source_balance)

                def _conv3(ir_a, ir_b, ir_fa, ir_fb):
                    ya = fft_convolve(exc_a, ir_a)
                    yb = fft_convolve(exc_b, ir_b)
                    yfa = fft_convolve(0.5 * exc_a, ir_fa)
                    yfb = fft_convolve(0.5 * exc_b, ir_fb)
                    n_y = max(len(ya), len(yb), len(yfa), len(yfb))
                    o = np.zeros(n_y, dtype=np.float64)
                    o[: len(ya)] += ya
                    o[: len(yb)] += yb
                    o[: len(yfa)] += yfa
                    o[: len(yfb)] += yfb
                    return o

                yL = _conv3(deA_L, deB_L, fA_L, fB_L)
                yR = _conv3(deA_R, deB_R, fA_R, fB_R)
            else:
                exc_a, exc_b, down, ga, gb = two_source_excitation(dry_l, dry_r, source_balance)

                def _driven(taps_src, src_plan, drive, det=None):
                    left, right = render_fdn_ir(
                        taps_src, room, sr, c, fdn_ms, g_loop, DEFAULT_DEPTH, delays,
                        n_lines=n_had, surfaces=surfaces, humidity=humidity,
                        air_lp=air_lp, air_shelf=air_shelf,
                        diffusion_master=diffusion_master,
                        mic_response_hz=mic_response_hz,
                        apply_mic=False,
                        weights=weights,
                        colour=mic_colour,
                        line_t60=line_t60,
                        air_climate=air_climate,
                        air_iso=air_iso,
                        src_diffuse=None if src_plan is None else src_plan.diffuse,
                        reaktor_parity=bool(reaktor_parity),
                        smooth=bool(smooth_on),
                        movement_ms=movement_ms,
                        drive=drive,
                        bloom_spec=bloom_spec,
                        bloom_det=det,
                        array_spec=array_spec,
                        room_spec=room_spec,
                        bus_place=bus_place,
                        tail_sos=tail_pack,
                    )
                    return float(fdn_wet) * mk * left, float(fdn_wet) * mk * right

                bloom_det = None
                if bloom_spec is not None:
                    na = int(np.asarray(exc_a).shape[0])
                    nb = int(np.asarray(exc_b).shape[0])
                    nlink = na if na > nb else nb
                    aa = np.zeros(nlink, dtype=np.float64)
                    bb = np.zeros(nlink, dtype=np.float64)
                    aa[:na] = np.abs(np.asarray(exc_a, dtype=np.float64))
                    bb[:nb] = np.abs(np.asarray(exc_b, dtype=np.float64))
                    bloom_det = np.maximum(aa, bb)
                fA_L, fA_R = _driven(taps, plan_a, 0.5 * exc_a, bloom_det)
                fB_L, fB_R = _driven(taps_b, plan_b, 0.5 * exc_b, bloom_det)

                def _sum4(ir_a, ir_b, fa, fb):
                    ya = fft_convolve(exc_a, ir_a)
                    yb = fft_convolve(exc_b, ir_b)
                    n_y = max(len(ya), len(yb), len(fa), len(fb))
                    o = np.zeros(n_y, dtype=np.float64)
                    o[: len(ya)] += ya
                    o[: len(yb)] += yb
                    o[: len(fa)] += fa
                    o[: len(fb)] += fb
                    return o

                yL = _sum4(deA_L, deB_L, fA_L, fB_L)
                yR = _sum4(deA_R, deB_R, fA_R, fB_R)
            n_dry_b = len(down)
            keep = n_dry_b + int(sr * fdn_ms * 0.001)
            yL = yL[:keep]
            yR = yR[:keep]
            dry_pad = np.zeros(keep, dtype=np.float64)
            dry_pad[:n_dry_b] = down
            mix_L = float(dry_gain) * dry_pad + yL
            mix_R = float(dry_gain) * dry_pad + yR
            mix_L, mix_R = fade_render_tail(mix_L, mix_R, yL, yR, dry_pad, float(dry_gain), n_dry_b, sr)
            mix_L, mix_R, peak, scale, lim_db, lim_n = apply_soft_limit(mix_L, mix_R)
            colour = colour_from_stereo(yL, yR, sr)
            info = {
                "mode": "two_sources",
                "source": prep.source,
                "source_b": prep_b.source,
                "mic_centre": prep.mic_centre,
                "mcz": prep.mcz,
                "mcx": prep.mcx,
                "gain_a": ga,
                "gain_b": gb,
                "two_sources": True,
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
                "colour_mode": mic_colour.mode,
                "colour_notice": getattr(mic_colour, "notice", ""),
                "mic_preset_l": mic_colour.preset_ids["l"],
                "mic_preset_c": mic_colour.preset_ids["c"],
                "mic_preset_r": mic_colour.preset_ids["r"],
                "fdn_ms": fdn_ms,
                "t60_s": t60_used,
                "limiter_db": lim_db,
                "limiter_samples": lim_n,
            }
            if progress_cb:
                progress_cb(1.0)
            return mix_L, mix_R, info

        if sx is not None and sz is not None and mcz is not None:
            taps, prep = taps_at_metres()
        else:
            taps, prep = taps_at(sox, soz)
        delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
        g_open = g
        line_t60 = 0.0
        if decay_lock and float(decay_s) > 0.05:
            g = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
            lim = 0.99 / math.sqrt(float(n_had))
            g = float(max(0.0, min(lim, g)))
            line_t60 = float(decay_s)
        t60_used = render_t60_s(delays, g_open, n_had, sr, decay_s, decay_lock)
        fdn_ms = planned_fdn_ms(early_ms, ir_length_ms, t60_used)
        src_plan = _source_plan(
            source_radiation, source_yaw, source_pitch, taps, prep, sr, source_size_m,
        )
        if movement_ms <= 0.0 and not insert_on:
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
                direct_wet=direct_wet,
                hadamard_n=n_had,
                surfaces=surfaces,
                diffusion_seed=seed,
                lambda_ref=lam,
                mic_left=prep.mic_left,
                mic_right=prep.mic_right,
                capsule_mm=capsule_mm,
                humidity=humidity,
                air_lp=air_lp,
                air_shelf=air_shelf,
                mic_response_hz=mic_response_hz,
                diffusion_master=diffusion_master,
                mic_gain_l=mic_gain_l, mic_gain_c=mic_gain_c, mic_gain_r=mic_gain_r,
                mic_pan_l=mic_pan_l, mic_pan_c=mic_pan_c, mic_pan_r=mic_pan_r,
                mic_phase_l=mic_phase_l, mic_phase_c=mic_phase_c, mic_phase_r=mic_phase_r,
                colour=mic_colour,
                line_t60=line_t60,
                loop_g=(1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else None,
                air_climate=air_climate,
                air_iso=air_iso,
                src_plan=src_plan,
                surfaces_solo=surfaces_solo,
                surfaces_mute=surfaces_mute,
                reaktor_parity=bool(reaktor_parity),
                desk=desk,
                smooth=bool(smooth_on),
                makeup_stand=_unplaced_stand(prep),
                makeup_source=prep.source,
                makeup_grid=grid,
                makeup_shelf=mic_colour.include_offaxis_shelf,
                prox_g=_prox_of(prep),
                tail_sos=tail_pack,
                room_shape=room_shape,
            )
            yL = fft_convolve(dry, ir_L)
            yR = fft_convolve(dry, ir_R)
        else:
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
                direct_wet=direct_wet,
                hadamard_n=n_had,
                surfaces=surfaces,
                diffusion_seed=seed,
                lambda_ref=lam,
                mic_left=prep.mic_left,
                mic_right=prep.mic_right,
                capsule_mm=capsule_mm,
                humidity=humidity,
                air_lp=air_lp,
                air_shelf=air_shelf,
                mic_response_hz=mic_response_hz,
                diffusion_master=diffusion_master,
                mic_gain_l=mic_gain_l, mic_gain_c=mic_gain_c, mic_gain_r=mic_gain_r,
                mic_pan_l=mic_pan_l, mic_pan_c=mic_pan_c, mic_pan_r=mic_pan_r,
                mic_phase_l=mic_phase_l, mic_phase_c=mic_phase_c, mic_phase_r=mic_phase_r,
                colour=mic_colour,
                line_t60=line_t60,
                loop_g=(1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else None,
                air_climate=air_climate,
                air_iso=air_iso,
                src_plan=src_plan,
                surfaces_solo=surfaces_solo,
                surfaces_mute=surfaces_mute,
                reaktor_parity=bool(reaktor_parity),
                desk=desk,
                smooth=bool(smooth_on),
                makeup_stand=_unplaced_stand(prep),
                makeup_source=prep.source,
                makeup_grid=grid,
                makeup_shelf=mic_colour.include_offaxis_shelf,
                include_fdn=False,
                prox_g=_prox_of(prep),
                room_shape=room_shape,
            )
            yL = fft_convolve(dry, ir_L)
            yR = fft_convolve(dry, ir_R)
            g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else g
            _w_move, mk_w, _desk_move = _mix_pair(
                desk,
                mic_gain_l, mic_gain_c, mic_gain_r,
                mic_pan_l, mic_pan_c, mic_pan_r,
                mic_phase_l, mic_phase_c, mic_phase_r,
            )
            mk = makeup_at_stand(
                _unplaced_stand(prep), desk, room, prep.source,
                c=c, grid=grid, hadamard_n=n_had,
                include_offaxis_shelf=mic_colour.include_offaxis_shelf,
                reaktor_parity=bool(reaktor_parity),
                surfaces=surfaces, g=g, ir_length_ms=fdn_ms, sr=sr,
                weights=mk_w,
                room_shape=room_shape,
            )
            fL, fR = render_fdn_ir(
                taps, room, sr, c, fdn_ms, g_loop, DEFAULT_DEPTH, delays,
                n_lines=n_had, surfaces=surfaces, humidity=humidity,
                air_lp=air_lp, air_shelf=air_shelf,
                diffusion_master=diffusion_master,
                mic_response_hz=mic_response_hz,
                apply_mic=False,
                weights=_w_move,
                colour=mic_colour,
                line_t60=line_t60,
                air_climate=air_climate,
                air_iso=air_iso,
                src_diffuse=None if src_plan is None else src_plan.diffuse,
                reaktor_parity=bool(reaktor_parity),
                smooth=bool(smooth_on),
                movement_ms=movement_ms,
                drive=dry,
                bloom_spec=bloom_spec,
                array_spec=array_spec,
                room_spec=room_spec,
                bus_place=bus_place,
                tail_sos=tail_pack,
            )
            scale = float(fdn_wet) * mk
            n_y = max(len(yL), len(yR), len(fL), len(fR))

            def _pad_m(a):
                if len(a) >= n_y:
                    return a
                o = np.zeros(n_y, dtype=np.float64)
                o[: len(a)] = a
                return o

            yL = _pad_m(yL) + scale * _pad_m(fL)
            yR = _pad_m(yR) + scale * _pad_m(fR)
        keep = n_dry + int(sr * fdn_ms * 0.001)
        yL = yL[:keep]
        yR = yR[:keep]
        dry_pad = np.zeros(keep, dtype=np.float64)
        dry_pad[:n_dry] = dry
        mix_L = dry_gain * dry_pad + yL
        mix_R = dry_gain * dry_pad + yR
        mix_L, mix_R = fade_render_tail(mix_L, mix_R, yL, yR, dry_pad, float(dry_gain), n_dry, sr)
        mix_L, mix_R, peak, scale, lim_db, lim_n = apply_soft_limit(mix_L, mix_R)
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
            "colour_mode": mic_colour.mode,
            "colour_notice": getattr(mic_colour, "notice", ""),
            "mic_preset_l": mic_colour.preset_ids["l"],
            "mic_preset_c": mic_colour.preset_ids["c"],
            "mic_preset_r": mic_colour.preset_ids["r"],
            "fdn_ms": fdn_ms,
            "t60_s": t60_used,
            "limiter_db": lim_db,
            "limiter_samples": lim_n,
        }
        if progress_cb:
            progress_cb(1.0)
        return mix_L, mix_R, info

    # Moving path — block/OLA (ASSUMED hop/frame like moving_room_demo).
    # One file length, from the rest-position lines. Lock-on T60 is decay_s.
    taps_len, _prep_len = taps_at(sox, soz)
    delays_len = fdn_delays_from_taps(taps_len, sr=sr, c=c, n=n_had)
    t60_used = render_t60_s(delays_len, g, n_had, sr, decay_s, decay_lock)
    fdn_ms = planned_fdn_ms(early_ms, ir_length_ms, t60_used)
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
        delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
        line_t60 = 0.0
        if decay_lock and float(decay_s) > 0.05:
            g = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
            lim = 0.99 / math.sqrt(float(n_had))
            g = float(max(0.0, min(lim, g)))
            line_t60 = float(decay_s)
        hop_plan = _source_plan(
            source_radiation, source_yaw, source_pitch, taps, last_prep, sr, source_size_m,
        )
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
            direct_wet=direct_wet,
            hadamard_n=n_had,
            surfaces=surfaces,
            diffusion_seed=seed,
            lambda_ref=lam,
            mic_left=last_prep.mic_left,
            mic_right=last_prep.mic_right,
            humidity=humidity,
            air_lp=air_lp,
            air_shelf=air_shelf,
            mic_response_hz=mic_response_hz,
            diffusion_master=diffusion_master,
            mic_gain_l=mic_gain_l, mic_gain_c=mic_gain_c, mic_gain_r=mic_gain_r,
            mic_pan_l=mic_pan_l, mic_pan_c=mic_pan_c, mic_pan_r=mic_pan_r,
            mic_phase_l=mic_phase_l, mic_phase_c=mic_phase_c, mic_phase_r=mic_phase_r,
            colour=mic_colour,
            line_t60=line_t60,
            loop_g=(1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else None,
            air_climate=air_climate,
            air_iso=air_iso,
            src_plan=hop_plan,
            surfaces_solo=surfaces_solo,
            surfaces_mute=surfaces_mute,
            reaktor_parity=bool(reaktor_parity),
            desk=desk,
            smooth=bool(smooth_on),
            makeup_stand=_unplaced_stand(last_prep),
            makeup_source=last_prep.source,
            makeup_grid=grid,
            makeup_shelf=mic_colour.include_offaxis_shelf,
            prox_g=_prox_of(last_prep),
            tail_sos=tail_pack,
            room_shape=room_shape,
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
    wet_sL = ola_comp * wet_L
    wet_sR = ola_comp * wet_R
    mix_L = dry_gain * dry_pad + wet_sL
    mix_R = dry_gain * dry_pad + wet_sR
    mix_L, mix_R = fade_render_tail(mix_L, mix_R, wet_sL, wet_sR, dry_pad, float(dry_gain), n_dry, sr)
    mix_L, mix_R, peak, scale, lim_db, lim_n = apply_soft_limit(mix_L, mix_R)
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
        "colour_mode": mic_colour.mode,
        "colour_notice": getattr(mic_colour, "notice", ""),
        "mic_preset_l": mic_colour.preset_ids["l"],
        "mic_preset_c": mic_colour.preset_ids["c"],
        "mic_preset_r": mic_colour.preset_ids["r"],
        "fdn_ms": fdn_ms,
        "t60_s": t60_used,
        "limiter_db": lim_db,
        "limiter_samples": lim_n,
    }
    return mix_L, mix_R, info


def _identity_n(spec) -> int:
    n = 0
    for row in (spec or {}).get("report") or []:
        guard = row.get("guard") if isinstance(row, dict) else None
        for g in guard or []:
            if isinstance(g, dict) and g.get("fallback") == "identity":
                n += 1
    return n


def _render_ceiling(*args, **kw):
    """Flat (2011) calls _render_core unchanged.

    decay_mode "surfaces" designs per-line attenuation sections and passes
    them to every FDN bus. A missing surf_directional stays room average.
    True uses per-line face hits with s' at least 0.5 (D-SL2). surf_cal is
    the one Render pass (D-SL4), seven factors, Play reuses the stored list.

    phys_ceiling uses that same section path. The server default is on.
    This pop stays False for a direct caller that omits the key. The pack is
    omitted when the decay lock is off. line_t60 inside _render_core stays
    the armed dial. Two-source, single-source, and movement all read the
    one spec. design_bus caches the movement hops by delay.
    """
    phys = bool(kw.pop("phys_ceiling", False))
    if str(kw.get("decay_mode") or "flat").lower() != "surfaces" and not phys:
        return _render_core(*args, **kw)
    import surf_loop as _SLP
    import surf_panels as _SP
    import surf_target as _STG
    ba = _insp.signature(_render_core).bind(*args, **kw)
    ba.apply_defaults()
    a = ba.arguments
    W, H, L = float(a["W"]), float(a["H"]), float(a["L"])
    surfaces_on = str(a.get("decay_mode") or "flat").lower() == "surfaces"
    surfaces = parse_surfaces(a["surfaces"]) if a["surfaces"] is not None else default_surfaces()
    cards = _SP.cards_with_treatment(surfaces, a.get("surf_treatment") or [])
    hum = float(a["humidity"] or 0.0)
    lock_armed = bool(a["decay_lock"]) and float(a["decay_s"] or 0.0) > 0.05
    dial = float(a["decay_s"]) if lock_armed else 0.0
    if surfaces_on and any("absorb_fn" in c for c in cards.values()):
        # Treatment is part of the face. Early reflections and the FDN
        # injection see the treated octave alpha, not only the loop.
        from surface_colour import ABSORB_BAND_HZ as _BH
        a["surfaces"] = {
            k: (
                dict(surfaces[k], absorb=[round(float(x), 4) for x in cards[k]["absorb_fn"](np.asarray(_BH, float))])
                if "absorb_fn" in cards[k] else surfaces[k]
            )
            for k in surfaces
        }
    anchor = float(a["decay_s"]) if lock_armed else None
    if surfaces_on and anchor is None:
        # Lock off: the materials set the length. The dial shows that result.
        a["decay_s"] = float(np.mean(_STG.room_target(W, H, L, cards, hum, np.array([500.0, 1000.0]))))
        a["decay_lock"] = True
    if surfaces_on and phys and lock_armed:
        spec = _SLP.phys_ceiling_pack(
            W, H, L, cards, dial, True, True, hum,
            directional=bool(a.get("surf_directional", False)),
            cal=a.get("surf_cal"),
        )
    elif surfaces_on:
        spec = _SLP.make_spec(
            W, H, L, cards, hum, anchor,
            directional=bool(a.get("surf_directional", False)),
            cal=a.get("surf_cal"),
        )
    elif lock_armed:
        spec = _SLP.phys_ceiling_pack(
            W, H, L, cards, dial, True, False, hum,
            directional=False, cal=None,
        )
    else:
        # Ceiling on, lock off. The section math assumes the dial loss is
        # already in the loop, so the pack is omitted.
        return _render_core(*ba.args, **ba.kwargs)
    if spec is None:
        return _render_core(*ba.args, **ba.kwargs)
    tok = _SURF_CTX.set(spec)
    try:
        y_l, y_r, info = _render_core(*ba.args, **ba.kwargs)
    finally:
        _SURF_CTX.reset(tok)
    info = dict(info or {})
    if surfaces_on:
        info["surf"] = dict(
            decay_mode="surfaces",
            target_T_oct=spec["target_T_oct"],
            anchor_s=anchor,
            decay_s_used=float(a["decay_s"]),
            directional=spec["directional"],
            cal=a.get("surf_cal"),
            buses=spec["report"],
        )
        if phys and lock_armed:
            info["surf"]["ceiling_t"] = spec.get("ceiling_t")
            info["surf"]["ceiling_hz"] = spec.get("ceiling_hz")
            info["surf"]["k"] = spec.get("k")
            info["surf"]["identity_n"] = _identity_n(spec)
    elif phys:
        info["phys_ceiling"] = {
            "ceiling_t": spec.get("ceiling_t"),
            "ceiling_hz": spec.get("ceiling_hz"),
            "k": spec.get("k"),
            "buses": spec.get("report") or [],
            "identity_n": _identity_n(spec),
        }
    return y_l, y_r, info


@_ft.wraps(_render_core)
def render(*args, **kw):
    """Public render. sub_hp on filters only the excitation entering the tank."""
    sub_on = bool(kw.pop("sub_hp", False))
    token = None
    if sub_on:
        sr_hp = args[1] if len(args) > 1 else 48000
        token = _SUB_HP.set(sub_hp_coeffs(float(sr_hp)))
    try:
        return _render_ceiling(*args, **kw)
    finally:
        if token is not None:
            _SUB_HP.reset(token)


def _shelf_off() -> dict:
    return {"on": False, "b0": 1.0, "b1": 0.0, "b2": 0.0, "a1": 0.0, "a2": 0.0}


def _shelf_on(raw) -> dict:
    if raw is None:
        return _shelf_off()
    b0, b1, b2, a1, a2 = normalize_biquad(raw)
    return {"on": True, "b0": b0, "b1": b1, "b2": b2, "a1": a1, "a2": a2}


def _live_air_for_distance(
    dist_m: float, sr: int, humidity: float, air_lp: float, air_shelf: float,
    air_climate: str = "studio_20C_50RH", air_iso: bool = True,
):
    """Per-line Structure 1-pole plus the two ISO shelves (same gains as Render)."""
    lp = max(0.0, min(1.0, float(air_lp)))
    sh = max(0.0, min(1.0, float(air_shelf)))
    air_g = 0.0
    if humidity > 0.0 and lp > 0.0:
        fc = air_abs_cutoff_hz(dist_m, air_abs_wet_from_humidity(humidity))
        air_g = one_pole_g_from_fc(fc, sr)
    shelf = _shelf_off()
    shelf2 = _shelf_off()
    if humidity > 0.0 and sh > 0.0 and air_iso:
        low, high = iso_shelf_pair(dist_m, sr, sh, air_climate, humidity)
        shelf = _shelf_on(low)
        shelf2 = _shelf_on(high)
    return air_g, lp, shelf, shelf2


def _early_gate_row(taps, n: int, solo_l, mute_s) -> list:
    """1 if the image stays in the early field, else 0. Same on every bus."""
    n_t = len(taps) if taps else 0
    row = []
    for i in range(int(n)):
        if n_t <= 0:
            row.append(1.0)
            continue
        row.append(1.0 if image_in_early(taps[i % n_t].n, solo_l, mute_s) else 0.0)
    return row


def _sos_from_spec(spec, room, taps, rate, n_had, line_t60, peaking, taps_b=None):
    """Play coefficients for one section spec. design_bus, not a new opcode.

    taps_b designs the second tank from B's own delays. One source leaves
    taps_b unset, so surf_stab stays {max_loop_db} and surf_sos_b is absent.
    identity_n, ceiling_hz and ceiling_t stay off the live dict.
    """
    import surf_loop as _SLP
    from early_field import axial_mode_hz
    c = SPEED_OF_SOUND_M_S
    dims = (float(room[0]), float(room[1]), float(room[2]))
    cut = float(spec.get("keep_cut_below_hz", _SLP.KEEP_CUT_BELOW_HZ))
    keep = []
    peaks15 = []
    for ax in range(3):
        bank = peaking[ax]
        f0 = axial_mode_hz(c, dims[ax])
        kept = bool(bank.get("on")) and float(f0) < cut
        keep.append(1 if kept else 0)
        if kept:
            peaks15.extend((
                float(bank["b0"]), float(bank["b1"]), float(bank["b2"]),
                float(bank["a1"]), float(bank["a2"]),
            ))
        else:
            peaks15.extend((1.0, 0.0, 0.0, 0.0, 0.0))

    def line_peak(i, keep=keep, peaks15=peaks15):
        ax = i % 3
        if not keep[ax]:
            return None
        o = ax * 5
        return tuple(peaks15[o:o + 5])

    def design_bank(tapset):
        sos = np.zeros(3 * 32 * 3 * 5, dtype=np.float64)
        worst = -1.0e9
        ident = 0
        for bi, ch in enumerate(("l", "c", "r")):
            dly = fdn_delays_from_taps(tapset, sr=rate, c=c, n=n_had, channel=ch)
            lg = np.asarray(
                [10.0 ** (-3.0 * float(d) / (float(rate) * float(line_t60))) for d in dly],
                dtype=np.float64,
            )
            peaks = [line_peak(i) for i in range(n_had)]
            if spec.get("directional"):
                from surface_colour import surfaces_hit_by_n
                n_t = len(tapset) if tapset else 0
                hits = []
                for i in range(n_had):
                    if n_t:
                        n = getattr(tapset[i % n_t], "n", (0, 0, 0))
                        hits.append(surfaces_hit_by_n(n))
                    else:
                        hits.append([])
            else:
                hits = [[] for _ in range(n_had)]
            rates = np.asarray(spec["rates_for"](dly, rate, hits), dtype=np.float64)
            res = _SLP.design_bus(dly, rate, lg, peaks, rates, spec.get("struct", "S1P2"))
            for g in res.get("guard") or []:
                if isinstance(g, dict) and g.get("fallback") == "identity":
                    ident += 1
            mx = float(res["stab"]["max_loop_db"])
            if mx > worst:
                worst = mx
            secs = np.asarray(res["secs"], dtype=np.float64)
            if secs.shape != (32, 3, 5) or not np.all(np.isfinite(secs)):
                return None, worst, ident
            sos[bi * 480:(bi + 1) * 480] = secs.reshape(-1)
        return sos, worst, ident

    def stab_of(worst, worst_a, worst_b):
        stab = {"max_loop_db": round(worst, 5)}
        if taps_b is not None:
            stab["max_loop_db_a"] = round(worst_a, 5)
            if worst_b is not None:
                stab["max_loop_db_b"] = round(worst_b, 5)
        return stab

    sos, worst_a, ident = design_bank(taps)
    worst = worst_a
    sos_b = None
    worst_b = None
    if sos is not None and taps_b is not None:
        sos_b, worst_b, ident_b = design_bank(taps_b)
        ident += ident_b
        if worst_b > worst:
            worst = worst_b
    if sos is None or (taps_b is not None and sos_b is None):
        return {"surf_on": 0, "surf_refused": "shape", "surf_stab": stab_of(worst, worst_a, worst_b)}
    if worst >= 0.0:
        return {"surf_on": 0, "surf_refused": "loop_gain", "surf_stab": stab_of(worst, worst_a, worst_b)}
    out = {
        "surf_on": 1,
        "surf_sos": [float(x) for x in sos],
        "surf_keep": keep,
        "surf_peaks": [float(x) for x in peaks15],
        "surf_stab": stab_of(worst, worst_a, worst_b),
        "identity_n": ident,
        "ceiling_hz": spec.get("ceiling_hz"),
        "ceiling_t": spec.get("ceiling_t"),
    }
    if taps_b is not None:
        out["surf_sos_b"] = [float(x) for x in sos_b]
    return out


def _ceiling_spec(p, room, surfaces, line_t60):
    """None when phys_ceiling is off or the lock is not armed."""
    if not bool(p.get("phys_ceiling")) or float(line_t60) <= 0.05:
        return None
    import surf_loop as _SLP
    import surf_panels as _SP
    W, H, L = float(room[0]), float(room[1]), float(room[2])
    cards = _SP.cards_with_treatment(surfaces, p.get("surf_treatment") or [])
    mode = str(p.get("decay_mode") or "flat").lower() == "surfaces"
    return _SLP.phys_ceiling_pack(
        W, H, L, cards, float(line_t60), True, mode,
        float(p.get("humidity") or 0.0),
        directional=bool(p.get("surf_directional")) if mode else False,
        cal=p.get("surf_cal") if mode else None,
    )


def _treat_sets_length(p) -> bool:
    """Treatment-sets-decay. Surfaces only. Flat and a missing flag leave the lock."""
    if not bool(p.get("treat_sets_decay")):
        return False
    return str(p.get("decay_mode") or "flat").lower() == "surfaces"


def _treat_material_mid(p, room, surfaces) -> float:
    """500 Hz / 1 kHz mean. The same number Render arms when the lock is off."""
    import numpy as np
    import surf_panels as _SP
    import surf_target as _STG
    W, H, L = float(room[0]), float(room[1]), float(room[2])
    cards = _SP.cards_with_treatment(surfaces, p.get("surf_treatment") or [])
    hum = float(p.get("humidity") or 0.0)
    return float(np.mean(_STG.room_target(
        W, H, L, cards, hum, np.array([500.0, 1000.0]),
    )))


def _live_surf_pack(p, room, surfaces, taps, rate, n_had, line_t60, peaking, taps_b=None):
    """SL3. Per-bus S1P2 for Play. Flat, lock-off, and N other than 32 return None.

    Directional only when the scene posts it (D-SL2). Flat stays the room
    pack with empty hits. D-SL3 keeps an axis whose mode is under 30 Hz. Loop gain at or above 0 dB
    leaves Surfaces off. That guard is not the C Jury check.

    phys_ceiling on, lock armed, N 32: the same designer, fed by
    phys_ceiling_pack. The key off leaves this body alone, so the live dict
    does not grow a key. treat_sets_decay skips that ceiling and uses the
    material mean, the Render lock-off path.
    """
    if (
        not _treat_sets_length(p)
        and bool(p.get("phys_ceiling"))
        and float(line_t60) > 0.05
        and int(n_had) == 32
    ):
        try:
            spec = _ceiling_spec(p, room, surfaces, line_t60)
            if spec is not None:
                return _sos_from_spec(
                    spec, room, taps, rate, n_had, line_t60, peaking, taps_b=taps_b,
                )
        except Exception as exc:
            return {"surf_on": 0, "surf_refused": "design:" + type(exc).__name__}
    mode = str(p.get("decay_mode") or "flat").lower()
    if mode != "surfaces" or float(line_t60) <= 0.05 or int(n_had) != 32:
        return None
    try:
        import surf_loop as _SLP
        import surf_panels as _SP
        W, H, L = float(room[0]), float(room[1]), float(room[2])
        cards = _SP.cards_with_treatment(surfaces, p.get("surf_treatment") or [])
        hum = float(p.get("humidity") or 0.0)
        spec = _SLP.make_spec(
            W, H, L, cards, hum, float(line_t60),
            directional=bool(p.get("surf_directional")),
            cal=p.get("surf_cal"),
        )
        return _sos_from_spec(
            spec, room, taps, rate, n_had, line_t60, peaking, taps_b=taps_b,
        )
    except Exception as exc:
        return {"surf_on": 0, "surf_refused": "design:" + type(exc).__name__}


def live_fdn_params(
    p: dict,
    sr: int = SAMPLE_RATE_HZ,
) -> dict:
    """Compact running-FDN coefficients for the browser worklet. ASSUMED live path.

    Same geometry / inject / Dffs / cut-only peaking as the offline IR.
    Air 1-pole + shelf run in the worklet (not baked into inject). Play
    honours hadamard_n 8, 16, and 32. 64 and 128 stay on the 32-line network.
    Makeup is running Mixer level (not IR-window RMS).
    A polygon ``room_shape`` (splay, lede, live) builds the taps with
    ``compute_poly_taps``, the same call Render uses. Absent or box stays
    ``compute_taps``, so those live dicts stay the shoebox bytes.
    When p["sample_rate"] is present and at least 8000, delays, the
    decay-lock mean, air, the shelf, and peaking use that integer. Missing
    or below 8000 stays on `sr` (44100 when the caller omits it). Measured
    colour already designs at the posted rate.
    """
    room: Vec3 = (float(p["W"]), float(p["H"]), float(p["L"]))
    c = SPEED_OF_SOUND_M_S
    surfaces = parse_surfaces(p.get("surfaces")) if p.get("surfaces") is not None else default_surfaces()
    # FDN inject, Dffs and makeup use the un-gated cards. Solo/Mute is an
    # early-field gate (SURF), not a hole in the tail.
    asked = p.get("hadamard_n", 32)
    try:
        asked_i = int(asked)
    except (TypeError, ValueError):
        asked_i = 32
    # 64/128 stay on today's 32-line Play (g/32). Packing a 64-grid into 32 slots would move the chip.
    n_had = asked_i if asked_i in (8, 16, 32) else 32
    g = float(max(0.0, min(1.0, float(p.get("fdn_g", 1.0))))) / float(n_had)
    decay_lock = bool(p.get("decay_lock"))
    decay_s = float(p.get("decay_s") or 0.0)
    grid = grid_bias_for_hadamard_n(n_had)
    humidity = float(p.get("humidity") or 0.0)
    air_lp = float(p.get("air_lp") if p.get("air_lp") is not None else 0.0)
    air_shelf = float(p.get("air_shelf") if p.get("air_shelf") is not None else 1.0)
    air_climate = str(p.get("air_climate") or "studio_20C_50RH")
    air_iso_on = p.get("air_iso")
    air_iso = True if air_iso_on is None else bool(air_iso_on)
    parity = bool(p.get("reaktor_parity"))
    # Reaktor snapshot is the 2011 one-pole only. ISO shelves stay off; air_lp stays.
    if parity:
        air_iso = False
    smooth_on = smooth_active(p, surfaces)
    move_ms = movement_peak_ms(p, surfaces)
    diffusion_master = float(p.get("diffusion_master") if p.get("diffusion_master") is not None else DIFFUSION_MASTER_LIVE)
    mic_response_hz = float(p.get("mic_response_hz") or 10000.0)
    ir_length_ms = float(p.get("ir_length_ms") if p.get("ir_length_ms") is not None else 1500.0)
    colour_sr = p.get("sample_rate")
    try:
        colour_sr_i = int(colour_sr) if colour_sr not in (None, "") else 0
    except (TypeError, ValueError):
        colour_sr_i = 0
    # Posted sound-card rate. mic_g stays on `sr`.
    rate = colour_sr_i if colour_sr_i >= 8000 else int(sr)
    binaural_on = str(p.get("mic_setup") or "") == "binaural"
    if binaural_on:
        from mic_colour.binaural import BinauralColour
        mic_colour = BinauralColour(
            str(p.get("binaural_preset") or "SADIE2_KU100"),
            rate,
        )
    else:
        mic_colour = MicColour(
            p.get("colour_mode"),
            p.get("mic_preset_l"),
            p.get("mic_preset_c"),
            p.get("mic_preset_r"),
            colour_sr_i if colour_sr_i >= 8000 else int(sr),
            hpf_engaged=bool(p.get("mic_hpf_engaged")),
            hpf_sides=p.get("mic_hpf_sides"),
            hpf_centre=p.get("mic_hpf_centre"),
            colour_impl=p.get("colour_impl") or "sos",
            hpf_l=p.get("mic_hpf_l"),
            hpf_r=p.get("mic_hpf_r"),
        )
    prep = direct_field_from_params(p)
    if binaural_on:
        stand = MicStand.binaural(
            cx=float(prep.mic_centre[0]),
            cy=float(prep.mic_centre[1]),
            cz=float(prep.mic_centre[2]),
            head_yaw_deg=float(p.get("head_yaw_deg") or 0.0),
            preset=str(p.get("binaural_preset") or "SADIE2_KU100"),
        )
    else:
        stand = MicStand.from_prepare(
            prep, car_omni=p.get("car_omni") or 1.0,
            pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
            yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
            family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
            polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
            centre_dz=p.get("centre_dz") or 0.0,
            ms_decode=bool(p.get("ms_decode")),
            capsule_mm=p.get("capsule_mm") or 17.0,
        )
    # Copy before place. Makeup rebuilds from this unplaced stand.
    stand_for_makeup = copy.copy(stand)
    if not binaural_on:
        stand = _place_stand(stand, p)
    shape = p.get("room_shape")

    def _shape_taps(source, stand_i):
        # Same call as _placed_taps. The pack is 32 lines. A longer list
        # would be cut on the way into the worklet.
        if poly_on(shape):
            return compute_poly_taps(
                room, source, stand_i, shape,
                c=c, n=n_had,
                include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            )
        return compute_taps(
            room, source, stand_i, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=n_had,
            include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            reaktor_parity=parity,
        )

    taps = _shape_taps(prep.source, stand)
    dff_per_tap = [tap_dff(t.n, surfaces, master=diffusion_master) for t in taps]
    solo_l = parse_solo(p.get("surfaces_solo"))
    mute_s = parse_mute(p.get("surfaces_mute"))
    peaking = live_peaking_banks(room, rate, c, DEFAULT_DEPTH)
    dffs_scale = diffusion_scale_from_room(room)
    buses = {}
    mean_ms_acc = 0.0
    mean_ms_n = 0
    for ch in ("l", "c", "r"):
        dly = fdn_delays_from_taps(taps, sr=rate, c=c, n=n_had, channel=ch)
        dffs = dffs_from_taps(taps, dff_per_tap, dffs_scale, n=n_had, channel=ch)
        if smooth_on:
            dffs = cap_dffs(dffs)
        mic_g = mic_g_from_taps(taps, n_had, ch, sr, res_hz=mic_response_hz)
        delay_ms = [1000.0 * float(d) / float(rate) for d in dly]
        inject = []
        air_g = []
        shelf = []
        shelf2 = []
        for i in range(n_had):
            t = taps[i % len(taps)]
            if ch == "l":
                amp = float(t.level_l)
            elif ch == "r":
                amp = float(t.level_r)
            else:
                amp = float(getattr(t, "level_c", 0.5 * (t.level_l + t.level_r)))
            # H-1: inject level is the true capsule. Line air stays at the stand.
            dist_m = _tap_distance(t, ch)
            amp *= tap_reflect_gain(t.n, surfaces)
            inject.append(amp)
            ag, _lp, sh, sh2 = _live_air_for_distance(
                dist_m, rate, humidity, air_lp, air_shelf, air_climate, air_iso,
            )
            air_g.append(ag)
            shelf.append(sh)
            shelf2.append(sh2)
            mean_ms_acc += delay_ms[i]
            mean_ms_n += 1
        buses[ch] = {
            "delay_ms": delay_ms,
            "inject": inject,
            "dffs": [float(x) for x in dffs],
            "mic_g": [float(x) for x in mic_g],
            "air_g": air_g,
            "air_lp": (max(0.0, min(1.0, air_lp)) if humidity > 0.0 else 0.0),
            "shelf": shelf,
            "shelf2": shelf2,
        }
    mean_ms = mean_ms_acc / float(max(1, mean_ms_n))
    if _treat_sets_length(p):
        mid = _treat_material_mid(p, room, surfaces)
        if mid > 0.05:
            # Local only. The posted lock stays what the client sent.
            decay_lock = True
            decay_s = mid
    if decay_lock and decay_s > 0.05:
        dly_mean = fdn_delays_from_taps(taps, sr=rate, c=c, n=n_had, channel="c")
        g = structure_gain_for_rt60(dly_mean, decay_s, rate, n_had) / float(n_had)
    lim = 0.99 / math.sqrt(float(n_had))
    g = float(max(0.0, min(lim, g)))
    # Decay lock: the loop runs lossless (g = 1/√N) and each line carries
    # 10^(-3 d/(sr T60)) (live_stereo.c line_t60). makeup/decay_out keep g.
    line_t60 = float(decay_s) if (decay_lock and decay_s > 0.05) else 0.0
    g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.0 else g
    di = direct_line_index(taps, n_had)
    _w_mix, mk_w, desk_section = _mix_pair(
        p,
        float(p.get("mic_gain_l", 1.0)),
        0.0 if binaural_on else float(p.get("mic_gain_c", 1.0)),
        float(p.get("mic_gain_r", 1.0)),
        float(p.get("mic_pan_l", -1.0)),
        float(p.get("mic_pan_c", 0.0)),
        float(p.get("mic_pan_r", 1.0)),
        float(p.get("mic_phase_l", 1.0)),
        float(p.get("mic_phase_c", 1.0)),
        float(p.get("mic_phase_r", 1.0)),
    )
    makeup = makeup_at_stand(
        stand_for_makeup, p, room, prep.source,
        c=c, grid=grid, hadamard_n=n_had,
        include_offaxis_shelf=mic_colour.include_offaxis_shelf,
        reaktor_parity=parity,
        surfaces=surfaces, g=g, ir_length_ms=ir_length_ms, sr=sr,
        weights=mk_w,
        room_shape=shape,
    )
    dm = direct_listen_gain(
        buses["l"]["inject"][di], buses["c"]["inject"][di], buses["r"]["inject"][di],
        weights=mk_w,
    )
    mean_t = mean_ms * 0.001
    loop = g * math.sqrt(float(n_had))
    decay_out = 0.0
    if 0.0 < loop < 0.999999 and mean_t > 1e-9:
        decay_out = mean_t * (math.log(0.001) / math.log(loop))
    if decay_lock and decay_s > 0.05:
        decay_out = decay_s
    two = bool(p.get("two_sources"))
    ga, gb = source_balance_gains(float(p.get("source_balance") or 0.0))
    source_b_out = None
    taps_b = None
    prep_b = None
    stand_b = None
    if two:
        if p.get("mirror_b"):
            sx_b, sy_b, sz_b = mirror_source_b(
                room[0], prep.source[0], prep.source[1], prep.source[2],
            )
        else:
            sx_b = room[0] - float(prep.source[0]) if p.get("sx_b") is None else float(p["sx_b"])
            sy_b = float(prep.source[1]) if p.get("sy_b") is None else float(p["sy_b"])
            sz_b = float(prep.source[2]) if p.get("sz_b") is None else float(p["sz_b"])
        sx_b = min(max(float(sx_b), 0.0), room[0])
        sy_b = min(max(float(sy_b), 0.0), room[1])
        sz_b = min(max(float(sz_b), 0.0), room[2])
        prep_b = direct_field_from_metres(
            room[0], room[1], room[2],
            sx=sx_b, sy=sy_b, sz=sz_b,
            mcx=float(prep.mcx), my=float(prep.mic_centre[1]), mcz=float(prep.mcz),
            space=float(p["space"]),
            diverg=float(p.get("diverg") if p.get("diverg") is not None else 1.0),
            toe_half_deg=p.get("toe_half_deg"),
            yaw_l_deg=p.get("yaw_l_deg"),
            yaw_r_deg=p.get("yaw_r_deg"),
        )
        if binaural_on:
            stand_b = MicStand.binaural(
                cx=float(prep_b.mic_centre[0]),
                cy=float(prep_b.mic_centre[1]),
                cz=float(prep_b.mic_centre[2]),
                head_yaw_deg=float(p.get("head_yaw_deg") or 0.0),
                preset=str(p.get("binaural_preset") or "SADIE2_KU100"),
            )
        else:
            stand_b = MicStand.from_prepare(
                prep_b, car_omni=p.get("car_omni") or 1.0,
                pattern_l=p.get("pattern_l"), pattern_c=p.get("pattern_c"), pattern_r=p.get("pattern_r"),
                yaw_l_deg=p.get("yaw_l_deg"), yaw_c_deg=p.get("yaw_c_deg"), yaw_r_deg=p.get("yaw_r_deg"),
                family_l=p.get("family_l"), family_c=p.get("family_c"), family_r=p.get("family_r"),
                polar_l=p.get("polar_l"), polar_c=p.get("polar_c"), polar_r=p.get("polar_r"),
                centre_dz=p.get("centre_dz") or 0.0,
                ms_decode=bool(p.get("ms_decode")),
                capsule_mm=p.get("capsule_mm") or 17.0,
            )
            stand_b = _place_stand(stand_b, p)
        taps_b = _shape_taps(prep_b.source, stand_b)
        dff_b = [tap_dff(t.n, surfaces, master=diffusion_master) for t in taps_b]
        for ch in ("l", "c", "r"):
            dly_b = fdn_delays_from_taps(taps_b, sr=rate, c=c, n=n_had, channel=ch)
            delay_ms_b = [1000.0 * float(d) / float(rate) for d in dly_b]
            inject_b = []
            air_g_b = []
            shelf_b = []
            shelf2_b = []
            n_tb = len(taps_b)
            for i in range(n_had):
                t = taps_b[i % n_tb]
                if ch == "l":
                    amp = float(t.level_l)
                elif ch == "r":
                    amp = float(t.level_r)
                else:
                    amp = float(getattr(t, "level_c", 0.5 * (t.level_l + t.level_r)))
                dist_m = _tap_distance(t, ch)
                amp *= tap_reflect_gain(t.n, surfaces)
                inject_b.append(amp)
                ag, _lp, sh, sh2 = _live_air_for_distance(
                    dist_m, rate, humidity, air_lp, air_shelf, air_climate, air_iso,
                )
                air_g_b.append(ag)
                shelf_b.append(sh)
                shelf2_b.append(sh2)
            dffs_b = dffs_from_taps(taps_b, dff_b, dffs_scale, n=n_had, channel=ch)
            if smooth_on:
                dffs_b = cap_dffs(dffs_b)
            buses[ch]["b"] = {
                "delay_ms": delay_ms_b,
                "inject": inject_b,
                "dffs": [float(x) for x in dffs_b],
                "air_g": air_g_b,
                "air_lp": buses[ch]["air_lp"],
                "shelf": shelf_b,
                "shelf2": shelf2_b,
            }
        sp = direct_capsule_spikes(taps[di % len(taps)])
        spb = direct_capsule_spikes(taps_b[di % len(taps_b)])
        for ch, idx in (("l", 0), ("c", 1), ("r", 2)):
            buses[ch]["direct_gain"] = sp[idx]
            buses[ch]["b"]["direct_gain"] = spb[idx]
        source_b_out = {"x": sx_b, "y": sy_b, "z": sz_b}
    if not (two and taps_b is not None) and has_side_strip(mk_w):
        sp = direct_capsule_spikes(taps[di % len(taps)])
        for ch, idx in (("l", 0), ("c", 1), ("r", 2)):
            buses[ch]["direct_gain"] = sp[idx]
    if binaural_on:
        colour_bank = mic_colour.bank_for(taps, taps_b, n_had, int(di))
    else:
        colour_bank = build_live_bank(
            mic_colour, taps, taps_b, n_had, int(di),
            p.get("sample_rate"), p.get("colour_rev") or "",
        )
    ic_hp = None
    ic_hm = None
    if binaural_on and str(p.get("binaural_tail_mode") or "diffuse_ic") == "diffuse_ic":
        from mic_colour.binaural import tail_fir
        fir = tail_fir(str(p.get("binaural_preset") or "SADIE2_KU100"), int(rate))
        if fir is not None:
            ic_hp = [float(x) for x in fir[0]]
            ic_hm = [float(x) for x in fir[1]]
    import source_radiation as _srcmod
    plan_a = _source_plan(
        p.get("source_radiation"), p.get("source_yaw"), p.get("source_pitch"),
        taps, prep, rate, p.get("source_size_m"),
    )
    plan_b = None
    if two and taps_b is not None:
        preset_b, yaw_b, pitch_b = _b_pose(
            p.get("source_radiation"), p.get("source_yaw"), p.get("source_pitch"),
            p.get("source_radiation_b"), p.get("source_yaw_b"), p.get("source_pitch_b"),
            p.get("mirror_b"),
        )
        plan_b = _source_plan(
            preset_b, yaw_b, pitch_b,
            taps_b, prep_b, rate, p.get("source_size_m"),
        )
    src_rad = _srcmod.pack_play(plan_a, plan_b)
    early_gate = None
    if solo_l is not None or mute_s:
        bank_b = taps_b if taps_b is not None else taps
        early_gate = []
        for _bus in ("l", "c", "r"):
            early_gate += _early_gate_row(taps, n_had, solo_l, mute_s)
            early_gate += _early_gate_row(bank_b, n_had, solo_l, mute_s)
    out = {
        "ok": True,
        "n": n_had,
        "g": g_loop,
        "g_decay": g,
        "line_t60": line_t60,
        # Headroom decision 6: fixed Play loop trim folded into the FDN send.
        "fdn_wet": float(p.get("fdn_wet", 1.0)) * loop_level_trim_lin("play", line_t60 > 0.0),
        "loop_trim_db": loop_level_trim_db("play", line_t60 > 0.0),
        "direct_wet": float(p.get("direct_wet", 1.0)),
        "early_wet": float(p.get("early_wet", 0.0)),
        "dry_gain": float(p.get("dry_gain", 0.0)),
        "mic_gain_l": float(p.get("mic_gain_l", 1.0)),
        "mic_gain_c": 0.0 if binaural_on else float(p.get("mic_gain_c", 1.0)),
        "mic_gain_r": float(p.get("mic_gain_r", 1.0)),
        "mic_pan_l": float(p.get("mic_pan_l", -1.0)),
        "mic_pan_c": float(p.get("mic_pan_c", 0.0)),
        "mic_pan_r": float(p.get("mic_pan_r", 1.0)),
        "mic_phase_l": float(p.get("mic_phase_l", 1.0)),
        "mic_phase_c": float(p.get("mic_phase_c", 1.0)),
        "mic_phase_r": float(p.get("mic_phase_r", 1.0)),
        "direct_index": int(di),
        "hadamard_n": n_had,
        # 0 = z^-1 in both (D3, 2 Oct). 1 = plain Hadamard (reaktor_parity).
        "loop_semantics": 1 if parity else 0,
        # Shared tail is Live-only. Parity and binaural never set it.
        "shared_tail": bool(p.get("shared_tail")) and not binaural_on and not parity,
        "solo_mute": solo_mute_gates(p.get("surfaces_solo"), p.get("surfaces_mute")),
        "makeup": makeup,
        "direct_makeup": dm,
        "max_delay_ms": MAX_DELAY_MS,
        "mean_delay_ms": mean_ms,
        "decay_s": decay_out,
        "peaking": peaking,
        "buses": buses,
        "source": {"x": prep.source[0], "y": prep.source[1], "z": prep.source[2]},
        "two_sources": two,
        "gain_a": ga,
        "gain_b": gb,
        "source_b": source_b_out,
        "colour_mode": mic_colour.mode,
        "colour_notice": getattr(mic_colour, "notice", ""),
        "colour_impl": mic_colour.impl,
        "mic_preset_l": mic_colour.preset_ids["l"],
        "mic_preset_c": mic_colour.preset_ids["c"],
        "mic_preset_r": mic_colour.preset_ids["r"],
        "mic_hpf_sides": bool(mic_colour.hpf_sides),
        "mic_hpf_centre": bool(mic_colour.hpf_centre),
        "colour": colour_bank,
        "ic_hp": ic_hp,
        "ic_hm": ic_hm,
        "src_rad": src_rad,
        "tag": "ASSUMED live FDN — same delays/inject/Dffs/mic/air/peaking as offline IR",
    }
    if early_gate is not None:
        out["early_gate"] = early_gate
    if desk_section is not None:
        out["desk_w"] = desk_section
    # reaktor_parity has no face shape on the wet. Flat cards omit the block.
    surf_tail, surf_fit = _play_surf_cascade(
        surfaces, taps, taps_b, rate, n_had, parity,
    )
    out["surf_fit"] = surf_fit
    if surf_tail is not None:
        out["surf_cascade"] = surf_tail
    if move_ms > 0.0 and int(n_had) == 32:
        out["movement_ms"] = float(move_ms)
    surf_pack = _live_surf_pack(
        p, room, surfaces, taps, rate, n_had, line_t60, peaking,
        taps_b=(taps_b if (two and taps_b is not None) else None),
    )
    if surf_pack:
        out["surf_on"] = int(surf_pack.get("surf_on") or 0)
        if surf_pack.get("surf_stab") is not None:
            out["surf_stab"] = surf_pack["surf_stab"]
        if surf_pack.get("surf_refused"):
            out["surf_refused"] = surf_pack["surf_refused"]
        if out["surf_on"]:
            out["surf_sos"] = surf_pack["surf_sos"]
            out["surf_keep"] = surf_pack["surf_keep"]
            out["surf_peaks"] = surf_pack["surf_peaks"]
            if surf_pack.get("surf_sos_b") is not None:
                out["surf_sos_b"] = surf_pack["surf_sos_b"]
    _tick = (
        p.get("prox_l", True),
        p.get("prox_c", True),
        p.get("prox_r", True),
    )
    g_a = capsule_gains(stand, prep.source, _tick[0], _tick[1], _tick[2])
    sc_a = scales_from_taps(taps, n_had)
    if two and taps_b is not None and stand_b is not None and prep_b is not None:
        g_b = capsule_gains(stand_b, prep_b.source, _tick[0], _tick[1], _tick[2])
        sc_b = scales_from_taps(taps_b, n_had)
    else:
        g_b = (0.0, 0.0, 0.0)
        sc_b = scales_from_taps(None)
    packed = pack_prox(g_a, g_b, sc_a, sc_b)
    # Far scenes stay off the side channel. The live MD5 is the room blob.
    if not prox_is_bypass(packed):
        out["prox"] = packed
    # ROOMTONE. Omitted when any first axial is under 30 Hz, so the boot
    # room and the five TLAW goldens stay the old bytes.
    harm = harmonic_pack(room, rate, c, line_t60)
    if harm is not None:
        out["harm"] = harm
    # Present only when the key is on. An absent field keeps the live MD5.
    if bool(p.get("sub_hp")):
        out["sub_hp"] = [float(v) for v in sub_hp_coeffs(rate)]
    # Bloom is absent unless Amount, predelay, or a pre is on. The off
    # path keeps the live MD5. Play reads the lower Play factors.
    import bloom_dsp as _bloom
    if _bloom.bloom_is_on(p):
        spec = _bloom.design(p, rate)
        if spec is not None:
            if float(spec.get("amount_db") or 0.0) > 0.0:
                out["bloom"] = _bloom.pack_coeffs(spec, play=True)
            if int(spec.get("predelay_n") or 0) > 0:
                out["predelay_n"] = int(spec["predelay_n"])
            pre = _bloom.pack_pre(spec, play=True)
            if pre:
                out["pre_colour"] = pre
    # Section 13. One field, only while an array or room strip is on.
    # Place lives inside that field. An off strip adds nothing.

    def _side_row(prefix):
        body = {
            "bloom_preset": str(p.get(prefix + "_preset") or "natural"),
            "bloom_amount": float(p.get(prefix + "_amount") or 0.0),
            "pre_colour": str(p.get(prefix + "_pre") or "off"),
            "pre_drive_db": float(p.get(prefix + "_drive_db") or 0.0),
        }
        if not _bloom.bloom_is_on(body):
            return None
        spec = _bloom.design(body, rate)
        if spec is None:
            return None
        comp = _bloom.pack_coeffs(spec, play=True) if float(spec.get("amount_db") or 0.0) > 0.0 else None
        pre = _bloom.pack_pre(spec, play=True)
        if not comp and not pre:
            return None
        return comp, pre

    def _side_pad(src, n):
        row = [0.0] * n
        if src:
            for i, v in enumerate(list(src)[:n]):
                row[i] = float(v)
        return row

    def _side_emit(row):
        if not row:
            return [0.0] + [0.0] * 80 + [0.0] + [0.0] * 25
        comp, pre = row
        return [1.0 if comp else 0.0] + _side_pad(comp, 80) + [1.0 if pre else 0.0] + _side_pad(pre, 25)

    array_row = _side_row("array")
    room_row = _side_row("room")
    if array_row or room_row:
        def _place_flag(ch):
            return 1.0 if str(p.get("place_" + ch) or "array").strip().lower() == "room" else 0.0
        out["side"] = (
            [_place_flag("l"), _place_flag("c"), _place_flag("r")]
            + _side_emit(array_row)
            + _side_emit(room_row)
        )
    # Present only for a polygon preset. Absent or box keeps the live MD5.
    if poly_on(shape):
        out["room_shape"] = normalize_shape(shape)
    # Present only when the key is on. An absent field keeps the live MD5.
    if bool(p.get("offaxis_tail")):
        from mic_colour.tail_diffuse import design_pack as _tail_design

        out["offaxis_tail"] = _tail_design(
            (
                mic_colour.preset_ids["l"],
                mic_colour.preset_ids["c"],
                mic_colour.preset_ids["r"],
            ),
            rate,
            (p.get("polar_l"), p.get("polar_c"), p.get("polar_r")),
        )
    return out


def _pb_num(v, d: float) -> float:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return d
    if n != n or n in (float("inf"), float("-inf")):
        return d
    return n


def _pb_shelf(a: list, sh) -> None:
    if sh and sh.get("on"):
        a += [1.0, _pb_num(sh.get("b0"), 1.0), _pb_num(sh.get("b1"), 0.0),
              _pb_num(sh.get("b2"), 0.0), _pb_num(sh.get("a1"), 0.0), _pb_num(sh.get("a2"), 0.0)]
    else:
        a += [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]


def _pb_arr(a: list, src, n: int, d: float) -> None:
    for i in range(n):
        v = src[i] if (src is not None and i < len(src)) else None
        a.append(v if isinstance(v, (int, float)) and not isinstance(v, bool) else d)


def _pb_side(a: list, bus, di: int) -> None:
    src = bus or {}
    shelf = src.get("shelf") or []
    _pb_arr(a, src.get("delay_ms"), 32, 20.0)
    _pb_arr(a, src.get("inject"), 32, 0.0)
    _pb_arr(a, src.get("dffs"), 32, 0.0)
    _pb_arr(a, src.get("air_g"), 32, 0.0)
    a.append(_pb_num(src.get("air_lp"), 0.0))
    for i in range(32):
        _pb_shelf(a, shelf[i] if i < len(shelf) else None)
    dl = src.get("delay_ms")
    dms = dl[di] if dl and isinstance(dl[di], (int, float)) and not isinstance(dl[di], bool) else 20.0
    a += [float(dms), _pb_num(src.get("direct_gain"), 1.0)]


def _pb_src(d: dict) -> list:
    """SRC_RAD payload. Anything other than 716 floats stays an empty section."""
    src = d.get("src_rad") if isinstance(d, dict) else None
    if not isinstance(src, (list, tuple)) or len(src) != 716:
        return []
    return [_pb_num(v, 0.0) for v in src]


def _pb_surf(d: dict) -> list:
    """SURF. Length 0: no Solo/Mute and no cascade. Length 192: gates only.

    A cascade is the 192 gates (ones, when Solo/Mute is off) then the v1 tail
    [version, K_max, per bank per line k_i and K_max*5 coefficients]. The tail
    is omitted when every line is a bypass, so flat cards stay the old length.
    """
    g = d.get("early_gate") if isinstance(d, dict) else None
    gates = []
    if isinstance(g, (list, tuple)) and len(g) == 192:
        gates = [_pb_num(v, 1.0) for v in g]
    cas = d.get("surf_cascade") if isinstance(d, dict) else None
    tail = []
    if isinstance(cas, (list, tuple)) and len(cas) >= 2:
        tail = [_pb_num(v, 0.0) for v in cas]
    if tail:
        if not gates:
            gates = [1.0] * 192
        return gates + tail
    return gates


def pack_blob_v2(params: dict) -> list:
    """v2 room blob. Same layout as fdn_worklet.js packRoom and the harness packer.

    CORE is the magic-1 body without the magic, plus hadamard_n, loop_semantics
    (0 = z^-1 in both, D3, 2 Oct; 1 = plain Hadamard under reaktor_parity),
    and solo_mute[6]. AIR is the second shelf (1152) or empty. SURF is empty
    (bit-exact), 192 early-gate floats, or those 192 plus a v1 cascade.
    SCATTER stays empty.
    SRC_RAD is 716 floats, or empty when the source is omni.
    Section 6 is one float, and only when shared_tail is true.
    Section 7 is six speaker weights, and only when desk_w is set.
    Section 8 is one float, peak depth in ms, and only when movement_ms > 0.
    Section 9 is five sub_hp coefficients, and only when that list is present.
    A default pack omits 7, 8, and 9.
    """
    d = params or {}
    di = int(_pb_num(d.get("direct_index"), 10.0))
    di = max(0, min(31, di))
    core: list = []
    core += [_pb_num(d.get("g"), 0.03), _pb_num(d.get("fdn_wet"), 1.0), _pb_num(d.get("direct_wet"), 1.0),
             _pb_num(d.get("early_wet"), 0.0), _pb_num(d.get("dry_gain"), 0.0), _pb_num(d.get("makeup"), 1.0),
             _pb_num(d.get("gain_a"), 1.0), _pb_num(d.get("gain_b"), 1.0)]
    core += [1.0 if d.get("two_sources") else 0.0, 1.0 if d.get("colour_on") else 0.0,
             1.0 if d.get("mono") else 0.0, float(di), _pb_num(d.get("max_delay_ms"), 1000.0),
             1.0 if d.get("snap", True) else 0.0, 0.0]
    for i, k in enumerate("lcr"):
        core += [_pb_num(d.get("mic_gain_" + k), 1.0),
                 _pb_num(d.get("mic_pan_" + k), (-1.0, 0.0, 1.0)[i]),
                 _pb_num(d.get("mic_phase_" + k), 1.0)]
    peaks = d.get("peaking") or [None, None, None]
    for i in range(3):
        pk = peaks[i] if i < len(peaks) else None
        if pk and pk.get("on"):
            core += [1.0, _pb_num(pk.get("b0"), 1.0), _pb_num(pk.get("b1"), 0.0),
                     _pb_num(pk.get("b2"), 0.0), _pb_num(pk.get("a1"), 0.0), _pb_num(pk.get("a2"), 0.0)]
        else:
            core += [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    buses = d.get("buses") or {}
    for k in "lcr":
        bus = buses.get(k)
        _pb_side(core, bus, di)
        _pb_side(core, bus.get("b") if bus else None, di)
    core.append(_pb_num(d.get("line_t60"), 0.0))
    sm = d.get("solo_mute") or []
    hn = d.get("hadamard_n")
    if hn is None:
        hn = d.get("n")
    core.append(_pb_num(hn, 32.0))
    # 0 = z^-1 in both (D3, 2 Oct). Play already delays g·H·y by one sample.
    core.append(_pb_num(d.get("loop_semantics"), 0.0))
    for i in range(6):
        core.append(_pb_num(sm[i] if i < len(sm) else 1.0, 1.0))
    air: list = []
    live = False
    for k in "lcr":
        src = buses.get(k)
        for _ in range(2):
            if not src:
                break
            for sh in (src.get("shelf2") or []):
                if sh and sh.get("on"):
                    live = True
            src = src.get("b") if isinstance(src, dict) else None
    if live:
        for k in "lcr":
            bus = buses.get(k) or {}
            shelf = bus.get("shelf2") or []
            for i in range(32):
                _pb_shelf(air, shelf[i] if i < len(shelf) else None)
            b = bus.get("b") or {}
            shelf = b.get("shelf2") or []
            for i in range(32):
                _pb_shelf(air, shelf[i] if i < len(shelf) else None)
    parts = [(1, core), (2, air), (3, _pb_surf(d)), (4, []), (5, _pb_src(d))]
    if d.get("shared_tail"):
        parts.append((6, [1.0]))
    desk_w = d.get("desk_w")
    if isinstance(desk_w, (list, tuple)) and len(desk_w) == 6:
        parts.append((7, [_pb_num(v, 0.0) for v in desk_w]))
    move_pack = _pb_num(d.get("movement_ms"), 0.0)
    if move_pack > 0.0:
        parts.append((8, [move_pack]))
    hp = d.get("sub_hp")
    if isinstance(hp, (list, tuple)) and len(hp) == 5:
        parts.append((9, [_pb_num(v, 0.0) for v in hp]))
    tail = d.get("offaxis_tail")
    if isinstance(tail, (list, tuple)) and len(tail) == 45:
        parts.append((14, [_pb_num(v, 0.0) for v in tail]))
    off = 5 + 4 * len(parts)
    directory: list = []
    body: list = []
    for sid, payload in parts:
        directory += [sid, off, len(payload), 1]
        if payload:
            body += payload
            off += len(payload)
    blob = [2.0, 2.0, 0.0, float(len(parts)), 0.0] + [float(x) for x in directory] + [float(x) for x in body]
    blob[4] = float(len(blob))
    return blob


def default_out_path() -> Path:
    return Path(__file__).resolve().parent / "renders" / "out.wav"


_STAMP_RE = re.compile(r"^out_\d{8}_\d{6}(?:_\d+)?\.wav$")
_preview_path: Optional[Path] = None


def publish_out_copy(out: Path) -> Path:
    """Copy the newest render to out_YYYYMMDD_HHMMSS.wav and keep the last 10 stamps.

    out.wav itself is the newest render. Stamp names that collide in the same
    second get a numeric suffix. Other files in the folder are left alone.
    """
    out = Path(out)
    renders = out.parent
    renders.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = renders / f"out_{stamp}.wav"
    n = 1
    while dest.exists():
        dest = renders / f"out_{stamp}_{n}.wav"
        n += 1
    shutil.copy2(out, dest)
    stamps = sorted(
        (p for p in renders.glob("out_*.wav") if _STAMP_RE.match(p.name)),
        key=lambda p: (p.stat().st_mtime_ns, p.name),
    )
    others = [p for p in stamps if p.resolve() != dest.resolve()]
    # dest plus the nine newest others: at most 10 stamp files, and out.wav is separate.
    for old in others[: max(0, len(others) - 9)]:
        old.unlink(missing_ok=True)
    return dest


def replace_preview(src: Path) -> Path:
    """Copy src to a new temp wav and delete the previous preview."""
    global _preview_path
    prev = _preview_path
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    shutil.copy2(src, tmp.name)
    path = Path(tmp.name)
    _preview_path = path
    if prev is not None and prev.resolve() != path.resolve():
        prev.unlink(missing_ok=True)
    return path


def preview_path() -> Optional[Path]:
    return _preview_path


def drop_preview() -> None:
    """Delete the temp preview. Called when the next render replaces it, and at shutdown."""
    global _preview_path
    if _preview_path is not None:
        _preview_path.unlink(missing_ok=True)
        _preview_path = None


atexit.register(drop_preview)
