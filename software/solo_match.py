"""Play-only solo match. Render, presets, and goldens do not apply it.

Make-up is sqrt(E_full / E_solo). E is the broadband wet early-plus-tail
energy over the first 500 ms, at unity sends, L and R after the 477 fold.
The tail is the un-gated tank. Solo only gates the early spikes.

The value is measured when a solo letter starts and then held. A later
material edit keeps that gain, so the absorb change stays audible. No solo,
or the switch off, is exactly 1. The cap is +24 dB. The page ramps the
output GainNode over 50 ms. This module does not write the live FDN dict.
"""

from __future__ import annotations

import json
import math
import threading
from typing import Callable, Optional

import numpy as np

from early_field import (
    SAMPLE_RATE_HZ,
    SPEED_OF_SOUND_M_S,
    MicStand,
    compute_taps,
    direct_field_from_params,
    grid_bias_for_hadamard_n,
)
from fdn import fdn_delays_from_taps, mixer_lcr_fold, structure_gain_for_rt60
from mic_colour.colour import MicColour
from poly_room import compute_poly_taps, poly_on
from render_pipeline import (
    DEFAULT_DEPTH,
    _place_stand,
    movement_peak_ms,
    render_fdn_ir,
    smooth_active,
    tap_reflect_gain,
)
from surface_colour import (
    SURFACE_LETTERS,
    default_surfaces,
    image_in_early,
    parse_mute,
    parse_solo,
    parse_surfaces,
)

WINDOW_S = 0.5
CAP_DB = 24.0
CAP_LIN = 10.0 ** (CAP_DB / 20.0)
SMOOTH_S = 0.05

_TAIL: dict = {}
_TAIL_LOCK = threading.Lock()


def match_lin(e_full: float, e_solo: float) -> float:
    """sqrt(E_full / E_solo), capped. A silent solo takes the cap."""
    full = float(e_full)
    solo = float(e_solo)
    if not math.isfinite(full) or full <= 0.0:
        return 1.0
    if not math.isfinite(solo) or solo <= 0.0:
        return CAP_LIN
    gain = math.sqrt(full / solo)
    if gain > CAP_LIN:
        return CAP_LIN
    return gain


def resolve_gain(
    solo: Optional[str],
    enabled: bool,
    held_letter,
    held_gain,
    measure: Callable[[], float],
) -> float:
    """1 with no solo or the switch off. A posted hold for this letter is kept."""
    if not solo or not enabled:
        return 1.0
    letter = str(solo).upper()
    if held_letter is not None and str(held_letter).strip().upper() == letter:
        try:
            gain = float(held_gain)
        except (TypeError, ValueError):
            gain = 0.0
        if math.isfinite(gain) and gain > 0.0:
            return min(gain, CAP_LIN)
    gain = float(measure())
    if not math.isfinite(gain) or gain <= 0.0:
        return 1.0
    return min(gain, CAP_LIN)


def lin_to_db(gain: float) -> float:
    if gain <= 0.0 or not math.isfinite(gain):
        return float("-inf")
    return 20.0 * math.log10(float(gain))


def _n_had(p: dict) -> int:
    try:
        n = int(p.get("hadamard_n", 32))
    except (TypeError, ValueError):
        n = 32
    return n if n in (8, 16, 32) else 32


def _rate(p: dict, sr: int) -> int:
    raw = p.get("sample_rate")
    try:
        v = int(raw) if raw not in (None, "") else 0
    except (TypeError, ValueError):
        v = 0
    return v if v >= 8000 else int(sr)


def _surfaces(p: dict):
    raw = p.get("surfaces")
    if raw is None:
        return default_surfaces()
    return parse_surfaces(raw)


def _colour(p: dict, rate: int):
    if str(p.get("mic_setup") or "") == "binaural":
        from mic_colour.binaural import BinauralColour

        return BinauralColour(
            str(p.get("binaural_preset") or "SADIE2_KU100"),
            rate,
        )
    return MicColour(
        p.get("colour_mode"),
        p.get("mic_preset_l"),
        p.get("mic_preset_c"),
        p.get("mic_preset_r"),
        rate,
        hpf_engaged=bool(p.get("mic_hpf_engaged")),
        hpf_sides=p.get("mic_hpf_sides"),
        hpf_centre=p.get("mic_hpf_centre"),
        colour_impl=p.get("colour_impl") or "sos",
        hpf_l=p.get("mic_hpf_l"),
        hpf_r=p.get("mic_hpf_r"),
    )


