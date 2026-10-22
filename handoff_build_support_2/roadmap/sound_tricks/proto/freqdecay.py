"""Target T(f)/T_mid for sound_tricks P1. Eyring + ISO 9613-1 air, dial anchors the mid (500 Hz-1 kHz)."""
import math, numpy as np
import fdn as F
from air_iso import _iso_alpha_db_per_m, climate_record, rh_pct_from_slider
BANDS = np.array([125, 250, 500, 1000, 2000, 4000, 8000], float)

def air_m(f, humidity, climate="studio_20C_50RH"):
    rh = rh_pct_from_slider(humidity, climate)
    if rh is None:
        return np.zeros_like(np.asarray(f, float))
    c = climate_record(climate)["conditions"]
    a_db = _iso_alpha_db_per_m(f, c["temperature_c"], rh, c.get("pressure_kpa", 101.325))
    return a_db / (10.0 * math.log10(math.e))     # energy attenuation, 1/m

def ratio_fn(W, H, L, t_dial, humidity, surfaces=None, mode="air+materials", climate="studio_20C_50RH"):
    V = W * H * L
    S = {"A": L * H, "C": L * H, "B": W * H, "D": W * H, "E": W * L, "F": W * L}
    St = sum(S.values())
    def abar(f):
        if mode == "air" or not surfaces:
            return np.full_like(f, 0.1)
        a = np.zeros_like(f)
        for k, s in S.items():
            ab = np.asarray(surfaces[k]["absorb"], float)
            a += s * np.interp(np.log(f), np.log(BANDS), ab)
        return a / St
    fm = np.array([500.0, 1000.0])
    def T_of(f, k):
        f = np.asarray(f, float)
        A = k * (-St * np.log(1 - abar(f))) + 4 * air_m(f, humidity, climate) * V
        return 0.161 * V / A
    # scale the surface absorption so the mid T equals the dial; air stays absolute
    Amid_needed = 0.161 * V / t_dial
    Amat_mid = float(np.mean(-St * np.log(1 - abar(fm))))
    Aair_mid = float(np.mean(4 * air_m(fm, humidity, climate) * V))
    k = max(1e-6, (Amid_needed - Aair_mid) / Amat_mid)
    def ratio(f):
        r = T_of(f, k) / t_dial
        if mode.endswith("_clamped"):   # real rooms rarely hold bass >1.25x mid (panel/membrane LF absorption)
            r = np.clip(r, 0.0, 1.25)
        return r
    return ratio, k

def enable(W, H, L, t_dial, humidity, surfaces, mode):
    r, k = ratio_fn(W, H, L, t_dial, humidity, surfaces, mode)
    F.FREQ_DECAY = {"ratio": r, "report": [], "mode": mode, "k": k}
    return r
