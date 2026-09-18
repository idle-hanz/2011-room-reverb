#!/usr/bin/env python3
"""
Colour (1/3-octave) + Surfaces (A–F) — ASSUMED tuning layer.

Honesty tags
------------
- Structure VERIFIED: A–F Code writers exist (0|1 → To V ~18–52); Surface Absor+Diffu
  serial chain exists. See findings/structure-screenshots-batch-3.md / batch-4.
- NOT invented / NOT Structure-locked here: letter A–F → physical wall dictionary;
  full OCR bit rows wired into audio; Surface EQ dictionary from Reaktor.
- This module is an **ASSUMED** hybrid-C tuning desk: geometric wall-crossing → which
  surface cards colour an image tap; editable absorb / EQ / diffusion per card;
  diffusion is seeded path-length jitter (not an allpass-stage proxy);
  long-term room Colour from wet IR as ISO-ish 1/3-octave magnitude.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

Biquad = Tuple[float, float, float, float, float, float]

# --- Surface cards (friendly + Advanced letter) --------------------------------
# ASSUMED geometric hit map (panel adjacency notes + opposing-wall split for A/C):
#   A Left (−X) nx<0 · C Right (+X) nx>0 · B Ahead (+Z) nz>0 · D Behind (−Z) nz<0
#   E Floor (−Y) ny<0 · F Ceiling (+Y) ny>0
# Panel note also said "Sides=A→X shared"; we split A/C so each card is audible.

SURFACE_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

SURFACE_META: Dict[str, Dict[str, str]] = {
    "A": {"label": "Left wall", "hint": "−X crossings (ASSUMED)"},
    "B": {"label": "Front / Ahead", "hint": "+Z crossings (ASSUMED)"},
    "C": {"label": "Right wall", "hint": "+X crossings (ASSUMED)"},
    "D": {"label": "Back / Behind", "hint": "−Z crossings (ASSUMED)"},
    "E": {"label": "Floor", "hint": "−Y crossings (ASSUMED)"},
    "F": {"label": "Ceiling", "hint": "+Y crossings (ASSUMED)"},
}

# Inward wall normals (into the room). ASSUMED geometric, not Structure OCR.
SURFACE_NORMAL: Dict[str, Tuple[float, float, float]] = {
    "A": (1.0, 0.0, 0.0),    # Left wall x=0
    "C": (-1.0, 0.0, 0.0),   # Right wall x=W
    "E": (0.0, 1.0, 0.0),    # Floor y=0
    "F": (0.0, -1.0, 0.0),   # Ceiling y=H
    "D": (0.0, 0.0, 1.0),    # Behind z=0
    "B": (0.0, 0.0, -1.0),   # Ahead / Front z=L
}

# Seeded path-length jitter (ASSUMED roughness). Replaces allpass-stage diffusion proxy.
DEFAULT_LAMBDA_REF_M = 0.02  # ASSUMED small roughness length (metres)
DEFAULT_DIFFUSION_SEED = 0
DIFFUSION_EPS_M = 1e-9

# Coarse absorb control bands (Hz) — ASSUMED UI curve, not Reaktor OCR
ABSORB_BAND_HZ: Tuple[float, ...] = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0)

# ISO preferred 1/3-octave centres (Hz), audio-relevant subset
THIRD_OCTAVE_HZ: Tuple[float, ...] = (
    25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
    800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
    12500, 16000, 20000,
)


def rbj_peaking(sr: float, f0: float, q: float, gain_db: float) -> Biquad:
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2.0 * q) if q > 1e-9 else 0.0
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cosw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha / A
    return b0, b1, b2, a0, a1, a2


def rbj_highshelf(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosw)
    a2 = (A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2


def rbj_lowshelf(sr: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    """RBJ low-shelf. ASSUMED helper for surface EQ."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = (sinw / 2.0) * math.sqrt(max((A + 1.0 / A) * (1.0 / slope - 1.0) + 2.0, 0.0))
    two_sqrt_A_alpha = 2.0 * math.sqrt(A) * alpha
    b0 = A * ((A + 1.0) - (A - 1.0) * cosw + two_sqrt_A_alpha)
    b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosw)
    b2 = A * ((A + 1.0) - (A - 1.0) * cosw - two_sqrt_A_alpha)
    a0 = (A + 1.0) + (A - 1.0) * cosw + two_sqrt_A_alpha
    a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosw)
    a2 = (A + 1.0) + (A - 1.0) * cosw - two_sqrt_A_alpha
    return b0, b1, b2, a0, a1, a2


