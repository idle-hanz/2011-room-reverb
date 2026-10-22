"""Signed desk matrix. The 477 fold stays on the old pan law.

A body with linear pan, no non-pan route, pair mode empty or stereo, and no
per-mic position is not an active desk. Those calls keep today's weights,
makeup, and blob. Section 7 is sent only when the signed weights differ from
what side() already does with mic gain, pan, and phase. A centre route at
gain 1 matches that pan law, so it omits the section. Both at gain 0.5 does
not, so it sends the section even though the six floats are the legacy fold.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Sequence, Tuple

LEGACY = (1.0, 0.0, 0.5, 0.5, 0.0, 1.0)
KEYS = ("ll", "lr", "cl", "cr", "rl", "rr")
SLOTS = ("l", "c", "r")


def route_name(value: Any, default: str = "pan") -> str:
    raw = str(value if value is not None else default).strip().lower()
    raw = raw.replace(" ", "").replace("→", "").replace("–", "").replace("—", "")
    raw = raw.replace("+", "").replace(",", "").replace("_", "")
    aliases = {
        "pan": "pan",
        "centre": "centre",
        "center": "centre",
        "both": "both",
        "l": "l",
        "left": "l",
        "r": "r",
        "right": "r",
        "s": "s",
        "sl-r": "s",
        "s+l-r": "s",
        "slr": "s",
    }
    return aliases.get(raw, "pan")


def pan_law_name(value: Any) -> str:
    raw = str(value if value is not None else "linear").strip().lower()
    raw = raw.replace(" ", "").replace("-", "").replace("_", "")
    if raw in ("power", "constant", "constantpower", "const"):
        return "power"
    return "linear"


def _has_pos(p: Mapping[str, Any], slot: str) -> bool:
    raw = p.get("mic_pos_" + slot)
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return True
    for key in ("mic_x_" + slot, "mic_y_" + slot, "mic_z_" + slot):
        if p.get(key) is not None and p.get(key) != "":
            return True
    return False


def routes_of(p: Optional[Mapping[str, Any]]) -> Tuple[str, str, str]:
    src = p or {}
    nested = src.get("mic_route")
    out = []
    for slot in SLOTS:
        if isinstance(nested, Mapping) and slot in nested:
            out.append(route_name(nested.get(slot)))
        else:
            out.append(route_name(src.get("mic_route_" + slot), "pan"))
    return out[0], out[1], out[2]


def desk_active(p: Optional[Mapping[str, Any]]) -> bool:
    """True only when the body asks for something other than the 477 fold."""
    if not p:
        return False
    if pan_law_name(p.get("pan_law")) != "linear":
        return True
    pair = str(p.get("pair_mode") or "").strip().lower()
    if pair in ("ms", "independent"):
        return True
    if any(r != "pan" for r in routes_of(p)):
        return True
    if any(_has_pos(p, slot) for slot in SLOTS):
        return True
    if p.get("s_detached"):
        return True
    third = str(p.get("third_mic") or "").strip().lower()
    if third in ("off", "room"):
        return True
    return False


def _clamp01(t: float) -> float:
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


def _amp(gain: float, phase: float) -> float:
    sign = -1.0 if float(phase) < 0.0 else 1.0
    g = float(gain)
    if g < 0.0:
        g = 0.0
    if g > 16.0:
        g = 16.0
    return g * sign


def _pair(route: str, gain: float, pan: float, phase: float, pan_law: str) -> Tuple[float, float]:
    g = _amp(gain, phase)
    name = route_name(route)
    if name == "centre":
        return g * 0.5, g * 0.5
    if name == "both":
        return g, g
    if name == "l":
        return g, 0.0
    if name == "r":
        return 0.0, g
    if name == "s":
        return g, -g
    t = _clamp01((float(pan) + 1.0) * 0.5)
    if pan_law == "power":
        left = math.cos(t * math.pi * 0.5)
        right = math.sin(t * math.pi * 0.5)
    else:
        left, right = 1.0 - t, t
    return g * left, g * right


def speaker_weights(
    gain_l: float,
    gain_c: float,
    gain_r: float,
    pan_l: float,
    pan_c: float,
    pan_r: float,
    phase_l: float,
    phase_c: float,
    phase_r: float,
    routes: Sequence[str],
    pan_law: str = "linear",
) -> dict:
    """Signed w[3][2]. S is (+g, −g). Both is (g, g). Centre is (g/2, g/2)."""
    law = pan_law_name(pan_law)
    names = [route_name(r) for r in routes]
    while len(names) < 3:
        names.append("pan")
    ll, lr = _pair(names[0], gain_l, pan_l, phase_l, law)
    cl, cr = _pair(names[1], gain_c, pan_c, phase_c, law)
    rl, rr = _pair(names[2], gain_r, pan_r, phase_r, law)
    return {"ll": ll, "lr": lr, "cl": cl, "cr": cr, "rl": rl, "rr": rr}


def is_legacy_fold(weights: Optional[Mapping[str, Any]]) -> bool:
    if not weights:
        return True
    for key, ref in zip(KEYS, LEGACY):
        if float(weights.get(key, 0.0)) != ref:
            return False
    return True


def _num(src: Mapping[str, Any], key: str, default: float) -> float:
    try:
        raw = src.get(key, default)
        if raw is None or raw == "":
            return float(default)
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _gains(src: Mapping[str, Any]) -> Tuple[float, float, float, float, float, float, float, float, float]:
    return (
        _num(src, "mic_gain_l", 1.0),
        _num(src, "mic_gain_c", 1.0),
        _num(src, "mic_gain_r", 1.0),
        _num(src, "mic_pan_l", -1.0),
        _num(src, "mic_pan_c", 0.0),
        _num(src, "mic_pan_r", 1.0),
        _num(src, "mic_phase_l", 1.0),
        _num(src, "mic_phase_c", 1.0),
        _num(src, "mic_phase_r", 1.0),
    )


def matrix_needed(p: Optional[Mapping[str, Any]]) -> bool:
    """True when side() from mic gain/pan/phase would not match the desk.

    Pan under the 2011 linear law stays on side(). A route whose signed pair
    equals that pan law (centre at gain 1) also stays off the blob. Both at
    half gain is the legacy six floats and still needs the section, because
    side() would halve them again.
    """
    if not desk_active(p):
        return False
    src = p or {}
    routes = routes_of(src)
    law = pan_law_name(src.get("pan_law"))
    if law == "linear" and all(r == "pan" for r in routes):
        return False
    gains = _gains(src)
    signed = speaker_weights(*gains, routes, law)
    from fdn import capsule_speaker_weights

    plain = capsule_speaker_weights(*gains)
    return any(float(signed[k]) != float(plain[k]) for k in KEYS)


def desk_w_list(weights: Optional[Mapping[str, Any]]) -> Optional[list]:
    """Six floats for blob section 7. Caller omits the key when matrix_needed is false."""
    if weights is None:
        return None
    return [float(weights[k]) for k in KEYS]


def mix_weights(
    gain_l: float = 1.0,
    gain_c: float = 1.0,
    gain_r: float = 1.0,
    pan_l: float = -1.0,
    pan_c: float = 0.0,
    pan_r: float = 1.0,
    phase_l: float = 1.0,
    phase_c: float = 1.0,
    phase_r: float = 1.0,
    desk: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Old pan body when the desk is idle or every route is still Pan / linear."""
    from fdn import capsule_speaker_weights

    if desk is None or not desk_active(desk):
        return capsule_speaker_weights(
            gain_l, gain_c, gain_r, pan_l, pan_c, pan_r, phase_l, phase_c, phase_r,
        )
    routes = routes_of(desk)
    law = pan_law_name(desk.get("pan_law"))
    if law == "linear" and all(r == "pan" for r in routes):
        return capsule_speaker_weights(
            gain_l, gain_c, gain_r, pan_l, pan_c, pan_r, phase_l, phase_c, phase_r,
        )
    return speaker_weights(
        gain_l, gain_c, gain_r, pan_l, pan_c, pan_r, phase_l, phase_c, phase_r,
        routes, law,
    )


