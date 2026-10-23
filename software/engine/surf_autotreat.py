"""SL6 · Auto-treat: SUGGESTS Treatment rows (D-SL5: never applies them) to reach a T_mid target,
plus "Make it a panel" for EQ_PLAN resonance rows below 300 Hz and the EBU control-room preset (D-SL9).

Port of roadmap/sound_tricks/proto2/treatment.py auto_treat (box plan for the default room:
4"+4" gap at 21 % on F/D/A/C; panels at 62.5 / 125 / 157.5 / 198 Hz). Drop into software/engine/.
"""
from __future__ import annotations

import copy
import math
from typing import Dict, List, Optional

import numpy as np

import surf_panels as P
import surf_target as ST

THIRD = ST.THIRD_40_8K
MAX_TUNED = 4                     # shared with EQ_PLAN's 4 resonance rows
BROADBAND_FACES = ["F", "D", "A", "C"]
PANEL_FACE_PREFS = ["D", "F", "A", "C", "B", "E"]    # floor last (riser)


def _T(W, H, L, surfaces, rows, humidity, f=THIRD):
    return ST.room_target(W, H, L, P.cards_with_treatment(surfaces, rows), humidity, f)


def _used(rows, face):
    return sum(float(r["coverage"]) for r in rows if r["face"] == face and r.get("on", True))


def _auto(W, H, L, surfaces, humidity, t_mid, porous, existing, max_panels):
    rows = [dict(r, suggested=False) for r in existing]          # accepted rows count as given
    new: List[dict] = []
    mid = (THIRD >= 500) & (THIRD <= 2000)
    live = lambda: rows + [dict(r, suggested=False) for r in new]
    # 1) broadband, axis-balanced (one common coverage on F, D, A, C; add B only if 80 % is not enough)
    for faces in (BROADBAND_FACES, BROADBAND_FACES + ["B"]):
        trs = [dict(type="porous", material=porous, coverage=0.8, face=k, on=True) for k in faces]
        if float(np.mean(_T(W, H, L, surfaces, live() + trs, humidity)[mid])) > t_mid and len(faces) == 4:
            continue
        lo, hi = 0.0, 0.8
        for _ in range(30):
            c = 0.5 * (lo + hi)
            for tr in trs:
                tr["coverage"] = c
            if float(np.mean(_T(W, H, L, surfaces, live() + trs, humidity)[mid])) > t_mid:
                lo = c
            else:
                hi = c
        for tr in trs:
            tr["coverage"] = round(hi, 3)
            tr["build"] = P.load_material(porous)["display_name"]
        new.extend(trs)
        break
    new[:] = [r for r in new if float(r["coverage"]) >= 0.005]   # no 0 % porous rows when the room is already short
    # 2) tuned panels at the worst low-frequency excess against the Makivirta target.
    # Treatment only adds absorption: if the room is already shorter than t_mid at mid, fit the SHAPE at the
    # room's own mid T (Decay lock then sets the length; see the UI lock note) instead of chasing an unreachable target.
    t_now = float(np.mean(_T(W, H, L, surfaces, live(), humidity)[mid]))
    t_fit = t_now if t_now < 0.98 * t_mid else t_mid
    tgt = ST.makivirta_target(THIRD, t_fit, ST.air_ratio_fn(W, H, L, humidity, t_fit))
    lf = (THIRD >= 40) & (THIRD <= 500)
    n_pan = sum(1 for r in rows if r["type"] in ("membrane", "helmholtz"))
    for _ in range(3 * max_panels):
        if n_pan >= max_panels:
            break
        T = _T(W, H, L, surfaces, live(), humidity)
        ex = np.where(lf, T / tgt, 0)
        i = int(np.argmax(ex))
        if ex[i] < 1.10:
            break
        f0 = float(THIRD[i])
        pan = (P.design_membrane(f0) if f0 < 180 else None) or P.design_helmholtz(f0)
        if pan is None:
            lf[i] = False
            continue
        md = [m for m in ST.modes(W, H, L, 400) if m[2] == "axial" and abs(math.log(m[0] / f0)) < 0.25]
        prefs = list(PANEL_FACE_PREFS)
        if md:
            ax = int(np.argmax(md[0][1]))
            first = {0: ["A", "C"], 1: ["F", "A", "C"], 2: ["D", "B"]}[ax]
            prefs = first + [x for x in prefs if x not in first]
        face = next((k for k in prefs if P.MAX_FACE_COVER - _used(live(), k) >= 0.1), None)
        if face is None:
            break
        free = P.MAX_FACE_COVER - _used(live(), face)
        pan = dict(pan, coverage=0.0, face=face, on=True, target_hz=round(f0, 1),
                   modes_near=[f"{m[0]:.0f} Hz {m[1]}" for m in md][:3])
        new.append(pan)
        lo, hi = 0.0, min(0.5, free)
        for _ in range(25):
            pan["coverage"] = 0.5 * (lo + hi)
            if _T(W, H, L, surfaces, live(), humidity)[i] / tgt[i] > 1.0:
                lo = pan["coverage"]
            else:
                hi = pan["coverage"]
        pan["coverage"] = round(hi, 3)
        n_pan += 1
    return new, tgt, t_fit


