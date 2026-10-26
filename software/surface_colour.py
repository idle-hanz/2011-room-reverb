#!/usr/bin/env python3
"""
Colour (1/3-octave) + Surfaces (A–F) — ASSUMED tuning layer.

Honesty tags
------------
- Structure VERIFIED: A–F Code writers exist (0|1 → To V ~18–52); Surface Absor+Diffu
  serial chain exists. See findings/structure-screenshots-batch-3.md / batch-4.
- Panel names VERIFIED 2026-09-19 (Diffusion Matrix): B Ahead, D Behind, E Floor,
  F Ceiling; A and C share Sides. Left vs Right split of A/C is ASSUMED.
- NOT Structure-locked here: A vs C which wall; full bit rows wired into audio;
  Surface EQ dictionary from Reaktor. Masks: engine/absorb_masks.py (data only).
- This module is an **ASSUMED** hybrid-C tuning desk: geometric wall-crossing → which
  surface cards colour an image tap; editable absorb / EQ / diffusion per card;
  diffusion is seeded path-length jitter (not an allpass-stage proxy);
  long-term room Colour from wet IR as ISO-ish 1/3-octave magnitude.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

Biquad = Tuple[float, float, float, float, float, float]

# --- Surface cards (friendly + Advanced letter) --------------------------------
# Geometric hit map. Panel names B/D/E/F VERIFIED (Diffusion Matrix 359 / panel 394).
# A and C share the Reaktor Sides panel; Left vs Right split is ASSUMED so each card
# is audible. Inward normals below match that split.

SURFACE_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

SURFACE_META: Dict[str, Dict[str, str]] = {
    "A": {"label": "Left wall (Sides)", "hint": "−X crossings; Sides panel, A vs C split ASSUMED"},
    "B": {"label": "Front / Ahead", "hint": "+Z crossings; panel name VERIFIED"},
    "C": {"label": "Right wall (Sides)", "hint": "+X crossings; Sides panel, A vs C split ASSUMED"},
    "D": {"label": "Back / Behind", "hint": "−Z crossings; panel name VERIFIED"},
    "E": {"label": "Floor", "hint": "−Y crossings; panel name VERIFIED"},
    "F": {"label": "Ceiling", "hint": "+Y crossings; panel name VERIFIED"},
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
        # Two layers. jitter_D smears path length. structure_dif feeds Structure Dffs.
        # diffusion is the old single key: a save that only has it is copied into both.
        "jitter_D": 0.15,
        "structure_dif": 0.15,
        "diffusion": 0.15,
        "assumed": True,
    }


def default_surfaces() -> Dict[str, Dict[str, Any]]:
    return {L: default_surface(L) for L in SURFACE_LETTERS}


# Acoustic fields only. C keeps its own letter, label, and hint.
_SIDE_MIRROR_KEYS = (
    "absorb",
    "material",
    "material_name",
    "honesty",
    "jitter_D",
    "structure_dif",
    "diffusion",
    "assumed",
)


def mirror_left_to_right(surfaces: Dict[str, Dict[str, Any]]) -> None:
    """Copy wall A's material onto C. Front, back, floor, and ceiling stay put."""
    if not isinstance(surfaces, dict):
        return
    src = surfaces.get("A")
    dst = surfaces.get("C")
    if not isinstance(src, dict) or not isinstance(dst, dict) or src is dst:
        return
    for key in _SIDE_MIRROR_KEYS:
        if key in src:
            val = src[key]
            dst[key] = copy.deepcopy(val) if isinstance(val, (list, dict)) else val
        elif key in ("material", "material_name", "honesty"):
            dst.pop(key, None)
    eq = src.get("eq")
    if isinstance(eq, dict):
        dst["eq"] = copy.deepcopy(eq)


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _opt01(src: Dict[str, Any], key: str) -> Optional[float]:
    if not isinstance(src, dict) or key not in src or src.get(key) is None:
        return None
    try:
        return _clamp01(float(src[key]))
    except (TypeError, ValueError):
        return None