def _scene(p: dict, sr: int = SAMPLE_RATE_HZ) -> dict:
    """Taps and loop gain. Same un-gated cards Play uses for inject and the tank."""
    room = (float(p["W"]), float(p["H"]), float(p["L"]))
    c = SPEED_OF_SOUND_M_S
    n_had = _n_had(p)
    rate = _rate(p, sr)
    surfaces = _surfaces(p)
    colour = _colour(p, rate)
    prep = direct_field_from_params(p)
    binaural = str(p.get("mic_setup") or "") == "binaural"
    if binaural:
        stand = MicStand.binaural(
            cx=float(prep.mic_centre[0]),
            cy=float(prep.mic_centre[1]),
            cz=float(prep.mic_centre[2]),
            head_yaw_deg=float(p.get("head_yaw_deg") or 0.0),
            preset=str(p.get("binaural_preset") or "SADIE2_KU100"),
        )
    else:
        stand = MicStand.from_prepare(
            prep,
            car_omni=p.get("car_omni") or 1.0,
            pattern_l=p.get("pattern_l"),
            pattern_c=p.get("pattern_c"),
            pattern_r=p.get("pattern_r"),
            yaw_l_deg=p.get("yaw_l_deg"),
            yaw_c_deg=p.get("yaw_c_deg"),
            yaw_r_deg=p.get("yaw_r_deg"),
            family_l=p.get("family_l"),
            family_c=p.get("family_c"),
            family_r=p.get("family_r"),
            polar_l=p.get("polar_l"),
            polar_c=p.get("polar_c"),
            polar_r=p.get("polar_r"),
            centre_dz=p.get("centre_dz") or 0.0,
            ms_decode=bool(p.get("ms_decode")),
            capsule_mm=p.get("capsule_mm") or 17.0,
        )
        stand = _place_stand(stand, p)
    shelf = bool(getattr(colour, "include_offaxis_shelf", True))
    pattern = not bool(getattr(colour, "measured", False))
    shape = p.get("room_shape")
    if poly_on(shape):
        taps = compute_poly_taps(
            room, prep.source, stand, shape,
            c=c, n=n_had,
            include_offaxis_shelf=shelf,
            include_pattern=pattern,
        )
    else:
        taps = compute_taps(
            room, prep.source, stand, c=c,
            grid=grid_bias_for_hadamard_n(n_had),
            origin="corner",
            z_face_4l=False,
            hadamard_n=n_had,
            include_offaxis_shelf=shelf,
            include_pattern=pattern,
            reaktor_parity=False,
        )
    g = float(max(0.0, min(1.0, float(p.get("fdn_g", 1.0))))) / float(n_had)
    decay_lock = bool(p.get("decay_lock"))
    decay_s = float(p.get("decay_s") or 0.0)
    delays = fdn_delays_from_taps(taps, sr=rate, c=c, n=n_had, channel="c")
    line_t60 = 0.0
    if decay_lock and decay_s > 0.05:
        g = structure_gain_for_rt60(delays, decay_s, rate, n_had) / float(n_had)
        lim = 0.99 / math.sqrt(float(n_had))
        g = float(max(0.0, min(lim, g)))
        line_t60 = float(decay_s)
    g_loop = (1.0 / math.sqrt(float(n_had))) if line_t60 > 0.0 else g
    air_on = p.get("air_iso")
    return {
        "p": p,
        "room": room,
        "c": c,
        "n_had": n_had,
        "rate": rate,
        "surfaces": surfaces,
        "colour": colour,
        "taps": taps,
        "g_loop": g_loop,
        "line_t60": line_t60,
        "humidity": float(p.get("humidity") or 0.0),
        "air_shelf": float(p.get("air_shelf") if p.get("air_shelf") is not None else 1.0),
        "air_climate": str(p.get("air_climate") or "studio_20C_50RH"),
        "air_iso": True if air_on is None else bool(air_on),
        "diffusion_master": float(
            p.get("diffusion_master") if p.get("diffusion_master") is not None else -0.25
        ),
        "smooth": smooth_active(p, surfaces),
        "movement_ms": movement_peak_ms(p, surfaces),
    }


def _window_n(rate: int) -> int:
    return int(float(rate) * (WINDOW_S * 1000.0) / 1000.0) + 1


def _early_stereo(scene: dict, solo, n_samp: int):
    """Play early spikes. Inject uses the un-gated cards. Solo is the gate."""
    taps = scene["taps"]
    n_had = scene["n_had"]
    surfaces = scene["surfaces"]
    solo_l = parse_solo(solo)
    mute_s = parse_mute(scene["p"].get("surfaces_mute"))
    acc = {ch: np.zeros(n_samp, dtype=np.float64) for ch in ("l", "c", "r")}
    n_t = len(taps) if taps else 0
    if n_t <= 0:
        return acc["l"], acc["r"]
    for ch in ("l", "c", "r"):
        delays = fdn_delays_from_taps(
            taps, sr=scene["rate"], c=scene["c"], n=n_had, channel=ch,
        )
        buf = acc[ch]
        for i in range(n_had):
            t = taps[i % n_t]
            if not image_in_early(t.n, solo_l, mute_s):
                continue
            if ch == "l":
                amp = float(t.level_l)
            elif ch == "r":
                amp = float(t.level_r)
            else:
                amp = float(getattr(t, "level_c", 0.5 * (float(t.level_l) + float(t.level_r))))
            amp *= tap_reflect_gain(t.n, surfaces)
            k = int(delays[i])
            if 0 <= k < n_samp:
                buf[k] += amp
    return mixer_lcr_fold(acc["l"], acc["r"], acc["c"])


