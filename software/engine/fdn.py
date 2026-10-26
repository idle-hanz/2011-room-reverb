#!/usr/bin/env python3
"""
Minimal working square FDN for the 2011 room reverb rebuild.

Agreed constraints (from them / overnight) + Structure 2026-09-20:
  * Unscaled ±1 Hadamard (Sylvester) — add/invert only; NO 1/sqrt(N)
  * Loop gain g in (0,1); maps to Structure ``(Gain/32)×H`` (218)
  * Delay is Diffuser Delay: image Distances ms, Max Delay 1000 ms (460, 476)
  * Hadamard only mixes; Fr.V is a voice picker (470). Feedback Delay Out + Air Abs
    → adder → Diffuser Delay In (473 cyan, both summands).
  * Inject at t=0 with per-line tap level (forward into the delay), NOT delayed
    Hadamard-column inject.
  * c=340 VERIFIED; sr=44100 ASSUMED; origin default corner
  * Mixer is L+0.5·C / R+0.5·C (477), Voice Combiner. Render: IR RMS makeup
    on the FDN. Play live: running Mixer makeup from inject energy (not an
    IR-window RMS). No delay in Mixer.
  * Dffs = Dis × Dff × (1/Diffusion), clip [−1, 1] LIKELY (462–465). Allpass on the delay.

Prime stagger is fallback only. Do not import A–F bit tables here.
"""

from __future__ import annotations

import argparse
import math
import sys
import wave
from typing import List, Optional, Sequence, Tuple

from maths_db import db_to_lin

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
    mic_one_pole_coeff,
    MIC_RES_HZ,
    MIC_CO,
    rbj_peaking,
    normalize_biquad,
    render_wav,
    filter_tap_impulse,
    peaking_stages_for_tap,
    apply_air_absorption,
    precompute_wall_peaking_coeffs,
    PEAKING_Q,
    HARM_MAX,
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
    """±1 Hadamard as float64 ndarray (unscaled). Left pure: no column signs."""
    return np.asarray(unscaled_hadamard_signs(n), dtype=np.float64)


# H·D column signs. Mirror-invariant under (b0 b4)(b1 b3), so a symmetric
# scene stays mono. Breaks the all-ones funnel through line 0. n=8 and n=16
# stay plain H. reaktor_parity keeps plain H (the 2011 matrix).
LOOP_COLUMN_D = np.array(
    [1, -1, -1, -1, -1, -1, 1, -1, -1, 1, -1, 1, 1, 1, 1, 1,
     -1, 1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1, -1, 1, 1, 1],
    dtype=np.float64,
)


def loop_hadamard(n: int, parity: bool = False) -> "np.ndarray":
    """Feedback matrix. n=32 without parity is H·D. Otherwise plain H."""
    H = unscaled_hadamard_matrix(int(n))
    if int(n) == 32 and not parity:
        H = H * LOOP_COLUMN_D[None, :]
    return H


# D3 (2 Oct): 0 in the CORE pack means z^-1 in both. Play already feeds
# g·H·y back on the next sample. Render takes that loop. 1 is plain
# Hadamard under reaktor_parity, not a second loop. The same-sample solve
# (I + g diag(d) H)^{-1} is gone.
LOOP_SEMANTICS = "z1_both"


# VERIFIED Diffuser Delay Properties (476). NI default was 200 ms.
MAX_DELAY_MS = 1000.0


def dffs_coeff(dis: float, dff: float, diffusion: float) -> float:
    """Diffuser Delay Dffs (462–465): Dis × Dff × (1/Diffusion).

    Shot 464 **202.633** is Diffusion **in** to 1/x (1/202.633), not the
    reciprocal sitting on the pin. Voice 1: 83.6099 × −0.46 / 202.633
    = −0.189804, matching 461/465. No clip in the Structure mul.
    NI Dffs is nominally [−1, 1]; clip is a LIKELY pin-range guard.
    diffusion ≈ 0 ⇒ 0 (avoid 1/x blow-up).
    """
    den = float(diffusion)
    if abs(den) <= 1e-12:
        return 0.0
    g = float(dis) * float(dff) / den
    if g > 1.0:
        return 1.0
    if g < -1.0:
        return -1.0
    return g


# |Dffs|=1 makes the NI delay disappear (selfcheck). Studio rooms clip 20/32
# lines to −1 because Diffusion scale is Hall-sized — FDN becomes a spring.
DFFS_STABLE = 0.98
# EQ-1a. |Dffs| above this is what Smooth caps. The 0.98 clamp stays the
# stability guard for Smooth off.
DFFS_SMOOTH_CAP = 0.7


def cap_dffs(gains, cap: float = DFFS_SMOOTH_CAP):
    """Cap |Dffs|. The decay-lock exponent is not scaled.

    Two computed per-line exponents were measured on this tree. The DC
    group-delay ratio, about 17 at g = −0.98, shortened every octave T30 by
    about 40 %. The additive stretch 1 + (τ_cap − τ_raw) / D brought the
    default room's 250 Hz band inside ±5 % and pushed the 3 × 2.4 × 4 m box
    further out. No one exponent meets both rooms, so Smooth does not write one.
    """
    cap = float(cap)
    out = []
    for raw in gains:
        g = float(raw)
        if abs(g) <= cap:
            out.append(g)
        else:
            out.append(cap if g > 0.0 else -cap)
    return out