# Letter → role. A–D walls, E floor, F ceiling. Locked with the materials brief.
LETTER_ROLE: Dict[str, str] = {
    "A": "wall", "B": "wall", "C": "wall", "D": "wall",
    "E": "floor", "F": "ceiling",
}


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
        legacy = _opt01(src, "diffusion")
        jitter = _opt01(src, "jitter_D")
        # jitter_d is the same smear knob as jitter_D. It does not touch Dffs.
        if jitter is None and "jitter_D" not in src:
            jitter = _opt01(src, "jitter_d")
        struct = _opt01(src, "structure_dif")
        # Old saves name one knob. Copy it into both layers so the sound is unchanged.
        if jitter is None and legacy is not None and "jitter_D" not in src:
            jitter = legacy
        if struct is None and legacy is not None and "structure_dif" not in src:
            struct = legacy
        if jitter is not None:
            dst["jitter_D"] = jitter
        if struct is not None:
            dst["structure_dif"] = struct
        if legacy is not None and "jitter_D" not in src and "structure_dif" not in src:
            dst["diffusion"] = legacy
        mat_id = src.get("material")
        if isinstance(mat_id, str) and mat_id.strip():
            dst["material"] = mat_id.strip()
        for extra in ("material_name", "honesty"):
            if isinstance(src.get(extra), str):
                dst[extra] = src[extra]
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