def _s_unity_weights(src: Mapping[str, Any], weights: Mapping[str, Any]) -> dict:
    """Makeup sees an S route at ±1. Width then scales only that side.

    The heard matrix keeps the real gain. A muted S (gain 0) stays out of
    the peak, so turning it down does not invent level.
    """
    out = {k: float(weights[k]) for k in KEYS}
    routes = routes_of(src)
    pairs = (("ll", "lr"), ("cl", "cr"), ("rl", "rr"))
    for route, (lk, rk) in zip(routes, pairs):
        if route != "s":
            continue
        a = out[lk]
        if a == 0.0:
            continue
        sign = 1.0 if a > 0.0 else -1.0
        out[lk] = sign
        out[rk] = -sign
    return out


def fold_for(p: Optional[Mapping[str, Any]] = None, **overrides: Any) -> Tuple[dict, Optional[dict], Optional[list]]:
    """(weights, makeup weights or None, section-7 list or None).

    Makeup keeps the hardcoded 477 expression unless the desk is active and
    the fold is not those six floats. A muted room mic then cannot move the
    peak. An S route is normalised to ±1 for that peak, so Width scales the
    side and leaves the mid. Section 7 follows matrix_needed.
    """
    src = dict(p or {})
    src.update(overrides)
    gains = _gains(src)
    active = desk_active(src)
    weights = mix_weights(*gains, desk=src if active else None)
    send = matrix_needed(src)
    listed = desk_w_list(weights) if send else None
    if active and not is_legacy_fold(weights):
        makeup = _s_unity_weights(src, weights)
    else:
        makeup = None
    return weights, makeup, listed