def dffs_from_taps(
    taps,
    dff_per_tap: Sequence[float],
    diffusion: float,
    n: int = 32,
    channel: str = "mean",
) -> List[float]:
    """Per-line Dffs from image metres × that tap's Dff / Diffusion."""
    n_t = len(taps) if taps is not None else 0
    n_d = len(dff_per_tap) if dff_per_tap is not None else 0
    ch = str(channel).strip().lower()
    if ch not in ("l", "r", "c", "mean"):
        ch = "mean"
    lim = float(DFFS_STABLE)
    out: List[float] = []
    for i in range(n):
        if n_t <= 0:
            out.append(0.0)
            continue
        t = taps[i % n_t]
        dff = float(dff_per_tap[i % n_d]) if n_d > 0 else 0.0
        g = dffs_coeff(_tap_distance(t, ch), dff, diffusion)
        if g > lim:
            g = lim
        elif g < -lim:
            g = -lim
        out.append(g)
    return out


# Live recall (464 Diffusion in = 202.633, room 57×34.241×97 from 395).
# 202.633 / (97 × mean) ≈ 0.0333. IC Min/Max/Default still unread.
DFFS_KNOB_DEFAULT = 0.0333
# Diffusion Master (485): Min 0, Max −0.5, Default −0.25. Live dump at Max.
# 202: sum(ADif…) × MDif → Clipper. MDif = this master (359 DMix).
# Locked 28 Sep 2026 (Idle): app default is the Structure Default −0.25 and the
# accepted range is clamped to the Structure span [−0.5, 0]. LIVE is kept as a
# name for callers; it now equals the default (the −0.5 live dump is still
# reachable as the clamp end-stop).
DIFFUSION_MASTER_DEFAULT = -0.25
DIFFUSION_MASTER_MIN = -0.5
DIFFUSION_MASTER_LIVE = DIFFUSION_MASTER_DEFAULT


def dff_after_master(sum_dif: float, master: float = DIFFUSION_MASTER_LIVE) -> float:
    """Clipper after × MDif (202). Live Master −0.5; v1 0.92×−0.5 = −0.46."""
    v = float(sum_dif) * float(master)
    if v > 1.0:
        return 1.0
    if v < -1.0:
        return -1.0
    return v


# ---------------------------------------------------------------------------
# Loop level trim (headroom decision 6, locked 28 Sep 2026).
# Fixed makeup trims, one row per loop change, so the same FDN fader gives the
# same loudness as before that change. dB, applied to the FDN bus only (the send
# `fdn_wet`), never to direct/early. The engine is float inside; the risk is
# clipping at 0 dBFS on the output, so trims only ever reduce level.
#   "play":   Play path (live_stereo.c via live_fdn_params)
#   "render": Render path (render_fdn_ir)
#   "when":   "lock" = only while line absorption carries the decay (F2 active,
#             decay_lock on); "always" = every loop.
# Values measured at the reference scene (page default room 6x3x8, decay lock
# 1.8 s, humidity 0.5, source pinned at the old default x 3.0 / y 1.5,
# diffusion_master at the locked default -0.25, air_lp held at the old 0.25 so
# the K2 change is not absorbed): FDN-only impulse-response energy, latest
# snapshot vs F2+F3 tree (build_support_2/4_engine_fix_patches/results/levels/
# levels_{latest,p4}_dm025). F3 alone = -1.70 dB on Play (unlocked scene);
# F2 = -2.81 dB on both paths. Not re-derived at diffusion -0.5: with F2 the
# loop level depends on diffusion_master (Render -0.5 -> -0.25: -9 dB). A fixed
# trim is exact only at that scene; residuals at other scenes are in the
# The old "+5.8 dB" was a same-sample port on an older tree. On this tree,
# before D3, Play's tail sat about 3 dB under Render. D3 removes the loop
# difference. D3b puts Play's F3 trim on Render too, so the tails match.
# D3 = z^-1 in both: Play unchanged; Play - Render tail 0.00 dB with equal trims (research_f5_allpass).
LOOP_LEVEL_TRIM_DB = {
    "f2_line_absorption": {"play": -2.81, "render": -2.81, "when": "lock"},
    "f3_play_rate_delays": {"play": -1.70, "render": -1.70, "when": "always"},
    "f5_same_sample": {"play": 0.0, "render": 0.0, "when": "always"},  # D3 = z^-1 in both: Play unchanged; Play - Render tail 0.00 dB with equal trims (research_f5_allpass)
}


def loop_level_trim_db(path: str = "play", lock_active: bool = True) -> float:
    """Summed loop trim in dB for `path` ("play" / "render")."""
    tot = 0.0
    for row in LOOP_LEVEL_TRIM_DB.values():
        if row.get("when") == "lock" and not lock_active:
            continue
        tot += float(row.get(path, 0.0))
    return tot


def loop_level_trim_lin(path: str = "play", lock_active: bool = True) -> float:
    return float(10.0 ** (loop_level_trim_db(path, lock_active) / 20.0))


def diffusion_scale_from_room(room: Vec3, knob: float = DFFS_KNOB_DEFAULT) -> float:
    """Room Dim Diffusion out (276): max(W,H,L) × mean(W,H,L) × knob.

    3-input Mul: largest, mean=(W+H+L)/3, Diffusion IC. Knob default is the
    live dump (464), not a Function-page Default.
    """
    W, H, L = float(room[0]), float(room[1]), float(room[2])
    mean = (W + H + L) / 3.0
    largest = max(W, H, L)
    return max(largest * mean * float(knob), 1e-9)


def inject_tap_into_fdn(
    tap_amplitude: float,
    tap_index: int,
    n_lines: int = 32,
    signs: Sequence[Sequence[int]] | None = None,
) -> List[float]:
    """Legacy Hadamard-column inject. Not the 2011 forward path — kept for tests."""
    if signs is None:
        signs = unscaled_hadamard_signs(n_lines)
    col = tap_index % n_lines
    return [float(tap_amplitude) * float(signs[row][col]) for row in range(n_lines)]


def stub_note() -> str:
    return (
        "FDN: unscaled ±1 Hadamard; delays = image ms (cap 1000); "
        "inject t=0 per line; Hadamard is feedback only."
    )


