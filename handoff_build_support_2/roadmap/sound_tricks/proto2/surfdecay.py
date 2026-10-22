"""SURFACES IN THE LOOP (box prototype). Per-band decay targets from the Surfaces table.

Room-average target (one T(f) for the room) and a directional per-line target (each FDN line's
loss comes from the faces its own image path hits). See SURFACES_IN_LOOP.md.
"""
import math, sys, os
import numpy as np
sys.path.insert(0, "/workspace/st_work/software"); sys.path.insert(0, "/workspace/st_work/software/engine")
import surface_colour as SC
from air_iso import _iso_alpha_db_per_m, climate_record, rh_pct_from_slider
from early_field import LIVE_32

BANDS = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)
C_AIR = 343.0
AX = {"x": ("A", "C"), "y": ("E", "F"), "z": ("B", "D")}

def face_areas(W, H, L):
    return {"A": L * H, "C": L * H, "B": W * H, "D": W * H, "E": W * L, "F": W * L}

def air_db_per_m(f, humidity, climate="studio_20C_50RH", T=None, RH=None):
    c = climate_record(climate)["conditions"]
    rh = RH if RH is not None else rh_pct_from_slider(humidity, climate)
    if rh is None:
        return np.zeros_like(np.asarray(f, float))
    return _iso_alpha_db_per_m(f, c["temperature_c"] if T is None else T, rh, c.get("pressure_kpa", 101.325))

def chamber_to_specular(alpha):
    """Reverberation-chamber (Sabine) alpha -> alpha for an Eyring / per-bounce model.
    alpha_E = 1 - exp(-alpha_S): makes Eyring give back the Sabine result the data were measured with
    (Kuttruff, Room Acoustics, sec. on Sabine vs Eyring absorption; ASSUMED reference). Caps >1 values."""
    return 1.0 - np.exp(-np.clip(np.asarray(alpha, float), 0.0, 1.5))

def face_bounce_db(card, f, sr=48000, convert=True, eq_in_loop=True):
    """Energy-consistent per-bounce reflection gain, dB (<= 0): absorption plus the face EQ (cuts only)."""
    if card.get("absorb_fn") is not None:
        a_f = np.asarray(card["absorb_fn"](f), float)
    else:
        hz = np.asarray(card.get("absorb_hz") or BANDS, float)
        a_f = np.interp(np.log(f), np.log(hz), np.asarray(card.get("absorb"), float))
    if convert:
        a_f = chamber_to_specular(a_f)
    r_db = 10 * np.log10(np.maximum(1 - a_f, 1e-4))
    if eq_in_loop:
        eq = card.get("eq") or {}
        st = []
        if abs(eq.get("low_shelf_db", 0)) >= .05: st.append(SC.rbj_lowshelf(sr, float(eq.get("low_shelf_hz", 200)), float(eq["low_shelf_db"])))
        if abs(eq.get("peak_db", 0)) >= .05: st.append(SC.rbj_peaking(sr, float(eq.get("peak_hz", 1000)), float(eq.get("peak_q", 1)), float(eq["peak_db"])))
        if abs(eq.get("high_shelf_db", 0)) >= .05: st.append(SC.rbj_highshelf(sr, float(eq.get("high_shelf_hz", 5000)), float(eq["high_shelf_db"])))
        for bq in st:
            b0, b1, b2, a0, a1, a2 = bq
            z = np.exp(-1j * 2 * np.pi * f / sr)
            r_db = r_db + 20 * np.log10(np.abs((b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)))
    return np.minimum(r_db, 0.0)   # no boosts inside the loop: energy can only be lost (keeps the loop stable)

def scatter_mean(surfaces, S):
    St = sum(S.values())
    return sum(S[k] * float(surfaces[k].get("diffusion", 0.15)) for k in S) / St

def room_target(W, H, L, surfaces, humidity, f, model="arau_scatter", convert=True, air=None):
    """Room-average T(f), seconds. model: eyring | arau | arau_scatter (log blend by mean scattering)."""
    V = W * H * L; S = face_areas(W, H, L); St = sum(S.values())
    m = (air if air is not None else air_db_per_m(f, humidity)) / (10 * math.log10(math.e))   # energy, 1/m
    a = {k: 1 - 10 ** (face_bounce_db(surfaces[k], f, convert=convert) / 10) for k in S}
    abar = sum(S[k] * a[k] for k in S) / St
    TE = 0.161 * V / (-St * np.log(1 - abar) + 4 * m * V)
    if model == "eyring":
        return TE
    lnTA = 0.0
    for ax, (p, q) in AX.items():
        Sx = S[p] + S[q]; ax_a = (S[p] * a[p] + S[q] * a[q]) / Sx
        Tx = 0.161 * V / (-St * np.log(1 - ax_a) + 4 * m * V)
        lnTA = lnTA + (Sx / St) * np.log(Tx)
    if model == "arau":
        return np.exp(lnTA)
    s = scatter_mean(surfaces, S)
    return np.exp(s * np.log(TE) + (1 - s) * lnTA)

def line_hits(n_lines=32):
    return [SC.surfaces_hit_by_n(LIVE_32[i % len(LIVE_32)]) for i in range(n_lines)]

S_MIN = float(__import__("os").environ.get("SL_SMIN", "0.5"))   # floor on the scattered share (late-field mixing), ASSUMED

def line_rates(delays, sr, W, H, L, surfaces, humidity, f, directional, model="arau_scatter", convert=True,
               t_anchor=None, s_min=None):
    """Per-line decay rate, dB/s (positive = loss), shape (n, len(f)).
    Room-average: every line gets 60/T(f) (homogeneous, Jot). Directional: specular share (1-s) of the
    surface loss follows the line's own hit list and path length, normalised so the delay-weighted mean
    equals the room target (so the overall T(f) still matches); the scattered share s stays room-average.
    t_anchor: if set, scale so the 500 Hz-1 kHz mean T equals the dial (Decay lock on)."""
    tau = np.asarray(delays, float) / sr
    air = air_db_per_m(f, humidity)
    T = room_target(W, H, L, surfaces, humidity, f, model, convert, air)
    if t_anchor:
        fm = np.array([500.0, 1000.0])
        Tm = float(np.mean(room_target(W, H, L, surfaces, humidity, fm, model, convert)))
        T = T * (t_anchor / Tm)
    G = 60.0 / T                                   # room dB/s
    Gair = air * C_AIR                              # dB/s from air (same for every line: loss per metre)
    Gs = np.maximum(G - Gair, 0.0)                  # surface share
    n = len(tau)
    if not directional:
        return np.tile(G, (n, 1)), T
    S = face_areas(W, H, L)
    s = max(scatter_mean(surfaces, S), S_MIN if s_min is None else s_min)
    fdb = {k: -face_bounce_db(surfaces[k], f, convert=convert) for k in S}   # loss per hit, dB
    hits = line_hits(n)
    raw = np.zeros((n, len(f)))
    for i in range(n):
        path = max(tau[i] * C_AIR, 0.5)
        for k in hits[i]:
            raw[i] += fdb[k] * C_AIR / path           # dB/s if the line kept its own geometry
    mean_raw = (tau[:, None] * raw).sum(0) / tau.sum()
    kappa = np.where(mean_raw > 1e-9, Gs / np.maximum(mean_raw, 1e-9), 0.0)
    Gdir = kappa[None, :] * raw
    rates = Gair[None, :] + s * Gs[None, :] + (1 - s) * Gdir
    return rates, T
