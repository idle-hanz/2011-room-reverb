"""Phase 3 live bank: SOS (default) or FIR, designed at the AudioContext rate.

Indices point at shared records. -1 is identity (on-axis, or no high-pass).
The records are not baked into inject scalars. Makeup stays a broadband
number computed from those scalars before this bank exists.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections import OrderedDict

import numpy as np

_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 512


def _deg(theta) -> float:
    return round(math.degrees(float(theta)), 4)


def _theta(tap, bus: str) -> float:
    if bus == "l":
        return float(tap.theta_l)
    if bus == "r":
        return float(tap.theta_r)
    return float(getattr(tap, "theta_c", 0.0))


def _parse_sr(value):
    if value is None or value == "":
        return None
    try:
        sr = int(value)
    except (TypeError, ValueError):
        return None
    if sr < 8000 or sr > 192000:
        return None
    return sr


def _remember(key, ir):
    _CACHE[key] = ir
    _CACHE.move_to_end(key)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


def _ir(colour, theta: float, bus: str):
    """Same rounding and high-pass stack as MicColour.payload_for. None is identity."""
    deg = _deg(theta)
    on = bool(colour._hpf_on.get(bus, False))
    impl = getattr(colour, "impl", "sos")
    key = (colour.preset_ids[bus], deg, int(colour.sr), on, impl)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    ir = colour.payload_for(float(theta), bus)
    if ir is not None:
        ir = np.asarray(ir, dtype=np.float32)
    _remember(key, ir)
    return ir


def _b64(ir: np.ndarray) -> str:
    raw = np.ascontiguousarray(ir, dtype=np.float32).tobytes()
    return base64.b64encode(raw).decode("ascii")


def _rev(blob) -> str:
    text = json.dumps(blob, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def _empty(on: bool, sr: int, notice: str = "") -> dict:
    out = {"on": bool(on), "sr": int(sr), "rev": "", "same": False}
    if notice:
        out["notice"] = notice
    return out


class _Indexer:
    def __init__(self, colour):
        self.colour = colour
        self.irs = []
        self._at = {}

    def idx(self, theta: float, bus: str) -> int:
        deg = _deg(theta)
        on = bool(self.colour._hpf_on.get(bus, False))
        impl = getattr(self.colour, "impl", "sos")
        key = (self.colour.preset_ids[bus], deg, int(self.colour.sr), on, impl)
        if key in self._at:
            return self._at[key]
        ir = _ir(self.colour, theta, bus)
        if ir is None:
            self._at[key] = -1
            return -1
        n = len(self.irs)
        self.irs.append(_b64(ir))
        self._at[key] = n
        return n


def _line_thetas(taps, n: int, bus: str):
    n_t = len(taps)
    out = []
    for i in range(n):
        out.append(_theta(taps[i % n_t], bus))
    return out


def build_live_bank(colour, taps, taps_b, n: int, direct_index: int, sample_rate, colour_rev: str = "") -> dict:
    """Colour bank for the three Play taps. `sample_rate` is the AudioContext rate.

    Missing rate does not design at 44.1 kHz. ASSUMED_TOYS and BYPASS return
    on=False so the worklet keeps today's unfiltered mix.
    """
    sr = _parse_sr(sample_rate)
    notice = str(getattr(colour, "notice", "") or "")
    if not getattr(colour, "measured", False) or sr is None or not taps:
        return _empty(False, sr or 0, notice)
    if int(colour.sr) != int(sr):
        return _empty(False, sr, notice)
    n = int(n)
    di = int(direct_index)
    n_t = len(taps)
    if n <= 0 or n_t <= 0:
        return _empty(False, sr, notice)
    direct_tap = taps[di % n_t]
    buses = ("l", "c", "r")
    sig = {
        "sr": int(sr),
        "impl": getattr(colour, "impl", "sos"),
        "presets": dict(colour.preset_ids),
        "hpf": {"l": bool(colour.hpf_sides), "c": bool(colour.hpf_centre)},
        "direct": {b: _deg(_theta(direct_tap, b)) for b in buses},
        "fdn": {b: [_deg(th) for th in _line_thetas(taps, n, b)] for b in buses},
        "early": {b: [_deg(th) for th in _line_thetas(taps, n, b)] for b in ("l", "r")},
    }
    if taps_b:
        n_b = len(taps_b)
        bt = taps_b[di % n_b]
        sig["direct_b"] = {b: _deg(_theta(bt, b)) for b in buses}
        sig["fdn_b"] = {b: [_deg(th) for th in _line_thetas(taps_b, n, b)] for b in buses}
        sig["early_b"] = {b: [_deg(th) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}
    rev = _rev(sig)
    if colour_rev and str(colour_rev) == rev:
        return {"on": True, "sr": int(sr), "rev": rev, "same": True}
    ix = _Indexer(colour)
    direct = {b: ix.idx(_theta(direct_tap, b), b) for b in buses}
    fdn = {b: [ix.idx(th, b) for th in _line_thetas(taps, n, b)] for b in buses}
    early = {b: [ix.idx(th, b) for th in _line_thetas(taps, n, b)] for b in ("l", "r")}
    out = {
        "on": True,
        "sr": int(sr),
        "rev": rev,
        "same": False,
        "direct": direct,
        "fdn": fdn,
        "early": early,
        "irs": ix.irs,
    }
    if taps_b:
        bt = taps_b[di % len(taps_b)]
        out["direct_b"] = {b: ix.idx(_theta(bt, b), b) for b in buses}
        out["fdn_b"] = {b: [ix.idx(th, b) for th in _line_thetas(taps_b, n, b)] for b in buses}
        out["early_b"] = {b: [ix.idx(th, b) for th in _line_thetas(taps_b, n, b)] for b in ("l", "r")}
    return out
