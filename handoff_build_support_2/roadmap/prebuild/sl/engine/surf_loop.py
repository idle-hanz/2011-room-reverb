"""SL2/SL4 · Surfaces in the loop: per-line attenuation filters (3 biquads, "S1P2") designed from
per-line decay rates (room average or directional with the s' >= 0.5 scattering floor), the stability
guard, and the one-pass Render calibration (T20 per octave, clamped 0.6-1.6).

Port of roadmap/sound_tricks/proto2/attfilt.py + surfdecay.line_rates + the SURF_LOOP block of
fdn_surf_loop.diff + run2.py `_cal`. Drop into software/engine/. FDN calls design_bus() only when a
`surf` dict is passed, so Flat (2011) never imports or runs any of this.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

import surf_target as ST

FIT_F = np.geomspace(20.0, 20000.0, 56)
OCT = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)
THIRD = 1000.0 * 2.0 ** (np.arange(-10, 11) / 3.0)
NB = {"S1": 0, "S1P1": 1, "S1P2": 2}
S_MIN = 0.5                    # D-SL2 (locked): floor on the scattered share s'
CAL_CLAMP = (0.6, 1.6)         # D-SL4 (locked)
KEEP_CUT_BELOW_HZ = 30.0       # D-SL3 (locked): per-axis cuts replaced by panels, except 21-29 Hz modes
IDENTITY = (1.0, 0.0, 0.0, 0.0, 0.0)


# ---- filter primitives (bit-identical to the prototype) -----------------------------------------
def shelf1(G_db, fc, sr, kind):
    G = 10.0 ** (G_db / 20.0); r = math.sqrt(G)
    w = 2.0 * sr * math.tan(math.pi * min(fc, 0.49 * sr) / sr); K = 2.0 * sr
    b0, b1, a0, a1 = ((1.0, r * w, 1.0, w / r) if kind == "lo" else (r, w, 1.0 / r, w))
    B0, B1, A0, A1 = b0 * K + b1, b1 - b0 * K, a0 * K + a1, a1 - a0 * K
    return B0 / A0, B1 / A0, A1 / A0


def peak(sr, f0, q, g_db):
    A = 10 ** (g_db / 40); w0 = 2 * math.pi * min(f0, 0.45 * sr) / sr; al = math.sin(w0) / (2 * q); c = math.cos(w0)
    b0, b1, b2, a0, a1, a2 = 1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def sections(p, struct, sr):
    lb0, lb1, la1 = shelf1(p[0], math.exp(p[1]), sr, "lo"); hb0, hb1, ha1 = shelf1(p[2], math.exp(p[3]), sr, "hi")
    out = [(lb0 * hb0, lb0 * hb1 + lb1 * hb0, lb1 * hb1, la1 + ha1, la1 * ha1)]
    for k in range(NB[struct]):
        g, lf, lq = p[4 + 3 * k: 7 + 3 * k]
        out.append(peak(sr, math.exp(lf), math.exp(lq), g))
    return out


def resp_db(secs, f, sr):
    z = np.exp(-1j * 2 * np.pi * np.asarray(f, float) / sr); h = np.ones_like(z)
    for b0, b1, b2, a1, a2 in secs:
        h = h * (b0 + b1 * z + b2 * z * z) / (1 + a1 * z + a2 * z * z)
    return 20 * np.log10(np.abs(h) + 1e-300)


def design_line(tau, rate_fn, fixed_db_fn, sr, struct="S1P2"):
    """tau s; rate_fn(f) -> wanted loss dB/s (>0); fixed_db_fn(f) -> dB already in the loop (lg + kept cuts).
    Returns (sections, max octave T error, max third-octave T error)."""
    from scipy.optimize import least_squares
    f = FIT_F; want = -tau * rate_fn(f); fixed = fixed_db_fn(f); tgt = want - fixed
    Tw = 60.0 / rate_fn(f)

    def Tgot(p, ff):
        tot = fixed_db_fn(ff) + resp_db(sections(p, struct, sr), ff, sr)
        return -60.0 * tau / np.minimum(tot, -1e-6)
    x0 = [float(tgt[0]), math.log(200.0), float(tgt[-1]), math.log(5000.0)]
    lo = [-40.0, math.log(30.0), -40.0, math.log(800.0)]; hi = [40.0, math.log(3000.0), 40.0, math.log(0.45 * sr)]
    for k in range(NB[struct]):
        x0 += [0.0, math.log([700.0, 2500.0][k % 2]), math.log(0.8)]
        lo += [-24.0, math.log(60.0), math.log(0.3)]; hi += [24.0, math.log(12000.0), math.log(4.0)]
    x0 = [min(max(v, l + 1e-6), h - 1e-6) for v, l, h in zip(x0, lo, hi)]
    dense = np.concatenate([[0.01], np.geomspace(2.0, 0.4999 * sr, 160)])
    t_cap = 2.0 * float(np.max(60.0 / rate_fn(f)))
    marg = np.full_like(dense, 60.0 * tau / t_cap)

    def resid(p):
        tot = fixed_db_fn(dense) + resp_db(sections(p, struct, sr), dense, sr)
        pen = 50.0 * np.maximum(0.0, tot + np.maximum(marg, 1e-4))
        return np.concatenate([Tgot(p, f) / Tw - 1.0, pen])
    res = least_squares(resid, x0, bounds=(lo, hi), max_nfev=600)
    secs = sections(res.x, struct, sr)
    e_oct = float(np.max(np.abs(Tgot(res.x, OCT) / (60.0 / rate_fn(OCT)) - 1)))
    th = THIRD[(THIRD >= 100) & (THIRD <= 10000)]
    e_3rd = float(np.max(np.abs(Tgot(res.x, th) / (60.0 / rate_fn(th)) - 1)))
    return secs, e_oct, e_3rd


# ---- per-line decay rates ------------------------------------------------------------------------
def line_rates(delays, sr, W, H, L, cards, humidity, f=FIT_F, directional=True, hits=None,
               t_anchor=None, s_min=S_MIN):
    """Per-line decay rate, dB/s (positive = loss), shape (n, len(f)); also returns the room T(f).
    hits[i]: face letters line i's image path crosses (surface_colour.surfaces_hit_by_n(tap.n))."""
    tau = np.asarray(delays, float) / sr
    air = ST.air_db_per_m(f, humidity)
    T = ST.room_target(W, H, L, cards, humidity, f, air=air)
    if t_anchor:
        Tm = float(np.mean(ST.room_target(W, H, L, cards, humidity, np.array([500.0, 1000.0]))))
        T = T * (float(t_anchor) / Tm)
    G = 60.0 / T
    Gair = air * ST.C_AIR
    Gs = np.maximum(G - Gair, 0.0)
    n = len(tau)
    if not directional:
        return np.tile(G, (n, 1)), T
    if hits is None:
        raise ValueError("directional rates need per-line hit lists")
    S = ST.face_areas(W, H, L)
    s = max(ST.scatter_mean(cards, S), s_min)
    fdb = {k: -ST.face_bounce_db(cards[k], f) for k in S}
    raw = np.zeros((n, len(f)))
    for i in range(n):
        path = max(tau[i] * ST.C_AIR, 0.5)
        for k in hits[i]:
            raw[i] += fdb[k] * ST.C_AIR / path
    mean_raw = (tau[:, None] * raw).sum(0) / tau.sum()
    kappa = np.where(mean_raw > 1e-9, Gs / np.maximum(mean_raw, 1e-9), 0.0)
    rates = Gair[None, :] + s * Gs[None, :] + (1 - s) * (kappa[None, :] * raw)
    return rates, T


