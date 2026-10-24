"""SL2/SL4 · Surfaces in the loop: per-line attenuation filters (3 biquads, "S1P2") designed from
per-line decay rates (room average or directional with the s' >= 0.5 scattering floor), the stability
guard, and the one-pass Render calibration (T20 per octave, clamped 0.6-1.6).

Port of roadmap/sound_tricks/proto2/attfilt.py + surfdecay.line_rates + the SURF_LOOP block of
fdn_surf_loop.diff + run2.py `_cal`. Drop into software/engine/. FDN calls design_bus() only when a
`surf` dict is passed, so Flat (2011) never imports or runs any of this.
"""
from __future__ import annotations

import math
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Sequence, Tuple

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
_LINE_CACHE: Dict = {}
_LINE_CACHE_MAX = 512


def _line_cache_key(delay, sr, lg_i, pk, rates_row, struct):
    """Same delay, rate, loop gain, kept peak, and rate row skip another scipy fit."""
    if pk is None:
        pk_t = None
    else:
        pk_t = tuple(round(float(x), 8) for x in pk)
    row = np.ascontiguousarray(rates_row, dtype=np.float64)
    return (int(delay), int(sr), round(float(lg_i), 10), pk_t, str(struct), row.tobytes())


def _design_line_cached(tau, rate_fn, fixed_db_fn, sr, struct, key):
    hit = _LINE_CACHE.get(key)
    if hit is not None:
        return hit
    secs, a, b = design_line(tau, rate_fn, fixed_db_fn, sr, struct)
    _LINE_CACHE[key] = (secs, a, b)
    if len(_LINE_CACHE) > _LINE_CACHE_MAX:
        _LINE_CACHE.pop(next(iter(_LINE_CACHE)))
    return secs, a, b


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
        secs, a, b = _design_line_cached(
            tau, rf, fixed, sr, struct,
            _line_cache_key(d, sr, lg[i], pk, rates[i], struct),
        )
        loop_db = fixed(dense) + resp_db(secs, dense, sr)
        mx = float(np.max(loop_db))
        lim = -60.0 * tau / (3.0 * float(np.max(60.0 / rf(FIT_F))))
        if mx > lim or a > 0.5:
            g = dict(line=i, delay=int(d), err=round(a, 3), max_loop_db=round(mx, 4),
                     at_hz=round(float(dense[int(np.argmax(loop_db))]), 1))
            secs, a, b = _design_line_cached(
                tau, rf, fixed, sr, "S1",
                _line_cache_key(d, sr, lg[i], pk, rates[i], "S1"),
            )
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


def hold_low_octaves(cal, hz: float = 500.0) -> List[float]:
    """Room-average auto-treat. Octaves at or under hz stay at 1.

    A factor below 1 at 500 Hz lengthens 315 Hz out of the ±10% window.
    Holding 125, 250 and 500 at 1 leaves the measured highs in place.
    On real_default the proved list is [1, 1, 1, 0.850, 0.878, 0.870, 0.906],
    rendered third-octave T20 16/23.
    """
    out = [float(x) for x in cal]
    for i, f in enumerate(OCT):
        if i < len(out) and float(f) <= float(hz) + 1e-9:
            out[i] = 1.0
    return [round(x, 4) for x in out]


def factors_for_calibrate(t20_measured, t_target_oct, directional: bool = True) -> List[float]:
    """Directional keeps the seven measured factors. Room average holds through 500 Hz."""
    cal = calibration_factors(t20_measured, t_target_oct)
    if directional:
        return cal
    return hold_low_octaves(cal)


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


# Octave row the physical ceiling reports. 63 Hz absorption on an untreated
# card is the 125 Hz coefficient: card_alpha interpolates absorb_hz, and
# that table starts at 125.
PHYS_BANDS = np.array([63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0])
# 0.20 / 0.15 / 0.08 are textbook plasterboard, window, and floor values.
# Used here times BASS_S. Panel absorption is the structure, so k and the
# dial do not scale it. BASS_S is the one factor that puts boot (6, 3, 8)
# at dial 1.8 on T(125) / mid = 1.30. Mid is the mean of 500 Hz and 1 kHz.
BASS_HZ = np.array([63.0, 125.0, 250.0, 500.0])
BASS_KNOTS = np.array([0.20, 0.15, 0.08, 0.0])
BASS_S = 0.106194
ALPHA_MIN = 0.01
ALPHA_MAX = 0.99
_K_CACHE: "OrderedDict[tuple, Tuple[float, bool]]" = OrderedDict()
_K_CACHE_MAX = 512
_FP_BANDS = np.array([63.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0])