def mixer_lcr_fold(
    L: "np.ndarray",
    R: "np.ndarray",
    C: Optional["np.ndarray"] = None,
) -> Tuple["np.ndarray", "np.ndarray"]:
    """2011 Mixer (477): L+0.5·C, R+0.5·C. C=None ⇒ L/R unchanged.

    Voice Combiner (479) is the poly sum — process_block_sum. RMS Volume
    Receive (478) is automatic_wet_level, not this fold.
    """
    if C is None:
        return L, R
    half = 0.5 * C
    return L + half, R + half


# Desk fader travel. u < 0.02 is off. Knots match static/js/app.js.
FADER_KNOTS = (
    (0.02, -60.0),
    (0.20, -24.0),
    (0.35, -12.0),
    (0.42, -6.0),
    (0.50, 0.0),
    (0.58, 3.0),
    (0.70, 6.0),
    (1.00, 12.0),
)


def fader_db(travel: float) -> float:
    """Travel 0..1 → dB. Below the first knot is silence."""
    u = float(travel)
    if u < 0.02 or u != u:
        return float("-inf")
    if u >= 1.0:
        return 12.0
    prev_u, prev_db = FADER_KNOTS[0]
    for ku, kdb in FADER_KNOTS[1:]:
        if u <= ku:
            span = ku - prev_u
            t = 0.0 if span <= 0.0 else (u - prev_u) / span
            return prev_db + t * (kdb - prev_db)
        prev_u, prev_db = ku, kdb
    return 12.0


def travel_from_db(db: float) -> float:
    """Inverse of fader_db for a finite dB. At or below −60 sits on the bottom knot."""
    if db != db or db <= -60.0:
        return 0.0 if db < -60.0 or db != db else 0.02
    if db >= 12.0:
        return 1.0
    prev_u, prev_db = FADER_KNOTS[0]
    for ku, kdb in FADER_KNOTS[1:]:
        if db <= kdb:
            span = kdb - prev_db
            t = 0.0 if span == 0.0 else (db - prev_db) / span
            return prev_u + t * (ku - prev_u)
        prev_u, prev_db = ku, kdb
    return 1.0


def gain_from_db(fader_db_value: float, trim_db: float = 0.0) -> float:
    """Linear send. Off fader is 0. Trim is decibels added to the fader. Cap +24 dB."""
    if fader_db_value != fader_db_value or fader_db_value == float("-inf"):
        return 0.0
    db = float(fader_db_value) + float(trim_db)
    if db < -120.0:
        return 0.0
    return float(max(0.0, min(16.0, db_to_lin(db))))


def pan_lr(pan: float) -> Tuple[float, float]:
    """Balance pan. −1 hard left, 0 is 0.5/0.5, +1 hard right."""
    t = max(0.0, min(1.0, (float(pan) + 1.0) * 0.5))
    return 1.0 - t, t


def capsule_speaker_weights(
    gain_l: float = 1.0,
    gain_c: float = 1.0,
    gain_r: float = 1.0,
    pan_l: float = -1.0,
    pan_c: float = 0.0,
    pan_r: float = 1.0,
    phase_l: float = 1.0,
    phase_c: float = 1.0,
    phase_r: float = 1.0,
    routes=None,
    pan_law: str = "linear",
) -> dict:
    """ASSUMED desk law. Defaults are the 477 fold: L+0.5·C, R+0.5·C.

    routes=None, or every route Pan with the 2011 linear law, keeps the body
    below. Other routes (Centre, Both, L, R, S → +L,−R) and constant-power
    pan go through desk_matrix.
    """
    if routes is not None or str(pan_law or "linear").strip().lower() not in ("", "linear", "2011"):
        from desk_matrix import pan_law_name, route_name, speaker_weights

        if isinstance(routes, dict):
            names = tuple(route_name(routes.get(k), "pan") for k in "lcr")
        elif routes is None:
            names = ("pan", "pan", "pan")
        else:
            names = tuple(route_name(r) for r in list(routes)[:3])
            if len(names) < 3:
                names = names + ("pan",) * (3 - len(names))
        law = pan_law_name(pan_law)
        if not (law == "linear" and names == ("pan", "pan", "pan")):
            return speaker_weights(
                gain_l, gain_c, gain_r, pan_l, pan_c, pan_r,
                phase_l, phase_c, phase_r, names, law,
            )

    def one(gain: float, pan: float, phase: float) -> Tuple[float, float]:
        left, right = pan_lr(pan)
        sign = -1.0 if float(phase) < 0.0 else 1.0
        amp = max(0.0, min(16.0, float(gain))) * sign
        return amp * left, amp * right

    ll, lr = one(gain_l, pan_l, phase_l)
    cl, cr = one(gain_c, pan_c, phase_c)
    rl, rr = one(gain_r, pan_r, phase_r)
    return {"ll": ll, "lr": lr, "cl": cl, "cr": cr, "rl": rl, "rr": rr}


def apply_capsule_weights(
    L: "np.ndarray",
    C: "np.ndarray",
    R: "np.ndarray",
    weights: dict,
) -> Tuple["np.ndarray", "np.ndarray"]:
    """Speaker pair from three capsule buses."""
    left = weights["ll"] * L + weights["cl"] * C + weights["rl"] * R
    right = weights["lr"] * L + weights["cr"] * C + weights["rr"] * R
    return left, right


def structure_agc_on_send(geo_levels: Sequence[float]) -> float:
    """AGC On Send (260): 1/x of 1/√(Σ geo).

    AGC In is per-voice 1/r² (256: Dis×Dis then 1/x). Fr.V 1… sum into
    the upper ``+``. No extra square before 1/Sq Root. Then 1/x ⇒ √(Σ 1/r²).
    261 4-mul is not on this path. Desktop Mixer still uses audio IR RMS
    (compensates loop gain; Structure detector is geometry only).
    """
    s = 0.0
    for v in geo_levels:
        x = float(v)
        if x > 0.0:
            s += x
    if s <= 1e-24:
        return 0.0
    inv_sqrt = s ** -0.5
    return 1.0 / inv_sqrt