# ---- one FDN bus --------------------------------------------------------------------------------
def design_bus(delays: Sequence[int], sr: int, lg: np.ndarray, peaks: List[Optional[tuple]],
               rates: np.ndarray, struct: str = "S1P2") -> Dict:
    """Sections (n, K, 5) for one bus + report/stab/guard. peaks[i]: kept per-axis biquad or None."""
    secs_all, eo, e3, guard = [], [], [], []
    n = len(delays)
    tot_oct = np.zeros((n, len(OCT))); want_oct = np.zeros((n, len(OCT)))
    dense = np.concatenate([[0.01], np.geomspace(1.0, 0.4999 * sr, 1200)])
    for i, d in enumerate(delays):
        tau = float(d) / float(sr)
        lgdb = 20.0 * math.log10(float(lg[i]))
        pk = peaks[i]
        fixed = (lambda ff, lgdb=lgdb, pk=pk: lgdb + (resp_db([pk], ff, sr) if pk is not None else 0.0) + 0.0 * np.asarray(ff, float))
        rf = (lambda ff, i=i: np.interp(np.log(ff), np.log(FIT_F), rates[i]))
        secs, a, b = design_line(tau, rf, fixed, sr, struct)
        loop_db = fixed(dense) + resp_db(secs, dense, sr)
        mx = float(np.max(loop_db))
        lim = -60.0 * tau / (3.0 * float(np.max(60.0 / rf(FIT_F))))
        if mx > lim or a > 0.5:
            g = dict(line=i, delay=int(d), err=round(a, 3), max_loop_db=round(mx, 4),
                     at_hz=round(float(dense[int(np.argmax(loop_db))]), 1))
            secs, a, b = design_line(tau, rf, fixed, sr, "S1")
            if float(np.max(fixed(dense) + resp_db(secs, dense, sr))) > lim:
                secs, a, b = [IDENTITY], 1.0, 1.0
                g["fallback"] = "identity"
            guard.append(g)
        secs_all.append(secs); eo.append(a); e3.append(b)
        tot_oct[i] = fixed(OCT) + resp_db(secs, OCT, sr); want_oct[i] = -tau * rf(OCT)
    sys_err = (want_oct.sum(0) / tot_oct.sum(0)) - 1.0
    mx_all, pole = -1e9, 0.0
    dd = np.geomspace(5.0, 0.499 * sr, 3000)
    for i, secs in enumerate(secs_all):
        l = 20.0 * math.log10(float(lg[i])) + resp_db(secs, dd, sr) + (resp_db([peaks[i]], dd, sr) if peaks[i] is not None else 0.0)
        mx_all = max(mx_all, float(np.max(l)))
        for s_ in secs:
            if s_[3] or s_[4]:
                pole = max(pole, float(np.max(np.abs(np.roots([1.0, s_[3], s_[4]])))))
    K = 3 if struct == "S1P2" else max(len(x) for x in secs_all)
    secs_all = [list(x) + [IDENTITY] * (K - len(x)) for x in secs_all]
    return dict(
        secs=np.asarray(secs_all, float),
        stab=dict(max_loop_db=round(mx_all, 5), max_pole=round(pole, 6)),
        guard=guard,
        report=dict(worst_line_oct_pct=round(100 * max(eo), 2), median_line_oct_pct=round(100 * float(np.median(eo)), 2),
                    worst_line_third_pct=round(100 * max(e3), 2),
                    system_oct_err_pct=[round(100 * float(x), 2) for x in sys_err], sections=K),
    )


