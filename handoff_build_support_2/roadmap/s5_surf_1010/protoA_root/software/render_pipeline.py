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
_SOFT = Path(__file__).resolve().parent
_ENGINE = _SOFT / "engine"
if str(_SOFT) not in sys.path:
    sys.path.insert(0, str(_SOFT))
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

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
    rbj_lowpass,
)
from fdn import (  # noqa: E402
    FDN,
    FDN32,
    build_inject_from_taps,
    propose_fdn_delays_samples,
    fdn_delays_from_taps,
    dffs_from_taps,
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

from surface_colour import (  # noqa: E402
    DEFAULT_DIFFUSION_SEED,
    DEFAULT_LAMBDA_REF_M,
    colour_from_stereo,
    default_surfaces,
    apply_surface_to_buffer,
    jittered_distance,
    mirror_x_partner_index,
    _MIRROR_X_LETTER,
    card_structure_dif,
    parse_lambda_ref,
    parse_surfaces,
    parse_solo,
    parse_mute,
    image_in_early,
    solo_mute_gates,
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
    # Mirrored source B reuses A's jitter draw: partner image order, side mic
    # swapped, side-wall letters swapped. One source is unchanged.
    partner = mirror_x_partner_index([tuple(t.n) for t in taps]) if mirror_x else None
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
            h_l = h_r = {}
            if partner is not None:
                h_l = dict(hash_index=partner[ti], hash_mic="R", hash_letters=_MIRROR_X_LETTER)
                h_r = dict(hash_index=partner[ti], hash_mic="L", hash_letters=_MIRROR_X_LETTER)
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
        bl = _colour_apply(colour, bl, float(t.theta_l), "l")
        br = _colour_apply(colour, br, float(t.theta_r), "r")
        Lch += bl
        Rch += br
    return Lch, Rch


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


def _scale_inject_reflect(inj, taps, surfaces, sr=None) -> None:
    if inj is None or taps is None or not surfaces:
        return
    n_t = len(taps)
    n_lines = int(inj.shape[1]) if hasattr(inj, "shape") else 0
    if n_t <= 0 or n_lines <= 0:
        return
    for i in range(n_lines):
        g = tap_reflect_gain(taps[i % n_t].n, surfaces)
        inj[:, i] *= g
        # S5 PROTOTYPE A (D-UI26=A, box only): per-face shape on the FDN inject.
        if g != 0.0 and sr:
            st = _surf_rel_stages(surfaces, surfaces_hit_by_n(taps[i % n_t].n), float(sr))
            if st:
                import surface_colour as _sc
                inj[:, i] = _sc.cascade_biquads(inj[:, i], st)


def _surf_rel_stages(surfaces, letters, sr):
    """Absorb peaking relative to the card mean (mean already in tap_reflect_gain) + EQ."""
    import surface_colour as _sc
    out = []
    for L in letters:
        s = surfaces.get(L) if isinstance(surfaces, dict) else None
        if not isinstance(s, dict) or s.get("muted"):
            continue
        absorb = s.get("absorb") or []
        if absorb:
            m = max(0.0, min(0.95, sum(float(x) for x in absorb) / float(len(absorb))))
            hz_list = s.get("absorb_hz") or list(_sc.ABSORB_BAND_HZ)
            for j, hz in enumerate(hz_list):
                if j >= len(absorb):
                    break
                f0 = float(hz)
                if f0 <= 0.0 or f0 >= sr * 0.49:
                    continue
                gdb = _sc._absorb_to_db(float(absorb[j])) - _sc._absorb_to_db(m)
                if abs(gdb) < 0.01:
                    continue
                out.append(_sc.rbj_peaking(sr, f0, 0.9, gdb))
        flat = dict(s); flat["absorb"] = []
        out.extend(_sc.surface_filter_stages({L: flat}, [L], sr))
    return out


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
    n_t = len(taps) if taps is not None else 0
    dff_per_tap = [
        tap_dff(t.n, surfaces, master=diffusion_master) for t in taps
    ] if n_t else []
    buses = {
        "l": np.zeros(n_samp, dtype=np.float64),
        "c": np.zeros(n_samp, dtype=np.float64),
        "r": np.zeros(n_samp, dtype=np.float64),
    }
    for ch, out in buses.items():
        dly = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_lines, channel=ch)
        inj = build_inject_from_taps(
            taps, n_samp, sr, c, n_lines, channel=ch, humidity=humidity,
            air_lp=air_lp, air_shelf=air_shelf,
            air_climate=air_climate, air_iso=air_iso,
        )
        _scale_inject_reflect(inj, taps, surfaces, sr)
        if src_diffuse is not None and not src_diffuse.bypass:
            from source_radiation import apply_coef
            for i in range(n_lines):
                inj[:, i] = apply_coef(inj[:, i], src_diffuse)
        dffs = dffs_from_taps(
            taps, dff_per_tap, diffusion_scale_from_room(room), n=n_lines, channel=ch,
        )
        mic_g = None
        if apply_mic:
            mic_g = mic_g_from_taps(taps, n_lines, ch, sr, res_hz=mic_response_hz)
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
        )
        poly = fdn.process_block_poly(inj)
        # Headroom decision 6. F2 applies while line absorption is on.
        # D3b: the F3 row applies on Render too, same total trim as Play.
        poly *= loop_level_trim_lin("render", float(line_t60) > 0.05)
        if colour is not None and colour.measured and n_t:
            for i in range(n_lines):
                col = poly[:, i]
                y = colour.apply(col, _bus_theta(taps[i % n_t], ch), ch)
                if y is not col:
                    poly[:, i] = y
        out += np.sum(poly, axis=1)
    if weights is None:
        return mixer_lcr_fold(buses["l"], buses["r"], buses["c"])
    return apply_capsule_weights(buses["l"], buses["c"], buses["r"], weights)


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


