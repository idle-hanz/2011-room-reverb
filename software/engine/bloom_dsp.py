"""Bloom tail gain, colour, and pre colour. Python designs every coefficient.

The live dict and the blob omit these keys while Bloom is off (Amount 0,
Predelay 0, Bloom colour off, Pre colour off). An explicit off body matches
a body that never had the keys.

Fitted numbers are labelled in the comments. The packed doubles come from
the JSON files. The rounded figures in the run prompt are not what ships.
"""
from __future__ import annotations

import cmath
import json
import math
from pathlib import Path

import numpy as np

# UAD-round2-fit, static_fit.json natural.T / glue.T. Current dynamics.
# Section A's two-stage opto and Glue knee 6 / attack 6.5 ms are not used.
_NAT_T = -25.6
_GLUE_T = -28.3

# Natural, compressor_presets.json + models.py opto_light_memory.
# UAD-measured attack split. Release weights are the current model.
_NAT_A1 = 0.002
_NAT_A2 = 0.16
_NAT_WF = 0.8
_NAT_TM = 0.3
_NAT_TMD = 0.3
_NAT_W0 = 0.12
_NAT_WM = 0.11
_NAT_TF0 = 0.032
_NAT_TFM = 0.045
_NAT_TS = 0.9

# Glue current, models.py series_two_section. Knee stays 12. Attack stays 10 ms.
_GLUE_R = 4.0
_GLUE_W = 12.0
_GLUE_TA = 0.010
_GLUE_T1 = 0.0428
_GLUE_T2 = 5.1
_GLUE_C1 = 0.47e-6
_GLUE_C2 = 6.8e-6

_PRESETS = ("natural", "glue", "room_crush", "nuke", "swell")
_PRE_TYPES = ("off", "u610a", "neve1073")

_DATA = (
    Path(__file__).resolve().parents[2]
    / "handoff_build_support_2"
    / "roadmap"
    / "bloom"
    / "uad"
    / "round3"
    / "data"
)
_PRESETS_JSON = (
    Path(__file__).resolve().parents[2]
    / "handoff_build_support_2"
    / "roadmap"
    / "bloom"
    / "compressor_presets.json"
)


def _f(v, d: float) -> float:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return d
    if n != n or n in (float("inf"), float("-inf")):
        return d
    return n


