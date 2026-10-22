"""SL5 · Treatment physics: porous absorbers with an air gap, membrane (panel) absorbers, Helmholtz
(perforated) absorbers, the "room shell" term, and alpha(f) per face with Treatment rows.

Two levels:
  * Design formulas used by Auto-treat and the Treatment rows (fast, closed form):
      membrane_f0  f0 = 60/sqrt(m d)  (empty cavity, adiabatic)  or 50/sqrt(m d) (mineral-wool fill)
      helmholtz_f0 f0 = c/(2 pi) sqrt(eps / (t' d)),  t' = t + 2*0.85*a   (Cox & D'Antonio, ch. 7)
      resonant_alpha  alpha(f) = amax / (1 + Q^2 (f/f0 - f0/f)^2)   (shape standard; Q/amax ASSUMED)
  * Impedance models (transfer-matrix, normal + Paris random incidence) used to check the formulas
    and to justify the Q / amax defaults:
      Miki (1990) porous layer, extended reaction, optional air gap (the app library presets were
      generated with exactly this model, sigma = 15 kPa s/m^2), membrane = mass + damping + filled
      cavity, perforate = Maa/Ingard plug mass + viscous resistance + filled cavity.

Drop into software/engine/. Pure numpy; no app imports except optional library loading.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

RHO0 = 1.21          # kg/m^3, air at 20 C
C0 = 343.0           # m/s
GAMMA = 1.4
NU = 1.5e-5          # kinematic viscosity of air, m^2/s
Z0 = RHO0 * C0
MAX_FACE_COVER = 0.9 # a real face holds at most 90 % treatment (doors, sockets, edges)

# ------------------------------------------------------------------------------------------------
# Closed-form design formulas
# ------------------------------------------------------------------------------------------------
def membrane_f0(m_kg_m2: float, d_m: float, porous_fill: bool = True) -> float:
    """Panel absorber resonance (Cox & D'Antonio eqs 7.9/7.10)."""
    return (50.0 if porous_fill else 60.0) / math.sqrt(m_kg_m2 * d_m)


def membrane_f0_physical(m_kg_m2: float, d_m: float, porous_fill: bool = True) -> float:
    """f0 = (1/2pi) sqrt(rho c^2 / (m d)); with fill the cavity is ~isothermal (c^2 -> c^2/gamma)."""
    k = RHO0 * C0 ** 2 / (GAMMA if porous_fill else 1.0)
    return math.sqrt(k / (m_kg_m2 * d_m)) / (2 * math.pi)


def helmholtz_f0(eps: float, t_m: float, a_m: float, d_m: float, delta: float = 0.85) -> float:
    """Perforated-panel resonance, a = hole radius, eps = open-area fraction (Cox & D'Antonio 7.4/7.6)."""
    return C0 / (2 * math.pi) * math.sqrt(eps / ((t_m + 2 * delta * a_m) * d_m))


def resonant_alpha(f, f0: float, q: float, amax: float) -> np.ndarray:
    f = np.asarray(f, float)
    return amax / (1.0 + (q * (f / f0 - f0 / f)) ** 2)


# Real boards for membrane panels: (name, surface mass kg/m^2)
SHEETS = [("3 mm hardboard", 2.7), ("6 mm plywood", 3.6), ("9 mm plywood", 5.4), ("12 mm MDF", 9.0),
          ("18 mm MDF", 13.5), ("2 x 12.5 mm plasterboard", 21.0)]
MEMBRANE_Q, MEMBRANE_AMAX = 2.0, 0.6      # ASSUMED defaults (see impedance check in README)
HELMHOLTZ_Q, HELMHOLTZ_AMAX = 3.0, 0.7    # ASSUMED defaults
PANEL_FACE_FLOOR = 0.05                    # off resonance the panel face still absorbs a little


def design_membrane(f0: float) -> Optional[dict]:
    """Pick the board whose cavity (50-300 mm) for f0 is closest to 120 mm."""
    best = None
    for name, m in SHEETS:
        d = (50.0 / f0) ** 2 / m
        if 0.05 <= d <= 0.30:
            cand = (abs(d - 0.12), name, m, d)
            best = min(best, cand) if best else cand
    if not best:
        return None
    _, name, m, d = best
    return dict(type="membrane", f0=round(membrane_f0(m, d), 1), q=MEMBRANE_Q, amax=MEMBRANE_AMAX,
                build=f"{name} ({m} kg/m2) on {round(d * 1000)} mm cavity, mineral wool fill", m=m, d=d)


def design_helmholtz(f0: float, t: float = 0.012, a: float = 0.003) -> Optional[dict]:
    """12 mm board, 6 mm holes (a = 3 mm radius); cavity 100/150/200/50 mm; open area 0.5-20 %."""
    for d in (0.10, 0.15, 0.20, 0.05):
        eps = ((2 * math.pi * f0 / C0) ** 2) * (t + 2 * 0.85 * a) * d
        if 0.005 <= eps <= 0.20:
            return dict(type="helmholtz", f0=round(helmholtz_f0(eps, t, a, d), 1), q=HELMHOLTZ_Q, amax=HELMHOLTZ_AMAX,
                        build=f"12 mm board, 6 mm holes, {eps * 100:.1f} % open, {round(d * 1000)} mm cavity with wool",
                        eps=eps, d=d, t=t, a=a)
    return None


def design_panel(f0: float) -> Optional[dict]:
    """'Make it a panel': membrane below 180 Hz, else Helmholtz (falls back to the other kind)."""
    return ((design_membrane(f0) if f0 < 180 else None) or design_helmholtz(f0) or design_membrane(f0))


def room_shell_rows(faces=("A", "B", "C", "D")) -> List[dict]:
    """D-SL6 (locked): doors, glazing and stud walls as a broad 90 Hz membrane on 30 % of each wall. ASSUMED."""
    return [dict(id=f"shell_{k}", face=k, type="shell", on=True, f0=90.0, q=1.0, amax=0.35, coverage=0.3,
                 build="room shell (doors, glazing, stud walls)", assumed=True, removable=True) for k in faces]


# ------------------------------------------------------------------------------------------------
# Impedance models (checks; Render could use them later)
# ------------------------------------------------------------------------------------------------
def miki(f, sigma: float):
    """Miki (1990) characteristic impedance and wavenumber, e^{j w t} convention."""
    f = np.asarray(f, float)
    X = f / sigma
    w = 2 * np.pi * f
    Zc = Z0 * (1 + 0.0699 * X ** -0.632 - 1j * 0.1071 * X ** -0.632)
    k = (w / C0) * (1 + 0.1093 * X ** -0.618 - 1j * 0.1597 * X ** -0.618)
    return Zc, k


def porous_surface_z(f, sigma: float, thick: float, gap: float = 0.0, theta: float = 0.0):
    """Surface impedance (normal component) of a porous layer on an air gap on a rigid wall,
    extended reaction at incidence angle theta (rad)."""
    f = np.asarray(f, float)
    k0 = 2 * np.pi * f / C0
    Zc, k = miki(f, sigma)
    s = math.sin(theta)
    kx = np.sqrt(k ** 2 - (k0 * s) ** 2)
    Zcx = Zc * k / kx                                   # normal-direction characteristic impedance
    if gap > 0:
        cth = max(math.cos(theta), 1e-6)
        Zb = -1j * (Z0 / cth) * (1.0 / np.tan(k0 * cth * gap))
        cot = 1.0 / np.tan(kx * thick)
        return Zcx * (-1j * Zb * cot + Zcx) / (Zb - 1j * Zcx * cot)
    return -1j * Zcx / np.tan(kx * thick)


def alpha_from_z(Zs, theta: float = 0.0) -> np.ndarray:
    ct = math.cos(theta)
    R = (Zs * ct - Z0) / (Zs * ct + Z0)
    return 1.0 - np.abs(R) ** 2


def paris(alpha_theta: Callable[[float], np.ndarray], theta_max_deg: float = 89.0, n: int = 90) -> np.ndarray:
    """Paris random-incidence average: int alpha(theta) sin 2theta dtheta / int sin 2theta dtheta."""
    th = np.linspace(0.0, math.radians(theta_max_deg), n)
    w = np.sin(2 * th)
    vals = np.array([alpha_theta(t) for t in th])
    return np.trapezoid(vals * w[:, None], th, axis=0) / np.trapezoid(w, th)


def porous_alpha(f, sigma: float, thick: float, gap: float = 0.0, incidence: str = "random") -> np.ndarray:
    if incidence == "normal":
        return alpha_from_z(porous_surface_z(f, sigma, thick, gap, 0.0), 0.0)
    return paris(lambda t: alpha_from_z(porous_surface_z(f, sigma, thick, gap, t), t))


def membrane_alpha_physical(f, m: float, d: float, sigma_fill: float = 10000.0, fill: float = 1.0,
                            r_panel: float = 0.0) -> np.ndarray:
    """Normal incidence: Z = j w m + r_panel + Z_cavity; cavity fill fraction `fill` (0 = empty) of Miki wool."""
    f = np.asarray(f, float)
    w = 2 * np.pi * f
    k0 = w / C0
    if fill > 0:
        Zc, k = miki(f, sigma_fill)
        Zcav = -1j * Zc / np.tan(k * d)
    else:
        Zcav = -1j * Z0 / np.tan(k0 * d)
    return alpha_from_z(1j * w * m + r_panel + Zcav)


def perforated_alpha_physical(f, eps: float, t: float, a: float, d: float, sigma_fill: float = 10000.0,
                              fill_thick: Optional[float] = 0.025) -> np.ndarray:
    """Normal incidence. Plug mass with end correction + viscous resistance (Ingard) on a cavity of depth d.
    fill_thick: wool layer directly behind the perforate (the textbook build), rest air; None = fully filled."""
    f = np.asarray(f, float)
    w = 2 * np.pi * f
    tp = t + 2 * 0.85 * a
    r_visc = (RHO0 / eps) * np.sqrt(8 * NU * w) * (1 + t / (2 * a))
    Zm = 1j * w * RHO0 * tp / eps + r_visc
    if fill_thick is None or fill_thick >= d:
        Zc, k = miki(f, sigma_fill)
        Zcav = -1j * Zc / np.tan(k * d)
    else:
        Zcav = porous_surface_z(f, sigma_fill, fill_thick, d - fill_thick, 0.0)
    return alpha_from_z(Zm + Zcav)


def fit_resonance(f, alpha) -> dict:
    """Peak f0, amax and Q (= f0 / -3 dB bandwidth) of a resonant alpha curve."""
    f = np.asarray(f, float); a = np.asarray(alpha, float)
    i = int(np.argmax(a)); amax = float(a[i]); half = amax / 2
    lo = i
    while lo > 0 and a[lo] > half:
        lo -= 1
    hi = i
    while hi < len(a) - 1 and a[hi] > half:
        hi += 1
    bw = float(f[hi] - f[lo])
    return dict(f0=float(f[i]), amax=amax, q=float(f[i] / bw) if bw > 0 else float("inf"))


# ------------------------------------------------------------------------------------------------
# alpha(f) per face with Treatment rows
# ------------------------------------------------------------------------------------------------
_LIB_CACHE: Dict[str, dict] = {}


def load_material(mid: str, root: Optional[Path] = None) -> dict:
    """Library card from software/presets/surfaces/<id>.json."""
    if mid in _LIB_CACHE:
        return _LIB_CACHE[mid]
    root = Path(root) if root else Path(__file__).resolve().parents[1] / "presets" / "surfaces"
    m = json.loads((root / f"{mid}.json").read_text())
    _LIB_CACHE[mid] = m
    return m


POROUS_PRESETS = ["absorber_panel_1in_gap1in", "absorber_panel_2in", "absorber_panel_2in_gap2in", "absorber_panel_4in_gap4in"]


def row_alpha(row: dict, f, lib_root: Optional[Path] = None) -> np.ndarray:
    f = np.asarray(f, float)
    if row["type"] == "porous":
        m = load_material(row["material"], lib_root)
        return np.interp(np.log(f), np.log(np.asarray(m["absorb_hz"], float)), np.asarray(m["absorb"], float))
    return np.maximum(resonant_alpha(f, row["f0"], row["q"], row["amax"]), PANEL_FACE_FLOOR)


def face_rows(rows: List[dict], face: str) -> List[dict]:
    return [r for r in (rows or []) if r.get("face") == face and r.get("on", True) and not r.get("suggested")]


def alpha_fn(card: dict, rows: List[dict], lib_root: Optional[Path] = None) -> Callable:
    """Continuous alpha(f) of one face: (1 - sum coverage) * base + sum coverage * row alpha."""
    hz = np.asarray(card.get("absorb_hz") or [125, 250, 500, 1000, 2000, 4000, 8000], float)
    a = np.asarray(card["absorb"], float)
    rows = list(rows)

    def fn(f):
        f = np.asarray(f, float)
        base = np.interp(np.log(f), np.log(hz), a)
        cov = min(sum(float(r["coverage"]) for r in rows), 1.0)
        out = (1 - cov) * base
        for r in rows:
            out = out + float(r["coverage"]) * row_alpha(r, f, lib_root)
        return np.clip(out, 0.0, 0.99)
    return fn


def cards_with_treatment(surfaces: Dict[str, dict], rows: List[dict], lib_root: Optional[Path] = None) -> Dict[str, dict]:
    """Copy of the cards where every treated face carries absorb_fn. Untreated faces are untouched."""
    out = {}
    for k, c in surfaces.items():
        fr = face_rows(rows, k)
        out[k] = dict(c, absorb_fn=alpha_fn(c, fr, lib_root)) if fr else c
    return out


def validate_rows(rows: List[dict]) -> List[str]:
    """Problems with a Treatment list (empty = OK)."""
    errs = []
    for k in "ABCDEF":
        cov = sum(float(r["coverage"]) for r in rows if r.get("face") == k and r.get("on", True) and not r.get("suggested"))
        if cov > MAX_FACE_COVER + 1e-9:
            errs.append(f"face {k}: {cov * 100:.0f} % treated > {MAX_FACE_COVER * 100:.0f} %")
    for r in rows:
        if r.get("type") not in ("porous", "membrane", "helmholtz", "shell"):
            errs.append(f"row {r.get('id')}: unknown type {r.get('type')}")
        if not (0.0 <= float(r.get("coverage", -1)) <= MAX_FACE_COVER):
            errs.append(f"row {r.get('id')}: coverage out of range")
        if r.get("type") == "porous" and r.get("material") not in POROUS_PRESETS:
            errs.append(f"row {r.get('id')}: porous material must be a library preset")
    return errs
