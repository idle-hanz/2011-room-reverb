"""SL1 · Surfaces "Room result" model (read-only; never touches the audio path).

Port of the box prototype roadmap/sound_tricks/proto2/surfdecay.py (room_target, face_bounce_db,
air_db_per_m, chamber_to_specular) plus the yardsticks used by the Room result panel and Auto-treat
(Makivirta target, EBU Tech 3276 Tm, Schroeder frequency, room modes).
Drop into software/engine/. Imports only surface_colour (software root) and air_iso (engine).

Tags: VERIFIED = standard formula / checked on the box; ASSUMED = engineering choice (see SURFACES_IN_LOOP.md).
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np

import surface_colour as SC
from air_iso import _iso_alpha_db_per_m, climate_record, rh_pct_from_slider
from maths_bands import exact_third_centres

C_AIR = 343.0
BANDS = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)          # octave centres
THIRD_40_8K = exact_third_centres(-14, 10)                                 # 24 third-octaves 40 Hz-8 kHz
THIRD_PANEL = exact_third_centres(-14, 11)                                 # 40 Hz-10 kHz (panel x-axis)
AX = {"x": ("A", "C"), "y": ("E", "F"), "z": ("B", "D")}
FACES = ("A", "B", "C", "D", "E", "F")
DEFAULT_SCATTER = 0.15                                                       # card "diffusion" fallback


def face_areas(W: float, H: float, L: float) -> Dict[str, float]:
    return {"A": L * H, "C": L * H, "B": W * H, "D": W * H, "E": W * L, "F": W * L}


def air_db_per_m(f, humidity: float, climate: str = "studio_20C_50RH") -> np.ndarray:
    """ISO 9613-1 air attenuation (dB/m) at the app's humidity slider. 0 = off (zeros)."""
    f = np.asarray(f, float)
    c = climate_record(climate)["conditions"]
    rh = rh_pct_from_slider(humidity, climate)
    if rh is None:
        return np.zeros_like(f)
    return _iso_alpha_db_per_m(f, c["temperature_c"], rh, c.get("pressure_kpa", 101.325))


def chamber_to_specular(alpha) -> np.ndarray:
    """Sabine (chamber) alpha -> per-bounce alpha: 1 - exp(-alpha). ASSUMED (Kuttruff); caps >1 data."""
    return 1.0 - np.exp(-np.clip(np.asarray(alpha, float), 0.0, 1.5))


def card_alpha(card: dict, f) -> np.ndarray:
    """alpha(f) of a face card: card['absorb_fn'] if present (treatment), else log-interp of absorb[]."""
    f = np.asarray(f, float)
    fn = card.get("absorb_fn")
    if fn is not None:
        return np.asarray(fn(f), float)
    hz = np.asarray(card.get("absorb_hz") or BANDS, float)
    return np.interp(np.log(f), np.log(hz), np.asarray(card.get("absorb"), float))


def _eq_db(card: dict, f, sr: float) -> np.ndarray:
    eq = card.get("eq") or {}
    out = np.zeros_like(np.asarray(f, float))
    st = []
    if abs(float(eq.get("low_shelf_db", 0) or 0)) >= 0.05:
        st.append(SC.rbj_lowshelf(sr, float(eq.get("low_shelf_hz", 200)), float(eq["low_shelf_db"])))
    if abs(float(eq.get("peak_db", 0) or 0)) >= 0.05:
        st.append(SC.rbj_peaking(sr, float(eq.get("peak_hz", 1000)), float(eq.get("peak_q", 1)), float(eq["peak_db"])))
    if abs(float(eq.get("high_shelf_db", 0) or 0)) >= 0.05:
        st.append(SC.rbj_highshelf(sr, float(eq.get("high_shelf_hz", 5000)), float(eq["high_shelf_db"])))
    z = np.exp(-1j * 2 * np.pi * np.asarray(f, float) / sr)
    for b0, b1, b2, a0, a1, a2 in st:
        out = out + 20 * np.log10(np.abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)))
    return out