def automatic_wet_level(
    L: "np.ndarray",
    R: "np.ndarray",
    *,
    target_rms: float = 0.12,
    peak_ceil: float = 0.9,
    floor: float = 1e-12,
) -> Tuple["np.ndarray", "np.ndarray"]:
    """Mixer × Receive RMS Volume (478/482).

    Structure AGC On (260) is geometry: √(Σ 1/r²), not audio. This Desktop
    path RMS-normalizes the wet IR so loop gain changes wetness not loudness
    (from-them). target_rms ASSUMED. Peak ceiling is only a clip guard.
    """
    g = automatic_wet_gain(
        L, R, target_rms=target_rms, peak_ceil=peak_ceil, floor=floor
    )
    return L * g, R * g


def automatic_wet_gain(
    L: "np.ndarray",
    R: "np.ndarray",
    *,
    target_rms: float = 0.12,
    peak_ceil: float = 0.9,
    floor: float = 1e-12,
) -> float:
    """Scalar from automatic_wet_level — apply to Direct and FDN tail together."""
    mix2 = 0.5 * (L * L + R * R)
    rms = float(np.sqrt(max(float(np.mean(mix2)), 0.0)))
    g = float(target_rms) / rms if rms > float(floor) else 1.0
    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R)), floor)) * g
    if peak > float(peak_ceil) and peak > 0.0:
        g *= float(peak_ceil) / peak
    return float(g)


def ir_rms_makeup_from_inject(
    inj_l: Sequence[float],
    inj_c: Sequence[float],
    inj_r: Sequence[float],
    g: float,
    n: int,
    ir_length_ms: float,
    sr: int,
    *,
    target_rms: float = 0.12,
    target_peak: float = 0.7,
    peak_ceil: float = 0.9,
    floor: float = 1e-12,
    skip_index: Optional[int] = None,
    only_index: Optional[int] = None,
    loop: bool = True,
    weights: Optional[dict] = None,
) -> float:
    """Live Mixer AGC (ASSUMED listen). Geometry is 1/r (Idle 2026-10-10).

    Sets the loudest first-arrival Mixer fold to ``target_peak`` so a
    distant / 1/r-quiet field is still audible. Relative image levels
    unchanged. ``sqrt(1−(g√N)²)`` keeps Feedback closer to wetness than
    loudness. Clamp 256 so a hall is not stuck at the old 8× mute.
    ``target_rms`` / ``ir_length_ms`` / ``sr`` unused (callers stable).
    """
    del ir_length_ms, sr, target_rms
    n = int(n)
    peak0 = 0.0
    n_i = min(n, len(inj_l), len(inj_c), len(inj_r))
    skip = None if skip_index is None else int(skip_index)
    only = None if only_index is None else int(only_index)
    for i in range(n_i):
        if only is not None and i != only:
            continue
        if skip is not None and i == skip:
            continue
        if weights is None:
            L = float(inj_l[i]) + 0.5 * float(inj_c[i])
            R = float(inj_r[i]) + 0.5 * float(inj_c[i])
        else:
            L = (float(weights["ll"]) * float(inj_l[i])
                 + float(weights["cl"]) * float(inj_c[i])
                 + float(weights["rl"]) * float(inj_r[i]))
            R = (float(weights["lr"]) * float(inj_l[i])
                 + float(weights["cr"]) * float(inj_c[i])
                 + float(weights["rr"]) * float(inj_r[i]))
        peak0 = max(peak0, abs(L), abs(R))
    makeup = float(target_peak) / max(peak0, float(floor))
    if loop:
        lam = float(g) * math.sqrt(max(float(n), 1.0))
        lam2 = min(lam * lam, 0.9801)
        makeup *= math.sqrt(max(1.0 - lam2, 0.02))
    peak = peak0 * makeup
    if peak > float(peak_ceil) and peak > 0.0:
        makeup *= float(peak_ceil) / peak
    return float(max(0.05, min(256.0, makeup)))


def direct_listen_gain(
    level_l: float,
    level_c: float,
    level_r: float,
    *,
    target: float = 0.7,
    ceil: float = 8.0,
    floor: float = 1e-12,
    weights: Optional[dict] = None,
) -> float:
    """Scale Mix Direct so the first arrival is an audible delayed file.

    Inject is 1/r (Idle 2026-10-10) — under the FDN that
    is not “a copy of the file”. This is listen gain, not a new mix bus.
    """
    if weights is None:
        L = float(level_l) + 0.5 * float(level_c)
        R = float(level_r) + 0.5 * float(level_c)
    else:
        L = (float(weights["ll"]) * float(level_l)
             + float(weights["cl"]) * float(level_c)
             + float(weights["rl"]) * float(level_r))
        R = (float(weights["lr"]) * float(level_l)
             + float(weights["cr"]) * float(level_c)
             + float(weights["rr"]) * float(level_r))
    peak = max(abs(L), abs(R), float(floor))
    return float(max(0.05, min(float(ceil), float(target) / peak)))