def _energy(left, right) -> float:
    return float(np.dot(left, left) + np.dot(right, right))


def _tail_key(scene: dict) -> str:
    surf = scene["surfaces"]
    cards = {}
    for letter in SURFACE_LETTERS:
        card = surf.get(letter) if isinstance(surf, dict) else None
        if not isinstance(card, dict):
            cards[letter] = None
            continue
        cards[letter] = {
            "absorb": [float(x) for x in (card.get("absorb") or [])],
            "eq": card.get("eq"),
            "structure_dif": card.get("structure_dif"),
            "diffusion": card.get("diffusion"),
        }
    p = scene["p"]
    blob = {
        "room": scene["room"],
        "n": scene["n_had"],
        "sr": scene["rate"],
        "g": scene["g_loop"],
        "t60": scene["line_t60"],
        "humidity": scene["humidity"],
        "air_shelf": scene["air_shelf"],
        "air_climate": scene["air_climate"],
        "air_iso": scene["air_iso"],
        "diffusion_master": scene["diffusion_master"],
        "smooth": scene["smooth"],
        "movement_ms": scene["movement_ms"],
        "shape": p.get("room_shape"),
        "sx": p.get("sx"),
        "sy": p.get("sy"),
        "sz": p.get("sz"),
        "mcx": p.get("mcx"),
        "my": p.get("my"),
        "mcz": p.get("mcz"),
        "space": p.get("space"),
        "cards": cards,
        "colour": [
            p.get("colour_mode"),
            p.get("mic_preset_l"),
            p.get("mic_preset_c"),
            p.get("mic_preset_r"),
            p.get("mic_setup"),
        ],
    }
    return json.dumps(blob, sort_keys=True, default=str)


def _tail(scene: dict):
    key = _tail_key(scene)
    with _TAIL_LOCK:
        hit = _TAIL.get(key)
    if hit is not None:
        return hit
    length_ms = WINDOW_S * 1000.0
    left, right = render_fdn_ir(
        scene["taps"],
        scene["room"],
        scene["rate"],
        scene["c"],
        length_ms,
        scene["g_loop"],
        DEFAULT_DEPTH,
        None,
        n_lines=scene["n_had"],
        surfaces=scene["surfaces"],
        humidity=scene["humidity"],
        air_lp=0.0,
        air_shelf=scene["air_shelf"],
        diffusion_master=scene["diffusion_master"],
        apply_mic=False,
        weights=None,
        colour=scene["colour"],
        line_t60=scene["line_t60"],
        air_climate=scene["air_climate"],
        air_iso=scene["air_iso"],
        reaktor_parity=False,
        smooth=bool(scene["smooth"]),
        movement_ms=float(scene["movement_ms"] or 0.0),
    )
    pair = (np.asarray(left, dtype=np.float64), np.asarray(right, dtype=np.float64))
    with _TAIL_LOCK:
        _TAIL[key] = pair
        if len(_TAIL) > 4:
            _TAIL.pop(next(iter(_TAIL)))
    return pair


def _sum_energy(early, tail) -> float:
    el, er = early
    tl, tr = tail
    n = max(len(el), len(tl))

    def fit(a):
        if len(a) == n:
            return a
        out = np.zeros(n, dtype=np.float64)
        out[: len(a)] = a
        return out

    return _energy(fit(el) + fit(tl), fit(er) + fit(tr))


def window_energies(p: dict, letter: str, sr: int = SAMPLE_RATE_HZ):
    """(E_full, E_solo) over the first 500 ms. One shared un-gated tail."""
    scene = _scene(p, sr)
    n = _window_n(scene["rate"])
    tail = _tail(scene)
    full = _early_stereo(scene, None, n)
    solo = _early_stereo(scene, letter, n)
    return _sum_energy(full, tail), _sum_energy(solo, tail)


def measure_lin(p: dict, letter: str, sr: int = SAMPLE_RATE_HZ) -> float:
    full, solo = window_energies(p, letter, sr)
    return match_lin(full, solo)


def play_early_energy(p: dict, sr: int = SAMPLE_RATE_HZ) -> float:
    """Energy of the gated early spikes Play hears while a face is soloed.

    The mix zeros the tail during solo, so this is the monitored signal
    before the output gain. Delays sit inside 1 s, under the line cap.
    """
    scene = _scene(p, sr)
    n = int(scene["rate"] * 1.0) + 4
    left, right = _early_stereo(scene, p.get("surfaces_solo"), n)
    return _energy(left, right)


def attach_solo_match(live: dict, p: dict, enabled: bool, held_letter, held_gain) -> dict:
    """Stamp the held gain onto the HTTP payload. Does not enter live_fdn_params."""
    solo = parse_solo(p.get("surfaces_solo")) if isinstance(p, dict) else None

    def measure():
        return measure_lin(p, solo)

    gain = resolve_gain(solo, bool(enabled), held_letter, held_gain, measure)
    live["solo_match_lin"] = float(gain)
    live["solo_match_db"] = float(lin_to_db(gain))
    live["solo_match_letter"] = solo
    live["match_solo_level"] = bool(enabled)
    return live