def face_bounce_db(card: dict, f, sr: float = 48000, convert: bool = True, eq_in_loop: bool = True) -> np.ndarray:
    """Per-bounce reflection gain in dB (<= 0): absorption plus face-EQ CUTS only (no boosts in the loop)."""
    a_f = card_alpha(card, f)
    if convert:
        a_f = chamber_to_specular(a_f)
    r_db = 10 * np.log10(np.maximum(1 - a_f, 1e-4))
    if eq_in_loop:
        # Only the face EQ's CUTS add loss. (The prototype clipped the sum instead, so a boost could
        # cancel material absorption; fixed here. Box A/B renders used flat face EQ, so no number moves.)
        r_db = r_db + np.minimum(_eq_db(card, f, sr), 0.0)
    return np.minimum(r_db, 0.0)


def scatter_mean(surfaces: Dict[str, dict], S: Dict[str, float]) -> float:
    St = sum(S.values())
    return sum(S[k] * float(surfaces[k].get("diffusion", DEFAULT_SCATTER)) for k in S) / St


def room_target(W, H, L, surfaces, humidity, f, model: str = "arau_scatter", convert: bool = True,
                air: Optional[np.ndarray] = None, include_air: bool = True) -> np.ndarray:
    """Room-average T(f) in s. model: eyring | arau | arau_scatter (log-blend by mean scattering)."""
    f = np.asarray(f, float)
    V = W * H * L
    S = face_areas(W, H, L)
    St = sum(S.values())
    if include_air:
        m = (air if air is not None else air_db_per_m(f, humidity)) / (10 * math.log10(math.e))
    else:
        m = np.zeros_like(f)
    a = {k: 1 - 10 ** (face_bounce_db(surfaces[k], f, convert=convert) / 10) for k in S}
    abar = sum(S[k] * a[k] for k in S) / St
    TE = 0.161 * V / (-St * np.log(1 - abar) + 4 * m * V)
    if model == "eyring":
        return TE
    lnTA = 0.0
    for p, q in AX.values():
        Sx = S[p] + S[q]
        ax_a = (S[p] * a[p] + S[q] * a[q]) / Sx
        Tx = 0.161 * V / (-St * np.log(1 - ax_a) + 4 * m * V)
        lnTA = lnTA + (Sx / St) * np.log(Tx)
    if model == "arau":
        return np.exp(lnTA)
    s = scatter_mean(surfaces, S)
    return np.exp(s * np.log(TE) + (1 - s) * lnTA)


def anchored_target(W, H, L, surfaces, humidity, f, t_anchor: Optional[float]) -> np.ndarray:
    """Decay lock on: scale so the 500 Hz-1 kHz mean equals the dial; off: absolute."""
    T = room_target(W, H, L, surfaces, humidity, f)
    if t_anchor:
        Tm = float(np.mean(room_target(W, H, L, surfaces, humidity, np.array([500.0, 1000.0]))))
        T = T * (float(t_anchor) / Tm)
    return T


# ---- yardsticks -------------------------------------------------------------------------------
def makivirta_target(f, t_mid: float, air_ratio: Optional[Callable] = None) -> np.ndarray:
    """EQ_PLAN R1.3 (locked): flat T_mid, +0.2 s on log f from 300 Hz down to 50 Hz; above 2 kHz air only."""
    f = np.asarray(f, float)
    T = np.full_like(f, float(t_mid))
    lo = f < 300.0
    T[lo] += 0.2 * np.clip(np.log(300.0 / f[lo]) / np.log(300.0 / 50.0), 0, 1)
    if air_ratio is not None:
        hi = f > 2000.0
        T[hi] = T[hi] * air_ratio(f[hi]) / air_ratio(np.array([2000.0]))[0]
    return T


def air_ratio_fn(W, H, L, humidity, t_mid):
    V = W * H * L
    A_mid = 0.161 * V / t_mid
    m = lambda f: air_db_per_m(f, humidity) / (10 * math.log10(math.e))
    return lambda f: (0.161 * V / (A_mid + 4 * m(f) * V)) / t_mid