def live_peaking_banks(
    room: Vec3,
    sr: int,
    c: float,
    depth_per_axis: float,
) -> List[dict]:
    """Cut-only axial peaking, one bank per X/Y/Z (same as FDN.axis_for_line).

    Float64 design, packed as float32 by the blob. Play restores b2 in double
    at load so the stored numerator still has unity DC. Do not scale it here.
    """
    W, Hh, L = float(room[0]), float(room[1]), float(room[2])
    dims = {"X": W, "Y": Hh, "Z": L}
    gain_db = -abs(float(depth_per_axis))
    out: List[dict] = []
    for ax in ("X", "Y", "Z"):
        f0 = axial_mode_hz(c, dims[ax])
        if 0.0 < f0 < float(sr) * 0.49 and gain_db < 0.0:
            b0, b1, b2, a1, a2 = normalize_biquad(
                rbj_peaking(float(sr), f0, PEAKING_Q, gain_db)
            )
            out.append({
                "on": True,
                "b0": float(b0), "b1": float(b1), "b2": float(b2),
                "a1": float(a1), "a2": float(a2),
            })
        else:
            out.append({"on": False, "b0": 1.0, "b1": 0.0, "b2": 0.0, "a1": 0.0, "a2": 0.0})
    return out


def structure_gain_for_rt60(
    delay_samples: Sequence[int],
    rt60_s: float,
    sr: int,
    n: int,
) -> float:
    """ASSUMED: Structure Gain 0–1 so (g·√N)^(t/t_mean) hits −60 dB at rt60.

    Engine loop g = Gain/N. Unscaled Hadamard has row norm √N, so one trip
    scales by g·√N. Returns the UI Gain slider value, not g.
    """
    n = int(n)
    if n < 1 or sr < 1 or not delay_samples:
        return 0.0
    rt60_s = float(rt60_s)
    if rt60_s <= 0.05:
        return 0.0
    mean_t = (sum(int(d) for d in delay_samples) / float(len(delay_samples))) / float(sr)
    if mean_t <= 1e-9:
        return 0.0
    # (g√N)^k = 0.001, k = rt60/mean_t → g = 0.001^(mean_t/rt60) / √N
    loop = 0.001 ** (mean_t / rt60_s)
    g = loop / math.sqrt(float(n))
    lim = 0.99 / math.sqrt(float(n))
    g = max(0.0, min(lim, g))
    # May exceed Structure Gain 0–1 so a small room can still reach seconds.
    return float(g * float(n))


def _fdn_distance(t, name: str, fallback: float) -> float:
    """H-1 line distance. Missing means the image-tap distance (flat stand)."""
    d = getattr(t, name, None)
    if d is not None:
        return float(d)
    return float(fallback)


def _tap_distance(t, channel: str) -> float:
    if channel == "l":
        return _fdn_distance(t, "fdn_distance_l", t.distance_l)
    if channel == "r":
        return _fdn_distance(t, "fdn_distance_r", t.distance_r)
    if channel == "c":
        d = getattr(t, "fdn_distance_c", None)
        if d is not None:
            return float(d)
        d = getattr(t, "distance_c", None)
        if d is not None:
            return float(d)
    return 0.5 * (
        _fdn_distance(t, "fdn_distance_l", t.distance_l)
        + _fdn_distance(t, "fdn_distance_r", t.distance_r)
    )


def _tap_dir(t, channel: str) -> float:
    """|θ| from capsule look. LIKELY Distances Dir (467 ~0.002–0.17 rad)."""
    if channel == "l":
        return abs(float(t.theta_l))
    if channel == "r":
        return abs(float(t.theta_r))
    if channel == "c":
        th = getattr(t, "theta_c", None)
        if th is not None:
            return abs(float(th))
    return 0.5 * (abs(float(t.theta_l)) + abs(float(t.theta_r)))


def mic_g_from_taps(
    taps,
    n: int,
    channel: str,
    sr: int,
    res_hz: float = MIC_RES_HZ,
    co: float = MIC_CO,
) -> List[float]:
    n_t = len(taps) if taps is not None else 0
    ch = str(channel).strip().lower()
    out: List[float] = []
    for i in range(n):
        if n_t <= 0:
            out.append(1.0)
            continue
        t = taps[i % n_t]
        out.append(mic_one_pole_coeff(_tap_dir(t, ch), sr, res_hz, co))
    return out


def _tap_level(t, channel: str) -> float:
    if channel == "l":
        return float(t.level_l)
    if channel == "r":
        return float(t.level_r)
    if channel == "c":
        lv = getattr(t, "level_c", None)
        if lv is not None:
            return float(lv)
    return 0.5 * (float(t.level_l) + float(t.level_r))


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


def fdn_delays_from_taps(
    taps,
    sr: int = SAMPLE_RATE_HZ,
    c: float = SPEED_OF_SOUND_M_S,
    n: int = 32,
    channel: str = "mean",
    max_delay_ms: float = MAX_DELAY_MS,
) -> List[int]:
    """FDN line lengths = image Distances (460 Dly = TL). Cap 1000 ms (476).

    channel: ``l`` / ``r`` / ``c`` / ``mean``. Line i uses tap i (wrap).
    Duplicate lengths are kept (Distances had real pairs). No +1 uniquify.
    """
    if n < 1 or (n & (n - 1)) != 0:
        raise ValueError(f"FDN size n must be power of 2, got {n}")
    n_t = len(taps) if taps is not None else 0
    min_d = 2
    max_d = max(min_d, int(round(float(max_delay_ms) * 0.001 * sr)))
    ch = str(channel).strip().lower()
    if ch not in ("l", "r", "c", "mean"):
        ch = "mean"
    out: List[int] = []
    for i in range(n):
        if n_t <= 0:
            out.append(min_d)
            continue
        t = taps[i % n_t]
        d = int(round(_tap_distance(t, ch) / c * sr))
        out.append(max(min_d, min(max_d, d)))
    return out


def axis_for_line(i: int) -> str:
    """PROPOSAL: lines i%3 → X/Y/Z for optional peaking in loop."""
    return ("X", "Y", "Z")[i % 3]