def bass_alpha(f) -> np.ndarray:
    """Log-interpolated membrane/panel alpha. Clamped below 63 Hz. 0 above 500."""
    f = np.asarray(f, float)
    x = np.clip(f, 63.0, 500.0)
    a = np.interp(np.log(x), np.log(BASS_HZ), BASS_KNOTS)
    return np.where(f > 500.0, 0.0, a)


def ceiling_card_copy(cards: Dict, k: float, s: float = BASS_S) -> Dict:
    """Copies. absorb_fn is clip(k * card_alpha, 0.01, 0.99) + s * bass.

    The caller's cards are not written. chamber_to_specular still runs inside
    face_bounce_db. bass is not a make_spec argument.
    """
    out = {}
    for key, card in cards.items():
        copied = dict(card)

        def fn(f, card=card, k=k, s=s):
            base = ST.card_alpha(card, f)
            return np.clip(float(k) * base, ALPHA_MIN, ALPHA_MAX) + float(s) * bass_alpha(f)

        copied["absorb_fn"] = fn
        out[key] = copied
    return out


def _cards_fingerprint(cards: Dict) -> str:
    """Sha1 of the fields room_target reads: alpha, diffusion, and face EQ.

    Treatment changes alpha through absorb_fn. A name-only change does not
    move k, so it does not move this key. Do not key on id(cards).
    """
    import hashlib
    parts = []
    for key in sorted(cards):
        card = cards[key]
        alpha = np.asarray(ST.card_alpha(card, _FP_BANDS), float)
        eq = card.get("eq") or {}
        eq_t = tuple(sorted(
            (str(k), float(v)) for k, v in eq.items() if isinstance(v, (int, float))
        ))
        diff = float(card.get("diffusion", ST.DEFAULT_SCATTER) or 0.0)
        parts.append((
            str(key),
            tuple(round(float(x), 8) for x in np.ravel(alpha)),
            round(diff, 8),
            eq_t,
        ))
    return hashlib.sha1(repr(parts).encode("utf-8")).hexdigest()


def _k_solve(W, H, L, cards, dial) -> Tuple[float, bool]:
    """70-step bisection. Returns hi, and whether one bound never moved.

    Same arithmetic as the historical boot solve: lo, hi = 1e-5, 4; if the
    mid is longer than the dial, raise lo, else lower hi; return hi.
    Humidity 0.35. Bass is 0 from 500 Hz up, so BASS_S does not move k.
    """
    lo, hi = 1.0e-5, 4.0
    target = float(dial)
    pinned_lo = True
    pinned_hi = True
    for _ in range(70):
        midk = 0.5 * (lo + hi)
        wrapped = ceiling_card_copy(cards, midk, BASS_S)
        Tm = float(np.mean(ST.room_target(
            float(W), float(H), float(L), wrapped, 0.35, np.array([500.0, 1000.0]),
        )))
        if Tm > target:
            lo = midk
            pinned_lo = False
        else:
            hi = midk
            pinned_hi = False
    return float(hi), bool(pinned_lo or pinned_hi)


def _k_cached(W, H, L, cards, dial) -> Tuple[float, bool]:
    """Cached (k, stuck-at-bound). 512 entries, least recently used."""
    key = (
        round(float(W), 6), round(float(H), 6), round(float(L), 6),
        _cards_fingerprint(cards), round(float(dial), 6),
    )
    hit = _K_CACHE.get(key)
    if hit is not None:
        _K_CACHE.move_to_end(key)
        return hit
    val, at_bound = _k_solve(W, H, L, cards, dial)
    _K_CACHE[key] = (val, at_bound)
    _K_CACHE.move_to_end(key)
    while len(_K_CACHE) > _K_CACHE_MAX:
        _K_CACHE.popitem(last=False)
    return val, at_bound


def k_for_room(W, H, L, cards, dial) -> float:
    """k for this room and these cards so the 500 Hz-1 kHz mean equals the dial.

    Unreachable dials still return the clamped k (a bound). phys_ceiling_row
    reports that with reachable False.
    """
    return _k_cached(W, H, L, cards, dial)[0]