def card_jitter_D(card: Optional[Dict[str, Any]]) -> float:
    """Surfaces path-length smear. A muted face adds nothing. Falls back to diffusion."""
    if not isinstance(card, dict) or card.get("muted"):
        return 0.0
    if "jitter_D" in card and card.get("jitter_D") is not None:
        try:
            return _clamp01(float(card["jitter_D"]))
        except (TypeError, ValueError):
            pass
    if "jitter_d" in card and card.get("jitter_d") is not None:
        try:
            return _clamp01(float(card["jitter_d"]))
        except (TypeError, ValueError):
            pass
    try:
        return _clamp01(float(card.get("diffusion", 0.0) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def card_structure_dif(card: Optional[Dict[str, Any]]) -> float:
    """Structure Dffs contribution. Independent of jitter_D. A muted face adds nothing."""
    if not isinstance(card, dict) or card.get("muted"):
        return 0.0
    if "structure_dif" in card and card.get("structure_dif") is not None:
        try:
            return _clamp01(float(card["structure_dif"]))
        except (TypeError, ValueError):
            pass
    try:
        return _clamp01(float(card.get("diffusion", 0.0) or 0.0))
    except (TypeError, ValueError):
        return 0.0


def parse_solo(raw: Any) -> Optional[str]:
    """None, or one of A–F. Missing, blank, and off/all clear the solo."""
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if s in ("", "NULL", "NONE", "OFF", "ALL"):
        return None
    return s if s in SURFACE_LETTERS else None


def parse_mute(raw: Any) -> set:
    """Muted letters. A dict of flags, a list of letters, or 'all'."""
    if raw is None:
        return set()
    if isinstance(raw, dict):
        out = set()
        for L in SURFACE_LETTERS:
            v = raw[L] if L in raw else raw.get(L.lower())
            if v is True or v == 1 or (isinstance(v, str) and v.strip().lower() in ("1", "true", "yes")):
                out.add(L)
        return out
    if isinstance(raw, str):
        if raw.strip().lower() in ("all", "*"):
            return set(SURFACE_LETTERS)
        parts = [p.strip().upper() for p in raw.replace(",", " ").split() if p.strip()]
        return {p for p in parts if p in SURFACE_LETTERS}
    if isinstance(raw, (list, tuple)):
        out = set()
        for item in raw:
            if isinstance(item, str) and item.strip().upper() in SURFACE_LETTERS:
                out.add(item.strip().upper())
        return out
    return set()


def mute_flags(raw: Any) -> Dict[str, bool]:
    muted = parse_mute(raw)
    return {L: L in muted for L in SURFACE_LETTERS}


def face_is_heard(letter: str, solo: Optional[str], mute: set) -> bool:
    """Solo wins on its own face. Every other face, and any mute, is silent."""
    L = str(letter).upper()
    if solo is not None and L == solo:
        return True
    if solo is not None and L != solo:
        return False
    return L not in mute


def solo_mute_gates(solo: Any, mute: Any) -> List[float]:
    """CORE solo_mute[6] in A–F order. 1 = the face still reflects, 0 = it does not."""
    solo_l = parse_solo(solo)
    mute_s = parse_mute(mute)
    return [1.0 if face_is_heard(L, solo_l, mute_s) else 0.0 for L in SURFACE_LETTERS]


def effective_surfaces(
    surfaces: Dict[str, Dict[str, Any]],
    solo: Any = None,
    mute: Any = None,
) -> Dict[str, Dict[str, Any]]:
    """One gate for the cascade, reflect gain, Dffs, and path smear.

    No solo and no mutes returns the same dict. A silenced face keeps its letter
    and its timing slot, with absorb 1, flat EQ, both diffusion knobs at 0, and
    muted=True so the reflect product is ×0 rather than the 0.95 clamp.
    """
    solo_l = parse_solo(solo)
    mute_s = parse_mute(mute)
    if solo_l is None and not mute_s:
        return surfaces
    out: Dict[str, Dict[str, Any]] = {}
    for L in SURFACE_LETTERS:
        card = surfaces.get(L) if isinstance(surfaces, dict) else None
        if not isinstance(card, dict):
            card = default_surface(L)
        if face_is_heard(L, solo_l, mute_s):
            out[L] = card
            continue
        c = dict(card)
        c["absorb"] = [1.0] * len(ABSORB_BAND_HZ)
        eq = dict(c.get("eq") or {})
        eq["low_shelf_db"] = 0.0
        eq["high_shelf_db"] = 0.0
        eq["peak_db"] = 0.0
        c["eq"] = eq
        c["jitter_D"] = 0.0
        c["structure_dif"] = 0.0
        c["diffusion"] = 0.0
        c["muted"] = True
        out[L] = c
    return out


def _preset_dir() -> Path:
    return Path(__file__).resolve().parent / "presets" / "surfaces"


def _load_material_presets() -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """12 textbook materials plus the modelled porous-gap presets. heavy_curtain is wall-only."""
    folder = _preset_dir()
    index_path = folder / "index.json"
    if not index_path.exists():
        return {}, []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    table: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    for row in index.get("presets") or []:
        name = str(row.get("file") or "")
        path = folder / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        mid = str(data.get("id") or row.get("id") or "")
        if not mid:
            continue
        table[mid] = data
        order.append(mid)
    return table, order


MATERIAL_PRESETS, MATERIAL_ORDER = _load_material_presets()


def material_legal(material: Dict[str, Any], letter: str) -> bool:
    """True when this preset may paint that card. Curtain is never floor or ceiling."""
    role = LETTER_ROLE.get(str(letter).upper())
    if role is None or not isinstance(material, dict):
        return False
    roles = set(material.get("roles") or [])
    banned = set(material.get("banned_on") or [])
    return role in roles and role not in banned


def materials_public() -> List[Dict[str, Any]]:
    rows = []
    for mid in MATERIAL_ORDER:
        m = MATERIAL_PRESETS.get(mid) or {}
        rows.append({
            "id": mid,
            "display_name": m.get("display_name") or mid,
            "honesty": m.get("honesty") or "",
            "roles": list(m.get("roles") or []),
            "banned_on": list(m.get("banned_on") or []),
            "absorb": list(m.get("absorb") or []),
            "absorb_hz": list(m.get("absorb_hz") or ABSORB_BAND_HZ),
        })
    return rows


def load_material_sets() -> List[Dict[str, Any]]:
    """Named face assignments. They do not replace default_surfaces()."""
    path = _preset_dir() / "sets.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for row in data.get("sets") or []:
        if not isinstance(row, dict):
            continue
        faces = row.get("faces") if isinstance(row.get("faces"), dict) else {}
        clean = {}
        for letter in SURFACE_LETTERS:
            mid = faces.get(letter)
            if isinstance(mid, str) and mid in MATERIAL_PRESETS:
                clean[letter] = mid
        if len(clean) != len(SURFACE_LETTERS):
            continue
        out.append({
            "id": str(row.get("id") or ""),
            "display_name": str(row.get("display_name") or row.get("id") or ""),
            "honesty": str(row.get("honesty") or "ASSUMED_TEXTBOOK"),
            "note": str(row.get("note") or ""),
            "faces": clean,
        })
    return out


def image_in_early(n: Tuple[int, int, int], solo_l: Optional[str], mute_s: set) -> bool:
    """D16 / D15. True when this image stays in the early field.

    No solo and no mute: every image stays. Solo X keeps every image that
    touches X, and drops the direct image n=(0,0,0). Mute X, with no solo,
    drops every image that touches X and keeps the direct image.
    """
    nx, ny, nz = int(n[0]), int(n[1]), int(n[2])
    if nx == 0 and ny == 0 and nz == 0:
        return solo_l is None
    hits = surfaces_hit_by_n((nx, ny, nz))
    if solo_l is not None:
        return solo_l in hits
    if mute_s:
        return not any(h in mute_s for h in hits)
    return True


def surfaces_hit_by_n(n: Tuple[int, int, int]) -> List[str]:
    """ASSUMED: which surface cards colour this image index (wall crossings).

    Does **not** apply Structure A–F To V OCR bit tables (voice↔tap map UNKNOWN).
    """
    nx, ny, nz = int(n[0]), int(n[1]), int(n[2])
    hit: List[str] = []
    # Sign = first wall on that axis. |n|>=2 also hits the opposite wall
    # (even-order Y: floor+ceiling). LIKELY image-source; matches 463 v1 Dff.
    if nx != 0:
        hit.append("A" if nx < 0 else "C")
        if abs(nx) >= 2:
            hit.append("C" if nx < 0 else "A")
    if ny != 0:
        hit.append("E" if ny < 0 else "F")
        if abs(ny) >= 2:
            hit.append("F" if ny < 0 else "E")
    if nz != 0:
        hit.append("D" if nz < 0 else "B")
        if abs(nz) >= 2:
            hit.append("B" if nz < 0 else "D")
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


# X-mirror swaps the side walls. Floor, ceiling, front and back stay put.
_MIRROR_X_LETTER = {"A": "C", "C": "A"}


def mirror_jitter_overrides(n: Tuple[int, int, int], mic: str, partner_index: int) -> Dict[str, Any]:
    """Hash kwargs so this image shares its jitter draw with its x-mirror.

    The mirror of (nx, ny, nz, mic) is (-nx, ny, nz) on the other capsule,
    with side walls A and C swapped. nx > 0 is the representative and keeps
    today's key, so the return is empty. nx < 0 uses the partner image's
    list index and the swapped capsule. nx == 0 is its own mirror, so both
    capsules use the left capsule's draw. lambda_ref and the u map are unchanged.
    """
    nx = int(n[0])
    mic_u = str(mic).upper()
    if nx < 0:
        swapped = "R" if mic_u == "L" else "L" if mic_u == "R" else mic_u
        return {
            "hash_index": int(partner_index),
            "hash_mic": swapped,
            "hash_letters": _MIRROR_X_LETTER,
        }
    if nx == 0 and mic_u != "L":
        return {"hash_mic": "L"}
    return {}


def mirror_x_partner_index(orders: Sequence[Tuple[int, int, int]]) -> List[int]:
    """Index whose image order is (-nx, ny, nz). An order on the centre plane maps to itself."""
    buckets: Dict[Tuple[int, int, int], List[int]] = {}
    keys = []
    for i, n in enumerate(orders):
        key = (int(n[0]), int(n[1]), int(n[2]))
        keys.append(key)
        buckets.setdefault(key, []).append(i)
    partner = list(range(len(keys)))
    used = set()
    for i, key in enumerate(keys):
        if i in used:
            continue
        flipped = (-key[0], key[1], key[2])
        if flipped == key:
            partner[i] = i
            used.add(i)
            continue
        pick = None
        for j in buckets.get(flipped, []):
            if j not in used:
                pick = j
                break
        if pick is None:
            partner[i] = i
            used.add(i)
            continue
        partner[i] = pick
        partner[pick] = i
        used.add(i)
        used.add(pick)
    return partner


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
    hash_index: Optional[int] = None,
    hash_mic: Optional[str] = None,
    hash_letters: Optional[Dict[str, str]] = None,
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
        D = card_jitter_D(s)
        if D <= 0.0 or lam <= 0.0:
            continue
        s2 = incidence_sin2(incident, surface_normal(letter))
        letter_h = letter if not hash_letters else hash_letters.get(letter, letter)
        idx_h = image_index if hash_index is None else hash_index
        mic_h = mic if hash_mic is None else hash_mic
        u = diffusion_u(int(seed), int(idx_h), letter_h, mic_h)
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
        if not s or s.get("muted"):
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


# D-UI26 = A, D-S5c-3. Per-line face colour. Play and the Render FDN inject
# use fit_line_cascade. Render early stays on the exact face chain.
SURF_K_MAX = 6
SURF_ERR_DB = 0.25
SURF_IDENTITY_DB = 0.05
_FIT_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _f32_row(row: Sequence[float]) -> Tuple[float, float, float, float, float]:
    """Blob coefficients are float32. The residual is measured after that round trip."""
    return tuple(float(np.float32(x)) for x in row)


def _norm5(bq: Sequence[float]) -> Tuple[float, float, float, float, float]:
    b0, b1, b2, a0, a1, a2 = (float(x) for x in bq)
    if abs(a0) < 1e-18:
        return 1.0, 0.0, 0.0, 0.0, 0.0
    inv = 1.0 / a0
    return b0 * inv, b1 * inv, b2 * inv, a1 * inv, a2 * inv


def _surf_grid(sr: float) -> np.ndarray:
    hi = min(18000.0, float(sr) * 0.45)
    if hi <= 60.0:
        hi = min(18000.0, float(sr) * 0.49)
    return np.geomspace(50.0, hi, 240)


def _db_of(coefs: Sequence[Sequence[float]], sr: float, freq: np.ndarray) -> np.ndarray:
    w = 2.0 * math.pi * np.asarray(freq, dtype=np.float64) / float(sr)
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    h = np.ones(freq.shape[0], dtype=np.complex128)
    for row in coefs:
        b0, b1, b2, a1, a2 = row
        h *= (b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2)
    return 20.0 * np.log10(np.maximum(np.abs(h), 1e-30))


def _fit_key(stages: Sequence[Biquad], sr: float) -> Tuple[Any, ...]:
    rows = tuple(tuple(round(float(x), 7) for x in bq) for bq in stages)
    return (round(float(sr), 3), rows)


def _surf_model(p: np.ndarray, k: int, sr: float) -> List[Tuple[float, float, float, float, float]]:
    st = [
        rbj_lowshelf(sr, math.exp(float(p[0])), float(p[1])),
        rbj_highshelf(sr, math.exp(float(p[2])), float(p[3])),
    ]
    for i in range(k - 2):
        st.append(rbj_peaking(
            sr,
            math.exp(float(p[4 + 3 * i])),
            math.exp(float(p[5 + 3 * i])),
            float(p[6 + 3 * i]),
        ))
    return [_norm5(bq) for bq in st]


def _fit_one(target: np.ndarray, k: int, sr: float, freq: np.ndarray, trials: int) -> Tuple[float, np.ndarray]:
    from scipy.optimize import least_squares

    x0 = [
        math.log(250.0),
        float(target[freq < 300].mean()) if np.any(freq < 300) else 0.0,
        math.log(4000.0),
        float(target[freq > 5000].mean() - target[(freq > 300) & (freq < 3000)].mean())
        if np.any(freq > 5000) else 0.0,
    ]
    lo = [math.log(30.0), -24.0, math.log(800.0), -24.0]
    hi = [math.log(2000.0), 24.0, math.log(16000.0), 24.0]
    if k > 2:
        for fk in np.geomspace(150.0, 10000.0, k - 2):
            x0 += [math.log(float(fk)), math.log(1.0), 0.0]
            lo += [math.log(60.0), math.log(0.3), -24.0]
            hi += [math.log(16000.0), math.log(8.0), 24.0]
    best_e = None
    best_x = np.asarray(x0, dtype=np.float64)
    for trial in range(max(1, int(trials))):
        x = np.array(x0, dtype=np.float64)
        if trial and k > 2:
            rng = np.random.default_rng(trial)
            x[4::3] = np.log(rng.uniform(80.0, 12000.0, k - 2))
        # A multi-face shelf can start outside ±24 dB. Clip into the bounds
        # so least_squares runs; the residual still records the miss.
        x = np.clip(x, np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64))

        def fun(pv: np.ndarray) -> np.ndarray:
            return _db_of(_surf_model(pv, k, sr), sr, freq) - target

        res = least_squares(fun, x, bounds=(lo, hi), max_nfev=400)
        err = float(np.max(np.abs(res.fun)))
        if best_e is None or err < best_e:
            best_e = err
            best_x = np.asarray(res.x, dtype=np.float64)
        if best_e <= SURF_ERR_DB:
            break
    return float(best_e if best_e is not None else 99.0), best_x


def fit_line_cascade(stages: Sequence[Biquad], sr: float) -> Dict[str, Any]:
    """Least-squares fit of one line's exact face cascade to at most SURF_K_MAX biquads.

    Section order is low shelf, high shelf, then peaks. The smallest K that
    stays within 0.25 dB is kept. Sections within ±0.05 dB of identity are
    dropped. A line with nothing left is a bypass. The residual is the shipped
    cascade against the exact chain, in dB, on 50 Hz–18 kHz.
    """
    sr_f = float(sr)
    key = _fit_key(stages, sr_f)
    cached = _FIT_CACHE.get(key)
    if cached is not None:
        return cached
    empty: Dict[str, Any] = {
        "k": 0,
        "coef": [],
        "residual_db": 0.0,
        "fit_db": 0.0,
        "k_fit": 0,
        "miss": False,
        "bypass": True,
    }
    if not stages:
        _FIT_CACHE[key] = empty
        return empty
    freq = _surf_grid(sr_f)
    target = _db_of([_norm5(bq) for bq in stages], sr_f, freq)
    if float(np.max(np.abs(target))) <= SURF_IDENTITY_DB:
        _FIT_CACHE[key] = empty
        return empty
    best = None
    for k in (2, 3, 4, SURF_K_MAX):
        # K = 2 and 3 miss 0.25 dB from the shelf start, so one start rejects them.
        # K = 4 needs a few peak restarts: four starts leave a 4-face default
        # line at 0.255 dB, and start 5 lands at 0.244 dB.
        trials = 1 if k < 4 else 8
        err, xv = _fit_one(target, k, sr_f, freq, trials)
        if best is None or err < best[0]:
            best = (err, k, xv)
        if err <= SURF_ERR_DB:
            break
    assert best is not None
    fit_db, k_fit, xv = best
    coefs = [_f32_row(row) for row in _surf_model(xv, k_fit, sr_f)]
    kept: List[Tuple[float, float, float, float, float]] = []
    for row in coefs:
        db = _db_of([row], sr_f, freq)
        if float(np.max(np.abs(db))) <= SURF_IDENTITY_DB:
            continue
        kept.append(row)
    if not kept:
        out = dict(empty)
        out["fit_db"] = fit_db
        out["k_fit"] = k_fit
        _FIT_CACHE[key] = out
        return out
    shipped = _db_of(kept, sr_f, freq)
    residual = float(np.max(np.abs(shipped - target)))
    # Dropping a near-identity section must not push a passing fit over 0.25 dB.
    if residual > SURF_ERR_DB and fit_db <= SURF_ERR_DB:
        kept = list(coefs)
        shipped = _db_of(kept, sr_f, freq)
        residual = float(np.max(np.abs(shipped - target)))
    out = {
        "k": len(kept),
        "coef": [tuple(float(x) for x in row) for row in kept],
        "residual_db": residual,
        "fit_db": float(fit_db),
        "k_fit": int(k_fit),
        "miss": residual > SURF_ERR_DB + 1e-9,
        "bypass": False,
    }
    _FIT_CACHE[key] = out
    return out


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
            "Tuning layer. Panel names B Ahead · D Behind · E Floor · F Ceiling "
            "VERIFIED. A and C share Sides; Left/Right split ASSUMED. "
            "A–F 0|1 masks exist (absorb_masks.py) but are NOT in the audio path. "
            "Hits use geometric wall crossings. "
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