def biquad_process(x: np.ndarray, coeffs: Biquad) -> np.ndarray:
    b0, b1, b2, a0, a1, a2 = coeffs
    inv_a0 = 1.0 / a0
    b0, b1, b2 = b0 * inv_a0, b1 * inv_a0, b2 * inv_a0
    a1, a2 = a1 * inv_a0, a2 * inv_a0
    y = np.zeros_like(x)
    z1 = z2 = 0.0
    for i in range(len(x)):
        xi = float(x[i])
        yi = b0 * xi + z1
        z1 = b1 * xi - a1 * yi + z2
        z2 = b2 * xi - a2 * yi
        y[i] = yi
    return y


def cascade_biquads(x: np.ndarray, stages: Sequence[Biquad]) -> np.ndarray:
    y = x
    for c in stages:
        y = biquad_process(y, c)
    return y


def default_surface(letter: str) -> Dict[str, Any]:
    meta = SURFACE_META[letter]
    # Mild default absorb rising with frequency (ASSUMED plaster-ish)
    absorb = [0.05, 0.06, 0.08, 0.10, 0.14, 0.18, 0.22]
    return {
        "letter": letter,
        "label": meta["label"],
        "hint": meta["hint"],
        "absorb_hz": list(ABSORB_BAND_HZ),
        "absorb": list(absorb),
        "eq": {
            "low_shelf_hz": 200.0,
            "low_shelf_db": 0.0,
            "high_shelf_hz": 5000.0,
            "high_shelf_db": 0.0,
            "peak_hz": 1000.0,
            "peak_db": 0.0,
            "peak_q": 1.0,
        },
        "diffusion": 0.15,
        "assumed": True,
    }