def k_for_dial(dial: float) -> float:
    """Boot room only. (6, 3, 8), default cards, no treatment.

    Thin wrapper around k_for_room. The boot path is the same bisection as
    before, so the boot k floats stay bit-exact. Other rooms do not share it.
    """
    import surf_panels as _SP
    from surface_colour import default_surfaces
    base = _SP.cards_with_treatment(default_surfaces(), [])
    return k_for_room(6.0, 3.0, 8.0, base, dial)


def phys_ceiling_row(W, H, L, cards, dial, bands=None) -> dict:
    """This room's T_phys(f; k). Shared by the pack and /api/phys_preview.

    No min(dial, ...). k is solved on this room and these cards. The returned
    cards are copies. reachable is false when the bisection sticks to a bound
    or the reached mid is more than 8 percent off the dial (T60_TOL). The
    clamped k is still returned.
    """
    f = PHYS_BANDS if bands is None else np.asarray(bands, float)
    k, at_bound = _k_cached(float(W), float(H), float(L), cards, float(dial))
    wrapped = ceiling_card_copy(cards, k, BASS_S)
    T = np.asarray(ST.room_target(float(W), float(H), float(L), wrapped, 0.35, f), float)
    mid = float(np.mean(ST.room_target(
        float(W), float(H), float(L), wrapped, 0.35, np.array([500.0, 1000.0]),
    )))
    rel = abs(mid - float(dial)) / max(abs(float(dial)), 1e-12)
    reachable = (not at_bound) and rel <= 0.08
    return {
        "k": k, "s": BASS_S, "t": T, "mid": mid, "cards": wrapped,
        "hz": np.asarray(f, float), "reachable": bool(reachable), "reached_mid": mid,
    }


def phys_teff_bands(W, H, L, cards, dial, bands=None) -> np.ndarray:
    """T_eff(f) = T_phys(f; k). Humidity 0.35, air on, arau_scatter, c 343.

    The dial chooses k. It does not cap a band.
    """
    return phys_ceiling_row(W, H, L, cards, dial, bands)["t"]


def phys_ceiling_pack(W, H, L, cards, dial, enabled, surfaces_on, humidity,
                      directional=False, cal=None) -> Optional[dict]:
    """Section spec, or None when the ceiling is off or the lock is not armed.

    Does not replace line_t60. One cascade: the greater of the Surfaces rate
    and 60/T_eff, or 60/T_eff alone when Surfaces is off. The ceiling path
    passes no dial anchor into make_spec. Flat keeps every axial peak
    (keep cut above the band). Surfaces keeps the D-SL3 30 Hz cut.
    Coefficients are designed by the caller, not here.
    """
    if not enabled or dial is None or float(dial) <= 0.05:
        return None
    dial_f = float(dial)
    state = phys_ceiling_row(W, H, L, cards, dial_f, PHYS_BANDS)
    Teff = state["t"]
    loss = 60.0 / np.maximum(Teff, 1e-4)
    logb = np.log(PHYS_BANDS)

    def row_at(f, loss=loss, logb=logb):
        return np.interp(np.log(np.asarray(f, float)), logb, loss)

    ceiling_hz = [float(x) for x in PHYS_BANDS]
    ceiling_t = [round(float(x), 4) for x in Teff]
    if surfaces_on:
        spec = make_spec(
            W, H, L, state["cards"], humidity, None,
            directional=bool(directional), cal=cal,
        )
        base = spec["rates_for"]

        def rates_for(delays, sr, hits, base=base, row_at=row_at):
            got = np.asarray(base(delays, sr, hits), float)
            return np.maximum(got, row_at(FIT_F))

        spec["rates_for"] = rates_for
        spec["ceiling_hz"] = ceiling_hz
        spec["ceiling_t"] = ceiling_t
        spec["k"] = state["k"]
        spec["phys_ceiling"] = True
        return spec

    def rates_for(delays, sr, hits, row_at=row_at):
        return np.tile(row_at(FIT_F), (len(delays), 1))

    return dict(
        rates_for=rates_for,
        struct="S1P2",
        keep_cut_below_hz=1.0e9,
        target_T_oct=ceiling_t,
        directional=False,
        report=[],
        ceiling_hz=ceiling_hz,
        ceiling_t=ceiling_t,
        k=state["k"],
        phys_ceiling=True,
    )