class FDN:
    """
    Square N-line FDN (N = power of 2, Sylvester Hadamard).
    Loop: inject + feedback → Schroeder allpass → y.
    Hadamard mixes y (the diffuser output), then × g, back to the input.
    With every Dffs at 0 this is delay read → Hadamard → × g → write.
    Forward input added at the diffuser input (t=0 tap levels). No 1/√N.
    Keep g < 1/√N so a lossless line stays under a trip of 1
    (g maps to Structure Gain/32; one trip stretches by g√N).
    Dffs: Schroeder allpass inside each Diffuser Delay (0 = pure delay).
    With any Dffs, g·H·y is stored and added on the next sample (D3, z^-1),
    the same loop as Play. No Dffs stays a same-sample delay. reaktor_parity
    uses the same timing with plain H.
    Mic 1-pole is on delay *output* to Mixer, not in the Hadamard loop (410).
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
        dffs: Optional[Sequence[float]] = None,
        mic_g: Optional[Sequence[float]] = None,
        line_t60: float = 0.0,
        parity: bool = False,
        surf: Optional[dict] = None,
        harm: Optional[Sequence] = None,
    ) -> None:
        n_lines = int(n) if n is not None else len(delays)
        if n_lines < 1 or (n_lines & (n_lines - 1)) != 0:
            raise ValueError(f"FDN size must be power of 2, got {n_lines}")
        if len(delays) != n_lines:
            raise ValueError(f"need {n_lines} delays, got {len(delays)}")
        self.n = n_lines
        # Unscaled Hadamard: stable only if g < 1/√N. Structure is Gain/N.
        # With line absorption (decay lock) every line loses gain < 1 per
        # trip, so the loop may run at the lossless g = 1/√N.
        self.line_t60 = float(line_t60 or 0.0)
        lim = (1.0 if self.line_t60 > 0.05 else 0.99) / math.sqrt(float(self.n))
        self.g = float(max(0.0, min(lim, g)))
        self.delays = [int(d) for d in delays]
        # lg_i = 10^(-3 d_i / (sr T60)): delay-proportional absorption (Jot).
        self._lg = None
        if self.line_t60 > 0.05:
            self._lg = np.asarray(
                [10.0 ** (-3.0 * float(d) / (float(sr) * self.line_t60)) for d in self.delays],
                dtype=np.float64,
            )
        self.max_d = max(self.delays) if self.delays else 0
        self.bufs = [np.zeros(d, dtype=np.float64) for d in self.delays]
        self.idx = [0] * self.n
        self.parity = bool(parity)
        self.H = loop_hadamard(self.n, self.parity)
        if dffs is None:
            self.dffs = np.zeros(self.n, dtype=np.float64)
        else:
            if len(dffs) != self.n:
                raise ValueError(f"need {self.n} dffs, got {len(dffs)}")
            self.dffs = np.asarray(
                [dffs_coeff(1.0, float(v), 1.0) for v in dffs],
                dtype=np.float64,
            )
        self._any_dffs = bool(np.any(np.abs(self.dffs) > 1e-15))
        # Previous sample's g·H·y. Zero at the start, so the first y is −d·xin.
        self._hy = np.zeros(self.n, dtype=np.float64)
        if mic_g is None:
            self.mic_g = np.ones(self.n, dtype=np.float64)
            self._any_mic = False
        else:
            if len(mic_g) != self.n:
                raise ValueError(f"need {self.n} mic_g, got {len(mic_g)}")
            self.mic_g = np.asarray([float(v) for v in mic_g], dtype=np.float64)
            self._any_mic = bool(np.any(self.mic_g < 0.999))
        self._mic_z = np.zeros(self.n, dtype=np.float64)
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
        # EQ-1b. None until a peak above 0 arms the Frenette allpass.
        self._mod = None
        if self.peaking:
            W, Hh, L = room
            dims = {"X": W, "Y": Hh, "Z": L}
            gain_db = -abs(self.depth_per_axis)  # cut only; never a boost
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
        # ROOMTONE. None is the size gate off: the old read, no extra biquads.
        self._harm_on = False
        self._harm_n = (0, 0, 0)
        self._harm_c = None
        self._harm_z1 = None
        self._harm_z2 = None
        if harm:
            counts = []
            any_h = False
            rows = []
            for ax in range(3):
                row = list(harm[ax]) if ax < len(harm) and harm[ax] else []
                if len(row) > HARM_MAX:
                    row = row[:HARM_MAX]
                rows.append(row)
                counts.append(len(row))
                if row:
                    any_h = True
            if any_h:
                self._harm_on = True
                self._harm_n = (counts[0], counts[1], counts[2])
                self._harm_c = np.zeros((3, HARM_MAX, 5), dtype=np.float64)
                for ax, row in enumerate(rows):
                    for k, coeff in enumerate(row):
                        self._harm_c[ax, k, 0] = float(coeff[0])
                        self._harm_c[ax, k, 1] = float(coeff[1])
                        self._harm_c[ax, k, 2] = float(coeff[2])
                        self._harm_c[ax, k, 3] = float(coeff[3])
                        self._harm_c[ax, k, 4] = float(coeff[4])
                self._harm_z1 = np.zeros((self.n, HARM_MAX), dtype=np.float64)
                self._harm_z2 = np.zeros((self.n, HARM_MAX), dtype=np.float64)
        # SL2. None is Flat (2011): the old path, no sections.
        self._sl = None
        if surf is not None and self._lg is not None:
            self._init_surf(surf)

    def _init_surf(self, surf: dict) -> None:
        """Per-line S1P2 sections (surf_loop.design_bus).

        D-SL3: a per-axis cut at or above keep_cut_below_hz is dropped.
        A lower cut stays and is folded into the fit.
        """
        import surf_loop as _SL
        W, Hh, L = self.room
        dims = {"X": W, "Y": Hh, "Z": L}
        keep_below = float(surf.get("keep_cut_below_hz", _SL.KEEP_CUT_BELOW_HZ))
        peaks = []
        for i in range(self.n):
            keep = False
            if self.peaking and self._use_peak[i]:
                keep = axial_mode_hz(self.c, dims[axis_for_line(i)]) < keep_below
                self._use_peak[i] = keep
            peaks.append((self._b0[i], self._b1[i], self._b2[i], self._a1[i], self._a2[i]) if keep else None)
        if not bool(np.any(self._use_peak)):
            self.peaking = False
        rates = np.asarray(surf["rates_for"](self.delays, self.sr, surf.get("hits")), float)
        res = _SL.design_bus(self.delays, self.sr, self._lg, peaks, rates, surf.get("struct", "S1P2"))
        self._sl = res["secs"]
        self._slz1 = np.zeros(self._sl.shape[:2])
        self._slz2 = np.zeros(self._sl.shape[:2])
        surf.setdefault("report", []).append(dict(
            res["report"], stab=res["stab"], guard=res["guard"],
            kept_cuts=int(sum(p is not None for p in peaks)),
        ))

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
        if _FDN_CORE is not None and self.n == 32 and not self._any_dffs and not self._any_mic and self._lg is None and self._sl is None:
            return self._process_block_c(inject)
        return self._process_block_py(inject)

    def process_block_sum(self, inject: "np.ndarray") -> "np.ndarray":
        """Sum of all line reads (poly mix). 2011 OutPorts sum voices."""
        Lch, Rch = self.process_block(inject)
        return Lch + Rch

    def _arm_movement(self, peak_ms: float):
        """16 of 32 lines: every other length after a stable sort. Shortest stays fixed.

        Frenette first-order allpass, new coefficient every sample (not every 16):
          D = delay + A*sin(w*t+ph)
          N = floor(D-0.5); dl = D-N; eta = (1-dl)/(1+dl)
          y = eta*hist[n-N] + hist[n-N-1] - eta*y[n-1]
        A is peak_ms. w = 2*pi*0.7*r/sr, r = 0.6+0.8*((k*phi)%1), ph = 112.5*k degrees.
        The sine is zero-mean, so the mean delay stays this engine's nominal delay.
        History stores the value written into the delay, not the diffuser output.
        Peak 0 does not call this. An allpass with A = 0 is not today's read.
        """
        peak = float(peak_ms)
        prev = self._mod
        if prev is not None and prev.get("peak") == peak:
            return prev
        delays = self.delays
        order = sorted(range(self.n), key=lambda i: (delays[i], i))
        lines = order[1::2]
        sr = float(self.sr)
        A = peak * 1e-3 * sr
        cfg = {}
        phi = 0.6180339887498949
        for k, i in enumerate(lines):
            r = 0.6 + 0.8 * ((k * phi) % 1.0)
            cfg[i] = (A, 2.0 * math.pi * 0.7 * r / sr, math.radians(112.5 * k))
        length = int(max(delays)) + int(math.floor(A)) + 8
        if length < 4:
            length = 4
        self._mod = {
            "peak": peak,
            "cfg": cfg,
            "hist": {i: np.zeros(length, dtype=np.float64) for i in cfg},
            "hp": {i: 0 for i in cfg},
            "yap": {i: 0.0 for i in cfg},
            "L": length,
            "abs": 0,
        }
        return self._mod

    def process_block_poly(self, inject: "np.ndarray", movement_ms: float = 0.0) -> "np.ndarray":
        """(n_samp, N) line outputs after mic 1-pole. Hadamard still mixes all N.

        Always Python — Mix Direct/tail split needs per-line taps. ASSUMED.
        movement_ms 0 skips the allpass and is today's read.
        """
        n_samp = inject.shape[0]
        n = self.n
        out = np.zeros((n_samp, n), dtype=np.float64)
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
        harm_on = self._harm_on
        if harm_on:
            harm_n = self._harm_n
            harm_c = self._harm_c
            harm_z1 = self._harm_z1
            harm_z2 = self._harm_z2
        dffs = self.dffs
        any_mic = self._any_mic
        mg = self.mic_g
        mz = self._mic_z
        lg = self._lg
        any_dffs = self._any_dffs
        hy = self._hy
        sl = self._sl
        if sl is not None:
            sz1, sz2 = self._slz1, self._slz2
            n_sec = sl.shape[1]
        peak = float(movement_ms or 0.0)
        mod = self._arm_movement(peak) if (peak > 0.0 and n == 32) else None
        for t in range(n_samp):
            for i in range(n):
                reads[i] = bufs[i][idx[i]]
            if mod is not None:
                # Same formula as Play's read_mod_allpass. Centre is the integer delay.
                Lh = mod["L"]
                hist = mod["hist"]
                hp = mod["hp"]
                yap = mod["yap"]
                abs_t = mod["abs"]
                for i, (A, w, ph) in mod["cfg"].items():
                    D = float(delays[i]) + A * math.sin(w * abs_t + ph)
                    Nlag = int(math.floor(D - 0.5))
                    dl = D - Nlag
                    eta = (1.0 - dl) / (1.0 + dl)
                    hh = hist[i]
                    hpi = hp[i]
                    y = eta * hh[(hpi - Nlag) % Lh] + hh[(hpi - Nlag - 1) % Lh] - eta * yap[i]
                    yap[i] = y
                    reads[i] = y
                mod["abs"] = abs_t + 1
            if lg is not None:
                reads *= lg
            if sl is not None:
                for k in range(n_sec):
                    xa = reads.copy()
                    ya = sl[:, k, 0] * xa + sz1[:, k]
                    sz1[:, k] = sl[:, k, 1] * xa - sl[:, k, 3] * ya + sz2[:, k]
                    sz2[:, k] = sl[:, k, 2] * xa - sl[:, k, 4] * ya
                    reads[:] = ya
            if peaking:
                for i in range(n):
                    if use_peak[i]:
                        x = reads[i]
                        yi = b0[i] * x + z1[i]
                        z1[i] = b1[i] * x - a1[i] * yi + z2[i]
                        z2[i] = b2[i] * x - a2[i] * yi
                        reads[i] = yi
            # ROOMTONE. After the kept first-axial peak, not inside that if.
            # One axis per line (i % 3). Direct and early never reach here.
            if harm_on:
                for i in range(n):
                    ax = i % 3
                    nh = harm_n[ax]
                    if nh <= 0:
                        continue
                    x = reads[i]
                    cc = harm_c[ax]
                    for k in range(nh):
                        hb0 = cc[k, 0]
                        hb1 = cc[k, 1]
                        hb2 = cc[k, 2]
                        ha1 = cc[k, 3]
                        ha2 = cc[k, 4]
                        yi = hb0 * x + harm_z1[i, k]
                        harm_z1[i, k] = hb1 * x - ha1 * yi + harm_z2[i, k]
                        harm_z2[i, k] = hb2 * x - ha2 * yi
                        x = yi
                    reads[i] = x
            inj_t = inject[t]
            if not any_dffs:
                # No Dffs: same-sample FDN. This is Play's !mix1 path.
                mixed = g * (H @ reads)
                for i in range(n):
                    wi = idx[i]
                    x = mixed[i] + inj_t[i]
                    gi = float(dffs[i])
                    v = reads[i]
                    y = -gi * x + v
                    bufs[i][wi] = x + gi * y
                    if mod is not None and i in mod["hist"]:
                        hpi = mod["hp"][i]
                        mod["hist"][i][hpi] = x + gi * y
                        mod["hp"][i] = (hpi + 1) % mod["L"]
                    ni = wi + 1
                    idx[i] = ni - delays[i] if ni >= delays[i] else ni
                    reads[i] = y
            else:
                # D3: z^-1, Play's DIFFUSE_FN. H is H·D, or plain H under parity.
                sv = inj_t + hy
                yv = reads - dffs * sv
                hy = g * (H @ yv)
                for i in range(n):
                    wi = idx[i]
                    s = float(sv[i])
                    gi = float(dffs[i])
                    yy = float(yv[i])
                    bufs[i][wi] = s + gi * yy
                    if mod is not None and i in mod["hist"]:
                        hpi = mod["hp"][i]
                        mod["hist"][i][hpi] = s + gi * yy
                        mod["hp"][i] = (hpi + 1) % mod["L"]
                    ni = wi + 1
                    idx[i] = ni - delays[i] if ni >= delays[i] else ni
                    reads[i] = yy
            if any_mic:
                for i in range(n):
                    gi = float(mg[i])
                    z = float(mz[i])
                    yo = z + gi * (float(reads[i]) - z)
                    mz[i] = yo
                    reads[i] = yo
            out[t, :] = reads
        if any_dffs:
            self._hy = hy
        return out

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
        poly = self.process_block_poly(inject)
        Lch = np.sum(poly[:, 0::2], axis=1)
        Rch = np.sum(poly[:, 1::2], axis=1)
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
        dffs: Optional[Sequence[float]] = None,
        mic_g: Optional[Sequence[float]] = None,
    ) -> None:
        super().__init__(
            delays, g, room, sr=sr, c=c,
            depth_per_axis=depth_per_axis, peaking=peaking, n=32,
            dffs=dffs, mic_g=mic_g,
        )



def build_inject_from_taps(
    taps,
    n_samp: int,
    sr: int,
    c: float,
    n_lines: int = 32,
    channel: str = "mean",
    humidity: float = 0.0,
    air_lp: float = 0.25,
    air_shelf: float = 1.0,
    air_climate: str = "studio_20C_50RH",
    air_iso: bool = True,
) -> "np.ndarray":
    """Forward input into Diffuser Delay: air-absorbed per-line inject.

    Independent 1-pole (256) and high-shelf (ASSUMED). humidity 0 or both
    mixes 0 ⇒ dirac at t=0. ``c`` unused (levels already include 1/r).
    """
    del c
    inj = np.zeros((n_samp, n_lines), dtype=np.float64)
    if n_samp < 1 or n_lines < 1:
        return inj
    ch = str(channel).strip().lower()
    if ch not in ("l", "r", "c", "mean"):
        ch = "mean"
    n_t = len(taps) if taps is not None else 0
    use_air = float(humidity) > 0.0 and (
        float(air_lp) > 0.0 or float(air_shelf) > 0.0
    )
    for i in range(n_lines):
        if n_t <= 0:
            break
        t = taps[i % n_t]
        amp = _tap_level(t, ch)
        if not use_air:
            inj[0, i] += amp
            continue
        col = np.zeros(n_samp, dtype=np.float64)
        col[0] = amp
        inj[:, i] += apply_air_absorption(
            col, _tap_distance(t, ch), sr, humidity,
            air_lp=air_lp, air_shelf=air_shelf,
            air_climate=air_climate, air_iso=air_iso,
        )
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
    z_face_4l: bool = False,
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
    inj = build_inject_from_taps(taps, n_samp, sr, c, n, humidity=humidity)
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
        bl = filter_tap_impulse(
            n_early, dl, t.level_l, t.allpass_stages, sr, peaks,
            humidity=humidity, distance=t.distance_l,
        )
        br = filter_tap_impulse(
            n_early, dr, t.level_r, t.allpass_stages, sr, peaks,
            humidity=humidity, distance=t.distance_r,
        )
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
                   help="Prepare Diverg → MLALR/MRALR = Diverg×0.5±0.25 VERIFIED Add")
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
    p.add_argument("--z-face-4l", action="store_true")
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
    print("LIKELY: FDN delays from image Distances per voice (shot 460)")
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
        z_face_4l=args.z_face_4l,
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