def _b(v, d: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return d
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if s in ("", "0", "false", "no", "off"):
        return False
    if s in ("1", "true", "yes", "on"):
        return True
    return d


def preset_id(v) -> str:
    s = str(v or "natural").strip().lower().replace("-", "_").replace(" ", "_")
    if s in ("roomcrush", "room_crush"):
        return "room_crush"
    if s in ("u610", "610", "610a", "u610a"):
        return "natural"
    return s if s in _PRESETS else "natural"


def pre_type(v) -> str:
    s = str(v or "off").strip().lower().replace("-", "").replace(" ", "")
    if s in ("", "off", "none", "0", "false"):
        return "off"
    if s in ("u610a", "610a", "610"):
        return "u610a"
    if s in ("neve", "neve1073", "1073"):
        return "neve1073"
    return "off"


def amount_db(amount_percent, cap_db: float) -> float:
    """Amount 0-100 percent maps to 0..12 dB, then the preset cap."""
    pct = min(100.0, max(0.0, _f(amount_percent, 0.0)))
    cap = min(12.0, max(0.0, _f(cap_db, 12.0)))
    return min(cap, pct / 100.0 * 12.0)


def wet_gain_db(amount_db_v: float, gr_positive: float, max_duck_db: float) -> float:
    """Tail gain in dB. gr_positive is the detector's GR (0 or above).

    The Bloom law uses GR_dB <= 0, so the sign flips here.
    """
    gr = -max(0.0, float(gr_positive))
    hi = float(amount_db_v)
    lo = -max(0.0, float(max_duck_db))
    g = hi + gr
    if g > hi:
        return hi
    if g < lo:
        return lo
    return g


def bloom_is_on(p: dict) -> bool:
    """True only when the tail gain, the predelay, or a pre type is actually on.

    bloom_colour true at Amount 0 stays off. pre_drive with type off stays off.
    A preset id alone stays off. This is Hard rule 4.
    """
    if not isinstance(p, dict):
        return False
    if _f(p.get("bloom_amount"), 0.0) > 0.0:
        return True
    if _f(p.get("predelay_ms"), 0.0) > 0.0:
        return True
    if pre_type(p.get("pre_colour")) != "off":
        return True
    return False


def predelay_samples(ms, sr: float) -> int:
    """Integer samples, 0 to 100 ms. 0 is the absent section.

    The ring is 4800 and the write happens before the read, so a delay of
    4800 would come back as the sample just written. Play and Render both
    stop at 4799. A 100 ms request at 48 kHz is that cap.
    """
    m = min(100.0, max(0.0, _f(ms, 0.0)))
    n = int(round(m * float(sr) / 1000.0))
    if n < 0:
        return 0
    if n > 4799:
        return 4799
    return n


def _load(name: str) -> dict:
    return json.loads((_DATA / name).read_text(encoding="utf-8"))


def _caps() -> dict:
    """max_duck_db and amount_cap_db from compressor_presets.json bloom_defaults."""
    doc = json.loads(_PRESETS_JSON.read_text(encoding="utf-8"))
    rows = doc.get("bloom_presets") or []
    out = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            continue
        bd = row.get("bloom_defaults") or {}
        out[str(row["id"])] = {
            "max_duck_db": _f(bd.get("max_duck_db"), 12.0),
            "amount_cap_db": _f(bd.get("amount_cap_db"), 12.0),
            "amount_db": _f(bd.get("amount_db"), 0.0),
        }
    return out


def gc_soft(x_db: float, T: float, R: float, W: float, R2: float, K2: float) -> float:
    """One-sample Giannoulis soft knee. Returns positive GR in dB.

    UAD-round2-fit where T/R/W come from a fit file. The equation is the
    current model (roadmap bloom round2 scripts models.py gc_soft).
    """
    d = x_db - T
    if W > 0.0 and 2.0 * d < -W:
        y = x_db
    elif W > 0.0 and abs(2.0 * d) <= W:
        y = x_db + (1.0 / R - 1.0) * (d + W / 2.0) ** 2 / (2.0 * W)
    elif W <= 0.0 and d <= 0.0:
        y = x_db
    else:
        y = T + d / R
    if R2 > 0.0 and d > K2:
        y = T + K2 / R + (d - K2) / R2
    gr = x_db - y
    if gr < 0.0:
        return 0.0
    return gr


def k_one(tau_s: float, sr: float) -> float:
    t = tau_s if tau_s > 1e-8 else 1e-8
    return 1.0 - math.exp(-1.0 / (t * sr))


class DetState:
    """Per-engine follower state. Zero at scrub. Not cleared on a room reload."""

    __slots__ = (
        "u", "fa", "sa", "rf", "rs", "w", "mode", "M",
        "f", "s", "g", "G", "cnt", "idle", "quiet",
        "v1", "v2", "vc", "vu",
        "sc_z",
    )

    def __init__(self) -> None:
        self.u = 0.0
        self.fa = 0.0
        self.sa = 0.0
        self.rf = 0.0
        self.rs = 0.0
        self.w = 0.0
        self.mode = 0
        self.M = 0.0
        self.f = 0.0
        self.s = 0.0
        self.g = 0.0
        self.G = 0.0
        self.cnt = 0
        self.idle = 1
        self.quiet = 0
        self.v1 = 0.0
        self.v2 = 0.0
        self.vc = 0.0
        self.vu = 0.0
        self.sc_z = 0.0


def sidechain_b0(sr: float) -> float:
    """First-order Butterworth high-pass at 100 Hz. b0 of the bilinear section.

    a1 = 1 - 2*b0. Same coefficients as dyn3 and the Play DF2T.
    """
    k = math.tan(math.pi * 100.0 / float(sr))
    return 1.0 / (1.0 + k)


def sidechain_hp(x: float, st: DetState, b0: float) -> float:
    """DF2T Butterworth. b0 is packed. a1 = 1 - 2*b0. State matches sosfilt."""
    if not (b0 > 0.0 and b0 < 1.0):
        return x
    a1 = 1.0 - 2.0 * b0
    y = b0 * x + st.sc_z
    st.sc_z = -b0 * x - a1 * y
    return y


def step_natural(st: DetState, x_db: float, c: dict) -> float:
    """Current opto. Not the round-3 opto2. UAD-measured times, current weights."""
    T = math.pow(10.0, x_db / 20.0) - 1.0
    if T < 0.0:
        T = 0.0
    if T > st.u:
        if st.mode != 1:
            st.fa = st.u
            st.sa = st.u
            st.mode = 1
        st.fa += (T - st.fa) * c["ka1"]
        st.sa += (T - st.sa) * c["ka2"]
        st.u = c["wf"] * st.fa + (1.0 - c["wf"]) * st.sa
    else:
        if st.mode != 2:
            st.rf = st.u
            st.rs = st.u
            w = _NAT_W0 + _NAT_WM * st.M
            if w < 0.0:
                w = 0.0
            if w > 0.9:
                w = 0.9
            st.w = w
            st.mode = 2
        tf = _NAT_TF0 * c["rel"] + _NAT_TFM * st.M * c["rel"]
        if tf < 1e-6:
            tf = 1e-6
        krf = 1.0 - math.exp(-1.0 / (tf * c["sr"]))
        st.rf += (T - st.rf) * krf
        st.rs += (T - st.rs) * c["ks"]
        st.u = (1.0 - st.w) * st.rf + st.w * st.rs
    if st.u > 0.06:
        st.M += (1.0 - st.M) * c["km"]
    else:
        st.M -= st.M * c["kmd"]
    if st.u < 0.0:
        return 0.0
    return 20.0 * math.log10(1.0 + st.u)


def step_glue(st: DetState, tgt: float, c: dict) -> float:
    v = st.v1 + st.v2
    cur = 0.0
    if tgt > v:
        cur = (tgt - v) * c["Cs"] / c["tau_att"]
    dt = c["dt"]
    st.v1 = (st.v1 + dt * cur / c["C1"]) / (1.0 + dt / c["tau1"])
    st.v2 = (st.v2 + dt * cur / c["C2"]) / (1.0 + dt / c["tau2"])
    return st.v1 + st.v2


def step_nuke(st: DetState, tgt: float, c: dict) -> float:
    """UAD-round3-fit, fit_nuke.json nuke_det. dyn3.py nuke_det."""
    t = tgt
    if t > st.f:
        st.f += (t - st.f) * c["ka"]
    else:
        st.f += (t - st.f) * c["kf"]
    if t > st.s:
        st.s += (t - st.s) * c["ka"]
    else:
        st.s += (t - st.s) * c["ks"]
    if t > 0.5:
        st.G += (1.0 - st.G) * c["kg"]
    else:
        st.G -= st.G * c["kg"] * 0.25
    w = c["ws0"] + c["wsg"] * st.G
    if w > 0.95:
        w = 0.95
    return (1.0 - w) * st.f + w * st.s


def step_room_crush(st: DetState, tgt: float, c: dict) -> float:
    """UAD-round3-fit, fit_room_crush.json rc_det2. Creep is not built."""
    if st.idle and tgt > 0.0:
        st.cnt += 1
        if st.cnt > c["nl"]:
            st.idle = 0
    if tgt > st.g and not st.idle:
        st.f += (tgt - st.f) * c["k1"]
        st.s += (tgt - st.s) * c["k2"]
        mix = c["wa"] * st.f + (1.0 - c["wa"]) * st.s
        if mix > st.g:
            st.g = mix
    elif tgt <= st.g:
        te = c["tr"] * (max(st.g, 0.5) / 10.0) ** c["beta"]
        if te < 1e-8:
            te = 1e-8
        kr = 1.0 - math.exp(-1.0 / (te * c["sr"]))
        st.g += (tgt - st.g) * kr
        if st.f > st.g:
            st.f = st.g
        if st.s > st.g:
            st.s = st.g
    if tgt <= 0.0:
        st.quiet += 1
    else:
        st.quiet = 0
    if st.g < 0.05 and st.quiet > c["nq"]:
        st.idle = 1
        st.cnt = 0
    return st.g


def step_swell(st: DetState, vt: float, c: dict) -> float:
    """UAD-round3-fit, fit_swell.json. No 10 dB clamp inside this computer.

    The tail safety cap is wet_gain_db, max_duck_db 10 for Swell.
    """
    cur = (vt - st.vc) / c["Ratt"] if vt > st.vc else 0.0
    iu = (st.vc - st.vu) / c["RU"]
    dt = c["dt"]
    st.vc += dt * (cur - st.vc / c["RT"] - iu) / c["CT"]
    st.vu += dt * iu / c["CU"]
    if st.vc < 0.0:
        v = 0.0
    else:
        v = st.vc
    return 18.1 * math.log1p(v / 8.06)


def design(p: dict, sr: float) -> dict | None:
    """Coefficients for one engine. None when Bloom is off. Per sample, no control rate."""
    if not bloom_is_on(p):
        return None
    name = preset_id(p.get("bloom_preset"))
    caps = _caps().get(name) or {"max_duck_db": 12.0, "amount_cap_db": 12.0}
    att = min(4.0, max(0.25, _f(p.get("bloom_attack_scale"), 1.0)))
    rel = min(4.0, max(0.25, _f(p.get("bloom_release_scale"), 1.0)))
    sr_f = float(sr) if float(sr) >= 8000.0 else 48000.0
    out = {
        "preset": name,
        "sr": sr_f,
        "amount_db": amount_db(p.get("bloom_amount"), caps["amount_cap_db"]),
        "max_duck_db": caps["max_duck_db"],
        "predelay_n": predelay_samples(p.get("predelay_ms"), sr_f),
        "colour": bool(_b(p.get("bloom_colour"), False) and _f(p.get("bloom_amount"), 0.0) > 0.0),
        "glue_colour": bool(_b(p.get("glue_colour"), False)),
        "pre": pre_type(p.get("pre_colour")),
        "pre_drive_db": _f(p.get("pre_drive_db"), 0.0),
        "att": att,
        "rel": rel,
    }
    if name == "nuke":
        fit = _load("fit_nuke.json")["params"]
        # UAD-round3-fit. ×1 keeps the JSON attack (0.325 ms), under the 0.1 ms floor exception.
        ta = float(fit["ta"]) * att
        if not (att == 1.0):
            if ta < 1.0e-4:
                ta = 1.0e-4
        out.update({
            "T": float(fit["T"]),
            "R": 1.0e6,
            "W": 0.0,
            "R2": 0.0,
            "K2": 0.0,
            "sc_a": sidechain_b0(sr_f),
            "ka": k_one(ta, sr_f),
            "kf": k_one(float(fit["trf"]) * rel, sr_f),
            "ks": k_one(float(fit["trs"]) * rel, sr_f),
            "kg": k_one(float(fit["tg"]), sr_f),
            "ws0": float(fit["ws0"]),
            "wsg": float(fit["wsg"]),
            "hpf": True,
        })
    elif name == "room_crush":
        fit = _load("fit_room_crush.json")["params"]
        ta1 = max(1.0e-4, float(fit["ta1"]) * att)
        ta2 = max(1.0e-4, float(fit["ta2"]) * att)
        out.update({
            "T": float(fit["T"]),
            "R": float(fit["R"]),
            "W": float(fit["W"]),
            "R2": 0.0,
            "K2": 0.0,
            "k1": k_one(ta1, sr_f),
            "k2": k_one(ta2, sr_f),
            "wa": float(fit["wa"]),
            "nl": int(float(fit["lag"]) * sr_f),
            "tr": float(fit["tr"]) * rel,
            "beta": float(fit["beta"]),
            "nq": int(0.020 * sr_f),
            "hpf": False,
        })
    elif name == "swell":
        fit = _load("fit_swell.json")["params"]
        ta = max(1.0e-4, float(fit["ta"]) * att)
        ct = float(fit["CT"])
        out.update({
            "T": float(fit["T"]),
            "R": float(fit["R"]),
            "W": float(fit["W"]),
            "R2": float(fit["R2"]),
            "K2": float(fit["K2"]),
            "Ratt": ta / ct,
            "CT": ct,
            "RT": float(fit["RT"]),
            "RU": float(fit["RU"]),
            "CU": float(fit["CU"]),
            "dt": 1.0 / sr_f,
            "sc_a": sidechain_b0(sr_f),
            "hpf": True,
        })
    elif name == "glue":
        ta = max(1.0e-4, _GLUE_TA * att)
        c1 = _GLUE_C1
        c2 = _GLUE_C2
        out.update({
            "T": _GLUE_T,
            "R": _GLUE_R,
            "W": _GLUE_W,
            "R2": 0.0,
            "K2": 0.0,
            "tau_att": ta,
            "tau1": _GLUE_T1 * rel,
            "tau2": _GLUE_T2 * rel,
            "C1": c1,
            "C2": c2,
            "Cs": c1 * c2 / (c1 + c2),
            "dt": 1.0 / sr_f,
            "hpf": False,
        })
    else:
        a1 = max(1.0e-4, _NAT_A1 * att)
        a2 = max(1.0e-4, _NAT_A2 * att)
        out.update({
            "T": _NAT_T,
            "R": 5.0,
            "W": 8.0,
            "R2": 4.0,
            "K2": 20.0,
            "ka1": k_one(a1, sr_f),
            "ka2": k_one(a2, sr_f),
            "wf": _NAT_WF,
            "km": k_one(_NAT_TM, sr_f),
            "kmd": k_one(_NAT_TMD, sr_f),
            "ks": k_one(_NAT_TS * rel, sr_f),
            "rel": rel,
            "hpf": False,
        })
    return out


def step_gr(st: DetState, x: float, c: dict) -> float:
    """Positive GR in dB for one dry sample. Linked caller passes max(|xA|,|xB|)."""
    sc = x
    if c.get("hpf"):
        sc = sidechain_hp(x, st, c["sc_a"])
    x_db = 20.0 * math.log10(abs(sc) + 1e-12)
    name = c["preset"]
    if name == "natural":
        tgt = gc_soft(x_db, c["T"], c["R"], c["W"], c["R2"], c["K2"])
        return step_natural(st, tgt, c)
    if name == "glue":
        tgt = gc_soft(x_db, c["T"], c["R"], c["W"], 0.0, 0.0)
        return step_glue(st, tgt, c)
    if name == "room_crush":
        tgt = gc_soft(x_db, c["T"], c["R"], c["W"], 0.0, 0.0)
        return step_room_crush(st, tgt, c)
    if name == "nuke":
        tgt = gc_soft(x_db, c["T"], c["R"], c["W"], 0.0, 0.0)
        return step_nuke(st, tgt, c)
    tgt = gc_soft(x_db, c["T"], c["R"], c["W"], c["R2"], c["K2"])
    vt = 8.06 * (math.exp(tgt / 18.1) - 1.0)
    return step_swell(st, vt, c)


_PID = {"natural": 0.0, "glue": 1.0, "room_crush": 2.0, "nuke": 3.0, "swell": 4.0}


# Render factors stay at the retry-3 values. Play Neve is 1x: 8x, 4x, and 2x
# missed the decay-8 cube. Play Room Crush colour is 1x: with Neve at 1x the
# cube still missed silence-late by 0.018 ms. Natural and Swell stay 2x.
# 610-A stays 8x on both engines.
_COLOUR_OS = {
    "natural": (2.0, 0.0),
    "swell": (2.0, 0.0),
    "room_crush": (2.0, 0.0),
    "glue": (1.0, 1.0),
    "nuke": (1.0, 1.0),
}
_PLAY_COLOUR_OS = {
    "natural": (2.0, 0.0),
    "swell": (2.0, 0.0),
    "room_crush": (1.0, 0.0),
    "glue": (1.0, 1.0),
    "nuke": (1.0, 1.0),
}
RENDER_NEVE_OS = 8.0
PLAY_NEVE_OS = 1.0


def pack_coeffs(spec: dict, play: bool = False) -> list:
    """40 floats, then 5 per EQ biquad. Section 10. Absent unless amount_db > 0.

    Slots 0..25 are the follower. 26..39 are Bloom colour (zeros when colour is off).
    EQ biquads are a0=1, series, b0 b1 b2 a1 a2. UAD-round3-fit from eq_fit.json.
    """
    c = [0.0] * 40
    name = spec["preset"]
    c[0] = _PID.get(name, 0.0)
    c[1] = float(spec["amount_db"])
    c[2] = float(spec["max_duck_db"])
    c[3] = float(spec["T"])
    c[4] = float(spec.get("R", 0.0))
    c[5] = float(spec.get("W", 0.0))
    c[6] = float(spec.get("R2", 0.0))
    c[7] = float(spec.get("K2", 0.0))
    c[8] = 1.0 if spec.get("hpf") else 0.0
    c[9] = float(spec.get("sc_a", 0.0))
    if name == "natural":
        c[10] = float(spec["ka1"])
        c[11] = float(spec["ka2"])
        c[12] = float(spec["wf"])
        c[13] = float(spec["km"])
        c[14] = float(spec["kmd"])
        c[15] = float(spec["ks"])
        c[16] = float(spec["rel"])
        c[17] = float(spec["sr"])
        # UAD-measured release weights, models.py. Packed so C does not invent them.
        c[18] = _NAT_W0
        c[19] = _NAT_WM
        c[20] = _NAT_TF0
        c[21] = _NAT_TFM
        c[22] = _NAT_TS
    elif name == "glue":
        c[10] = float(spec["tau_att"])
        c[11] = float(spec["tau1"])
        c[12] = float(spec["tau2"])
        c[13] = float(spec["C1"])
        c[14] = float(spec["C2"])
        c[15] = float(spec["Cs"])
        c[16] = float(spec["dt"])
    elif name == "room_crush":
        c[10] = float(spec["k1"])
        c[11] = float(spec["k2"])
        c[12] = float(spec["wa"])
        c[13] = float(spec["nl"])
        c[14] = float(spec["tr"])
        c[15] = float(spec["beta"])
        c[16] = float(spec["nq"])
        c[17] = float(spec["sr"])
    elif name == "nuke":
        c[10] = float(spec["ka"])
        c[11] = float(spec["kf"])
        c[12] = float(spec["ks"])
        c[13] = float(spec["kg"])
        c[14] = float(spec["ws0"])
        c[15] = float(spec["wsg"])
    else:
        c[10] = float(spec["Ratt"])
        c[11] = float(spec["CT"])
        c[12] = float(spec["RT"])
        c[13] = float(spec["RU"])
        c[14] = float(spec["CU"])
        c[15] = float(spec["dt"])
    col = _colour_pack(spec, play=play)
    for i, v in enumerate(col):
        c[26 + i] = v
    c.extend(_eq_pack(spec))
    return c


def _colour_on(spec: dict) -> bool:
    if float(spec.get("amount_db") or 0.0) <= 0.0:
        return False
    if spec.get("preset") == "glue":
        return bool(spec.get("glue_colour"))
    return bool(spec.get("colour"))


def _colour_pack(spec: dict, play: bool = False) -> list:
    """14 floats at slots 26..39. Zeros when this preset's colour is off."""
    out = [0.0] * 14
    if not _colour_on(spec):
        return out
    choice = _load("colour_choice.json")[spec["preset"]]
    # UAD-round3-fit, colour_choice.json. fam 0 poly, fam 1 biased tanh.
    out[0] = 1.0
    out[1] = float(choice.get("fam", 0))
    vr_db = float(choice.get("vr_db", 0.0))
    out[2] = 1.0 if vr_db == 0.0 else 10.0 ** (vr_db / 20.0)
    out[3] = float(choice.get("a2", 0.0))
    out[4] = float(choice.get("a3", 0.0))
    out[5] = float(choice.get("b", 0.0))
    out[6] = float(choice.get("d0", 1.0))
    out[7] = float(choice.get("Gs", 1.0))
    fc = float(choice.get("fc", 0.0) or 0.0)
    sr = float(spec["sr"])
    out[8] = math.exp(-2.0 * math.pi * fc / sr) if fc > 0.0 else 0.0
    out[9] = math.exp(-2.0 * math.pi * 5.0 / sr)
    side_in = spec["preset"] == "swell"
    table = _PLAY_COLOUR_OS if play else _COLOUR_OS
    os_n, adaa = table.get(spec["preset"], (1.0, 0.0))
    # The table picks the factor. Render Room Crush is 2x. Play Room Crush is 1x.
    out[10] = float(os_n)
    out[11] = float(adaa)
    out[12] = 1.0 if side_in else 0.0
    return out


def _eq_pack(spec: dict) -> list:
    if not _colour_on(spec):
        return []
    rows = _load("eq_fit.json")[spec["preset"]]["biquads"]
    out = []
    for bq in rows:
        b = bq["b"]
        a = bq["a"]
        out.extend((float(b[0]), float(b[1]), float(b[2]), float(a[1]), float(a[2])))
    return out


# derived: 2 biquads fit to kernels.npz klin_* , delay removed at the peak (sample 64).
# Measured 2026-10-20: magnitude error 40 Hz-16 kHz, Neve max 0.512 dB, 610-A max 0.696 dB.
# Noise null about -19.6 dB (Neve) and -15.5 dB (610-A). Under the 1 dB cost gate.
_PRE_SOS = {
    "neve1073": (
        (89.417550178506829, 155.58739295316738, 70.53516754803654, 1.2739933631350364, 0.50238552357565247),
        (2.0221579747288181, 3.5281002742979015, 1.8714018737916018, 1.6860940621702063, 0.90484075925623109),
    ),
    "u610a": (
        (111.20940456172353, -2.5006042091363394, 1.9330944199533893, -0.76094600734404538, -0.23492576254189973),
        (1.0002530929954785, -0.062647096440998654, -0.93786668356649194, 0.077901596679357851, -0.039306262300920929),
    ),
}


def _cascade_gain_1k(kind: str, sr: float) -> float:
    """|H1*H2| at 1 kHz. The raw kernel carries this gain. Section C wants unity."""
    w = 2.0 * math.pi * 1000.0 / float(sr)
    z1 = cmath.exp(-1j * w)
    z2 = z1 * z1
    g = 1.0 + 0.0j
    for b0, b1, b2, a1, a2 in _PRE_SOS[kind]:
        num = b0 + b1 * z1 + b2 * z2
        den = 1.0 + a1 * z1 + a2 * z2
        g *= num / den
    return abs(g)


def _neve_ship() -> dict:
    """Neve coefficients that ship.

    The 16x nclip_emph_flux_mem model measured 2.934 ms median on the
    decay-8 cube (2026-10-20 02:58 BST), over the 2.40 ms ceiling.
    R3-D switches Neve to nclip_flux at 8x. 610-A stays on pre_choice.json.
    """
    doc = _load("prefit_neve_nclip_emph_nclip_flux_nclip_emph_flux.json")
    return doc["nclip_flux"]


def pack_pre(spec: dict, play: bool = False) -> list:
    """Section 12. Absent when the type is off. 25 floats.

    0 kind (1 = 610-A, 2 = Neve). 1 oversample. 2 drive dB.
    3 vc linear. 4 p0 5 p1 6 p2. 7 emph flag. 8 emph pole 9 emph gain.
    10 phi pole 11 Vphi 12 phi_c. 13 mem_m 14 mem pole.
    15..19 H1. 20..24 H2. b0 b1 b2 a1 a2, a0 = 1.
    610-A is pre_choice.json at 8x on Play and on Render.
    Neve Render is the 8x nclip_flux model. Play uses PLAY_NEVE_OS.
    H1/H2 derived from kernels.npz.
    """
    kind = spec.get("pre") or "off"
    if kind == "off":
        return []
    sr = float(spec["sr"])
    if kind == "neve1073":
        choice = _neve_ship()
        th = choice["th"]
        emph = 0.0
        os_n = PLAY_NEVE_OS if play else RENDER_NEVE_OS
    else:
        doc = _load("pre_choice.json")
        th = doc["u610a"]["th"]
        emph = 1.0 if doc["u610a"]["cfg"].get("emph") else 0.0
        os_n = 8.0
    e_fc = float(th.get("emph_fc", 0.0) or 0.0)
    e_db = float(th.get("emph_db", 0.0) or 0.0)
    p_fc = float(th["phi_fc"])
    mem_tau = float(th.get("mem_tau", 0.0) or 0.0)
    row = [
        2.0 if kind == "neve1073" else 1.0,
        os_n,
        float(spec.get("pre_drive_db") or 0.0),
        10.0 ** (float(th["vc_db"]) / 20.0),
        float(th["p0"]),
        float(th["p1"]),
        float(th["p2"]),
        emph,
        math.exp(-2.0 * math.pi * e_fc / sr) if emph and e_fc > 0.0 else 0.0,
        10.0 ** (e_db / 20.0) if emph else 1.0,
        math.exp(-2.0 * math.pi * p_fc / sr),
        10.0 ** (float(th["phi_db"]) / 20.0),
        float(th["phi_c"]),
        float(th.get("mem_m", 0.0) or 0.0),
        math.exp(-1.0 / (max(mem_tau, 1.0e-4) * sr)) if mem_tau else 0.0,
    ]
    for sos in _PRE_SOS[kind]:
        row.extend(sos)
    # Section C: output small-signal gain is unity at 1 kHz. The trim is on
    # H2 so the shaper still sees the kernel level. Drive is divided back off
    # at the output of both engines, so +6 dB Drive does not raise the linear
    # level.
    g = _cascade_gain_1k(kind, sr)
    if g > 1.0e-12:
        scale = 1.0 / g
        row[20] *= scale
        row[21] *= scale
        row[22] *= scale
    return row


def halfband_47() -> list:
    """47-tap Blackman lowpass, cutoff pi/2. derived. Centre tap 0.5, DC gain 1.

    A 2x upsample uses these taps times 2. Two passes (up and down) delay
    23 samples at 1x. The linear part of the tail is not delayed.
    """
    n = 47
    m = 23
    out = []
    for i in range(n):
        k = i - m
        window = (
            0.42
            - 0.5 * math.cos(2.0 * math.pi * i / (n - 1))
            + 0.08 * math.cos(4.0 * math.pi * i / (n - 1))
        )
        if k == 0:
            h = 0.5
        else:
            h = math.sin(0.5 * math.pi * k) / (math.pi * k)
        out.append(h * window)
    centre = out[m]
    scale = 0.5 / centre
    return [v * scale for v in out]


def _gain_env(det: np.ndarray, spec: dict) -> tuple:
    """Linear tail gain and positive GR. Amount 0 is unity, no detector run."""
    n = int(det.shape[0])
    g = np.ones(n, dtype=np.float64)
    gr = np.zeros(n, dtype=np.float64)
    if float(spec.get("amount_db") or 0.0) <= 0.0:
        return g, gr
    st = DetState()
    step = 1.0 / (0.015 * float(spec["sr"]))
    if not (step > 0.0) or step > 1.0:
        step = 1.0
    u = 0.0
    amt = float(spec["amount_db"])
    duck = float(spec["max_duck_db"])
    for i in range(n):
        gri = step_gr(st, float(det[i]), spec)
        target = 10.0 ** (wet_gain_db(amt, gri, duck) / 20.0)
        u += step
        if u > 1.0:
            u = 1.0
        g[i] = 1.0 + (target - 1.0) * u
        gr[i] = gri
    return g, gr


def _bq(x: float, s0: float, s1: float, q: tuple) -> tuple:
    y = q[0] * x + s0
    n0 = q[1] * x - q[3] * y + s1
    n1 = q[2] * x - q[4] * y
    return y, n0, n1


class _Colour:
    """One bus of the packed shaper. Linear sample stays undelayed."""

    def __init__(self, pack: list) -> None:
        self.p = pack
        self.x0 = 0.0
        self.f0 = 0.0
        self.mem = 0.0
        self.dc_x = 0.0
        self.dc_y = 0.0
        self.hb_u = [0.0] * 46
        self.hb_d = [0.0] * 46
        self.eq_z = [(0.0, 0.0) for _ in range(6)]
        self.h = halfband_47()

    def _dot(self, z: list, x: float, gain2: bool) -> float:
        g = 2.0 if gain2 else 1.0
        acc = g * self.h[0] * x
        for i in range(46):
            acc += g * self.h[i + 1] * z[i]
        for i in range(45, 0, -1):
            z[i] = z[i - 1]
        z[0] = x
        return acc

    def _dist(self, v: float, depth: float) -> float:
        p = self.p
        vr = p[28] if p[28] > 1.0e-12 else 1.0
        u = v / vr
        fam = int(p[27] + 0.5)
        if fam == 1:
            tb = math.tanh(p[31])
            s2 = max(1.0e-12, 1.0 - tb * tb)
            o = vr * depth * ((math.tanh(u + p[31]) - tb) / s2 - u)
        elif p[37] > 0.5:
            F = p[29] * u * u * u / 3.0 + p[30] * u * u * u * u / 4.0
            du = u - self.x0
            if du > 1.0e-7 or du < -1.0e-7:
                gv = (F - self.f0) / du
            else:
                m = 0.5 * (u + self.x0)
                gv = p[29] * m * m + p[30] * m * m * m
            self.x0 = u
            self.f0 = F
            o = vr * depth * gv
        else:
            o = vr * depth * (p[29] * u * u + p[30] * u * u * u)
        return o

    def _mem_dc(self, o: float) -> float:
        """Once per base-rate sample, after the down-halfband."""
        p = self.p
        if 0.0 < p[34] < 1.0:
            self.mem = p[34] * self.mem + (1.0 - p[34]) * o
            o = self.mem
        if 0.0 < p[35] < 1.0:
            y = o - self.dc_x + p[35] * self.dc_y
            self.dc_x = o
            self.dc_y = y
            o = y
        return o

    def shape(self, v: float, gr: float, mix: float) -> float:
        p = self.p
        if p[26] < 0.5 or mix <= 0.0:
            return v
        d0 = p[32]
        Gs = p[33]
        depth = d0
        if Gs > 1.0e-12:
            t = gr / Gs
            if t < 0.0:
                t = 0.0
            if t > 1.0:
                t = 1.0
            depth = d0 + (1.0 - d0) * t
        if p[36] > 1.5:
            a = self._dot(self.hb_u, v, True)
            b = self._dot(self.hb_u, 0.0, True)
            y0 = self._dist(a, depth)
            y1 = self._dist(b, depth)
            self._dot(self.hb_d, y0, False)
            dist = self._dot(self.hb_d, y1, False)
            return v + self._mem_dc(dist) * mix
        return v + self._mem_dc(self._dist(v, depth)) * mix

    def eq(self, x: float) -> float:
        n = (len(self.p) - 40) // 5
        if n < 0:
            n = 0
        if n > 6:
            n = 6
        for s in range(n):
            q = tuple(self.p[40 + 5 * s : 45 + 5 * s])
            s0, s1 = self.eq_z[s]
            x, s0, s1 = _bq(x, s0, s1, q)
            self.eq_z[s] = (s0, s1)
        return x


def apply_fdn_buses(buses: dict, det, spec: dict) -> None:
    """Bloom and pre colour on each FDN bus, before the fold and the limiter.

    Amount 0 does not multiply. Predelay is a shift of the drive, done by
    the caller. Direct, early and dry are not in these buses.
    """
    if float(spec.get("amount_db") or 0.0) <= 0.0 and (spec.get("pre") or "off") == "off":
        return
    n = max(int(np.asarray(v).shape[0]) for v in buses.values())
    dry = np.zeros(n, dtype=np.float64)
    src = np.asarray(det, dtype=np.float64).reshape(-1)
    m = min(n, int(src.shape[0]))
    if m:
        dry[:m] = src[:m]
    g, gr = _gain_env(dry, spec)
    pack = pack_coeffs(spec) if float(spec.get("amount_db") or 0.0) > 0.0 else None
    pre = pack_pre(spec)
    swell = bool(pack) and pack[38] > 0.5 and pack[26] > 0.5
    colour = bool(pack) and pack[26] > 0.5
    cols = []
    for key in ("l", "c", "r"):
        y = np.asarray(buses[key], dtype=np.float64)
        if y.shape[0] < n:
            z = np.zeros(n, dtype=np.float64)
            z[: y.shape[0]] = y
            y = z
        cols.append(y.copy())
    if pack is not None and (colour or float(spec.get("amount_db") or 0.0) > 0.0):
        states = [_Colour(pack) for _ in range(3)]
        for i in range(n):
            for b in range(3):
                v = cols[b][i]
                if swell:
                    # Input side: colour the raw sample, then 10^(W/20), then EQ.
                    v = states[b].shape(v, gr[i], 1.0)
                    v *= g[i]
                    v = states[b].eq(v)
                elif colour:
                    # Output side: full GR attenuation, colour, then makeup
                    # 10^((W+GR)/20), then EQ. g is the ramped 10^(W/20).
                    att = 10.0 ** (-gr[i] / 20.0)
                    v = states[b].shape(v * att, gr[i], 1.0)
                    v *= g[i] * (10.0 ** (gr[i] / 20.0))
                    v = states[b].eq(v)
                else:
                    v = v * g[i]
                cols[b][i] = v
    elif pack is not None:
        for b in range(3):
            cols[b] *= g
    if pre:
        # Pre colour is the same pack the Play engine reads. The 15 ms
        # crossfade is inside the Play ramp; a render starts from silence,
        # so the first block is the settled coloured path.
        for b in range(3):
            cols[b] = _pre_bus(cols[b], pre)
    for b, key in enumerate(("l", "c", "r")):
        buses[key] = cols[b]


def _onepole(x: np.ndarray, a: float) -> np.ndarray:
    """s = a*s + (1-a)*x, s starts at 0. Same recurrence as the sample loop."""
    from scipy.signal import lfilter

    if x.size == 0:
        return x
    return lfilter([1.0 - a], [1.0, -a], x)


def _nclip_vec(v: np.ndarray, p: list) -> np.ndarray:
    """Memoryless nclip. The memory term stays a sample loop; shipped presets have mem_m 0."""
    p0 = float(p[4])
    if p0 < 0.5:
        p0 = 0.5
    p1 = float(p[5])
    p2 = float(p[6])
    if float(p[13]) != 0.0 and float(p[14]) > 0.0:
        out = np.empty_like(v)
        state = 0.0
        pole = float(p[14])
        mem = float(p[13])
        for i in range(v.shape[0]):
            x = float(v[i])
            state = pole * state + (1.0 - pole) * x
            a = p1 + mem * state
            sc = 1.0 + a if x > 0.0 else 1.0 - a
            if sc < 1.0e-6:
                sc = 1.0e-6
            w = x / sc
            aw = abs(w)
            den = math.exp(math.log(1.0 + math.exp(p0 * math.log(aw + 1.0e-30))) / p0)
            out[i] = sc * w / den - x + p2 * x * x
        return out
    a = p1
    sc = np.where(v > 0.0, 1.0 + a, 1.0 - a)
    sc = np.maximum(sc, 1.0e-6)
    w = v / sc
    aw = np.abs(w)
    den = np.exp(np.log1p(np.exp(p0 * np.log(aw + 1.0e-30))) / p0)
    return sc * w / den - v + p2 * v * v


def _pre_bus(y: np.ndarray, p: list) -> np.ndarray:
    """H1, emphasis, nclip, de-emphasis, flux, H2. Oversample is cascaded halfband.

    The halfbands are the same 47-tap FIR as the sample loop, run as filters.
    Checked 2026-10-20 against that loop: max abs under 1e-10 on 4096 samples
    for Neve 8x and 610-A 8x. The C engine is unchanged.
    """
    from scipy.signal import lfilter

    y = np.asarray(y, dtype=np.float64)
    drive = 10.0 ** (float(p[2]) / 20.0)
    os_n = int(p[1] + 0.5)
    if os_n < 1:
        os_n = 1
    if os_n > 16:
        os_n = 16
    h = np.asarray(halfband_47(), dtype=np.float64)
    stages = 0
    t = os_n
    while t > 1 and stages < 4:
        stages += 1
        t >>= 1

    def bq(x, b0, b1, b2, a1, a2):
        out = np.empty(x.shape[0], dtype=np.float64)
        s0 = 0.0
        s1 = 0.0
        for i in range(x.shape[0]):
            v = float(x[i])
            o = b0 * v + s0
            s0 = b1 * v - a1 * o + s1
            s1 = b2 * v - a2 * o
            out[i] = o
        return out

    v = bq(y * drive, p[15], p[16], p[17], p[18], p[19])
    if p[7] > 0.5:
        a = float(p[8])
        ue = v + (float(p[9]) - 1.0) * _onepole(v, a)
    else:
        ue = v
    vc = float(p[3]) if float(p[3]) > 1.0e-12 else 1.0
    u = ue / vc
    if os_n == 1:
        d = vc * _nclip_vec(u, p)
    else:
        cur = np.asarray(u, dtype=np.float64)
        for _s in range(stages):
            up = np.zeros(cur.size * 2, dtype=np.float64)
            up[0::2] = cur
            cur = lfilter(2.0 * h, [1.0], up)
        cur = _nclip_vec(cur, p)
        for _s in range(stages):
            filt = lfilter(h, [1.0], cur)
            cur = filt[1::2]
        d = vc * cur
    if p[7] > 0.5:
        a = float(p[8])
        g = float(p[9]) if float(p[9]) > 1.0e-12 else 1.0
        d = d + (1.0 / g - 1.0) * _onepole(d, a)
    af = float(p[10])
    if 0.0 < af < 1.0:
        s1 = _onepole(v, af)
        Vphi = float(p[11]) if float(p[11]) > 1.0e-12 else 1.0
        e = (s1 / Vphi) ** 3
        e_prev = np.empty_like(e)
        e_prev[0] = 0.0
        if e.size > 1:
            e_prev[1:] = e[:-1]
        den = 1.0 - af if 1.0 - af > 1.0e-12 else 1.0e-12
        d = d + float(p[12]) * Vphi * (e - af * e_prev) / den
    out = bq(v + d, p[20], p[21], p[22], p[23], p[24])
    drive_db = float(p[2])
    if drive_db != 0.0:
        drive = 10.0 ** (drive_db / 20.0)
        if drive > 1.0e-12:
            out = out / drive
    return out
