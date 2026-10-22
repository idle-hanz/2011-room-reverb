"""Per-render colour: one minimum-phase design per preset, angle, and sample rate."""

from __future__ import annotations

import math

import numpy as np

from mic_colour.design import apply_fir, design_ir
from mic_colour.modes import (
    ASSUMED_TOYS,
    COLOUR_FIR,
    COLOUR_SOS,
    fitter_on_for,
    parse_colour_impl,
    parse_colour_mode,
    shelf_in_scalars_for,
)
from mic_colour.preset_store import get_store, resolve_preset_id
from mic_colour.sos_fit import apply_sos, unpack_record


class MicColour:
    def __init__(
        self,
        mode,
        preset_l,
        preset_c,
        preset_r,
        sr: int,
        hpf_engaged: bool = False,
        hpf_sides: bool | None = None,
        hpf_centre: bool | None = None,
        colour_impl: str = "sos",
        hpf_l: bool | None = None,
        hpf_r: bool | None = None,
    ):
        self.mode = parse_colour_mode(mode)
        self.impl = parse_colour_impl(colour_impl)
        self.sr = int(sr)
        sides = bool(hpf_engaged) if hpf_sides is None else bool(hpf_sides)
        centre = bool(hpf_engaged) if hpf_centre is None else bool(hpf_centre)
        # Absent per-side keys stay on the shared side flag, so an unsplit body
        # is the same filters as before. Split sends mic_hpf_l / mic_hpf_r.
        left = sides if hpf_l is None else bool(hpf_l)
        right = sides if hpf_r is None else bool(hpf_r)
        self._hpf_on = {"l": left, "r": right, "c": centre}
        self.hpf_sides = sides
        self.hpf_centre = centre
        self.hpf_engaged = sides or centre
        self.measured = fitter_on_for(self.mode)
        self.notice = ""
        if self.measured and self.impl == COLOUR_SOS:
            from mic_colour.sos_table import rate_supported, unsupported_rate_notice
            if not rate_supported(self.sr):
                self.measured = False
                self.notice = unsupported_rate_notice(self.sr)
        self.early_toys = self.mode == ASSUMED_TOYS
        self.include_offaxis_shelf = shelf_in_scalars_for(self.mode)
        self.preset_ids = {
            "l": resolve_preset_id(preset_l, explicit=False),
            "c": resolve_preset_id(preset_c, explicit=False),
            "r": resolve_preset_id(preset_r, explicit=False),
        }
        self._models = {}
        self._hpf = {}
        self._ir = {}
        self._payload = {}
        if self.measured:
            store = get_store()
            for bus, mic_id in self.preset_ids.items():
                self._models[bus] = store.model_for(mic_id)
                self._hpf[bus] = store.hpf_of(mic_id)

    def ir_for(self, theta_rad: float, bus: str):
        key_bus = bus if bus in self._models else "c"
        deg = math.degrees(float(theta_rad))
        on = bool(self._hpf_on.get(key_bus, False))
        key = (key_bus, round(deg, 4), self.sr, on)
        if key in self._ir:
            return self._ir[key]
        ir = design_ir(
            self._models[key_bus],
            deg,
            self.sr,
            hpf=self._hpf.get(key_bus),
            hpf_engaged=on,
        )
        self._ir[key] = ir
        return ir

    def payload_for(self, theta_rad: float, bus: str):
        """Play bank entry: SOS record, FIR impulse, or None (identity)."""
        if not self.measured:
            return None
        key_bus = bus if bus in self._models else "c"
        deg = math.degrees(float(theta_rad))
        on = bool(self._hpf_on.get(key_bus, False))
        key = (key_bus, round(deg, 4), self.sr, on, self.impl)
        if key in self._payload:
            return self._payload[key]
        if self.impl == COLOUR_FIR:
            ir = self.ir_for(theta_rad, bus)
            payload = None if ir is None else np.asarray(ir, dtype=np.float32)
            self._payload[key] = payload
            return payload
        from mic_colour.sos_table import pack_for

        packed = pack_for(
            self.preset_ids[key_bus],
            self._models[key_bus],
            deg,
            self.sr,
            hpf=self._hpf.get(key_bus),
            hpf_engaged=on,
        )
        if packed is False:
            ir = self.ir_for(theta_rad, bus)
            payload = None if ir is None else np.asarray(ir, dtype=np.float32)
            self._payload[key] = payload
            return payload
        self._payload[key] = packed
        return packed

    def apply(self, buf: np.ndarray, theta_rad: float, bus: str) -> np.ndarray:
        """Filter one capsule buffer. Bypass and toys return the buffer unchanged."""
        if not self.measured:
            return buf
        if self.impl == COLOUR_SOS:
            payload = self.payload_for(theta_rad, bus)
            if payload is None:
                return buf
            sos = unpack_record(payload)
            if sos is not None:
                return apply_sos(buf, sos)
        ir = self.ir_for(theta_rad, bus)
        if ir is None:
            return buf
        return apply_fir(buf, ir)