def auto_treat(W, H, L, surfaces: Dict[str, dict], humidity: float, t_mid: float,
               existing_rows: Optional[List[dict]] = None, max_panels: int = MAX_TUNED,
               porous: Optional[str] = None) -> dict:
    """Returns {'suggested': rows (suggested=True), 'porous', 'before', 'after', 'target', 'f', report...}.
    The scene is never modified; rows only count once the user accepts them (suggested -> False)."""
    existing = copy.deepcopy(existing_rows or [])
    best = None
    band = (THIRD >= 200) & (THIRD <= 8000)
    for pm in ([porous] if porous else P.POROUS_PRESETS):
        new, tgt, t_fit = _auto(W, H, L, surfaces, humidity, t_mid, pm, existing, max_panels)
        aft = _T(W, H, L, surfaces, existing + new, humidity)
        err = float(np.sqrt(np.mean(np.log(aft[band] / tgt[band]) ** 2)))
        if best is None or err < best[0]:
            best = (err, pm, new, aft, tgt, t_fit)
    err, pm, new, aft, tgt, t_fit = best
    before = _T(W, H, L, surfaces, existing, humidity)
    V = W * H * L
    S = ST.face_areas(W, H, L)
    for j, r in enumerate(new):
        r["suggested"] = True
        r["id"] = f"auto_{j}"
        r["area_m2"] = round(r["coverage"] * S[r["face"]], 2)
    within = np.abs(aft / tgt - 1) <= 0.10
    mid = (THIRD >= 500) & (THIRD <= 2000)
    return dict(
        suggested=new, porous=pm if any(r["type"] == "porous" for r in new) else None,
        t_fit=round(t_fit, 3), shape_only=bool(t_fit < t_mid),
        rms_log_err_200_8k=round(err, 3), f=THIRD.tolist(),
        before=before.tolist(), after=aft.tolist(), target=tgt.tolist(),
        n_within_10pct=int(within.sum()), n_bands=len(THIRD),
        coverage={k: round(_used(existing + new, k), 3) for k in "ABCDEF"},
        schroeder_before=round(ST.schroeder_hz(float(np.mean(before[mid])), V), 1),
        schroeder_after=round(ST.schroeder_hz(float(t_mid), V), 1),
        ebu_tm=round(ST.ebu_tm(V), 3), ebu_pass=ST.ebu_check(THIRD, aft, V),
    )


def ebu_preset_t_mid(W, H, L) -> float:
    """D-SL9 'EBU control room' preset: the dial target is Tm = 0.25 (V/100)^(1/3)."""
    return ST.ebu_tm(W * H * L)


def make_it_a_panel(f0: float, W, H, L, existing_rows: Optional[List[dict]] = None) -> Optional[dict]:
    """One suggested tuned row for an EQ_PLAN resonance row (< 300 Hz only; rows above 500 Hz stay cuts)."""
    if f0 >= 300.0:
        return None
    pan = P.design_panel(f0)
    if pan is None:
        return None
    rows = existing_rows or []
    md = [m for m in ST.modes(W, H, L, 400) if m[2] == "axial" and abs(math.log(m[0] / f0)) < 0.25]
    prefs = list(PANEL_FACE_PREFS)
    if md:
        ax = int(np.argmax(md[0][1]))
        first = {0: ["A", "C"], 1: ["F", "A", "C"], 2: ["D", "B"]}[ax]
        prefs = first + [x for x in prefs if x not in first]
    face = next((k for k in prefs if P.MAX_FACE_COVER - _used(rows, k) >= 0.1), None)
    if face is None:
        return None
    cov = min(0.25, P.MAX_FACE_COVER - _used(rows, face))
    return dict(pan, id=f"panel_{round(f0)}", face=face, on=True, suggested=True, coverage=round(cov, 3),
                target_hz=round(f0, 1), area_m2=round(cov * ST.face_areas(W, H, L)[face], 2))
