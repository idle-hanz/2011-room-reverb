"""Binaural HRTF colour. One mirror-symmetric K=6 table for both ears.

Nearest grid node, no interpolation. The right ear at node n uses the left
record of mirror(n). FDN lines stay uncoloured in diffuse-tail mode; each
early tap and the direct path keep their own node record. No SciPy.
"""

from __future__ import annotations

import base64
import hashlib
import json

import numpy as np

from engine.early_field import binaural_pack_dir
from mic_colour.sos_fit import pack_record

SUPPORTED_RATES = (44100, 48000)


def unsupported_rate_notice(sr) -> str:
    return (
        f"Binaural colour is OFF: the audio device runs at {int(sr) / 1000:g} kHz; "
        "binaural HRTF tables exist for 44.1 and 48 kHz only."
    )


def _sph(az_deg, el_deg) -> np.ndarray:
    """SOFA unit vector: x front, y left, z up."""
    a = np.radians(np.asarray(az_deg, dtype=np.float64))
    e = np.radians(np.asarray(el_deg, dtype=np.float64))
    return np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], axis=-1)


def load_table(preset_id: str, sr: int):
    if int(sr) not in SUPPORTED_RATES:
        return None
    path = binaural_pack_dir() / "sos_tables" / str(int(sr)) / f"{preset_id}.json"
    if not path.is_file():
        return None
    table = json.loads(path.read_text(encoding="utf-8"))
    if int(table.get("fit_fs") or 0) != int(sr):
        return None
    return table


def tail_fir(preset_id: str, sr: int):
    """Shipped linear-phase M/S FIRs, or None when this rate has no table."""
    if int(sr) not in SUPPORTED_RATES:
        return None
    path = binaural_pack_dir() / "tail_ic" / f"{preset_id}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    fir = (data.get("fir") or {}).get(str(int(sr)))
    if not fir:
        return None
    hp = np.asarray(fir["hp"], dtype=np.float64)
    hm = np.asarray(fir["hm"], dtype=np.float64)
    return hp, hm


def _b64(rec: np.ndarray) -> str:
    raw = np.ascontiguousarray(rec, dtype=np.float32).tobytes()
    return base64.b64encode(raw).decode("ascii")


class BinauralColour:
    def __init__(self, preset_id: str, sr: int):
        self.preset_id = str(preset_id or "SADIE2_KU100")
        self.sr = int(sr)
        self.impl = "sos"
        self.mode = "BINAURAL"
        self.include_offaxis_shelf = False
        self.hpf_sides = False
        self.hpf_centre = False
        self.preset_ids = {"l": self.preset_id, "c": self.preset_id, "r": self.preset_id}
        table = load_table(self.preset_id, self.sr)
        self._table = table
        if table is None:
            self.measured = False
            self.notice = unsupported_rate_notice(self.sr)
            self._nodes = None
            self._mirror = None
            self._sos = None
            return
        self.measured = True
        self.notice = ""
        nodes = table["nodes"]
        az = [float(n[0]) for n in nodes]
        el = [float(n[1]) for n in nodes]
        self._nodes = _sph(az, el)
        self._mirror = [int(i) for i in table["mirror"]]
        self._sos = table["sos"]["L"]

    def _node(self, az: float, el: float) -> int:
        u = _sph([float(az)], [float(el)])[0]
        return int(np.argmax(self._nodes @ u))

    def _record_index(self, bus: str, az: float, el: float) -> int:
        n = self._node(az, el)
        if str(bus).lower() == "r":
            return int(self._mirror[n])
        return n

    def _packed(self, index: int) -> np.ndarray:
        return pack_record(np.asarray(self._sos[int(index)], dtype=np.float64))

    def record_for(self, bus: str, az: float, el: float):
        """Packed SOS record (tuple) for one ear, or None when colour is off."""
        if not self.measured or str(bus).lower() == "c":
            return None
        rec = self._packed(self._record_index(bus, az, el))
        return tuple(float(x) for x in rec)

    def all_records(self):
        if not self.measured:
            return []
        return [tuple(float(x) for x in self._packed(i)) for i in range(len(self._sos))]

    def bank_for(self, taps, taps_b, n: int, direct_index: int) -> dict:
        """Live bank. FDN slots are wires (−1). Early and direct use node records."""
        sr = int(self.sr)
        if not self.measured or not taps:
            out = {"on": False, "sr": sr, "rev": "", "same": False, "irs": []}
            if self.notice:
                out["notice"] = self.notice
            return out
        n = int(n)
        irs = []
        at = {}

        def slot(bus: str, tap) -> int:
            if bus == "c" or tap is None:
                return -1
            idx = self._record_index(
                bus,
                float(getattr(tap, "az_head_deg", 0.0)),
                float(getattr(tap, "el_head_deg", 0.0)),
            )
            hit = at.get(idx)
            if hit is not None:
                return hit
            irs.append(_b64(self._packed(idx)))
            at[idx] = len(irs) - 1
            return at[idx]

        def rows(src, buses):
            n_t = len(src) if src else 0
            out = {}
            for bus in buses:
                if n_t <= 0:
                    out[bus] = [-1] * n
                else:
                    out[bus] = [slot(bus, src[i % n_t]) for i in range(n)]
            return out

        direct_tap = taps[int(direct_index) % len(taps)]
        direct = {b: slot(b, direct_tap) for b in ("l", "c", "r")}
        fdn = {b: [-1] * n for b in ("l", "c", "r")}
        early = rows(taps, ("l", "r"))
        sig = {"direct": direct, "fdn": fdn, "early": early, "n_irs": len(irs)}
        if taps_b:
            bt = taps_b[int(direct_index) % len(taps_b)]
            sig["direct_b"] = {b: slot(b, bt) for b in ("l", "c", "r")}
            sig["fdn_b"] = {b: [-1] * n for b in ("l", "c", "r")}
            sig["early_b"] = rows(taps_b, ("l", "r"))
        sig["n_irs"] = len(irs)
        text = json.dumps(sig, sort_keys=True, separators=(",", ":"))
        rev = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        out = {
            "on": True,
            "sr": sr,
            "rev": rev,
            "same": False,
            "direct": direct,
            "fdn": fdn,
            "early": early,
            "irs": irs,
        }
        if taps_b:
            out["direct_b"] = sig["direct_b"]
            out["fdn_b"] = sig["fdn_b"]
            out["early_b"] = sig["early_b"]
        return out