# ---- calibration (Render only) ------------------------------------------------------------------
def _octave(x, fc, sr, order=3):
    from scipy import signal
    lo, hi = fc / 2 ** 0.5, min(fc * 2 ** 0.5, 0.45 * sr)
    sos = signal.butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x)


def t20_per_octave(ir_mono, sr=48000, bands=OCT) -> List[float]:
    """ISO 3382-style T20 (-5..-25 dB Schroeder slope) per octave; onset = first sample >= -20 dB of peak."""
    x = np.asarray(ir_mono, float)
    a = np.abs(x); n0 = int(np.argmax(a >= 0.1 * a.max()))
    out = []
    for fc in bands:
        y = _octave(x, fc, sr)[n0:]
        e = np.cumsum((y ** 2)[::-1])[::-1]; e = e / max(e[0], 1e-300)
        edc = 10 * np.log10(np.maximum(e, 1e-30))
        i0 = int(np.argmax(edc <= -5)); i1 = int(np.argmax(edc <= -25))
        if i1 <= i0 + 2:
            out.append(float("nan")); continue
        t = np.arange(i0, i1) / sr
        slope = np.polyfit(t, edc[i0:i1], 1)[0]
        out.append(float(-60.0 / slope))
    return out


def calibration_factors(t20_measured, t_target_oct) -> List[float]:
    """D-SL4: scale each band's loss by T20_measured / T_target, clamped 0.6-1.6 (applied to the rates)."""
    r = np.asarray(t20_measured, float) / np.asarray(t_target_oct, float)
    r = np.where(np.isfinite(r), r, 1.0)
    return [round(float(x), 4) for x in np.clip(r, *CAL_CLAMP)]


def cal_fn(cal: Optional[Sequence[float]]):
    if not cal:
        return lambda ff: np.ones_like(np.asarray(ff, float))
    c = np.asarray(cal, float)
    return lambda ff: np.interp(np.log(np.asarray(ff, float)), np.log(OCT), c)


# ---- scene-level spec (what render() hands to render_fdn_ir) -------------------------------------
def make_spec(W, H, L, cards, humidity, t_anchor, directional=True, cal=None, struct="S1P2",
              keep_cut_below_hz=None, report=None) -> dict:
    """cards: face cards incl. absorb_fn for treated faces (surf_panels.cards_with_treatment)."""
    cf = cal_fn(cal)

    def rates_for(delays, sr, hits):
        r, _ = line_rates(delays, sr, W, H, L, cards, humidity, FIT_F, directional, hits, t_anchor)
        return r * cf(FIT_F)[None, :]
    T_oct = ST.room_target(W, H, L, cards, humidity, OCT)
    if t_anchor:
        T_oct = T_oct * float(t_anchor) / float(np.mean(ST.room_target(W, H, L, cards, humidity, np.array([500.0, 1000.0]))))
    if keep_cut_below_hz is None:
        keep_cut_below_hz = KEEP_CUT_BELOW_HZ
    return dict(rates_for=rates_for, struct=struct, keep_cut_below_hz=keep_cut_below_hz,
                target_T_oct=[round(float(x), 4) for x in T_oct], directional=bool(directional),
                report=report if report is not None else [])