def direct_capsule_spikes(tap) -> Tuple[float, float, float]:
    """ASSUMED two-source direct level. Hottest capsule stays 1.

    Pattern only (cardioid / fig-8 sign). Not 1/r². One source stays (1, 1, 1).
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


def render_listen_direct_ir(taps, sr, length_ms, n_lines=32, weights=None, colour=None, spikes=None, src_direct=None):
    """Delayed spikes, capsule weights, × 0.55.

    Default weights are the 477 fold (L+0.5·C, R+0.5·C).
    Mic colour, when on, filters Ld/Cd/Rd before that fold.
    One source uses spike amplitude 1. Two sources pass pattern spikes.
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
):
    weights = capsule_speaker_weights(
        mic_gain_l, mic_gain_c, mic_gain_r,
        mic_pan_l, mic_pan_c, mic_pan_r,
        mic_phase_l, mic_phase_c, mic_phase_r,
    )
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
        )
    else:
        Le = np.zeros(1, dtype=np.float64)
        Re = np.zeros(1, dtype=np.float64)
    Ld, Rd = render_listen_direct_ir(
        taps, sr, fdn_ms, n_lines=hadamard_n, weights=weights, colour=colour,
        src_direct=None if src_plan is None else src_plan.direct,
    )
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
    )
    n = max(len(Le), len(Lf), len(Ld))
    def _pad(a):
        if len(a) >= n:
            return a
        o = np.zeros(n, dtype=np.float64)
        o[: len(a)] = a
        return o
    Ld, Rd, Lf, Rf, Le, Re = _pad(Ld), _pad(Rd), _pad(Lf), _pad(Rf), _pad(Le), _pad(Re)
    inj_l, inj_c, inj_r = _inject_levels(taps, hadamard_n, surfaces)
    mk = ir_rms_makeup_from_inject(
        inj_l, inj_c, inj_r, fdn_g, hadamard_n, fdn_ms, sr,
    )
    Lf, Rf = Lf * mk, Rf * mk
    # Early FIR is left-capsule / right-capsule, no centre bus.
    # Default weights leave it unchanged. Centre gain does not scale it.
    eL = weights["ll"] * Le + weights["rl"] * Re
    eR = weights["lr"] * Le + weights["rr"] * Re
    Le, Re = eL * mk, eR * mk
    L = float(fdn_wet) * Lf + float(direct_wet) * Ld + float(early_wet) * Le
    R = float(fdn_wet) * Rf + float(direct_wet) * Rd + float(early_wet) * Re
    L, R, _peak, _s = clip_guard(L, R, peak_ceil=1.2)
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
    mic_preset_l: str = "ShureSM57",
    mic_preset_c: str = "ShureSM57",
    mic_preset_r: str = "ShureSM57",
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
    )
    surfaces = parse_surfaces(surfaces) if surfaces is not None else default_surfaces()
    # Solo/Mute colours the early field only. FDN inject, Dffs and makeup
    # stay on the un-gated cards.
    seed = int(diffusion_seed)
    lam = parse_lambda_ref(lambda_ref)
    n_dry = len(dry)

    # Split IR length: early gets min(90, ir_len); FDN uses full ir_len (ASSUMED split)
    early_ms = min(DEFAULT_EARLY_MS, float(ir_length_ms))
    fdn_ms = max(early_ms, float(ir_length_ms))

    wall_cache = precompute_wall_peaking_coeffs(room, sr, c, DEFAULT_DEPTH)
    ap_cache = {
        0: None,
        1: allpass_ir_for_stages(1, sr),
        2: allpass_ir_for_stages(2, sr),
    }
    n_had = normalize_hadamard_n(hadamard_n)
    # UI fdn_g is Structure Gain 0–1; loop scale is Gain/N (215).
    g = float(np.clip(fdn_g, 0.0, 1.0)) / float(n_had)
    grid = grid_bias_for_hadamard_n(n_had)
    delays = propose_fdn_delays_samples(W, H, L, sr=sr, c=c, n=n_had)  # fallback; overwritten from taps

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
            family_l=family_l, family_c=family_c, family_r=family_r,
            polar_l=polar_l, polar_c=polar_c, polar_r=polar_r,
            centre_dz=centre_dz,
            ms_decode=ms_decode,
            capsule_mm=capsule_mm,
        )
        taps = compute_taps(
            room, prep.source, stand, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=n_had,
            include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            reaktor_parity=reaktor_parity,
        )
        return taps, prep

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
        stand_i = MicStand.from_prepare(
            prep_i, car_omni=car_omni,
            pattern_l=pattern_l, pattern_c=pattern_c, pattern_r=pattern_r,
            yaw_l_deg=yaw_l_deg, yaw_c_deg=yaw_c_deg, yaw_r_deg=yaw_r_deg,
            family_l=family_l, family_c=family_c, family_r=family_r,
            polar_l=polar_l, polar_c=polar_c, polar_r=polar_r,
            centre_dz=centre_dz,
            ms_decode=ms_decode,
            capsule_mm=capsule_mm,
        )
        taps_i = compute_taps(
            room, prep_i.source, stand_i, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=n_had,
            include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            reaktor_parity=reaktor_parity,
        )
        return taps_i, prep_i

    def taps_at_metres():
        sy_v = float(my) if sy is None else float(sy)
        return taps_for(float(sx), sy_v, float(sz))

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
            g_split = g
            line_t60 = 0.0
            if decay_lock and float(decay_s) > 0.05:
                g_split = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
                lim = 0.99 / math.sqrt(float(n_had))
                g_split = float(max(0.0, min(lim, g_split)))
                line_t60 = float(decay_s)
            # Loop runs lossless when line absorption carries the decay; makeup keeps g_split.
            g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.05 else g_split
            weights = capsule_speaker_weights(
                mic_gain_l, mic_gain_c, mic_gain_r,
                mic_pan_l, mic_pan_c, mic_pan_r,
                mic_phase_l, mic_phase_c, mic_phase_r,
            )
            inj_l, inj_c, inj_r = _inject_levels(taps, n_had, surfaces)
            mk = ir_rms_makeup_from_inject(
                inj_l, inj_c, inj_r, g_split, n_had, fdn_ms, sr,
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

            def direct_early(taps_src, src_plan, mirror_x=False):
                di_src = direct_line_index(taps_src, n_had)
                spikes = None
                if taps_src and 0 <= di_src < len(taps_src):
                    spikes = direct_capsule_spikes(taps_src[di_src])
                Ld, Rd = render_listen_direct_ir(
                    taps_src, sr, fdn_ms, n_lines=n_had, weights=weights, colour=mic_colour,
                    spikes=spikes,
                    src_direct=None if src_plan is None else src_plan.direct,
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

            deA_L, deA_R = direct_early(taps, plan_a, False)
            deB_L, deB_R = direct_early(taps_b, plan_b, bool(mirror_b))

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
            n_dry_b = len(down)
            keep = n_dry_b + int(sr * fdn_ms * 0.001)
            yL = yL[:keep]
            yR = yR[:keep]
            dry_pad = np.zeros(keep, dtype=np.float64)
            dry_pad[:n_dry_b] = down
            mix_L = float(dry_gain) * dry_pad + yL
            mix_R = float(dry_gain) * dry_pad + yR
            mix_L, mix_R, peak, scale = clip_guard(mix_L, mix_R)
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
            }
            if progress_cb:
                progress_cb(1.0)
            return mix_L, mix_R, info

        if sx is not None and sz is not None and mcz is not None:
            taps, prep = taps_at_metres()
        else:
            taps, prep = taps_at(sox, soz)
        delays = fdn_delays_from_taps(taps, sr=sr, c=c, n=n_had)
        line_t60 = 0.0
        if decay_lock and float(decay_s) > 0.05:
            g = structure_gain_for_rt60(delays, float(decay_s), sr, n_had) / float(n_had)
            lim = 0.99 / math.sqrt(float(n_had))
            g = float(max(0.0, min(lim, g)))
            line_t60 = float(decay_s)
        src_plan = _source_plan(
            source_radiation, source_yaw, source_pitch, taps, prep, sr, source_size_m,
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
        mix_L, mix_R, peak, scale = clip_guard(mix_L, mix_R)
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
    mix_L, mix_R, peak, scale = clip_guard(mix_L, mix_R, peak_ceil=1.2)
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
    }
    return mix_L, mix_R, info


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


def live_fdn_params(
    p: dict,
    sr: int = SAMPLE_RATE_HZ,
) -> dict:
    """Compact running-FDN coefficients for the browser worklet. ASSUMED live path.

    Same geometry / inject / Dffs / cut-only peaking as the offline IR.
    Air 1-pole + shelf run in the worklet (not baked into inject). Play
    honours hadamard_n 8, 16, and 32. 64 and 128 stay on the 32-line network.
    Makeup is running Mixer level (not IR-window RMS).
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
    taps = compute_taps(
        room, prep.source, stand, c=c, grid=grid, origin="corner",
        z_face_4l=False, hadamard_n=n_had,
        include_offaxis_shelf=mic_colour.include_offaxis_shelf,
        reaktor_parity=parity,
    )
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
                dist_m = float(t.distance_l)
            elif ch == "r":
                amp = float(t.level_r)
                dist_m = float(t.distance_r)
            else:
                amp = float(getattr(t, "level_c", 0.5 * (t.level_l + t.level_r)))
                dist_m = float(getattr(t, "distance_c", 0.5 * (t.distance_l + t.distance_r)))
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
    makeup = ir_rms_makeup_from_inject(
        buses["l"]["inject"], buses["c"]["inject"], buses["r"]["inject"],
        g, n_had, ir_length_ms, sr,
    )
    dm = direct_listen_gain(
        buses["l"]["inject"][di], buses["c"]["inject"][di], buses["r"]["inject"][di],
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
        taps_b = compute_taps(
            room, prep_b.source, stand_b, c=c, grid=grid, origin="corner",
            z_face_4l=False, hadamard_n=n_had,
            include_offaxis_shelf=mic_colour.include_offaxis_shelf,
            reaktor_parity=parity,
        )
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
                    dist_m = float(t.distance_l)
                elif ch == "r":
                    amp = float(t.level_r)
                    dist_m = float(t.distance_r)
                else:
                    amp = float(getattr(t, "level_c", 0.5 * (t.level_l + t.level_r)))
                    dist_m = float(getattr(t, "distance_c", 0.5 * (t.distance_l + t.distance_r)))
                amp *= tap_reflect_gain(t.n, surfaces)
                inject_b.append(amp)
                ag, _lp, sh, sh2 = _live_air_for_distance(
                    dist_m, rate, humidity, air_lp, air_shelf, air_climate, air_iso,
                )
                air_g_b.append(ag)
                shelf_b.append(sh)
                shelf2_b.append(sh2)
            dffs_b = dffs_from_taps(taps_b, dff_b, dffs_scale, n=n_had, channel=ch)
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
    """SURF v0: early_gate[3 buses][32] for bank A, then bank B. Empty = no Solo/Mute."""
    g = d.get("early_gate") if isinstance(d, dict) else None
    if not isinstance(g, (list, tuple)) or len(g) != 192:
        return []
    return [_pb_num(v, 1.0) for v in g]


def pack_blob_v2(params: dict) -> list:
    """v2 room blob. Same layout as fdn_worklet.js packRoom and the harness packer.

    CORE is the magic-1 body without the magic, plus hadamard_n, loop_semantics
    (0 = z^-1 in both, D3, 2 Oct; 1 = plain Hadamard under reaktor_parity),
    and solo_mute[6]. AIR is the second shelf (1152) or empty. SURF is the
    early gate (192) or empty (no Solo/Mute, bit-exact). SCATTER stays empty.
    SRC_RAD is 716 floats, or empty when the source is omni.
    Section 6 is one float, and only when shared_tail is true.
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