def default_surfaces() -> Dict[str, Dict[str, Any]]:
    return {L: default_surface(L) for L in SURFACE_LETTERS}


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def parse_surfaces(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Merge client POST surfaces into defaults. Always tagged assumed=True."""
    out = default_surfaces()
    if not isinstance(raw, dict):
        return out
    for L in SURFACE_LETTERS:
        src = raw.get(L) or raw.get(L.lower())
        if not isinstance(src, dict):
            continue
        dst = out[L]
        if "absorb" in src and isinstance(src["absorb"], (list, tuple)):
            abs_list = []
            for i in range(len(ABSORB_BAND_HZ)):
                if i < len(src["absorb"]):
                    try:
                        abs_list.append(_clamp01(float(src["absorb"][i])))
                    except (TypeError, ValueError):
                        abs_list.append(dst["absorb"][i])
                else:
                    abs_list.append(dst["absorb"][i])
            dst["absorb"] = abs_list
        if "diffusion" in src:
            try:
                dst["diffusion"] = _clamp01(float(src["diffusion"]))
            except (TypeError, ValueError):
                pass
        eq_src = src.get("eq") if isinstance(src.get("eq"), dict) else src
        eq = dst["eq"]
        for key, lo, hi in (
            ("low_shelf_hz", 20.0, 2000.0),
            ("low_shelf_db", -24.0, 24.0),
            ("high_shelf_hz", 500.0, 18000.0),
            ("high_shelf_db", -24.0, 24.0),
            ("peak_hz", 40.0, 16000.0),
            ("peak_db", -24.0, 24.0),
            ("peak_q", 0.2, 8.0),
        ):
            if key in eq_src:
                try:
                    v = float(eq_src[key])
                    eq[key] = float(max(lo, min(hi, v)))
                except (TypeError, ValueError):
                    pass
        dst["assumed"] = True
    return out


def surfaces_hit_by_n(n: Tuple[int, int, int]) -> List[str]:
    """ASSUMED: which surface cards colour this image index (wall crossings).

    Does **not** apply Structure A–F To V OCR bit tables (voice↔tap map UNKNOWN).
    """
    nx, ny, nz = int(n[0]), int(n[1]), int(n[2])
    hit: List[str] = []
    if nx < 0:
        hit.append("A")
    if nx > 0:
        hit.append("C")
    if nz > 0:
        hit.append("B")
    if nz < 0:
        hit.append("D")
    if ny < 0:
        hit.append("E")
    if ny > 0:
        hit.append("F")
    return hit


def last_hit_letter_from_n(n: Tuple[int, int, int]) -> Optional[str]:
    """Fallback last-hit wall from image-index sign (crossed axes). ASSUMED.

    Prefer last_hit_letter() in image_geometry when bounce vertices are available.
    """
    hits = surfaces_hit_by_n(n)
    return hits[-1] if hits else None


def surface_normal(letter: str) -> Tuple[float, float, float]:
    """Inward wall normal for surface letter. ASSUMED geometric."""
    return SURFACE_NORMAL.get(str(letter).upper(), (1.0, 0.0, 0.0))


def incidence_sin2(
    incident: Sequence[float],
    normal: Sequence[float],
) -> float:
    """sin²(θ) for θ = angle between incident ray and wall normal.

    Normal incidence (θ=0) → 0; grazing (θ=90°) → 1.
    """
    ix, iy, iz = float(incident[0]), float(incident[1]), float(incident[2])
    nx, ny, nz = float(normal[0]), float(normal[1]), float(normal[2])
    il = math.sqrt(ix * ix + iy * iy + iz * iz)
    nl = math.sqrt(nx * nx + ny * ny + nz * nz)
    if il < 1e-15 or nl < 1e-15:
        return 0.0
    cos_th = abs((ix * nx + iy * ny + iz * nz) / (il * nl))
    cos_th = min(1.0, max(0.0, cos_th))
    return 1.0 - cos_th * cos_th


def parse_diffusion_seed(raw: Any, default: int = DEFAULT_DIFFUSION_SEED) -> int:
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return int(default)


def parse_lambda_ref(raw: Any, default: float = DEFAULT_LAMBDA_REF_M) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return float(default)
    return float(max(0.0, min(1.0, v)))


def diffusion_u(seed: int, image_index: int, surface_letter: str, mic: str) -> float:
    """Deterministic u ∈ [-1, 1] Uniform. Key = (seed, image index, surface, mic).

    SHA-256 stream — no Python hash() randomization, no unseeded random() in audio.
    Same params + seed ⇒ bit-identical IR.
    """
    key = "{}|{}|{}|{}".format(
        int(seed),
        int(image_index),
        str(surface_letter).upper(),
        str(mic).upper(),
    ).encode("ascii")
    digest = hashlib.sha256(key).digest()
    n = int.from_bytes(digest[:8], byteorder="little", signed=False)
    # Map uint64 → [-1, 1] inclusive.
    return (n / 18446744073709551615.0) * 2.0 - 1.0


def jittered_distance(
    d: float,
    n: Tuple[int, int, int],
    image_index: int,
    mic: str,
    image_xyz: Sequence[float],
    mic_xyz: Sequence[float],
    surfaces: Optional[Dict[str, Dict[str, Any]]],
    seed: int = DEFAULT_DIFFUSION_SEED,
    lambda_ref: float = DEFAULT_LAMBDA_REF_M,
    eps: float = DIFFUSION_EPS_M,
) -> float:
    """Path-length jitter: Δd = D · λ_ref · sin²(θ) · u ; d' = max(ε, d + ΣΔd).

    One term per geometric hit surface (same letters as absorb/EQ). Incident ray
    is unfolded image→mic; θ vs that surface's inward normal. ASSUMED.
    D=0 or empty hits ⇒ d' = d (specular).
    """
    d0 = float(d)
    if not surfaces:
        return max(float(eps), d0)
    hit = surfaces_hit_by_n(n)
    if not hit:
        return max(float(eps), d0)
    incident = (
        float(mic_xyz[0]) - float(image_xyz[0]),
        float(mic_xyz[1]) - float(image_xyz[1]),
        float(mic_xyz[2]) - float(image_xyz[2]),
    )
    lam = float(lambda_ref)
    delta = 0.0
    for letter in hit:
        s = surfaces.get(letter) or {}
        D = _clamp01(float(s.get("diffusion", 0.0) or 0.0))
        if D <= 0.0 or lam <= 0.0:
            continue
        s2 = incidence_sin2(incident, surface_normal(letter))
        u = diffusion_u(int(seed), int(image_index), letter, mic)
        delta += D * lam * s2 * u
    return max(float(eps), d0 + delta)


def _absorb_to_db(alpha: float) -> float:
    """Energy absorb α → amplitude reflection gain in dB. ASSUMED: |R|=√(1−α)."""
    a = _clamp01(alpha)
    refl = math.sqrt(max(1.0 - a, 1e-4))
    return 20.0 * math.log10(refl)


def surface_filter_stages(
    surfaces: Dict[str, Dict[str, Any]],
    letters: Sequence[str],
    sr: float,
) -> List[Biquad]:
    """Cascade ASSUMED absorb peaking + surface EQ for all hit letters (serial)."""
    stages: List[Biquad] = []
    for L in letters:
        s = surfaces.get(L)
        if not s:
            continue
        absorb = s.get("absorb") or []
        hz_list = s.get("absorb_hz") or list(ABSORB_BAND_HZ)
        for i, hz in enumerate(hz_list):
            if i >= len(absorb):
                break
            f0 = float(hz)
            if f0 <= 0.0 or f0 >= sr * 0.49:
                continue
            gdb = _absorb_to_db(float(absorb[i]))
            if abs(gdb) < 0.05:
                continue
            stages.append(rbj_peaking(float(sr), f0, 0.9, gdb))
        eq = s.get("eq") or {}
        ls_db = float(eq.get("low_shelf_db", 0.0))
        if abs(ls_db) >= 0.05:
            stages.append(
                rbj_lowshelf(float(sr), float(eq.get("low_shelf_hz", 200.0)), ls_db)
            )
        pk_db = float(eq.get("peak_db", 0.0))
        if abs(pk_db) >= 0.05:
            stages.append(
                rbj_peaking(
                    float(sr),
                    float(eq.get("peak_hz", 1000.0)),
                    float(eq.get("peak_q", 1.0)),
                    pk_db,
                )
            )
        hs_db = float(eq.get("high_shelf_db", 0.0))
        if abs(hs_db) >= 0.05:
            stages.append(
                rbj_highshelf(float(sr), float(eq.get("high_shelf_hz", 5000.0)), hs_db)
            )
    return stages


def diffusion_extra_stages(
    surfaces: Dict[str, Dict[str, Any]],
    letters: Sequence[str],
    base_stages: int,
) -> int:
    """Deprecated no-op. Surfaces diffusion is seeded path-length jitter, not allpass stages.

    Geometric order allpass (tap.allpass_stages) is unchanged. Kept so leftover callers
    do not bump Schroeder stages from the Diffusion knob.
    """
    del surfaces, letters
    return int(base_stages)


def apply_surface_to_buffer(
    buf: np.ndarray,
    surfaces: Dict[str, Dict[str, Any]],
    letters: Sequence[str],
    sr: float,
) -> np.ndarray:
    stages = surface_filter_stages(surfaces, letters, sr)
    if not stages:
        return buf
    return cascade_biquads(buf, stages)


def third_octave_band_edges(f_c: float) -> Tuple[float, float]:
    r = 2.0 ** (1.0 / 6.0)
    return f_c / r, f_c * r


def _nearest_centre_index(centres: Sequence[float], target_hz: float) -> int:
    best_i = 0
    best_d = abs(float(centres[0]) - target_hz) if centres else 0.0
    for i, c in enumerate(centres):
        d = abs(float(c) - target_hz)
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def third_octave_levels(
    ir: np.ndarray,
    sr: float,
    centres: Sequence[float] = THIRD_OCTAVE_HZ,
    ref_mode: str = "peak",
) -> Dict[str, Any]:
    """Long-term magnitude Colour of an IR as 1/3-octave band levels (dB).

    ref_mode:
      - "peak" (default): peak band = 0 dB
      - "1khz": nearest centre to 1000 Hz = 0 dB
    Both relative curves are returned so the UI can switch without re-render.
    """
    mode = str(ref_mode or "peak").strip().lower()
    if mode in ("1k", "1khz", "1000", "1_khz"):
        mode = "1khz"
    else:
        mode = "peak"

    x = np.asarray(ir, dtype=np.float64).ravel()
    if x.size == 0:
        empty = [-120.0] * len(centres)
        return {
            "centres_hz": list(centres),
            "levels_db": list(empty),
            "levels_db_peak": list(empty),
            "levels_db_1khz": list(empty),
            "levels_db_abs": list(empty),
            "ref_db": -120.0,
            "ref_mode": mode,
            "ref_hz": 1000.0 if mode == "1khz" else None,
            "method": "1/3-octave FFT power (empty)",
            "assumed_note": "Long-term Colour from wet IR — not Structure Surface EQ OCR",
        }
    n = int(2 ** math.ceil(math.log2(max(x.size * 2, 4096))))
    spec = np.fft.rfft(x, n=n)
    power = (spec.real * spec.real + spec.imag * spec.imag)
    freqs = np.fft.rfftfreq(n, d=1.0 / float(sr))
    levels: List[float] = []
    for fc in centres:
        lo, hi = third_octave_band_edges(float(fc))
        if hi < freqs[1] or lo > freqs[-1]:
            levels.append(-120.0)
            continue
        mask = (freqs >= lo) & (freqs < hi)
        if not np.any(mask):
            levels.append(-120.0)
            continue
        e = float(np.sum(power[mask]))
        levels.append(10.0 * math.log10(max(e, 1e-30)))
    peak = max(levels) if levels else -120.0
    rel_peak = [lv - peak for lv in levels]
    i1k = _nearest_centre_index(centres, 1000.0)
    ref_1k = levels[i1k] if levels else -120.0
    rel_1k = [lv - ref_1k for lv in levels]
    if mode == "1khz":
        rel = rel_1k
        ref_db = float(ref_1k)
        ref_hz = float(centres[i1k])
        method = "1/3-octave FFT band power (relative to 1 kHz)"
    else:
        rel = rel_peak
        ref_db = float(peak)
        ref_hz = None
        method = "1/3-octave FFT band power (relative to peak)"
    return {
        "centres_hz": [float(c) for c in centres],
        "levels_db": rel,
        "levels_db_peak": rel_peak,
        "levels_db_1khz": rel_1k,
        "levels_db_abs": levels,
        "ref_db": ref_db,
        "ref_mode": mode,
        "ref_hz": ref_hz,
        "method": method,
        "assumed_note": "Long-term Colour from wet IR — not Structure Surface EQ OCR",
    }


def colour_from_stereo(
    L: np.ndarray,
    R: np.ndarray,
    sr: float,
    ref_mode: str = "peak",
) -> Dict[str, Any]:
    mono = 0.5 * (np.asarray(L, dtype=np.float64) + np.asarray(R, dtype=np.float64))
    return third_octave_levels(mono, sr, ref_mode=ref_mode)


def surfaces_payload(surfaces: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "assumed": True,
        "note": (
            "ASSUMED tuning layer. Structure A–F 0|1 mask writers exist, but "
            "letter→wall dictionary and Surface EQ OCR are NOT locked into audio. "
            "Hits use geometric image indices (wall crossings). "
            "Diffusion is seeded path-length jitter Δd = D·λ_ref·sin²(θ)·u "
            "(not an allpass-stage proxy)."
        ),
        "absorb_hz": list(ABSORB_BAND_HZ),
        "surfaces": surfaces,
        "meta": SURFACE_META,
        "diffusion_model": {
            "assumed": True,
            "formula": "Δd = D · λ_ref · sin²(θ) · u;  d' = max(ε, d + Δd)",
            "lambda_ref_m_default": DEFAULT_LAMBDA_REF_M,
            "seed_default": DEFAULT_DIFFUSION_SEED,
            "u": "Uniform[-1,1] keyed by (seed, image index, surface, mic)",
        },
    }