def _fallback_pos(stand: Any, slot: str) -> Tuple[float, float, float]:
    from early_field import centre_position, mic_positions

    if slot == "l":
        return tuple(mic_positions(stand)[0])  # type: ignore[return-value]
    if slot == "r":
        return tuple(mic_positions(stand)[1])  # type: ignore[return-value]
    return tuple(centre_position(stand))  # type: ignore[return-value]


def _yaw_of(stand: Any, slot: str) -> float:
    if slot == "l":
        return float(stand.mlalr)
    if slot == "r":
        return float(stand.mralr)
    return float(stand.mcalr)


def _set_yaw(stand: Any, slot: str, yaw: float) -> None:
    if slot == "l":
        stand.mlalr = float(yaw)
    elif slot == "r":
        stand.mralr = float(yaw)
    else:
        stand.mcalr = float(yaw)


def _set_pos(stand: Any, slot: str, pos: Tuple[float, float, float]) -> None:
    setattr(stand, "pos_" + slot, (float(pos[0]), float(pos[1]), float(pos[2])))


def _set_colour_yaw(stand: Any, slot: str, yaw: Optional[float]) -> None:
    setattr(stand, "colour_yaw_" + slot, None if yaw is None else float(yaw))


def position_override(p: Mapping[str, Any], slot: str, fallback: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    raw = p.get("mic_pos_" + slot)
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        return (float(raw[0]), float(raw[1]), float(raw[2]))
    keys = ("mic_x_" + slot, "mic_y_" + slot, "mic_z_" + slot)
    if not any(p.get(k) is not None and p.get(k) != "" for k in keys):
        return None
    vals = []
    for i, key in enumerate(keys):
        if p.get(key) is None or p.get(key) == "":
            vals.append(float(fallback[i]))
        else:
            vals.append(float(p.get(key)))
    return (vals[0], vals[1], vals[2])


def _dist(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _slot_letter(value: Any, default: str) -> str:
    raw = str(value or default).strip().lower()[:1]
    return raw if raw in SLOTS else default


def apply_desk_geometry(stand: Any, p: Optional[Mapping[str, Any]]) -> Any:
    """Place an active desk. Idle calls return the stand unchanged.

    M/S pair parks S on M, aim M + 90°. While those positions match, colour
    and the toys shelf follow the M axis. Pattern gain stays on the S aim.
    A move off that point (s_detached, or a position that is not M) uses the
    S axis for both.
    """
    if stand is None:
        return stand
    from early_field import apply_capsule_heights
    apply_capsule_heights(stand, p or {})
    if not desk_active(p or {}):
        return stand
    stand.ms_decode = False
    src = p or {}
    for slot in SLOTS:
        _set_colour_yaw(stand, slot, None)
    for slot in SLOTS:
        base = _fallback_pos(stand, slot)
        ov = position_override(src, slot, base)
        if ov is not None:
            _set_pos(stand, slot, ov)
    pair = str(src.get("pair_mode") or "").strip().lower()
    if pair != "ms":
        return stand
    s_slot = _slot_letter(src.get("ms_s"), "l")
    m_slot = _slot_letter(src.get("ms_m"), "c")
    if m_slot == s_slot:
        m_slot = "c" if s_slot != "c" else "l"
    m_pos = _fallback_pos(stand, m_slot)
    m_yaw = _yaw_of(stand, m_slot)
    s_base = _fallback_pos(stand, s_slot)
    explicit = position_override(src, s_slot, s_base)
    detached = bool(src.get("s_detached"))
    if explicit is not None and _dist(explicit, m_pos) > 1.0e-4:
        detached = True
    if detached:
        _set_colour_yaw(stand, s_slot, None)
        return stand
    _set_pos(stand, s_slot, m_pos)
    _set_yaw(stand, s_slot, m_yaw + 0.5 * math.pi)
    _set_colour_yaw(stand, s_slot, m_yaw)
    return stand


place_stand = apply_desk_geometry
