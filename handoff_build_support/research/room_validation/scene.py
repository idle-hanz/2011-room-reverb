"""Map BRAS CR2 onto the 2011 Room Reverb shoebox (Render path parameters).
Geometry = ESTIMATED shoebox (see geometry_fit.json / VALIDATION_REPORT.md section 2)."""
import json, os
import numpy as np
import bras_cr2 as B

HERE = os.path.dirname(os.path.abspath(__file__))
# Adopted box in the BRAS frame (metres). x/y planes from the matched-filter arrival fit (1-8 kHz);
# floor z=0 (BRAS frame, VERIFIED origin on the floor); ceiling chosen so W*L*H = 145 m^3 (BRAS volume),
# which lies inside the 2.86-2.99 m range of ceiling vertices seen in CR2.skp (ESTIMATED).
X0, X1 = -2.985, 2.890
Y0, Y1 = -4.030, 4.640
Z1 = round(B.VOLUME_M3 / ((X1 - X0) * (Y1 - Y0)), 3)
W, L, H = X1 - X0, Y1 - Y0, Z1


def to_model(ls, mp):
    """Model frame: x = width (0..W), y = height, z = length (0..L). The Reaktor image table (LIVE_32)
    has no -Z images, i.e. no reflection from the wall at model z=0, and assumes the source is ahead (+z) of
    the mic. So z is flipped for LS1 (source at low BRAS y) and not for LS2 (source at high BRAS y)."""
    s, r = B.SOURCES[ls], B.RECEIVERS[mp]
    flip = s[1] < r[1]
    fz = (lambda y: Y1 - y) if flip else (lambda y: y - Y0)
    return dict(sx=s[0] - X0, sy=s[2], sz=fz(s[1]), mcx=r[0] - X0, my=r[2], mcz=fz(r[1]), flip=flip,
                back_wall_bras=("y1=%.2f" % Y1) if flip else ("y0=%.2f" % Y0))


def interp_alpha(name, bands=(125, 250, 500, 1000, 2000, 4000, 8000)):
    f, a, s = B.load_material(name)
    return [float(np.interp(np.log(b), np.log(f), a)) for b in bands]


def surfaces(flip):
    """ASSUMED material layout (CR2.skp material names VERIFIED: ceiling, concrete, floor, plaster, windows;
    which wall carries which is not parsed from the .skp). Walls: plaster; the window wall (+x side,
    per the Geometry png, ESTIMATED) = 50 % windows + 50 % plaster; front/back walls = 50 % concrete + 50 % plaster."""
    pl, co, wi = interp_alpha("plaster"), interp_alpha("concrete"), interp_alpha("windows")
    mix = lambda a, b: [0.5 * (u + v) for u, v in zip(a, b)]
    card = lambda a: {"absorb": [round(v, 4) for v in a], "diffusion": 0.15}
    return {"A": card(pl), "C": card(mix(wi, pl)), "B": card(mix(co, pl)), "D": card(mix(co, pl)),
            "E": card(interp_alpha("floor")), "F": card(interp_alpha("ceiling"))}


def eyring_t60(bands=(125, 250, 500, 1000, 2000, 4000, 8000)):
    """Eyring T60 of the adopted box with the ASSUMED layout, incl. air attenuation (ISO 9613-1, via
    python-free approximation below). Returns dict band -> seconds."""
    S = {"A": L * H, "C": L * H, "B": W * H, "D": W * H, "E": W * L, "F": W * L}
    surf = surfaces(False)
    V = W * L * H
    out = {}
    for i, b in enumerate(bands):
        St = sum(S.values())
        abar = sum(S[k] * surf[k]["absorb"][i] for k in S) / St
        m = air_m(b)  # intensity attenuation coefficient, 1/m
        out[b] = 0.161 * V / (-St * np.log(1 - abar) + 4 * m * V)
    return out


def air_m(f, T=B.TEMP_C, hr=B.HUMIDITY_PCT, pa=101.325):
    """ISO 9613-1 pure-tone air absorption -> energy attenuation m (1/m)."""
    T0, T01, pr = 293.15, 273.16, 101.325
    Tk = T + 273.15
    psat = pr * 10 ** (-6.8346 * (T01 / Tk) ** 1.261 + 4.6151)
    h = hr * psat / pa
    frO = pa / pr * (24 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    frN = pa / pr * (Tk / T0) ** -0.5 * (9 + 280 * h * np.exp(-4.170 * ((Tk / T0) ** (-1 / 3) - 1)))
    alpha = 8.686 * f ** 2 * (1.84e-11 * (pr / pa) * (Tk / T0) ** 0.5 + (Tk / T0) ** -2.5 * (
        0.01275 * np.exp(-2239.1 / Tk) / (frO + f ** 2 / frO) + 0.1068 * np.exp(-3352.0 / Tk) / (frN + f ** 2 / frN)))
    return alpha / (10 * np.log10(np.e))  # dB/m -> Np/m (energy)


def body(ls, mp, decay_s, humidity=0.35):
    m = to_model(ls, mp)
    return {"W": W, "H": H, "L": L, "sx": m["sx"], "sy": m["sy"], "sz": m["sz"], "mcx": m["mcx"], "my": m["my"],
            "mcz": m["mcz"], "space": 0.0, "pattern_l": "omni", "pattern_c": "omni", "pattern_r": "omni",
            "colour_mode": "BYPASS", "mic_gain_l": 0.0, "mic_gain_r": 0.0, "mic_gain_c": 1.0, "mic_pan_c": 0.0,
            "early_wet": 0.0, "fdn_wet": 1.0, "direct_wet": 1.0, "dry_gain": 0.0, "fdn_g": 1.0,
            "decay_lock": bool(decay_s > 0), "decay_s": float(decay_s), "humidity": humidity, "air_lp": 0.25, "air_shelf": 1.0,
            "surfaces": surfaces(m["flip"]), "hadamard_n": 32}