def ebu_tm(V: float) -> float:
    """EBU Tech 3276 / ITU-R BS.1116-3 nominal control-room T (VERIFIED)."""
    return 0.25 * (V / 100.0) ** (1.0 / 3.0)


def ebu_tolerance(f) -> np.ndarray:
    """(+tol, -tol) seconds per frequency, EBU 3276 Figure 1 simplified (VERIFIED, see SURFACES §3)."""
    f = np.asarray(f, float)
    up = np.where((f >= 200) & (f <= 4000), 0.05, np.where(f < 100, 0.3, 0.1))
    dn = np.where((f >= 200) & (f <= 4000), 0.05, 0.1)
    return np.stack([up, dn])


def ebu_check(f, T, V: float) -> List[bool]:
    tm = ebu_tm(V)
    up, dn = ebu_tolerance(f)
    T = np.asarray(T, float)
    return [bool((tm - d) <= t <= (tm + u)) for t, u, d in zip(T, up, dn)]


def schroeder_hz(T: float, V: float) -> float:
    return 2000.0 * math.sqrt(T / V)


def modes(W, H, L, fmax: float = 300.0):
    out = []
    for nx in range(12):
        for ny in range(12):
            for nz in range(12):
                if nx == ny == nz == 0:
                    continue
                f = C_AIR / 2 * math.sqrt((nx / W) ** 2 + (ny / H) ** 2 + (nz / L) ** 2)
                if f <= fmax:
                    k = sum(v > 0 for v in (nx, ny, nz))
                    out.append((f, (nx, ny, nz), {1: "axial", 2: "tangential", 3: "oblique"}[k]))
    return sorted(out)


# ---- API payload (/api/room_result) ------------------------------------------------------------
def room_result(W, H, L, surfaces, humidity, decay_s: Optional[float] = None, decay_lock: bool = True,
                cards_with_fn: Optional[Dict[str, dict]] = None, rendered_t20: Optional[dict] = None) -> dict:
    """JSON-ready Room result. surfaces: parsed cards; cards_with_fn: same with absorb_fn (treatment)."""
    cards = cards_with_fn or surfaces
    f = THIRD_PANEL
    V = W * H * L
    T_faces = room_target(W, H, L, cards, humidity, f, include_air=False)
    T_all = room_target(W, H, L, cards, humidity, f)
    Tm = float(np.mean(room_target(W, H, L, cards, humidity, np.array([500.0, 1000.0]))))
    anchor = float(decay_s) if (decay_lock and decay_s and decay_s > 0.05) else None
    scale = (anchor / Tm) if anchor else 1.0
    t_mid_target = anchor or Tm
    tgt = makivirta_target(f, t_mid_target, air_ratio_fn(W, H, L, humidity, t_mid_target))
    Tsh = float(np.mean(T_all[(f >= 500) & (f <= 1000)])) * scale
    within = [bool(abs(t * scale / g - 1) <= 0.10) for t, g in zip(T_all, tgt)]
    return {
        "f": [round(float(x), 2) for x in f],
        "T_faces": [round(float(x) * scale, 4) for x in T_faces],
        "T_faces_air": [round(float(x) * scale, 4) for x in T_all],
        "T_absolute_mid": round(Tm, 4),
        "anchor_s": anchor,
        "target": [round(float(x), 4) for x in tgt],
        "within_10pct": within,
        "n_within_10pct": int(sum(within)),
        "schroeder_hz": round(schroeder_hz(Tsh, V), 1),
        "ebu_tm": round(ebu_tm(V), 3),
        "ebu_pass": ebu_check(f, T_all * scale, V),
        "modes": [{"f": round(m[0], 1), "n": list(m[1]), "kind": m[2]} for m in modes(W, H, L, 300.0) if m[2] == "axial"],
        "rendered_t20": rendered_t20,
        "model": "Eyring/Arau scatter blend + ISO 9613 air; alpha 1-exp(-a); face EQ cuts only",
    }
