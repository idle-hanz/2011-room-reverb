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

import math
import threading
from dataclasses import astuple
from typing import Callable, Optional

import numpy as np

from early_field import SAMPLE_RATE_HZ
from fdn import fdn_delays_from_taps, mixer_lcr_fold
from render_pipeline import (
    DEFAULT_DEPTH,
    play_listen_scene,
    render_fdn_ir,
    tap_reflect_gain,
)
from surface_colour import image_in_early, parse_mute, parse_solo

WINDOW_S = 0.5
CAP_DB = 24.0
CAP_LIN = 10.0 ** (CAP_DB / 20.0)

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


def _scene(p: dict, sr: int = SAMPLE_RATE_HZ) -> dict:
    """Taps and loop gain. Same un-gated cards Play uses for inject and the tank."""
    built = play_listen_scene(p, sr)
    return {
        "p": p,
        "room": built["room"],
        "c": built["c"],
        "n_had": built["n_had"],
        "rate": built["rate"],
        "surfaces": built["surfaces"],
        "colour": built["colour"],
        "taps": built["taps"],
        "g_loop": built["g_loop"],
        "line_t60": built["line_t60"],
        "humidity": built["humidity"],
        "air_shelf": built["air_shelf"],
        "air_climate": built["air_climate"],
        "air_iso": built["air_iso"],
        "diffusion_master": built["diffusion_master"],
        "smooth": built["smooth"],
        "movement_ms": built["movement_ms"],
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


def _hashable(value):
    """Dict key. Lists and sets become tuples. Unknown objects become repr."""
    if isinstance(value, dict):
        return tuple((str(k), _hashable(value[k])) for k in sorted(value, key=str))
    if isinstance(value, (list, tuple)):
        return tuple(_hashable(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_hashable(v) for v in value), key=repr))
    if isinstance(value, float):
        return float(value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _hashable(item())
        except (TypeError, ValueError):
            pass
    return repr(value)


def _colour_key(colour) -> tuple:
    hpf = getattr(colour, "_hpf_on", None)
    if isinstance(hpf, dict):
        hpf_key = tuple((k, bool(hpf[k])) for k in ("l", "c", "r") if k in hpf)
    else:
        hpf_key = None
    ids = getattr(colour, "preset_ids", None)
    if isinstance(ids, dict):
        id_key = tuple((k, str(ids[k])) for k in ("l", "c", "r") if k in ids)
    else:
        id_key = None
    return (
        type(colour).__name__,
        getattr(colour, "mode", None),
        getattr(colour, "impl", None),
        int(getattr(colour, "sr", 0) or 0),
        bool(getattr(colour, "measured", False)),
        bool(getattr(colour, "include_offaxis_shelf", True)),
        bool(getattr(colour, "hpf_sides", False)),
        bool(getattr(colour, "hpf_centre", False)),
        str(getattr(colour, "preset_id", "") or ""),
        id_key,
        hpf_key,
    )


def _tail_key(scene: dict) -> tuple:
    """Fields render_fdn_ir takes for this tail. Constants included."""
    taps = scene["taps"]
    tap_key = tuple(_hashable(astuple(t)) for t in taps) if taps else ()
    return (
        tap_key,
        _hashable(scene["room"]),
        int(scene["rate"]),
        float(scene["c"]),
        float(WINDOW_S * 1000.0),
        float(scene["g_loop"]),
        float(DEFAULT_DEPTH),
        None,
        int(scene["n_had"]),
        _hashable(scene["surfaces"]),
        float(scene["humidity"]),
        0.0,
        float(scene["air_shelf"]),
        float(scene["diffusion_master"]),
        False,
        None,
        _colour_key(scene["colour"]),
        float(scene["line_t60"]),
        str(scene["air_climate"]),
        bool(scene["air_iso"]),
        False,
        bool(scene["smooth"]),
        float(scene["movement_ms"] or 0.0),
    )


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
